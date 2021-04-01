from databroker import Broker
#from bluesky import RunEngine
#from bluesky.callbacks.best_effort import BestEffortCallback


#RE = RunEngine()
#bec = BestEffortCallback()
#RE.subscribe(bec)
#db = Broker.named('bluesky-cartpole')
#db = Broker.named('sirepo-bluesky')
def test_broker():
	db = Broker.named("local")

#RE.subscribe(db.insert)

