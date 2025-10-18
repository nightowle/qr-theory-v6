from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Counter:
    name: str
    description: str
    value: int = 0

    def inc(self, amount: int = 1) -> None:
        self.value += amount


@dataclass
class Gauge:
    name: str
    description: str
    value: float = 0.0

    def set(self, value: float) -> None:
        self.value = value


@dataclass
class Histogram:
    name: str
    description: str
    buckets: Dict[str, int] = field(default_factory=dict)

    def observe(self, bucket: str) -> None:
        self.buckets[bucket] = self.buckets.get(bucket, 0) + 1


class MetricsRegistry:
    """Einfache In-Memory-Metrikverwaltung ohne externe Abhängigkeiten."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}

    async def counter(self, name: str, description: str) -> Counter:
        async with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name=name, description=description)
            return self._counters[name]

    async def gauge(self, name: str, description: str) -> Gauge:
        async with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name=name, description=description)
            return self._gauges[name]

    async def histogram(self, name: str, description: str) -> Histogram:
        async with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name=name, description=description)
            return self._histograms[name]

    async def snapshot(self) -> Dict[str, Dict[str, object]]:
        async with self._lock:
            return {
                "counters": {name: counter.value for name, counter in self._counters.items()},
                "gauges": {name: gauge.value for name, gauge in self._gauges.items()},
                "histograms": {name: dict(hist.buckets) for name, hist in self._histograms.items()},
            }


__all__ = ["MetricsRegistry", "Counter", "Gauge", "Histogram"]
