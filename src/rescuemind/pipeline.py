from __future__ import annotations
import math
from dataclasses import asdict
from .models import *
from .simulation import *
from .fusion import *
from .decision import *

def run_simulation(seed=0,steps=18,loss=.15,method='reliability'):
    world=DisasterWorld(seed);sensors=SensorSuite(world)
    agents=[Agent('UAV-1','UAV',Pose2D(20,20),3,1,18,['thermal','rgb']),Agent('UGV-1','UGV',Pose2D(5,5),1,1,10,['acoustic','radar','depth']),Agent('NODE-1','STATIC',Pose2D(12,28),0,1,14,['acoustic','environmental'])]
    net=CommunicationNetwork(seed,loss);buffer=TemporalBuffer();twin=DigitalTwin(world);traces=[];ys=[];ps=[];ranks=[];all_conflicts=[]
    for t in range(steps):
        world.step()
        for i,a in enumerate(agents[:2]):
            target=world.survivors[i];dx,dy=target.pose.x-a.pose.x,target.pose.y-a.pose.y;d=max(1,math.hypot(dx,dy));a.pose=Pose2D(a.pose.x+a.speed*dx/d,a.pose.y+a.speed*dy/d)
        for a in agents:
            for m in a.sensors:
                if m=='depth':continue
                for survivor in world.survivors:
                    o=sensors.observe(a,survivor,m,t);buffer.add(o);net.send(t,asdict(o))
        delivered=net.receive(t);aligned=buffer.aligned(t);hyps=[]
        for survivor in world.survivors:
            local=[o for o in aligned if math.hypot(o.pose.x-survivor.pose.x,o.pose.y-survivor.pose.y)<2]
            p,u={'fixed':Fusion.fixed,'bayes':Fusion.bayes}.get(method,Fusion.reliability)(local)
            h=Hypothesis(survivor.survivor_id,survivor.pose,p,u,[o.provenance.observation_id for o in local if o.value>=.5],[o.provenance.observation_id for o in local if o.value<.3],urgency=survivor.urgency)
            x,y=int(h.pose.x),int(h.pose.y);h.hazard=float(world.hazard[y,x]);h.accessibility=float(world.accessibility[y,x]);h.status='HIGH_PRIORITY' if p>.75 else 'PROBABLE' if p>.6 else 'POSSIBLE' if p>.45 else 'REQUIRES_REOBSERVATION'
            twin.update(h,t);hyps.append(h);ys.append(1);ps.append(p)
        neg=[o for o in aligned if o.modality=='thermal'][:2]
        pneg,_=Fusion.reliability([Observation(o.modality,max(0,o.value-.55),o.confidence,o.reliability,o.timestamp,Pose2D(2,2),o.spatial_uncertainty,o.valid_for,o.provenance,o.raw) for o in neg]);ys.append(0);ps.append(pneg)
        pri=[PriorityModel().score(h,math.hypot(h.pose.x-5,h.pose.y-5)) for h in hyps];pri.sort(key=lambda x:x.score,reverse=True);ranks.append([p.site_id for p in pri])
        allocation=Allocator.allocate(agents,hyps,'communication_aware',1-loss);conflicts=[]
        for h in hyps:conflicts+=ConflictDetector.detect([o for o in aligned if o.pose==h.pose])
        all_conflicts+=conflicts;top=next(h for h in hyps if h.hypothesis_id==pri[0].site_id);ex=Explainer.explain(pri[0],top,conflicts,pri[1:])
        traces.append({'t':t,'agents':[asdict(a) for a in agents],'hypotheses':[asdict(h) for h in hyps],'priorities':[asdict(x) for x in pri],'allocation':allocation,'delivered_messages':len(delivered),'conflicts':conflicts,'explanation':ex})
    reversals=sum(ranks[i][0]!=ranks[i-1][0] for i in range(1,len(ranks)))
    metrics=calibration_metrics(ys,ps)|{'rank_reversals':reversals,'messages_sent':net.sent,'messages_delivered':net.delivered,'messages_dropped':net.dropped,'packet_loss_observed':net.dropped/max(1,net.sent),'twin_revisions':twin.revision,'conflicts_detected':len(all_conflicts)}
    return {'seed':seed,'method':method,'world':world,'agents':agents,'twin':twin,'traces':traces,'metrics':metrics}
