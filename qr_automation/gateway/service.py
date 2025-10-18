from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import List, Optional

from ..chat.models import ChatMessage
from .config import GatewayConfig, load_gateway_config
from .manager import GatewayManager


@dataclass
class GatewayRequest:
    adapter_name: str
    message: ChatMessage
    future: "asyncio.Future[Optional[dict]]"


class GatewayService:
    """Gateway mit Warteschlange, Rate-Limiting und Cache-Unterstützung."""

    def __init__(self, manager: GatewayManager, config: GatewayConfig) -> None:
        self.manager = manager
        self.config = config
        self._queue: "asyncio.Queue[GatewayRequest | None]" = asyncio.Queue(
            maxsize=config.queue_size
        )
        self._workers: List[asyncio.Task[None]] = []
        self._queue_gauge = None
        self._running = False
        self._start_lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._start_lock:
            if self._running:
                return
            await self.manager.reload_from_config(self.config)
            metrics = self.manager._metrics  # Zugriff auf Registry für Queue-Beobachtung
            self._queue_gauge = await metrics.gauge(
                "gateway_queue_depth",
                "Aktuelle Auslastung der Gateway-Warteschlange",
            )
            for _ in range(self.config.concurrency):
                self._workers.append(asyncio.create_task(self._worker_loop()))
            self._running = True

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        for _ in self._workers:
            await self._queue.put(None)
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def submit(self, adapter_name: str, message: ChatMessage) -> Optional[dict]:
        if not self._running:
            await self.start()
        loop = asyncio.get_running_loop()
        future: "asyncio.Future[Optional[dict]]" = loop.create_future()
        await self._queue.put(GatewayRequest(adapter_name=adapter_name, message=message, future=future))
        self._update_queue_metric()
        return await future

    async def apply_config(self, config: GatewayConfig) -> None:
        self.config = config
        await self.manager.reload_from_config(config)
        if not self._running:
            self._queue = asyncio.Queue(maxsize=config.queue_size)
        else:
            if self._queue.qsize() > config.queue_size:
                # In laufender Konfiguration priorisieren wir bestehende Elemente
                pass
            new_queue: "asyncio.Queue[GatewayRequest | None]" = asyncio.Queue(maxsize=config.queue_size)
            while not self._queue.empty():
                try:
                    item = self._queue.get_nowait()
                    new_queue.put_nowait(item)
                except asyncio.QueueEmpty:  # pragma: no cover - seltene Rennbedingung
                    break
                finally:
                    self._queue.task_done()
            self._queue = new_queue

    def _update_queue_metric(self) -> None:
        if self._queue_gauge is not None:
            self._queue_gauge.set(float(self._queue.qsize()))

    async def _worker_loop(self) -> None:
        while True:
            request = await self._queue.get()
            if request is None:
                self._queue.task_done()
                break
            try:
                response = await self.manager.dispatch(request.adapter_name, request.message)
                if not request.future.done():
                    request.future.set_result(response)
            except Exception as exc:  # pragma: no cover - Fehlerpfade werden im Test geprüft
                if not request.future.done():
                    request.future.set_exception(exc)
            finally:
                self._queue.task_done()
                self._update_queue_metric()


async def build_gateway_service_from_file(config_path: str | bytes | None) -> GatewayService:
    if config_path is None:
        raise ValueError("Konfigurationspfad darf nicht None sein")
    config = load_gateway_config(config_path)
    manager = GatewayManager()
    service = GatewayService(manager, config)
    return service


__all__ = ["GatewayService", "GatewayRequest", "build_gateway_service_from_file"]
