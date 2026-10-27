"""Reconcile real Desktop DAX results against independently computed CSV values."""
import base64,csv,hashlib,json,math,re
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'powerbi/TokyoOlympics'
raw=(p/'data/olympic_country_dashboard.csv').read_bytes()
source=list(csv.DictReader(raw.decode('utf-8-sig').splitlines()))
e=json.loads((p/'live-dax-evidence.json').read_text(encoding='utf-8-sig'))
model=json.loads((p/'TokyoOlympics.SemanticModel/model.bim').read_text(encoding='utf-8-sig'))
query='\n'.join(model['model']['tables'][0]['partitions'][0]['source']['expression'])
assert base64.b64decode(re.search(r'Binary.FromText\("([A-Za-z0-9+/=]+)"',query)[1])==raw
assert hashlib.sha256(raw).hexdigest()=='37495ff232f8aa5140e6f194d851f41c053aa4cf4390f65faaf45e6283956bcb'
def number(r,k):return float(r[k])
def expected(rows):
    total=sum(number(r,'Total') for r in rows);athletes=sum(number(r,'athlete_count') for r in rows)
    return {'Countries':len(rows),'Medals':total,'Athletes':athletes,'Teams':sum(number(r,'team_count') for r in rows),'Medal Countries':sum(number(r,'Total')>0 for r in rows),'Efficiency':100*total/athletes if athletes else 0,'Gold Share':sum(number(r,'Gold') for r in rows)/total if total else 0}
def match(actual,expected):
    for k,v in expected.items():assert actual['['+k+']'] is not None and math.isclose(actual['['+k+']'],v,rel_tol=1e-12,abs_tol=1e-12),(k,actual,v)
match(e['totals']['rows'][0],expected(source))
match(e['selection']['rows'][0],expected([r for r in source if r['country'] in {'India','United States of America'}]))
lookup={r['country']:r for r in source};assert len(e['countries']['rows'])==len(lookup)==206
for r in e['countries']['rows']:
    original=lookup[r['CountryResults[country]']];ex=expected([original]);ex.pop('Countries');ex.pop('Medal Countries')
    ex.update({k:number(original,k) for k in ['Gold','Silver','Bronze']});match(r,ex)
    rank=1+sum(number(s,'Total')>number(original,'Total') for s in source)
    assert r['[Rank]']==rank
    assert r['[TopTotal]']==(number(original,'Total') if rank<=10 and number(original,'Total')>0 else None)
assert all(v is None for v in e['empty']['rows'][0].values())
summary=json.loads((p/'source-validation.json').read_text())
summary.update(validation='passed: real Desktop DAX reconciled to CSV',measure_count=len(model['model']['tables'][0]['measures']),live_dax_captured_at=e['captured_at'],checks=['Embedded import bytes equal pinned CSV','All 206 countries: medals, medal colors, athletes, teams, efficiency and gold share','Global totals and ratio-of-sums','India + United States combined filter totals and ratios','Empty selection returns blanks','All 206 medal ranks and top-ten visibility, including ties'],cloud_lineage='Local validated analytics snapshot; no successful Stage 3 Databricks output exists')
(p/'source-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
