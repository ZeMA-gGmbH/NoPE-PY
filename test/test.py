from nope.observables import NopeObservable
from nope.helpers import extract_unique_values
from nope.merging import MergeData,DictBasedMergeData
called = 0

def callback(data, *args, **kwargs):
    global called
    called += 1

observable = NopeObservable()
observable.set_content(1) 
sub = observable.subscribe(callback, {"skip_current": True})    
observable.set_content(2) 

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
res = extract_unique_values(d, "a/+/content", "a/+/id")


d = dict()
merge = MergeData(d, lambda m: extract_unique_values(m))

called = 0

def callback_01(data, *args, **kwargs):
    global called
    called += 1

merge.data.subscribe(callback_01)

d["a"]="b"
d["b"]="b"

merge.update()
merge.update()

r = merge.data.get_content()
assert called == 2, "Called the subscription twice"

d = {
    "a": { "key": "keyA", "data": "dataA" },
    "b": { "key": "keyB", "data": "dataB" }
}
merge = DictBasedMergeData(d, "data", "key")
merge.update()
print("H")