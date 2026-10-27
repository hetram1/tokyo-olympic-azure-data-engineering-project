import ast
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from src.azure.adf import template, orchestration_template
from src.azure.contracts import (ROOT, CONTRACT_PATH, build_contract, load_pinned_sources,
                                 assert_parity, digest, verify_export)
from src.azure.inventory import inventory


class AzureContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT_PATH.read_text())

    def test_pins_match_source_and_reference_bytes(self):
        self.assertEqual(build_contract(), self.contract)
        contents = {n: (ROOT / 'data' / spec['file']).read_bytes()
                    for n, spec in self.contract['inputs'].items()}
        prepared, report = load_pinned_sources(contents, self.contract)
        self.assertTrue(report['valid'])
        self.assertEqual(len(prepared['Athletes']), 11084)
        self.assertEqual(len(prepared['Coaches']), 393)
        self.assertEqual(prepared['Medals'].Total.sum(), 1080)
        self.assertEqual(self.contract['inputs']['Athletes']['encoding'], 'ISO-8859-1')

    def test_source_tampering_fails_before_transform(self):
        contents = {n: (ROOT / 'data' / spec['file']).read_bytes()
                    for n, spec in self.contract['inputs'].items()}
        contents['Teams'] += b'\n'
        with self.assertRaisesRegex(ValueError, 'checksum'):
            load_pinned_sources(contents, self.contract)

    def test_ingestion_is_binary_run_specific_and_secret_free(self):
        value = template(self.contract)
        deployed = json.loads((ROOT / 'infra/azure/adf_ingestion.arm.json').read_text())
        self.assertEqual(deployed, value)
        self.assertEqual(len(value['resources']), 4)
        ls, source, sink, pipeline = value['resources']
        self.assertEqual(ls['properties']['type'], 'AzureBlobFS')
        self.assertEqual(set(ls['properties']['typeProperties']), {'url'})
        self.assertEqual(source['properties']['type'], 'Binary')
        self.assertEqual(source['properties']['typeProperties']['location']['folderPath'],
                         'staging/' + self.contract['dataset_version'])
        self.assertEqual(sink['properties']['typeProperties']['location']['folderPath']['value'],
                         "@concat('raw/adf/', dataset().runId)")
        foreach = pipeline['properties']['activities'][0]
        self.assertTrue(foreach['typeProperties']['isSequential'])
        copy = foreach['typeProperties']['activities'][0]
        self.assertEqual(copy['typeProperties']['source']['type'], 'BinarySource')
        self.assertEqual(copy['typeProperties']['sink']['type'], 'BinarySink')
        self.assertEqual(copy['outputs'][0]['parameters']['runId']['value'], '@pipeline().RunId')
        self.assertEqual(copy['policy']['retry'], 0)
        self.assertNotIn('triggers', json.dumps(value))

    def test_orchestration_waits_for_copy_and_never_creates_compute(self):
        value = orchestration_template()
        self.assertEqual(value, json.loads((ROOT / 'infra/azure/adf_orchestration.arm.json').read_text()))
        ls, pipeline = value['resources']
        self.assertEqual(ls['properties']['typeProperties']['authentication'], 'MSI')
        self.assertNotIn('existingClusterId', ls['properties']['typeProperties'])
        self.assertNotIn('newClusterNodeType', json.dumps(value))
        ingest, transform = pipeline['properties']['activities']
        self.assertTrue(ingest['typeProperties']['waitOnCompletion'])
        self.assertEqual(transform['dependsOn'][0]['dependencyConditions'], ['Succeeded'])
        self.assertEqual(transform['type'], 'DatabricksJob')
        self.assertEqual(transform['typeProperties']['jobId'], "[parameters('jobId')]")
        self.assertEqual(transform['typeProperties']['jobParameters']['raw_run_id']['value'],
                         "@activity('Ingest').output.pipelineRunId")

    def test_parity_tolerates_order_but_rejects_keys_schema_and_changed_values(self):
        expected = pd.DataFrame({'country': ['A', 'B'], 'count': [1, 2]})
        assert_parity(expected.iloc[::-1], expected)
        for bad in [expected.rename(columns={'count': 'counts'}),
                    pd.DataFrame({'country': ['A', 'A'], 'count': [1, 2]}),
                    pd.DataFrame({'country': ['A', 'B'], 'count': [1, 3]})]:
            with self.assertRaises((ValueError, AssertionError)):
                assert_parity(bad, expected)

    def test_export_requires_success_checksums_and_reference_parity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            manifest = {'status': 'validated', 'dataset_version': self.contract['dataset_version'],
                        'run_id': '00000000-0000-0000-0000-000000000001',
                        'raw_run_id': '00000000-0000-0000-0000-000000000002',
                        'code_sha256': self.contract['code_sha256'],
                        'input_sha256': {n: s['sha256'] for n, s in self.contract['inputs'].items()}, 'outputs': {}}
            for name, spec in self.contract['outputs'].items():
                raw = (ROOT / spec['reference']).read_bytes()
                (path / name).write_bytes(raw)
                manifest['outputs'][name] = {'sha256': digest(raw), 'rows': spec['rows'], 'columns': spec['columns']}
            (path / 'manifest.json').write_text(json.dumps(manifest))
            self.assertTrue(verify_export(path, self.contract)['valid'])
            manifest['status'] = 'failed'; (path / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'successful-run'):
                verify_export(path, self.contract)
            manifest['status'] = 'validated'; (path / 'manifest.json').write_text(json.dumps(manifest))
            (path / 'country_features.csv').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                verify_export(path, self.contract)

    def test_inventory_requires_explicit_subscription_and_cli(self):
        with self.assertRaises(ValueError):
            inventory('not-a-subscription')
        with patch('shutil.which', return_value=None), self.assertRaisesRegex(RuntimeError, 'CLI missing'):
            inventory('00000000-0000-0000-0000-000000000000')

    def test_inventory_never_requests_keys_tokens_or_changes(self):
        calls = []
        def fake_run(args, **kwargs):
            calls.append(args)
            value = {'id': '00000000-0000-0000-0000-000000000000', 'name': 'Azure for Students'}
            if args[1:3] != ['account', 'show']:
                value = None
            return subprocess.CompletedProcess(args, 0, json.dumps(value), '')
        with patch('shutil.which', return_value='/usr/bin/az'), patch('subprocess.run', side_effect=fake_run):
            result = inventory('00000000-0000-0000-0000-000000000000')
        commands = json.dumps(calls)
        for forbidden in ['listKeys', 'get-access-token', 'login', 'create', 'register', 'deployment']:
            if forbidden == 'login':
                continue  # --auth-mode login is data-plane Entra auth, not an interactive login command.
            self.assertNotIn(forbidden, commands)
        self.assertFalse(result['cloud_execution_verified'])
        self.assertTrue(all(c[1] in ['account', 'group', 'rest', 'storage', 'provider', 'resource', 'role'] for c in calls))

    def test_notebook_parses_without_execution_and_uses_no_mounts(self):
        source = (ROOT / 'databricks/tokyo_transform.py').read_text()
        ast.parse(source)
        self.assertNotIn('dbutils.fs.mount(', source)
        self.assertNotIn('overwrite=True', source)
        self.assertIn('verify_reference_parity(outputs, references)', source)
        self.assertIn("'/manifest.json'", source)

    def test_credit_query_uses_only_the_selected_subscriptions_profile(self):
        calls = []
        profile = '/providers/Microsoft.Billing/billingAccounts/test-account/billingProfiles/test-profile'
        def fake_run(args, **kwargs):
            calls.append(args)
            value = None
            if args[1:3] == ['account', 'show']:
                value = {'id': '00000000-0000-0000-0000-000000000000', 'name': 'Azure for Students'}
            elif any('billingProperty/default' in item for item in args):
                value = {'billingProfileId': profile}
            elif any('credits/balanceSummary' in item for item in args):
                value = {'balanceSummary': {'currentBalance': {'currency': 'USD', 'value': 100}}}
            return subprocess.CompletedProcess(args, 0, json.dumps(value), '')
        with patch('shutil.which', return_value='/usr/bin/az'), patch('subprocess.run', side_effect=fake_run):
            result = inventory('00000000-0000-0000-0000-000000000000')
        self.assertEqual(result['checks']['billing_profile_credit_summary']['value']['balanceSummary']['currentBalance']['value'], 100)
        credit_calls = [c for c in calls if any('credits/balanceSummary' in arg for arg in c)]
        self.assertEqual(len(credit_calls), 1)
        self.assertIn('https://management.azure.com' + profile +
                      '/providers/Microsoft.Consumption/credits/balanceSummary?api-version=2024-08-01', credit_calls[0])

    def test_inventory_failure_codes_and_timeouts_do_not_leak_stderr(self):
        def fake_run(args, **kwargs):
            if args[1:3] == ['account', 'show']:
                return subprocess.CompletedProcess(args, 0, json.dumps({
                    'id': '00000000-0000-0000-0000-000000000000', 'name': 'Azure for Students'}), '')
            if args[1:3] == ['group', 'show']:
                raise subprocess.TimeoutExpired(args, 120)
            return subprocess.CompletedProcess(args, 1, '', 'PathNotFound: private diagnostic detail')
        with patch('shutil.which', return_value='/usr/bin/az'), patch('subprocess.run', side_effect=fake_run):
            result = inventory('00000000-0000-0000-0000-000000000000')
        self.assertNotIn('private diagnostic detail', json.dumps(result))
        self.assertEqual(result['checks']['resource_group']['reason'], 'Read-only query timed out')
        self.assertEqual(result['checks']['acl_staging']['error_code'], 'PathNotFound')


if __name__ == '__main__':
    unittest.main()
