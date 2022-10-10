from asyncio import sleep

import yappi, time

import pytest

from nope import getLayer, NopeRpcManager, formatException, getTimestamp, EXECUTOR


@pytest.fixture
def event_loop():
    loop = EXECUTOR.loop
    yield loop


async def main():
    manager = NopeRpcManager({
        "communicator": await getLayer("io-client"),
        "logger": False,
    }, lambda *args: "test", "test")

    await manager.ready.waitFor()

    async def hello(name: str) -> str:
        return f"Hello {name}!"

    async def delayed(name: str) -> str:
        await sleep(1)
        return await hello(name)

    manager.registerService(hello, {
       "id": "hello"
    })

    manager.registerService(delayed, {
        "id": "delayed"
    })

    await sleep(1.5)

    assert "hello" in manager.services.extracted_key, "Failed to register the services"
    assert "delayed" in manager.services.extracted_key, "Failed to register the services"

    # Try calling the Service
    res = await manager.performCall("hello", ["Pytest"])
    assert res == "Hello Pytest!"

    try:
        res = await manager.performCall("delayed", ["Pytest"], {"timeout": 2000})
        assert res == "Hello Pytest!"
    except Exception as error:
        print("HERE", error)

    try:
        res = await manager.performCall("delayed", ["Pytest"], {"timeout": 200})
        assert res == "Hello Pytest!"
    except Exception as error:
        print(formatException(error))

    start = getTimestamp()
    res = await manager.performCall(["delayed"] * 5, ["Pytest"])
    end = getTimestamp()

    if False:
        delta = []
        bench = 10

        start = time.process_time()
        for i in range(bench):
            #s = time.process_time()
            await manager.performCall("hello", ["Benchmark"])
            #delta = (time.process_time() - s) * 1000
            #print(i, "mainloop:", delta, "[ms]")
        end = time.process_time()
        delta = end-start
        print(delta, bench)
        time_per_call = delta*1000 / bench
        qps = 1000.0 / time_per_call

        print("NOPE    ", round(time_per_call, 5), "[ms] ->", round(qps, 5), "[R/s]" )


        bench = 10

        start = getTimestamp()
        for i in range(bench):
            await hello("delayed")
        end = getTimestamp()
        delta = end-start
        time_per_call = delta / bench
        qps = 1000.0 / time_per_call

        print("ORIGINAL", round(time_per_call, 5), "[ms] ->", round(qps, 5), "[R/s]" )
    

    #await manager.dispose()

EXECUTOR.loop.run_until_complete(main())
EXECUTOR.loop.run_forever()

# yappi.set_clock_type("CPU")
# with yappi.run():
#     EXECUTOR.loop.run_until_complete(main())
# yappi.get_func_stats().print_all()

