from rescuemind import *

def test_deterministic():
    assert run_simulation(3,5)['metrics']==run_simulation(3,5)['metrics']

def test_reliability_degrades():
    world=DisasterWorld(1);suite=SensorSuite(world);pose=Pose2D(24,27);world.step();q1,_=suite.reliability('rgb',pose,1);world.hazard[27,24]=1;q2,state=suite.reliability('rgb',pose,2);assert q2<q1 and state in {ReliabilityState.DEGRADED,ReliabilityState.UNCERTAIN}

def test_provenance_duplicate_rejection():
    provenance=Provenance('x','a','s');obs=Observation('thermal',.9,.9,.9,0,Pose2D(1,1),1,2,provenance);assert Fusion.reliability([obs,obs])==Fusion.reliability([obs])

def test_stale_rejection_and_conflict():
    buffer=TemporalBuffer(2);first=Observation('thermal',.9,.9,.8,0,Pose2D(0,0),1,1,Provenance('1','a','t'));buffer.add(first);assert not buffer.aligned(3)
    second=Observation('rgb',.1,.9,.8,0,Pose2D(0,0),1,3,Provenance('2','b','r'));assert ConflictDetector.detect([first,second])

def test_priority_decomposition():
    estimate=PriorityModel().score(Hypothesis('S',Pose2D(1,1),.8,.2,urgency=.9,accessibility=.7,hazard=.2),10);assert abs(sum(estimate.decomposition.values())-estimate.score)<1e-9 and estimate.low<estimate.score<estimate.high

def test_allocators_and_loss():
    agents=[Agent('a','UAV',Pose2D(0,0),2,1,10,['thermal']),Agent('b','UGV',Pose2D(9,9),1,1,8,['acoustic'])];targets=[Hypothesis('S',Pose2D(3,3),.8,.3)]
    for method in ['nearest','greedy','information_gain','communication_aware']:assert Allocator.allocate(agents,targets,method)
    network=CommunicationNetwork(0,loss=1);network.send(0,{'x':1});assert network.dropped==1 and not network.receive(2)

def test_end_to_end_core():
    result=run_simulation(2,8,loss=.3);metrics=result['metrics'];assert len(result['agents'])==3 and metrics['twin_revisions']>=16 and metrics['messages_dropped']>0 and 'brier' in metrics
