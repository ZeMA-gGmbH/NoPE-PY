import asyncio

import pytest

from ..asyncHelpers import EXECUTOR, waitFor


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    EXECUTOR.assignLoop(loop)
    yield loop
    loop.close()


async def test_waitFor():
    counter = 0

    def test():
        nonlocal counter

        counter += 1

        return counter > 5

    await waitFor(test, maxTimeout=1000)
