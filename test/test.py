from nope.helpers import extractUniqueValues
from nope.merging import MergeData, DictBasedMergeData
from nope.observable import NopeObservable

called = 0


def callback(data, *args, **kwargs):
    global called
    called += 1


observable = NopeObservable()
observable.setContent(1)
sub = observable.subscribe(callback, {"skipCurrent": True})
observable.setContent(2)

d = {
    "a": {
        "a": [
            {
                "content": "a",
                "id": 1,
            },
            {
                "content": "b",
                "id": 2,
            },
        ], },
    "b": {
        "a": [
            {
                "content": "c",
                "id": 1,
            },
            {
                "content": "d",
                "id": 3,
            },
        ]
    }
}
res = extractUniqueValues(d, "a/+/content", "a/+/id")

d = dict()
merge = MergeData(d, lambda m: extractUniqueValues(m))

called = 0


def callback_01(data, *args, **kwargs):
    global called
    called += 1


merge.data.subscribe(callback_01)

d["a"] = "b"
d["b"] = "b"

merge.update()
merge.update()

r = merge.data.getContent()
assert called == 2, "Called the subscription twice"

d = {
    "a": {"key": "keyA", "data": "dataA"},
    "b": {"key": "keyB", "data": "dataB"}
}
merge = DictBasedMergeData(d, "data", "key")
merge.update()
print("H")
