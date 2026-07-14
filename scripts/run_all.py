from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from rescuemind import run_simulation
ROOT=Path(__file__).resolve().parents[1]

def artifacts(result,mode):
    for p in ['results/metrics','results/figures','results/manifests','results/reports','results/videos','assets/gifs','assets/videos']:(ROOT/p).mkdir(parents=True,exist_ok=True)
    (ROOT/f'results/metrics/{mode}.json').write_text(json.dumps(result['metrics'],indent=2))
    (ROOT/f'results/manifests/{mode}.json').write_text(json.dumps({'seed':result['seed'],'mode':mode,'method':result['method'],'synthetic_validation':True},indent=2))
    result['twin'].serialize(ROOT/f'results/manifests/{mode}_twin.npz')
    selected=result['traces'] if mode in {'smoke','full'} else [result['traces'][-1]];frames=[]
    for idx,tr in enumerate(selected):
        fig,ax=plt.subplots(figsize=(6,6));ax.imshow(result['world'].hazard,origin='lower',cmap='Reds',vmin=0,vmax=1,alpha=.45)
        for a in tr['agents']:ax.scatter(a['pose']['x'],a['pose']['y'],marker='^' if a['kind']=='UAV' else 's',s=70);ax.text(a['pose']['x']+.4,a['pose']['y']+.4,a['agent_id'],fontsize=7)
        for h in tr['hypotheses']:ax.scatter(h['pose']['x'],h['pose']['y'],s=180*h['score']+20,facecolors='none',edgecolors='black');ax.text(h['pose']['x']+.5,h['pose']['y'],f"{h['hypothesis_id']} {h['score']:.2f}",fontsize=8)
        ax.set(xlim=(0,40),ylim=(0,40),title=f'RescueMind synthetic run — t={tr["t"]}\nDecision support research prototype');fig.tight_layout();fp=ROOT/f'results/figures/{mode}_{idx:03d}.png';fig.savefig(fp,dpi=110);plt.close(fig);frames.append(Image.open(fp).convert('RGB'))
    if mode in {'smoke','full'}:
        frames[0].save(ROOT/'assets/gifs/rescuemind_multiagent_demo.gif',save_all=True,append_images=frames[1:],duration=250,loop=0)
        try:
            import imageio.v2 as imageio
            imageio.mimsave(ROOT/'assets/videos/rescuemind_research_demo.mp4',[np.array(f) for f in frames],fps=4)
            (ROOT/'results/videos/rescuemind_research_demo.mp4').write_bytes((ROOT/'assets/videos/rescuemind_research_demo.mp4').read_bytes())
        except Exception as exc:(ROOT/'results/videos/MP4_BLOCKER.txt').write_text(str(exc))
    report='# RescueMind Research Run\n\n**Status:** Synthetic Validation\n\nThis report is generated from deterministic synthetic simulation and does not demonstrate operational capability.\n\n## Metrics\n\n'+'\n'.join(f'- **{k}:** {v}' for k,v in result['metrics'].items())+'\n\n## Limitations\n\nNo hardware, ROS2 runtime, external dataset, medical assessment, structural assessment, or field validation was used.\n'
    (ROOT/'results/reports/RESCUEMIND_PHD_RESEARCH_REPORT.md').write_text(report)

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['smoke','perception','fusion','digital-twin','coordination','priority','benchmark','full'],default='smoke');p.add_argument('--seed',type=int,default=7);a=p.parse_args()
    method='fixed' if a.mode=='perception' else 'bayes' if a.mode=='fusion' else 'reliability';result=run_simulation(a.seed,6 if a.mode=='smoke' else 18,.35 if a.mode in {'coordination','full'} else .15,method);artifacts(result,a.mode);print(json.dumps(result['metrics'],indent=2))
if __name__=='__main__':main()
