from __future__ import annotations
import math, uuid
import numpy as np
from .models import *

class DisasterWorld:
    def __init__(self,seed:int=0,size:int=40):
        self.seed=seed; self.rng=np.random.default_rng(seed); self.size=size; self.t=0
        self.occupancy=np.zeros((size,size)); self.accessibility=np.ones((size,size)); self.comm=np.ones((size,size)); self.hazard=np.zeros((size,size))
        self.occupancy[12:20,17:24]=.8; self.accessibility[12:20,17:24]=.25; self.comm[25:36,2:15]=.25
        self.survivors=[Survivor('S1',Pose2D(29,8),.9),Survivor('S2',Pose2D(9,31),.55,acoustic=.9,visibility=.3)]
        self.hazards=[Hazard('fire',Pose2D(24,27),4,.65,.02)]
    def step(self):
        self.t+=1; yy,xx=np.mgrid[:self.size,:self.size]; self.hazard*=.98
        for h in self.hazards:
            h.radius+=h.growth; d=np.hypot(xx-h.pose.x,yy-h.pose.y)
            self.hazard=np.maximum(self.hazard,np.clip(h.severity*(1-d/max(h.radius,1e-6)),0,1))
        if self.t==10:self.accessibility[8:14,26:31]=.15

class SensorSuite:
    BASE={'thermal':(.88,.12),'rgb':(.80,.15),'acoustic':(.78,.18),'radar':(.82,.14),'environmental':(.90,.10),'depth':(.86,.12)}
    def __init__(self,world):self.world=world
    def reliability(self,modality,pose,t,failed=False):
        if failed:return 0.,ReliabilityState.FAILED
        q=self.BASE[modality][0]; hz=self.world.hazard[int(np.clip(pose.y,0,self.world.size-1)),int(np.clip(pose.x,0,self.world.size-1))]
        if modality in {'rgb','thermal'}:q-=.45*hz
        if modality=='acoustic':q-=.15*hz
        q=float(np.clip(q,0,1)); st=ReliabilityState.RELIABLE if q>=.75 else ReliabilityState.DEGRADED if q>=.45 else ReliabilityState.UNCERTAIN
        return q,st
    def observe(self,a,s,m,t):
        d=math.hypot(a.pose.x-s.pose.x,a.pose.y-s.pose.y); q,_=self.reliability(m,a.pose,t,a.failed)
        signal={'thermal':s.thermal,'rgb':s.visibility,'acoustic':s.acoustic,'radar':s.motion,'environmental':.35,'depth':.7}[m]
        noise=self.world.rng.normal(0,self.BASE[m][1]+(1-q)*.25); score=float(np.clip(signal*math.exp(-d/16)+noise,0,1))
        if m=='thermal':score=float(np.clip(score+.5*self.world.hazard[int(a.pose.y),int(a.pose.x)],0,1))
        oid=str(uuid.uuid4()); return Observation(m,score,float(np.clip(1-abs(noise),0,1)),q,float(t),s.pose,1.5+(1-q)*3,4.,Provenance(oid,a.agent_id,f'{a.agent_id}:{m}'),{'distance':d,'signal_quality':q})

class TemporalBuffer:
    def __init__(self,window=3):self.window=window;self.items=[]
    def add(self,o):self.items.append(o);self.items.sort(key=lambda x:x.timestamp)
    def aligned(self,now):return [o for o in self.items if not o.stale(now) and abs(now-o.timestamp)<=self.window]
