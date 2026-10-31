"""Load the official Baly media-based splits into JSONL for Stage 1."""
import csv,json
from pathlib import Path
ROOT=Path('data/external/Article-Bias-Prediction/data')
OUT=Path('data/external/baly_prepared');OUT.mkdir(parents=True,exist_ok=True)
for split in ('train','valid','test'):
 rows=[]
 with (ROOT/'splits'/'media'/f'{split}.tsv').open(encoding='utf-8') as f:
  for x in csv.DictReader(f,delimiter='\t'):
   p=ROOT/'jsons'/f"{x['ID']}.json"
   if p.exists():
    a=json.loads(p.read_text(encoding='utf-8'));text=(a.get('title','')+' '+a.get('content','')).strip()
    if text: rows.append({'text':text,'label':int(x['bias'])})
 (OUT/f'{split}.jsonl').write_text('\n'.join(json.dumps(x) for x in rows),encoding='utf-8');print(split,len(rows))
