import asyncio
from asyncio import sleep

import pytest

from ..rpcManager import NopeRpcManager
from ...communication import getLayer
from ...helpers import EXECUTOR


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    EXECUTOR.assignLoop(loop)
    yield loop
    loop.close()


async def test_rpc_manager():
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

    await manager.registerService(hello, {
        "id": "hello"
    })

    await manager.registerService(delayed, {
        "id": "delayed"
    })

    await sleep(0.1)

    assert "hello" in manager.services.extracted_key, "Failed to register the services"
    assert "delayed" in manager.services.extracted_key, "Failed to register the services"

    # Try calling the Service
    res = await manager.performCall("hello", ["Pytest"])
    assert res == "Hello Pytest!"

    res = await manager.performCall("delayed", ["Pytest"])
    assert res == "Hello Pytest!"
