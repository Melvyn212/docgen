import asyncio
import contextlib
from datetime import timedelta

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from documents.services.metrics import get_metrics


class DocumentMetricsConsumer(AsyncJsonWebsocketConsumer):
    """
    Broadcasts basic document generation metrics (counts by status) to connected clients.
    Intended for lightweight monitoring in the web client without polling.
    """

    async def connect(self):
        await self.accept()
        self._running = True
        await self.send_metrics()
        self._task = asyncio.create_task(self._loop())

    async def disconnect(self, close_code):
        self._running = False
        if hasattr(self, "_task"):
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _loop(self):
        while self._running:
            await asyncio.sleep(3)
            await self.send_metrics()

    async def send_metrics(self):
        metrics = get_metrics()
        if metrics is None:
            await self.send_json(
                {
                    "type": "metrics",
                    "pending": "-",
                    "ready": "-",
                    "failed": "-",
                    "stale_pending": "-",
                    "avg_seconds": None,
                    "total_seconds": None,
                    "docs_per_sec": None,
                    "elapsed_seconds": None,
                }
            )
            return
        await self.send_json(
            {
                "type": "metrics",
                "pending": metrics["pending"],
                "ready": metrics["ready"],
                "failed": metrics["failed"],
                "stale_pending": metrics["stale_pending"],
                "avg_seconds": metrics["avg_seconds"],
                "total_seconds": metrics["total_seconds"],
                "docs_per_sec": metrics["docs_per_sec"],
                "elapsed_seconds": metrics["elapsed_seconds"],
            }
        )
