from time import sleep

from nope.eventEmitter import NopeEventEmitter
from nope.helpers import getTimestamp, formatException, getOrCreateEventloop, offload_function_to_event_loop


# emitter = NopeEventEmitter()

# def cb(*args):
#     print(getTimestamp(), *args)
#     try:
#         emitter.emit(True)
#     except Exception as e:
#         print(formatException(e))

# setTimeout(cb, 100)
# setTimeout(cb, 200)
# setTimeout(cb, 300)

# emitter.once(lambda value, rest: print(value,rest))
# emitter.waitForUpdate().done(print, lambda *args: print("error"))


async def test_waitForUpdate():
    emitter = NopeEventEmitter()

    def timer():
        try:
            print(getTimestamp())
            sleep(1)
            emitter.emit(True)
            print(getTimestamp())
        except Exception as e:
            print(formatException(e))

    # setTimeout = offload_function(timer)

    try:
        offload_function_to_event_loop(timer)
        value = await emitter.waitForUpdate()
    except Exception as e:
        print(formatException(e))

    print("done")


loop = getOrCreateEventloop()
loop.run_until_complete(test_waitForUpdate())
