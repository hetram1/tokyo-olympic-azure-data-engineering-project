"""Version-pinned cloud inputs and output parity; no Azure SDK or network calls."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from uuid import UUID

import pandas as pd

from src.quality.gates import SCHEMAS, validate_sources, DataQualityError

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / 'infra/azure/data_contract.json'
OUTPUTS = {
    'country_features.csv': ('models/country_features.csv', 206, 10),
    'country_analytics.csv': ('models/country_analytics.csv', 206, 14),
    'olympic_country_dashboard.csv': ('dashboards/olympic_country_dashboard.csv', 206, 16),
}


def digest(content):
    return hashlib.sha256(content).hexdigest()


def build_contract(root=ROOT):
    inputs = {}
    for name, columns in SCHEMAS.items():
        raw = (root / 'data' / (name + '.csv')).read_bytes()
        try:
            raw.decode('utf-8'); encoding = 'utf-8'
        except UnicodeDecodeError:
            encoding = 'ISO-8859-1'
        frame = pd.read_csv(io.BytesIO(raw), encoding=encoding)
        if list(frame.columns) != columns:
            raise ValueError(f'{name}: unexpected source schema')
        inputs[name] = {'file': name + '.csv', 'sha256': digest(raw), 'bytes': len(raw),
                        'rows': len(frame), 'encoding': encoding, 'columns': columns}
    version = digest(json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode())
    outputs = {}
    for name, (path, rows, columns) in OUTPUTS.items():
        raw = (root / path).read_bytes(); frame = pd.read_csv(io.BytesIO(raw))
        if frame.shape != (rows, columns):
            raise ValueError(f'{name}: reference shape changed; review contract')
        outputs[name] = {'reference': path, 'sha256': digest(raw), 'rows': rows,
                         'columns': list(frame.columns), 'key': 'country'}
    code = {str(path.relative_to(root)): digest(path.read_bytes())
            for path in sorted([*(root / 'src').rglob('*.py'), *(root / 'databricks').glob('*.py')])}
    return {'schema_version': 1, 'dataset_version': version, 'inputs': inputs,
            'outputs': outputs, 'code_sha256': code,
            'source_checkpoint': 'eb30e6fbf31afe59d74b67973fd230df43a59c23',
            'publication': 'Only a successful run manifest authorizes consumption',
            'counts_are_snapshot_specific': True}


def load_pinned_sources(contents, contract):
    sources = {}
    for name, entry in contract['inputs'].items():
        raw = contents[name]
        if len(raw) != entry['bytes'] or digest(raw) != entry['sha256']:
            raise ValueError(f'{name}: pinned source checksum/length mismatch')
        frame = pd.read_csv(io.BytesIO(raw), encoding=entry['encoding'])
        if list(frame.columns) != entry['columns'] or len(frame) != entry['rows']:
            raise ValueError(f'{name}: pinned source schema/row mismatch')
        sources[name] = frame
    prepared, quality = validate_sources(sources)
    if not quality['valid']:
        raise DataQualityError(quality)
    return prepared, quality


def assert_parity(actual, expected, key='country'):
    """Compare keys, schemas and values; floats tolerate serialization only."""
    if list(actual.columns) != list(expected.columns):
        raise ValueError('Output column schema differs')
    if actual[key].isna().any() or actual[key].duplicated().any():
        raise ValueError('Output keys must be unique and nonnull')
    pd.testing.assert_frame_equal(actual.sort_values(key).reset_index(drop=True),
        expected.sort_values(key).reset_index(drop=True), check_dtype=False,
        check_categorical=False, rtol=1e-12, atol=1e-12)


def verify_export(directory, contract, root=ROOT):
    """Read a downloaded run; never overwrite the established local outputs."""
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    if manifest.get('dataset_version') != contract['dataset_version'] or manifest.get('status') != 'validated':
        raise ValueError('Missing compatible successful-run manifest')
    UUID(manifest['run_id'])
    UUID(manifest['raw_run_id'])
    if manifest.get('code_sha256') != contract['code_sha256'] or manifest.get('input_sha256') != {
            name: spec['sha256'] for name, spec in contract['inputs'].items()}:
        raise ValueError('Manifest code/input provenance differs from pinned contract')
    for name, spec in contract['outputs'].items():
        raw = (directory / name).read_bytes()
        if digest(raw) != manifest['outputs'][name]['sha256']:
            raise ValueError(f'{name}: export checksum mismatch')
        if (manifest['outputs'][name].get('rows') != spec['rows']
                or manifest['outputs'][name].get('columns') != spec['columns']):
            raise ValueError('Manifest output schema/count differs from pinned contract')
        reference = (root / spec['reference']).read_bytes()
        if digest(reference) != spec['sha256']:
            raise ValueError('Local reference changed since contract was pinned')
        assert_parity(pd.read_csv(io.BytesIO(raw)), pd.read_csv(io.BytesIO(reference)))
    return {'valid': True, 'outputs': len(contract['outputs']), 'run_id': manifest['run_id']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-export', type=Path)
    args = parser.parse_args()
    contract = json.loads(CONTRACT_PATH.read_text())
    if build_contract() != contract:
        raise ValueError('Contract is stale; review inputs, references or code before repinning')
    prepared, report = load_pinned_sources(
        {name: (ROOT / 'data' / spec['file']).read_bytes() for name, spec in contract['inputs'].items()}, contract)
    print(json.dumps({'valid': report['valid'], 'dataset_version': contract['dataset_version'],
                      'prepared_rows': {name: len(frame) for name, frame in prepared.items()},
                      'warning_codes': sorted({w['code'] for w in report['warnings']})}))
    if args.verify_export:
        print(json.dumps(verify_export(args.verify_export, contract)))


if __name__ == '__main__':
    main()
