from ..nope_observable import NopeObservable

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
   
