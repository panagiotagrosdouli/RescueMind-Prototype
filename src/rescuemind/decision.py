from __future__ import annotations
import math, random
import numpy as np
from .models import *

class DigitalTwin:
    def __init__(self,world):
        self.world=world;self.revision=0;self.layers={k:np.zeros((world.size,world.size)) for k in ['survivor','uncertainty','age','priority']}
    def update(self,h,t):
        x,y=int(round(h.pose.x)),int(round(h.pose.y));self.layers['survivor'][y,x]=h.score;self.layers['uncertainty'][y,x]=h.uncertainty;self.layers['age'][y,x]=0;self.layers['age']+=1;self.revision+=1
    def serialize(self,path):path.parent.mkdir(parents=True,exist_ok=True);np.savez(path,revision=self.revision,**self.layers,hazard=self.world.hazard,accessibility=self.world.accessibility,communication=self.world.comm)

class PriorityModel:
    def __init__(self,weights=None):self.w=weights or {'presence':.34,'urgency':.22,'survival':.14,'access':.15,'hazard':.10,'time':.03,'uncertainty':.12}
    def score(self,h,travel_time):
        d={'presence':h.score,'urgency':h.urgency,'survival':max(0,1-h.hazard*.7),'access':h.accessibility,'hazard':-h.hazard,'time':-min(1,travel_time/60),'uncertainty':-h.uncertainty}
        s=sum(self.w[k]*d[k] for k in self.w);interval=.08+.25*h.uncertainty
        return PriorityEstimate(h.hypothesis_id,float(s),float(s-interval),float(s+interval),{k:self.w[k]*d[k] for k in self.w},float(min(1,2*interval)))

class Allocator:
    @staticmethod
    def allocate(agents,targets,method='greedy',comm_quality=1.):
        out={};available=[a for a in agents if not a.failed]
        for h in sorted(targets,key=lambda z:z.score,reverse=True):
            def cost(a):
                d=math.hypot(a.pose.x-h.pose.x,a.pose.y-h.pose.y)/max(a.speed,.1);cap=1 if set(a.sensors)&{'thermal','acoustic','radar','rgb'} else .3
                if method=='nearest':return d
                if method=='information_gain':return d-4*h.uncertainty*cap
                if method=='communication_aware':return d+8*(1-comm_quality)-2*cap
                return d-2*cap
            if available:a=min(available,key=cost);out[h.hypothesis_id]=a.agent_id;a.current_task=f'inspect:{h.hypothesis_id}'
        return out

class CommunicationNetwork:
    def __init__(self,seed=0,loss=.1,delay=1):self.r=random.Random(seed);self.loss=loss;self.delay=delay;self.queue=[];self.sent=0;self.delivered=0;self.dropped=0
    def send(self,t,payload):
        self.sent+=1
        if self.r.random()<self.loss:self.dropped+=1;return
        self.queue.append((t+self.delay,payload))
    def receive(self,t):
        ready=[p for dt,p in self.queue if dt<=t];self.queue=[x for x in self.queue if x[0]>t];self.delivered+=len(ready);return ready

class Explainer:
    @staticmethod
    def explain(p,h,conflicts,alternatives):
        top=sorted(p.decomposition.items(),key=lambda kv:abs(kv[1]),reverse=True)[:3]
        text=f'{h.hypothesis_id} is recommended for operator review with score {p.score:.3f} ({p.low:.3f}–{p.high:.3f}). Dominant computed terms: '+', '.join(f'{k}={v:+.3f}' for k,v in top)+f'. Evidence includes {len(h.supporting)} supporting and {len(h.contradicting)} contradicting observations.'
        if conflicts:text+=f' {len(conflicts)} modality conflict(s) require verification.'
        return {'decision_support_only':True,'text':text,'counterfactual':{'condition':'independent confirmation','estimated_effect':round(.12*(1-h.uncertainty),3),'statement':f'{h.hypothesis_id} priority would increase if an independent modality confirms presence and uncertainty decreases.'},'alternatives':[a.site_id for a in alternatives[:2]]}
