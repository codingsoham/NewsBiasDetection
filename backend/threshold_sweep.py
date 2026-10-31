"""Run clustering thresholds and report only structural, not quality, metrics."""
import subprocess,sys,sqlite3,json
from pathlib import Path
results=[]
for t in (.65,.70,.72,.75,.80):
 subprocess.run([sys.executable,'backend/ingest.py','--threshold',str(t)],check=True)
 c=sqlite3.connect('data/articles.db');row={'threshold':t,'stories':c.execute('select count(*) from stories').fetchone()[0],'links':c.execute('select count(*) from story_articles').fetchone()[0]};results.append(row);print(row)
Path('results').mkdir(exist_ok=True);Path('results/threshold_sweep.json').write_text(json.dumps(results,indent=2))
# Keep the database in the documented production configuration after the sweep.
subprocess.run([sys.executable,'backend/ingest.py','--threshold','.72'],check=True)
