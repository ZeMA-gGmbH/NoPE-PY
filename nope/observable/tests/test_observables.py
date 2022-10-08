from ..nope_observable import NopeObservable
from ...helpers import format_exception, offload_function_to_event_loop

def test_once():
    called = 0

    def callback(data, *args, **kwargs):
        nonlocal called
        called += 1

    observable = NopeObservable()
    observable.once(callback)

    observable.set_content(1)

    assert called == 1

def test_inital_value():
    called = 0

    def callback(data, *args, **kwargs):
        nonlocal called
        called += 1

    observable = NopeObservable()
    observable.set_content("This is a Test!")
    observable.subscribe(callback)
    observable.set_content(1)

    assert called == 2
    assert observable.get_content() == 1

def test_change_detection():
    called = 0

    def callback(data, *args, **kwargs):
        nonlocal called
        called += 1

    observable = NopeObservable()
    observable.set_content(1)
    observable.subscribe(callback)
    observable.set_content(1)
    observable.set_content(1)
    observable.set_content(1)    
    observable.set_content(2)

    assert called == 2    
    assert observable.get_content() == 2

def test_setter():
    def callback(data, *args, **kwargs):
        assert data == "Hello World!"

    def setter(data, rest):
        return {
            "valid": True,
            "data": f"Hello {data}!"
        }

    observable = NopeObservable()
    observable.setter = setter
    observable.subscribe(callback)

    observable.set_content("World")

def test_getter():
    def callback(data, *args, **kwargs):
        assert data == "Hello World!"

    def getter(data):
        return f"{data}!"

    observable = NopeObservable()
    observable.getter = getter
    sub = observable.subscribe(callback)

    observable.set_content("Hello World")

def test_options():
    called = 0

    def callback(data, *args, **kwargs):
        nonlocal called
        called += 1

    observable = NopeObservable()
    observable.set_content(1) 
    sub = observable.subscribe(callback, {"skip_current": True})    
    observable.set_content(2) 

    assert called == 1, "Failed to skip the current value"


async def test_wait_for():
    import asyncio
    import time

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    obs = NopeObservable()
    obs.set_content(True)

    await obs.wait_for()

    obs.set_content(False)

    def change_value():
        try:
            time.sleep(0.1)
            obs.set_content(True)
        except Exception as e:
            print(format_exception(e))

    try:
        offload_function_to_event_loop(change_value)

        await obs.wait_for()
    except Exception as e:
        print(format_exception(e))
   
