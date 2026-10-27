"""Stage 1 only: exact ADF identity/container grant, new source blobs, ingestion ARM.

Default is read-only inspect. --apply requires prior explicit user authorization.
Never invokes createRun, debug, compute, provider registration, keys or ACL changes.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from uuid import NAMESPACE_URL, uuid5

from src.azure.adf import template
from src.azure.contracts import CONTRACT_PATH, ROOT, build_contract, digest

SUB = 'b52df7c6-044d-4326-92c8-496670def7c1'
GROUP = 'rg-tokyo-olympics'
FACTORY = 'adf-tokyo-olympics-hetram-2026'
STORAGE = 'tokyoolympicdatahetram'
CONTAINER = 'tokyo-olympic-data'
PRINCIPAL = '2b14c4a6-9415-4738-b6a6-a8b671d97d6f'
ROLE = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
BASE = f'/subscriptions/{SUB}/resourceGroups/{GROUP}'
FACTORY_ID = BASE + '/providers/Microsoft.DataFactory/factories/' + FACTORY
STORAGE_ID = BASE + '/providers/Microsoft.Storage/storageAccounts/' + STORAGE
SCOPE = STORAGE_ID + '/blobServices/default/containers/' + CONTAINER
ARM = 'https://management.azure.com'
KINDS = {'linkedservices': ['ls_tokyo_adls_mi'],
         'datasets': ['ds_tokyo_staged_binary', 'ds_tokyo_raw_binary'],
         'pipelines': ['pl_tokyo_ingest']}
EVIDENCE_DIR = ROOT / 'docs/azure/stage1'
ENV = dict(os.environ, AZURE_EXTENSION_USE_DYNAMIC_INSTALL='no', AZURE_CORE_COLLECT_TELEMETRY='false')


def az(args, timeout=180):
    result = subprocess.run(['az', *args, '--only-show-errors', '--output', 'json'],
                            capture_output=True, text=True, env=ENV, timeout=timeout)
    if result.returncode:
        code = next((x for x in ['AuthorizationPermissionMismatch', 'AuthorizationFailed',
             'RoleAssignmentExists', 'InvalidTemplateDeployment', 'BlobAlreadyExists',
             'ConditionNotMet', 'PathNotFound'] if x in result.stderr), 'AzureCommandFailed')
        raise RuntimeError(f'{args[0]} operation failed: {code}; stopped, no credential fallback')
    return json.loads(result.stdout) if result.stdout.strip() else None


def rest(path, query=None):
    args = ['rest', '--method', 'get', '--url', ARM + path]
    if query:
        args += ['--query', query]
    return az(args)


def require_identity(factory, account, roles):
    if (account.get('id', '').lower() != SUB or account.get('name') != 'Azure for Students'
            or account.get('state') != 'Enabled'):
        raise ValueError('Subscription differs from authorization')
    if (factory['id'].lower() != FACTORY_ID.lower()
            or factory['identity']['type'] != 'SystemAssigned'
            or factory['identity']['principalId'].lower() != PRINCIPAL):
        raise ValueError('ADF identity differs from authorization')
    for role in roles:
        if (role['principalId'].lower() != PRINCIPAL or role['scope'].lower() != SCOPE.lower()
                or role['roleDefinitionId'].split('/')[-1].lower() != ROLE or role.get('condition')):
            raise ValueError('Existing role identity/scope/definition differs from reviewed plan')


def check_template(contract, value):
    if value != template(contract):
        raise ValueError('Prepared ingestion template differs from reviewed renderer')
    expected = {('Microsoft.DataFactory/factories/' + kind, name)
                for kind, names in KINDS.items() for name in names}
    actual = {(r['type'], r['name'].split("'/")[-1].split("'")[0]) for r in value['resources']}
    if actual != expected:
        raise ValueError('Template contains unexpected resources')


def list_definitions():
    return {kind: rest(FACTORY_ID + '/' + kind + '?api-version=2018-06-01', 'value[].name')
            for kind in [*KINDS, 'triggers']}


def inspect():
    contract = json.loads(CONTRACT_PATH.read_text())
    if build_contract() != contract:
        raise ValueError('Pinned sources/reference/code contract differs; review required')
    value = json.loads((ROOT / 'infra/azure/adf_ingestion.arm.json').read_text())
    check_template(contract, value)
    account = az(['account', 'show', '--query', '{id:id,name:name,state:state}'])
    factory = rest(FACTORY_ID + '?api-version=2018-06-01',
                   '{id:id,identity:identity,location:location,publicNetworkAccess:properties.publicNetworkAccess}')
    roles = az(['role', 'assignment', 'list', '--assignee-object-id', PRINCIPAL,
        '--scope', SCOPE, '--include-inherited', '--subscription', SUB, '--query',
        '[].{id:id,principalId:principalId,roleDefinitionId:roleDefinitionId,scope:scope,condition:condition}'])
    require_identity(factory, account, roles)
    storage = az(['storage', 'account', 'show', '-g', GROUP, '-n', STORAGE, '--subscription', SUB,
        '--query', '{id:id,isHnsEnabled:isHnsEnabled,location:location,networkRuleSet:networkRuleSet,publicNetworkAccess:publicNetworkAccess,allowSharedKeyAccess:allowSharedKeyAccess}'])
    if storage['id'].lower() != STORAGE_ID.lower() or storage['isHnsEnabled'] is not True:
        raise ValueError('Storage resource differs from authorization')
    container = az(['storage', 'container', 'show', '-n', CONTAINER, '--account-name', STORAGE,
        '--auth-mode', 'login', '--subscription', SUB, '--query', '{name:name,publicAccess:properties.publicAccess}'])
    if container['name'] != CONTAINER or container['publicAccess'] is not None:
        raise ValueError('Container differs from reviewed plan')
    definitions = list_definitions()
    if any(definitions.values()):
        raise ValueError('Unexpected existing ADF objects; refusing to overwrite')
    prefix = 'staging/' + contract['dataset_version'] + '/'
    existing = az(['storage', 'blob', 'list', '-c', CONTAINER, '--prefix', prefix,
        '--account-name', STORAGE, '--auth-mode', 'login', '--subscription', SUB, '--query', '[].name'])
    if existing:
        raise ValueError('Staging destination not empty; refusing to overwrite')
    role_definition = az(['role', 'definition', 'list', '--name', ROLE, '--subscription', SUB,
        '--query', '[].{id:id,roleName:roleName,roleType:roleType}'])
    if (len(role_definition) != 1 or role_definition[0]['id'].split('/')[-1].lower() != ROLE
            or role_definition[0]['roleName'] != 'Storage Blob Data Contributor'
            or role_definition[0]['roleType'] != 'BuiltInRole'):
        raise ValueError('Required role differs from authorization')
    return {'subscription': account, 'factory_id': FACTORY_ID, 'principal_id': PRINCIPAL,
        'role': role_definition[0], 'scope': SCOPE, 'existing_assignments': roles,
        'storage_settings_before': storage, 'container': container, 'definitions_before': definitions,
        'source_prefix': prefix, 'sources': contract['inputs'], 'template_sha256': digest(
            (ROOT / 'infra/azure/adf_ingestion.arm.json').read_bytes()),
        'deployment_mode': 'Incremental', 'objects': KINDS, 'pipeline_execution_authorized': False}


def expected_subset(actual, expected):
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise ValueError('Deployed property type differs')
        for key, value in expected.items():
            if key not in actual:
                raise ValueError('Deployed property missing: ' + key)
            expected_subset(actual[key], value)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError('Deployed property list differs')
        for a, b in zip(actual, expected):
            expected_subset(a, b)
    elif actual != expected:
        raise ValueError('Deployed property value differs')


def resolved(value):
    mapping = {"[parameters('container')]": CONTAINER,
        "[concat('https://', parameters('storageAccount'), '.dfs.core.windows.net')]":
            f'https://{STORAGE}.dfs.core.windows.net'}
    if isinstance(value, dict):return {k: resolved(v) for k, v in value.items()}
    if isinstance(value, list):return [resolved(v) for v in value]
    return mapping.get(value, value) if isinstance(value, str) else value


def apply_stage1():
    preview = inspect()  # Recheck exact boundaries immediately before any change.
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    evidence_path = EVIDENCE_DIR / ('deployment-' + stamp + '.json')
    evidence = {'stage': 1, 'started_at_utc': stamp, 'status': 'started', 'preview': preview,
                'changes': [], 'source_verification': [], 'pipeline_triggered': False}
    def save():
        evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n')
    save()
    try:
        if not preview['existing_assignments']:
            role = az(['role', 'assignment', 'create', '--assignee-object-id', PRINCIPAL,
                '--assignee-principal-type', 'ServicePrincipal', '--role', ROLE, '--scope', SCOPE,
                '--name', str(uuid5(NAMESPACE_URL, SCOPE.lower() + PRINCIPAL + ROLE)), '--subscription', SUB,
                '--query', '{id:id,principalId:principalId,roleDefinitionId:roleDefinitionId,scope:scope,condition:condition}'])
            factory = rest(FACTORY_ID + '?api-version=2018-06-01', '{id:id,identity:identity}')
            require_identity(factory, preview['subscription'], [role])
            evidence['changes'].append({'action': 'grant_existing_adf_identity_only', 'assignment': role})
            save()
            print('Approved container-only role assigned.', flush=True)
        contract = json.loads(CONTRACT_PATH.read_text())
        with tempfile.TemporaryDirectory(prefix='tokyo-stage1-readback-') as temp:
            for name, entry in contract['inputs'].items():
                blob = preview['source_prefix'] + entry['file']
                upload = az(['storage', 'blob', 'upload', '--account-name', STORAGE, '-c', CONTAINER,
                    '-n', blob, '-f', str(ROOT / 'data' / entry['file']), '--auth-mode', 'login',
                    '--overwrite', 'false', '--if-none-match', '*', '--subscription', SUB,
                    '--metadata', 'provenance=manual-stage-only', 'sha256=' + entry['sha256'],
                    '--query', '{etag:etag,lastModified:lastModified}'])
                evidence['changes'].append({'action': 'create_source_blob_no_overwrite', 'name': blob, 'etag': upload['etag']})
                save()
                destination = Path(temp) / entry['file']
                az(['storage', 'blob', 'download', '--account-name', STORAGE, '-c', CONTAINER,
                    '-n', blob, '-f', str(destination), '--auth-mode', 'login', '--if-match', upload['etag'],
                    '--overwrite', 'false', '--subscription', SUB, '--query', '{name:name}'])
                raw = destination.read_bytes()
                if digest(raw) != entry['sha256'] or len(raw) != entry['bytes']:
                    raise ValueError('Uploaded source checksum mismatch')
                evidence['source_verification'].append({'file': entry['file'], 'blob': blob,
                    'bytes': len(raw), 'sha256': digest(raw), 'downloaded_and_verified': True})
                save()
                print(name + ': source uploaded and byte-verified.', flush=True)
        if any(list_definitions().values()):
            raise ValueError('ADF objects appeared concurrently; refusing deployment')
        deployment_name = 'tokyo-stage1-' + stamp.lower()
        deployment = az(['deployment', 'group', 'create', '--subscription', SUB, '-g', GROUP,
            '-n', deployment_name, '--mode', 'Incremental', '--template-file', str(ROOT / 'infra/azure/adf_ingestion.arm.json'),
            '--parameters', '@' + str(ROOT / 'infra/azure/adf_ingestion.parameters.json'),
            '--query', '{id:id,provisioningState:properties.provisioningState,timestamp:properties.timestamp}'], timeout=600)
        evidence['changes'].append({'action': 'deploy_ingestion_definitions_only', 'deployment': deployment})
        save()
        if deployment['provisioningState'] != 'Succeeded':
            raise ValueError('ARM deployment did not succeed')
        value = json.loads((ROOT / 'infra/azure/adf_ingestion.arm.json').read_text())
        verified = []
        for resource in value['resources']:
            kind = resource['type'].split('/')[-1]
            name = resource['name'].split("'/")[-1].split("'")[0]
            actual = rest(FACTORY_ID + '/' + kind + '/' + name + '?api-version=2018-06-01')
            expected_subset(actual['properties'], resolved(resource['properties']))
            verified.append({'id': actual['id'], 'name': actual['name'], 'etag': actual.get('etag'),
                             'properties_match_prepared_template': True})
        evidence['deployed_resources'] = verified
        definitions = list_definitions()
        if any(set(definitions[k]) != set(KINDS.get(k, [])) for k in definitions):
            raise ValueError('Unexpected final ADF resource inventory')
        evidence['definitions_after'] = definitions
        storage = az(['storage', 'account', 'show', '-g', GROUP, '-n', STORAGE, '--subscription', SUB,
            '--query', '{id:id,isHnsEnabled:isHnsEnabled,location:location,networkRuleSet:networkRuleSet,publicNetworkAccess:publicNetworkAccess,allowSharedKeyAccess:allowSharedKeyAccess}'])
        if storage != preview['storage_settings_before']:
            raise ValueError('Storage security/network settings changed unexpectedly')
        evidence['storage_settings_unchanged'] = True
        evidence['status'] = 'succeeded'
        save()
        print('Stage 1 succeeded; ingestion pipeline NOT executed. Evidence: ' + str(evidence_path), flush=True)
    except Exception as exc:
        evidence['status'] = 'stopped_with_error'
        evidence['error'] = str(exc) if isinstance(exc, (RuntimeError, ValueError)) else type(exc).__name__
        save()
        print('Stopped. Completed changes retained; no deletion or extra permission attempted. Evidence: ' + str(evidence_path), flush=True)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply-stage1', action='store_true')
    args = parser.parse_args()
    if args.apply_stage1:
        apply_stage1()
    else:
        print(json.dumps(inspect(), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
