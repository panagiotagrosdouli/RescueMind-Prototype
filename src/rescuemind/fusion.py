from __future__ import annotations
import math
import numpy as np

class Fusion:
    @staticmethod
    def fixed(obs):
        if not obs:return .5,1.
        v=np.array([o.value for o in obs]);return float(v.mean()),float(v.std()+.15)
    @staticmethod
    def reliability(obs):
        if not obs:return .5,1.
        obs=list({o.provenance.observation_id:o for o in obs}.values())
        w=np.array([max(.01,o.reliability)*max(.01,o.confidence) for o in obs]);v=np.array([o.value for o in obs])
        p=float(np.average(v,weights=w));u=float(np.clip(np.average(np.abs(v-p),weights=w)+(1-w.mean())*.3,0,1));return p,u
    @staticmethod
    def bayes(obs,prior=.5):
        logit=math.log(prior/(1-prior));seen=set()
        for o in obs:
            if o.provenance.observation_id in seen:continue
            seen.add(o.provenance.observation_id);p=float(np.clip(.5+(o.value-.5)*o.reliability,.01,.99));logit+=math.log(p/(1-p))
        post=1/(1+math.exp(-np.clip(logit,-20,20)));return float(post),float(1-abs(post-.5)*2)

class ConflictDetector:
    @staticmethod
    def detect(obs):
        out=[];by={o.modality:o for o in obs}
        for a,b in [('thermal','rgb'),('acoustic','thermal'),('radar','thermal')]:
            if a in by and b in by and abs(by[a].value-by[b].value)>.45:
                out.append({'modalities':[a,b],'values':[by[a].value,by[b].value],'confidence':min(by[a].confidence,by[b].confidence),'likely_cause':'environmental degradation or false positive','recommended_next_observation':f'independent {b} confirmation'})
        return out

def calibration_metrics(y,p,bins=5):
    y=np.asarray(y);p=np.clip(np.asarray(p),1e-6,1-1e-6);pred=p>=.5
    tp=((pred==1)&(y==1)).sum();fp=((pred==1)&(y==0)).sum();fn=((pred==0)&(y==1)).sum();tn=((pred==0)&(y==0)).sum()
    precision=tp/max(1,tp+fp);recall=tp/max(1,tp+fn);f1=2*precision*recall/max(1e-9,precision+recall);ece=0.;mce=0.
    for lo,hi in zip(np.linspace(0,1,bins,endpoint=False),np.linspace(0,1,bins+1)[1:]):
        mask=(p>=lo)&(p<(hi if hi<1 else hi+1e-9))
        if mask.any():gap=abs(float(y[mask].mean()-p[mask].mean()));ece+=mask.mean()*gap;mce=max(mce,gap)
    return {'brier':float(np.mean((p-y)**2)),'ece':float(ece),'mce':float(mce),'precision':float(precision),'recall':float(recall),'f1':float(f1),'false_alarm_rate':float(fp/max(1,fp+tn)),'missed_detection_rate':float(fn/max(1,fn+tp))}
