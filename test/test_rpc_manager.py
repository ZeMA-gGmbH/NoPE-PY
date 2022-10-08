from nope import get_or_create_eventloop, get_layer, NopeRpcManager, format_exception, get_timestamp
from asyncio import sleep


async def main():
    manager = NopeRpcManager({
        "communicator": await get_layer("event"),
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

    await sleep(0.1)

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
    res = await manager.perform_call(["delayed"]*5, ["Pytest"])
    end = get_timestamp()

    delta = []
    bench = 1

    start = get_timestamp()
    for i in range(bench):        
        await manager.perform_call("hello", ["Benchmark"])        
    end = get_timestamp()
    
    print("NOPE",(end-start) / (bench * 1.0),"[ms]")

    bench = 1

    start = get_timestamp()
    for i in range(bench):        
        await hello("Benchmark")
    end = get_timestamp()
    
    print("ORIGINAL",(end-start) / (bench * 1.0),"[ms]")


loop = get_or_create_eventloop()
loop.run_until_complete(main())
