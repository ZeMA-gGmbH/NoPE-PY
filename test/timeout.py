from nope.helpers import get_timestamp, format_exception, get_or_create_eventloop, offload_function_to_event_loop
from nope.event_emitter import NopeEventEmitter
from asyncio import ensure_future, to_thread
from time import sleep

# emitter = NopeEventEmitter()

# def cb(*args):
#     print(get_timestamp(), *args)
#     try:
#         emitter.emit(True)
#     except Exception as e:
#         print(format_exception(e))

# set_timeout(cb, 100)
# set_timeout(cb, 200)
# set_timeout(cb, 300)

# emitter.once(lambda value, rest: print(value,rest))
# emitter.wait_for_update().done(print, lambda *args: print("error"))


async def test_wait_for_update():
    emitter = NopeEventEmitter()

    def timer():        
        try:
            print(get_timestamp())
            sleep(1)
            emitter.emit(True)
            print(get_timestamp())
        except Exception as e:
            print(format_exception(e))

    # set_timeout = offload_function(timer)
    
    try:
        offload_function_to_event_loop(timer)
        value = await emitter.wait_for_update()
    except Exception as e:
        print(format_exception(e))

    print("done")

loop = get_or_create_eventloop()
loop.run_until_complete(test_wait_for_update())
