from asyncio import sleep

import pytest

from ...communication import getLayer
from ..rpc_manager import NopeRpcManager
from ...helpers import EXECUTOR


@pytest.fixture
def event_loop():
    loop = EXECUTOR.loop
    yield loop


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

    manager.registerService(hello, {
        "id": "hello"
    })

    manager.registerService(delayed, {
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
