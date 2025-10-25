from __future__ import annotations

import asyncio
import inspect
import sys
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any, Callable

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Stellt einen frischen asyncio-Event-Loop pro Test bereit."""

    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.run_until_complete(_shutdown_loop(loop))
        loop.close()


async def _shutdown_loop(loop: asyncio.AbstractEventLoop) -> None:
    current = asyncio.current_task(loop=loop)
    pending = [
        task
        for task in asyncio.all_tasks(loop=loop)
        if task is not current and not task.done()
    ]
    if not pending:
        return
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """Ermöglicht Ausführung von ``async def``-Tests ohne pytest-asyncio-Plugin."""

    test_obj = pyfuncitem.obj
    if not inspect.iscoroutinefunction(test_obj):
        return None

    loop: asyncio.AbstractEventLoop | None = pyfuncitem.funcargs.get("event_loop")
    if loop is None:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_call_async_test(test_obj, pyfuncitem.funcargs))
        finally:
            loop.run_until_complete(_shutdown_loop(loop))
            loop.close()
    else:
        loop.run_until_complete(_call_async_test(test_obj, pyfuncitem.funcargs))
    return True


async def _call_async_test(
    func: Callable[..., AsyncGenerator[Any, None] | Any],
    funcargs: dict[str, Any],
) -> None:
    signature = inspect.signature(func)
    accepted_args = {
        name: funcargs[name]
        for name in signature.parameters.keys()
        if name in funcargs
    }
    result = func(**accepted_args)
    if inspect.isasyncgen(result):
        async for _ in result:
            pass
    elif inspect.isawaitable(result):
        await result
    else:
        raise TypeError("Async-Testfunktion hat kein awaitable Ergebnis geliefert")
