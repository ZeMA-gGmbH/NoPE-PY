from asyncio import sleep

import pytest

from nope import get_layer, NopeRpcManager, format_exception, get_timestamp, EXECUTOR


@pytest.fixture
def event_loop():
    loop = EXECUTOR.loop
    yield loop


async def main():
    manager = NopeRpcManager({
        "communicator": await get_layer("io-client"),
        "logger": False,
    }, lambda *args: "test", "test")

    await manager.ready.wait_for()

    async def hello(name: str) -> str:
        return f"Hello {name}!"

    async def delayed(name: str) -> str:
        await sleep(1)
        return await hello(name)

    manager.register_service(hello, {
       "id": "hello"
    })

    manager.register_service(delayed, {
        "id": "delayed"
    })

    await sleep(0.5)

    assert "hello" in manager.services.extracted_key, "Failed to register the services"
    assert "delayed" in manager.services.extracted_key, "Failed to register the services"

    # Try calling the Service
    res = await manager.perform_call("hello", ["Pytest"])
    res = await manager.perform_call("hello", ["Pytest"])
    assert res == "Hello Pytest!"

    try:
        res = await manager.perform_call("delayed", ["Pytest"], {"timeout": 2000})
        assert res == "Hello Pytest!"
    except Exception as error:
        print("HERE", error)

    try:
        res = await manager.perform_call("delayed", ["Pytest"], {"timeout": 200})
        assert res == "Hello Pytest!"
    except Exception as error:
        print(format_exception(error))

    start = get_timestamp()
    res = await manager.perform_call(["delayed"] * 5, ["Pytest"])
    end = get_timestamp()

    delta = []
    bench = 100

    start = get_timestamp()
    for i in range(bench):
        await manager.perform_call("hello", ["Benchmark"])
    end = get_timestamp()
    delta = end-start
    time_per_call = delta / bench
    qps = 1000.0 / time_per_call

    print("NOPE    ", round(time_per_call, 5), "[ms] ->", round(qps, 5), "[R/s]" )


    bench = 10000

    start = get_timestamp()
    for i in range(bench):
        await hello("delayed")
    end = get_timestamp()
    delta = end-start
    time_per_call = delta / bench
    qps = 1000.0 / time_per_call

    print("ORIGINAL", round(time_per_call, 5), "[ms] ->", round(qps, 5), "[R/s]" )

EXECUTOR.loop.run_until_complete(main())
EXECUTOR.run()