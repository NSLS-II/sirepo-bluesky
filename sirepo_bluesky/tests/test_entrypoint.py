from databroker import Broker


def test_broker():
    db = Broker.named("local")
    return db
