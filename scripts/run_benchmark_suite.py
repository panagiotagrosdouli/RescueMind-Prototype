import argparse,json,statistics
from pathlib import Path
from rescuemind import run_simulation
p=argparse.ArgumentParser();p.add_argument('--num-seeds',type=int,default=5);a=p.parse_args();out={}
for method in ['fixed','reliability','bayes']:
    rows=[run_simulation(seed,12,method=method)['metrics'] for seed in range(a.num_seeds)]
    out[method]={key:{'mean':statistics.fmean(row[key] for row in rows),'stdev':statistics.stdev([row[key] for row in rows]) if len(rows)>1 else 0.0} for key in rows[0]}
Path('results/metrics').mkdir(parents=True,exist_ok=True);Path('results/metrics/benchmark.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
