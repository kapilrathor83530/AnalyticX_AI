import json
from pathlib import Path
import pandas as pd

df = pd.read_csv('storage/uploads/btech_aiml_sem6_results.csv')
records = df.to_dict(orient='records')

out_dir = Path('frontend/src/data')
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / 'studentResultsData.json'

with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(records, f, indent=2)

print(f"Saved {len(records)} records to {out_file}")
