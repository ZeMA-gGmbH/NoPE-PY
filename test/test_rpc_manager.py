import asyncio
from asyncio import sleep

import yappi
import time

import pytest

from nope import getLayer, NopeRpcManager, formatException, getTimestamp, EXECUTOR

IN_PY_TEST = False


@pytest.fixture
def event_loop():
    global IN_PY_TEST
    IN_PY_TEST = True
    loop = asyncio.new_event_loop()
    EXECUTOR.assignLoop(loop)
    yield loop
    loop.close()


async def main():
    manager = NopeRpcManager({
        "communicator": await getLayer("event"),
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

    if not IN_PY_TEST:
        delta = []
        bench = 100000

        start = time.process_time()
        for i in range(bench):
            #s = time.process_time()
            await manager.performCall("hello", ["Benchmark"])
            #delta = (time.process_time() - s) * 1000
            #print(i, "mainloop:", delta, "[ms]")
        end = time.process_time()
        delta = end - start
        print(delta, bench)
        time_per_call = delta * 1000 / bench
        qps = 1000.0 / time_per_call

        print(
            "NOPE    ",
            round(
                time_per_call,
                5),
            "[ms] ->",
            round(
                qps,
                5),
            "[R/s]")

        start = getTimestamp()
        for i in range(bench):
            await hello("delayed")
        end = getTimestamp()
        delta = end - start
        time_per_call = delta / bench
        qps = 1000.0 / time_per_call

        print(
            "ORIGINAL",
            round(
                time_per_call,
                5),
            "[ms] ->",
            round(
                qps,
                5),
            "[R/s]")

    # await manager.dispose()

if __name__ == "__main__":
    EXECUTOR.loop.run_until_complete(main())
    # EXECUTOR.loop.run_forever()

# yappi.set_clock_type("CPU")
# with yappi.run():
#     EXECUTOR.loop.run_until_complete(main())
# yappi.get_func_stats().print_all()
