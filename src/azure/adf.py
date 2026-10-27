"""Render ADF-only ARM templates locally. Rendering never deploys or runs Azure."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = '2018-06-01'


def expression(value):
    return {'value': value, 'type': 'Expression'}


def template(contract):
    def resource(kind, name, properties, dependencies=()):
        return {'type': 'Microsoft.DataFactory/factories/' + kind, 'apiVersion': API,
                'name': "[concat(parameters('factoryName'), '/" + name + "')]",
                'dependsOn': ["[resourceId('Microsoft.DataFactory/factories/" + k + "', parameters('factoryName'), '" + n + "')]" for k, n in dependencies],
                'properties': properties}
    linked = resource('linkedservices', 'ls_tokyo_adls_mi', {'type': 'AzureBlobFS',
        'typeProperties': {'url': "[concat('https://', parameters('storageAccount'), '.dfs.core.windows.net')]"}})
    def dataset(name, folder):
        return resource('datasets', name, {'type': 'Binary', 'linkedServiceName': {
            'referenceName': 'ls_tokyo_adls_mi', 'type': 'LinkedServiceReference'},
            'parameters': {'fileName': {'type': 'String'}, 'runId': {'type': 'String', 'defaultValue': ''}},
            'typeProperties': {'location': {'type': 'AzureBlobFSLocation',
                'fileSystem': "[parameters('container')]", 'folderPath': folder,
                'fileName': expression('@dataset().fileName')}}}, [('linkedservices', 'ls_tokyo_adls_mi')])
    source = dataset('ds_tokyo_staged_binary', 'staging/' + contract['dataset_version'])
    sink = dataset('ds_tokyo_raw_binary', expression("@concat('raw/adf/', dataset().runId)"))
    copy = {'name': 'CopyPinnedFile', 'type': 'Copy', 'policy': {'timeout': '0.00:10:00',
        'retry': 0, 'secureInput': True, 'secureOutput': True}, 'inputs': [{
        'referenceName': 'ds_tokyo_staged_binary', 'type': 'DatasetReference',
        'parameters': {'fileName': expression('@item()')}}], 'outputs': [{
        'referenceName': 'ds_tokyo_raw_binary', 'type': 'DatasetReference',
        'parameters': {'fileName': expression('@item()'), 'runId': expression('@pipeline().RunId')}}],
        'typeProperties': {'source': {'type': 'BinarySource', 'storeSettings': {
            'type': 'AzureBlobFSReadSettings', 'recursive': False}}, 'sink': {
            'type': 'BinarySink', 'storeSettings': {'type': 'AzureBlobFSWriteSettings'}},
            'enableStaging': False, 'dataIntegrationUnits': 2, 'parallelCopies': 1}}
    pipeline = resource('pipelines', 'pl_tokyo_ingest', {'concurrency': 1,
        'annotations': ['Pinned binary copy; source manually staged; raw files created only by ADF'],
        'activities': [{'name': 'CopyAllFive', 'type': 'ForEach', 'typeProperties': {
            'isSequential': True, 'items': expression('@createArray(' + ','.join(
                "'" + entry['file'] + "'" for entry in contract['inputs'].values()) + ')'),
            'activities': [copy]}}]}, [('datasets', 'ds_tokyo_staged_binary'), ('datasets', 'ds_tokyo_raw_binary')])
    return {'$schema': 'https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#',
        'contentVersion': '1.0.0.0', 'parameters': {
            'factoryName': {'type': 'string'}, 'storageAccount': {'type': 'string'},
            'container': {'type': 'string'}}, 'resources': [linked, source, sink, pipeline]}


def orchestration_template():
    """Run an approved Databricks job; its job definition controls compute."""
    def res(kind, name, properties, depends=()):
        return {'type': 'Microsoft.DataFactory/factories/' + kind, 'apiVersion': API,
            'name': "[concat(parameters('factoryName'), '/" + name + "')]", 'properties': properties,
            'dependsOn': ["[resourceId('Microsoft.DataFactory/factories/linkedservices', parameters('factoryName'), '" + d + "')]" for d in depends]}
    linked = res('linkedservices', 'ls_tokyo_databricks_mi', {'type': 'AzureDatabricks',
        'typeProperties': {'domain': "[parameters('workspaceUrl')]", 'authentication': 'MSI',
            'workspaceResourceId': "[parameters('workspaceResourceId')]"}})
    pipeline = res('pipelines', 'pl_tokyo_end_to_end', {'concurrency': 1, 'activities': [
        {'name': 'Ingest', 'type': 'ExecutePipeline', 'typeProperties': {'pipeline': {
            'referenceName': 'pl_tokyo_ingest', 'type': 'PipelineReference'}, 'waitOnCompletion': True}},
        {'name': 'TransformAndValidate', 'type': 'DatabricksJob',
         'dependsOn': [{'activity': 'Ingest', 'dependencyConditions': ['Succeeded']}],
         'policy': {'timeout': '0.00:20:00', 'retry': 0, 'secureInput': True, 'secureOutput': True},
         'linkedServiceName': {'referenceName': 'ls_tokyo_databricks_mi', 'type': 'LinkedServiceReference'},
         'typeProperties': {'jobId': "[parameters('jobId')]", 'jobParameters': {
            'repo_path': "[parameters('repoPath')]", 'storage_account': "[parameters('storageAccount')]",
            'container': "[parameters('container')]", 'raw_run_id': expression("@activity('Ingest').output.pipelineRunId"),
            'output_run_id': expression('@pipeline().RunId')}}}]}, ['ls_tokyo_databricks_mi'])
    return {'$schema': 'https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#',
        'contentVersion': '1.0.0.0', 'parameters': {name: {'type': 'string', 'minLength': 1} for name in [
            'factoryName', 'storageAccount', 'container', 'workspaceUrl', 'workspaceResourceId',
            'jobId', 'repoPath']}, 'resources': [linked, pipeline]}


def main():
    # Deterministic local generation only. No deployment client is imported.
    contract = json.loads((ROOT / 'infra/azure/data_contract.json').read_text())
    for name, value in [('adf_ingestion.arm.json', template(contract)),
                        ('adf_orchestration.arm.json', orchestration_template())]:
        (ROOT / 'infra/azure' / name).write_text(json.dumps(value, indent=2) + '\n')


if __name__ == '__main__':
    main()
