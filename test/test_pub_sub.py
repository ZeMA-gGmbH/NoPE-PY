from nope import PubSubSystem, NopeEventEmitter

called = 0

pub_sub = PubSubSystem()

publisher = NopeEventEmitter()
subscriber = NopeEventEmitter()

pub_sub.register(publisher, {
    "mode": "publish",
    "schema": {},
    "topic": "this/is/a/test",
})

pub_sub.register(subscriber, {
    "mode": "subscribe",
    "schema": {},
    "topic": "this/#",
})


def callback(data, rest):
    global called
    called += 1
    assert data == "Hello World"

def incremental(data, rest):
    print(data, rest)


pub_sub.onIncrementalDataChange.subscribe(incremental)

subscriber.subscribe(callback)
publisher.emit("Hello World")

assert called == 1
