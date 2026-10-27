"""Read-only Azure CLI inventory; never logs in, deploys or installs extensions.

Requires an explicit subscription UUID and writes only a sanitized local report
when --output is supplied. No credentials, account keys or access tokens queried.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from uuid import UUID

API_ROOT = 'https://management.azure.com'


def inventory(subscription_id):
    UUID(subscription_id)
    if not shutil.which('az'):
        raise RuntimeError('Azure CLI missing; install using official Microsoft instructions first')
    env = dict(os.environ, AZURE_EXTENSION_USE_DYNAMIC_INSTALL='no', AZURE_CORE_COLLECT_TELEMETRY='false')
    result = {'captured_at_utc': datetime.now(timezone.utc).isoformat(),
              'subscription_id': subscription_id, 'mode': 'read-only; no resource changes',
              'checks': {}, 'unknowns': ['Student credit balance is not inferred from budgets or cost totals.',
                  'Provider registration/SKU listing does not guarantee workspace creation eligibility or compute quota.']}
    def check(name, args):
        try:
            process = subprocess.run(['az', *args, '--only-show-errors', '--output', 'json'],
                                     capture_output=True, text=True, env=env, timeout=120)
        except subprocess.TimeoutExpired:
            result['checks'][name] = {'status': 'unavailable', 'reason': 'Read-only query timed out'}
            return None
        if process.returncode:
            codes = ['PathNotFound', 'SubscriptionNotRegistered', 'AuthorizationFailed',
                     'AuthorizationPermissionMismatch', 'AuthenticationFailed', 'InvalidAuthenticationToken']
            result['checks'][name] = {'status': 'unavailable',
                'error_code': next((code for code in codes if code in process.stderr), 'UnclassifiedFailure'),
                'reason': 'Command failed: authentication, permission, API availability or network; no raw stderr retained'}
            return None
        try:
            value = json.loads(process.stdout)
        except ValueError:
            result['checks'][name] = {'status': 'unavailable', 'reason': 'Non-JSON response'}
            return None
        result['checks'][name] = {'status': 'read', 'value': value}
        return value
    sub = ['--subscription', subscription_id]
    scope = '/subscriptions/' + subscription_id
    account = check('subscription', ['account', 'show', *sub, '--query', '{id:id,name:name,state:state}'])
    if not account or account['id'].lower() != subscription_id.lower() or account['name'] != 'Azure for Students':
        raise ValueError('Explicit subscription must resolve to Azure for Students before inventory continues')
    check('subscription_policies', ['rest', '--method', 'get', '--url', API_ROOT + scope + '?api-version=2022-12-01',
        '--query', '{state:state,subscriptionPolicies:subscriptionPolicies}'])
    check('subscription_resources', ['resource', 'list', *sub, '--query',
        '[].{name:name,type:type,location:location,resourceGroup:resourceGroup}'])
    check('resource_group', ['group', 'show', '-n', 'rg-tokyo-olympics', *sub,
          '--query', '{id:id,name:name,location:location,provisioningState:properties.provisioningState}'])
    # Generic REST avoids the optional datafactory/databricks CLI extensions.
    factory_id = '/subscriptions/' + subscription_id + '/resourceGroups/rg-tokyo-olympics/providers/Microsoft.DataFactory/factories/adf-tokyo-olympics-hetram-2026'
    factory = check('factory_rest', ['rest', '--method', 'get', '--url', API_ROOT + factory_id + '?api-version=2018-06-01',
         '--query', '{id:id,location:location,identity:identity,publicNetworkAccess:properties.publicNetworkAccess}'])
    storage = check('storage', ['storage', 'account', 'show', '-g', 'rg-tokyo-olympics', '-n',
        'tokyoolympicdatahetram', *sub, '--query',
        '{id:id,location:location,isHnsEnabled:isHnsEnabled,kind:kind,sku:sku.name,allowSharedKeyAccess:allowSharedKeyAccess,publicNetworkAccess:publicNetworkAccess,networkRuleSet:networkRuleSet}'])
    container_scope = (storage['id'] + '/blobServices/default/containers/tokyo-olympic-data') if storage else None
    if factory and (factory.get('identity') or {}).get('principalId'):
        check('factory_storage_roles', ['role', 'assignment', 'list', '--assignee-object-id',
            factory['identity']['principalId'], '--scope', container_scope if container_scope else '/subscriptions/' + subscription_id,
            '--include-inherited', *sub, '--query', '[].{role:roleDefinitionName,scope:scope,principalType:principalType}'])
    if storage:
        check('my_storage_management_permissions', ['rest', '--method', 'get', '--url', API_ROOT + storage['id'] +
            '/providers/Microsoft.Authorization/permissions?api-version=2022-04-01', '--query',
            'value[].{actions:actions,notActions:notActions,dataActions:dataActions,notDataActions:notDataActions}'])
        check('regional_compute_usage', ['vm', 'list-usage', '--location', storage['location'], *sub,
            '--query', '[].{name:name.value,currentValue:currentValue,limit:limit}'])
    for kind in ['pipelines', 'datasets', 'linkedservices', 'triggers']:
        check('adf_' + kind, ['rest', '--method', 'get', '--url',
            API_ROOT + factory_id + '/' + kind + '?api-version=2018-06-01', '--query', 'value[].{name:name,type:type}'])
    check('container', ['storage', 'fs', 'show', '-n', 'tokyo-olympic-data', '--account-name',
        'tokyoolympicdatahetram', '--auth-mode', 'login', *sub, '--query', '{name:name,publicAccess:publicAccess}'])
    check('all_containers', ['storage', 'container', 'list', '--account-name',
        'tokyoolympicdatahetram', '--auth-mode', 'login', *sub, '--query', '[].{name:name,publicAccess:properties.publicAccess}'])
    check('root_paths', ['storage', 'fs', 'file', 'list', '-f', 'tokyo-olympic-data', '--account-name',
        'tokyoolympicdatahetram', '--auth-mode', 'login', *sub, '--query', '[].{name:name,isDirectory:isDirectory,contentLength:contentLength}'])
    for path in ['/', 'raw', 'curated', 'analytics', 'staging']:
        check('acl_' + path.replace('/', 'root'), ['storage', 'fs', 'access', 'show',
            '-f', 'tokyo-olympic-data', '--path', path, '--account-name', 'tokyoolympicdatahetram',
            '--auth-mode', 'login', *sub, '--query', '{acl:acl,permissions:permissions}'])
    check('databricks_provider', ['provider', 'show', '-n', 'Microsoft.Databricks', *sub,
        '--query', '{registrationState:registrationState,workspaces:resourceTypes[?resourceType==`workspaces`].{locations:locations,apiVersions:apiVersions}}'])
    check('databricks_workspaces', ['resource', 'list', '--resource-type', 'Microsoft.Databricks/workspaces',
        *sub, '--query', '[].{id:id,name:name,location:location,sku:sku}'])
    check('budgets', ['rest', '--method', 'get', '--url', API_ROOT + scope +
          '/providers/Microsoft.Consumption/budgets?api-version=2024-08-01', '--query',
          'value[].{name:name,amount:properties.amount,timeGrain:properties.timeGrain,currentSpend:properties.currentSpend,timePeriod:properties.timePeriod}'])
    # Cost query is a read-only POST, not an Azure mutation or pipeline execution.
    body = {'type': 'ActualCost', 'timeframe': 'MonthToDate', 'dataset': {'granularity': 'None',
        'aggregation': {'totalCost': {'name': 'PreTaxCost', 'function': 'Sum'}},
        'grouping': [{'type': 'Dimension', 'name': 'ServiceName'}]}}
    check('month_to_date_cost', ['rest', '--method', 'post', '--url', API_ROOT + scope +
          '/providers/Microsoft.CostManagement/query?api-version=2025-03-01', '--body', json.dumps(body),
          '--query', '{columns:properties.columns,rows:properties.rows}'])
    billing = check('subscription_billing_profile', ['rest', '--method', 'get', '--url', API_ROOT + scope +
        '/providers/Microsoft.Billing/billingProperty/default?api-version=2024-04-01',
        '--query', '{billingProfileId:properties.billingProfileId}'])
    profile = billing.get('billingProfileId') if isinstance(billing, dict) else None
    if profile and re.fullmatch(r'/providers/Microsoft\.Billing/billingAccounts/[A-Za-z0-9:_-]+/billingProfiles/[A-Za-z0-9_-]+', profile):
        check('billing_profile_credit_summary', ['rest', '--method', 'get', '--url', API_ROOT + profile +
            '/providers/Microsoft.Consumption/credits/balanceSummary?api-version=2024-08-01', '--query',
            '{balanceSummary:properties.balanceSummary,billingCurrency:properties.billingCurrency,creditCurrency:properties.creditCurrency,isEstimatedBalance:properties.isEstimatedBalance,pendingEligibleCharges:properties.pendingEligibleCharges,expiredCredit:properties.expiredCredit}'])
    result['cloud_execution_verified'] = False
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--subscription-id', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = inventory(args.subscription_id)
    content = json.dumps(result, indent=2) + '\n'
    if args.output:
        # Refuse to overwrite prior evidence.
        with args.output.open('x') as handle:
            handle.write(content)
    else:
        print(content)


if __name__ == '__main__':
    main()
