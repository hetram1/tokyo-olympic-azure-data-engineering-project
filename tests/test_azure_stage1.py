from copy import deepcopy
import io
import json
import unittest
from unittest.mock import patch

from scripts.azure_stage1 import (SUB, PRINCIPAL, ROLE, SCOPE, FACTORY_ID,
    require_identity, check_template, expected_subset, resolved, main)
from src.azure.contracts import CONTRACT_PATH
from src.azure.adf import template


class AzureStage1Tests(unittest.TestCase):
    def test_exact_identity_role_and_scope_required(self):
        account = {'id': SUB, 'name': 'Azure for Students', 'state': 'Enabled'}
        factory = {'id': FACTORY_ID, 'identity': {'type': 'SystemAssigned', 'principalId': PRINCIPAL}}
        role = {'principalId': PRINCIPAL, 'scope': SCOPE,
                'roleDefinitionId': '/providers/Microsoft.Authorization/roleDefinitions/' + ROLE, 'condition': None}
        require_identity(factory, account, [])
        require_identity(factory, account, [role])
        for key, value in [('principalId', 'other'), ('scope', '/subscriptions/' + SUB),
                           ('roleDefinitionId', 'other'), ('condition', 'unreviewed')]:
            bad = dict(role); bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                require_identity(factory, account, [bad])
        bad = deepcopy(factory); bad['identity']['principalId'] = 'other'
        with self.assertRaises(ValueError):require_identity(bad, account, [])
        with self.assertRaises(ValueError):require_identity(factory, dict(account, id='other'), [])

    def test_template_allowlist_rejects_any_added_resource_or_change(self):
        contract = json.loads(CONTRACT_PATH.read_text())
        value = template(contract)
        check_template(contract, value)
        bad = deepcopy(value); bad['resources'].append({'type': 'Microsoft.Databricks/workspaces'})
        with self.assertRaises(ValueError):check_template(contract, bad)
        bad = deepcopy(value); bad['resources'][1]['properties']['typeProperties']['location']['folderPath'] = 'raw'
        with self.assertRaises(ValueError):check_template(contract, bad)

    def test_readback_accepts_service_defaults_but_not_altered_definition(self):
        expected = {'type': 'Binary', 'parameters': {'runId': {'type': 'String', 'defaultValue': ''}}}
        expected_subset(dict(expected, serviceDefault=[]), expected)
        with self.assertRaises(ValueError):expected_subset({'type': 'DelimitedText'}, expected)
        self.assertEqual(resolved({'fileSystem': "[parameters('container')]"}),
                         {'fileSystem': 'tokyo-olympic-data'})

    def test_default_cli_is_read_only(self):
        with patch('sys.argv', ['azure_stage1']), patch('scripts.azure_stage1.inspect', return_value={'mode':'preview'}) as inspect, \
             patch('scripts.azure_stage1.apply_stage1') as apply, patch('sys.stdout', new_callable=io.StringIO):
            main()
        inspect.assert_called_once()
        apply.assert_not_called()


if __name__ == '__main__':
    unittest.main()
