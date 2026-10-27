# Databricks notebook source
# No mounts, embedded credentials, package installation or model training.
# This file is prepared offline; cloud execution requires explicit approval.
import hashlib
import json
from pathlib import Path
import re
import sys
from uuid import UUID

for name in ['repo_path', 'storage_account', 'container', 'raw_run_id', 'output_run_id']:
    dbutils.widgets.text(name, '')
settings = {name: dbutils.widgets.get(name) for name in
            ['repo_path', 'storage_account', 'container', 'raw_run_id', 'output_run_id']}
for key in ['raw_run_id', 'output_run_id']:
    UUID(settings[key])
if not re.fullmatch(r'[a-z0-9]{3,24}', settings['storage_account']):
    raise ValueError('Invalid storage account')
if not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,61}[a-z0-9]', settings['container']):
    raise ValueError('Invalid container')
repo = Path(settings['repo_path']).resolve()
sys.path.insert(0, str(repo))
from src.azure.contracts import digest, load_pinned_sources
from src.azure.spark_transform import transform_prepared, verify_reference_parity

contract = json.loads((repo / 'infra/azure/data_contract.json').read_text())
for name, expected in contract['code_sha256'].items():
    if digest((repo / name).read_bytes()) != expected:
        raise ValueError('Code bundle differs from pinned contract')
root = f"abfss://{settings['container']}@{settings['storage_account']}.dfs.core.windows.net"
raw_path = root + '/raw/adf/' + settings['raw_run_id']
curated_path = root + '/curated/adf/' + settings['output_run_id']
analytics_path = root + '/analytics/adf/' + settings['output_run_id']
# Read exact ADF-created files. Hashes distinguish ingestion from manual staging.
contents = {}
for name, spec in contract['inputs'].items():
    records = spark.read.format('binaryFile').load(raw_path + '/' + spec['file']).select('length', 'content').collect()
    if len(records) != 1 or records[0]['length'] != spec['bytes']:
        raise ValueError('Unexpected raw input count or size')
    contents[name] = bytes(records[0]['content'])
prepared, quality = load_pinned_sources(contents, contract)
frames, outputs = transform_prepared(spark, prepared)
references = {}
for name, spec in contract['outputs'].items():
    raw = (repo / spec['reference']).read_bytes()
    if digest(raw) != spec['sha256']:
        raise ValueError('Reference bundle checksum mismatch')
    references[name] = raw
verify_reference_parity(outputs, references)
# Never overwrite an existing run. Partial failed runs have no success manifest.
for path in [curated_path, analytics_path]:
    try:
        dbutils.fs.ls(path)
    except Exception as exc:
        if not any(marker in str(exc) for marker in ['FileNotFoundException', 'PATH_NOT_FOUND', 'does not exist']):
            raise
    else:
        raise ValueError('Output run already exists; use a new ADF run')
for name, frame in frames.items():
    frame.write.mode('errorifexists').parquet(curated_path + '/' + name)
    saved = spark.read.parquet(curated_path + '/' + name)
    if saved.schema != frame.schema or saved.count() != frame.count():
        raise ValueError('Curated Parquet schema/count mismatch')
    if saved.exceptAll(frame).limit(1).count() or frame.exceptAll(saved).limit(1).count():
        raise ValueError('Curated Parquet values differ after writing')
manifest = {'status': 'validated', 'run_id': settings['output_run_id'],
    'raw_run_id': settings['raw_run_id'], 'dataset_version': contract['dataset_version'],
    'code_sha256': contract['code_sha256'], 'spark_version': spark.version,
    'input_sha256': {name: digest(value) for name, value in contents.items()},
    'quality_warnings': sorted({item['code'] for item in quality['warnings']}), 'outputs': {}}
for name, frame in outputs.items():
    # Small country-level CSVs: stable filenames, UTF-8, no Spark part-file ambiguity.
    content = frame.to_csv(index=False, float_format='%.17g')
    dbutils.fs.put(analytics_path + '/' + name, content, overwrite=False)
    manifest['outputs'][name] = {'sha256': digest(content.encode('utf-8')), 'rows': len(frame),
                                  'columns': list(frame.columns)}
# Re-read every export before publishing success. No head()/truncation of CSVs.
import io
import pandas as pd
from src.azure.contracts import assert_parity
for name, frame in outputs.items():
    saved = spark.read.format('binaryFile').load(analytics_path + '/' + name).select('content').collect()
    if len(saved) != 1:
        raise ValueError('Unexpected export file count')
    content = bytes(saved[0]['content'])
    if digest(content) != manifest['outputs'][name]['sha256']:
        raise ValueError('Export round-trip checksum mismatch')
    assert_parity(pd.read_csv(io.BytesIO(content)), frame)
dbutils.fs.put(analytics_path + '/manifest.json', json.dumps(manifest, indent=2, sort_keys=True) + '\n', overwrite=False)
dbutils.notebook.exit(json.dumps({'status': 'validated', 'manifest': analytics_path + '/manifest.json',
    'dataset_version': contract['dataset_version'], 'run_id': settings['output_run_id']}))
