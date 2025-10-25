import asyncio
import inspect

import pytest


def _shutdown_loop(loop: asyncio.AbstractEventLoop) -> None:
    pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
    for task in pending:
        task.cancel()
    if pending:
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()


@pytest.fixture
def event_loop():
    """Create a fresh event loop for each test.

    pytest-asyncio normally provides this fixture; we replicate the behaviour so
    that async tests can run without requiring the external plugin.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        _shutdown_loop(loop)
        asyncio.set_event_loop(None)


def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool:
    """Execute ``async def`` tests by driving them with ``asyncio``.

    Pytest does not handle coroutine tests unless an async plugin is installed.
    The suite marks async tests with ``@pytest.mark.asyncio``; this hook detects
    coroutine functions and runs them using ``asyncio.run`` so that we do not
    depend on the external plugin at test time.
    """
    test_function = pyfuncitem.obj
    if inspect.iscoroutinefunction(test_function):
        signature = inspect.signature(test_function)
        call_kwargs = {
            name: pyfuncitem.funcargs[name]
            for name in signature.parameters
            if name in pyfuncitem.funcargs
        }
        event_loop = pyfuncitem.funcargs.get("event_loop")
        if event_loop is None:
            event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(event_loop)
            try:
                event_loop.run_until_complete(test_function(**call_kwargs))
            finally:
                _shutdown_loop(event_loop)
                asyncio.set_event_loop(None)
        else:
            event_loop.run_until_complete(test_function(**call_kwargs))
        return True
    return False


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "asyncio: mark test as requiring an asyncio event loop"
    )
