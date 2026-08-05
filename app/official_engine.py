from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class OfficialEngineError(RuntimeError):
    pass


@dataclass
class EngineStatus:
    ready: bool
    detail: str
    metadata: dict[str, Any]


class OfficialEngine:
    """Persistent Node worker for EN 16931 and Croatian CIUS Schematron rules."""

    def __init__(self) -> None:
        self._process: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()
        self._status = EngineStatus(False, "not started", {})
        self._worker_path = Path(
            os.getenv("OFFICIAL_WORKER_PATH", "/app/node/worker.mjs")
        )
        self._timeout = float(os.getenv("OFFICIAL_ENGINE_TIMEOUT_SECONDS", "20"))

    @property
    def status(self) -> EngineStatus:
        return self._status

    async def start(self) -> None:
        if os.getenv("ENABLE_OFFICIAL_ENGINE", "true").lower() not in {
            "1", "true", "yes", "on"
        }:
            self._status = EngineStatus(False, "disabled by configuration", {})
            return
        try:
            await self._spawn()
            metadata = await self.request("ping")
            self._status = EngineStatus(True, "ready", metadata)
        except Exception as exc:  # readiness exposes the reason without crashing dev mode
            self._status = EngineStatus(False, str(exc), {})
            await self.stop()

    async def _spawn(self) -> None:
        if not self._worker_path.exists():
            raise OfficialEngineError(f"worker not found: {self._worker_path}")
        self._process = await asyncio.create_subprocess_exec(
            "node",
            str(self._worker_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=5_000_000,
        )

    async def stop(self) -> None:
        process = self._process
        self._process = None
        if not process:
            return
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=3)
            except TimeoutError:
                process.kill()
                await process.wait()

    async def _ensure_process(self) -> asyncio.subprocess.Process:
        if self._process and self._process.returncode is None:
            return self._process
        await self._spawn()
        assert self._process is not None
        return self._process

    async def request(self, op: str, **payload: Any) -> dict[str, Any]:
        async with self._lock:
            process = await self._ensure_process()
            if not process.stdin or not process.stdout:
                raise OfficialEngineError("worker pipes are unavailable")
            request_id = str(uuid.uuid4())
            message = json.dumps(
                {"id": request_id, "op": op, **payload},
                separators=(",", ":"),
                ensure_ascii=False,
            )
            process.stdin.write((message + "\n").encode("utf-8"))
            await process.stdin.drain()
            try:
                raw = await asyncio.wait_for(process.stdout.readline(), self._timeout)
            except TimeoutError as exc:
                await self.stop()
                raise OfficialEngineError("official validator timed out") from exc
            if not raw:
                stderr = ""
                if process.stderr:
                    try:
                        stderr = (await asyncio.wait_for(process.stderr.read(), 0.2)).decode(
                            "utf-8", errors="replace"
                        )[-2000:]
                    except TimeoutError:
                        pass
                await self.stop()
                raise OfficialEngineError(f"official validator stopped unexpectedly: {stderr}")
            response = json.loads(raw)
            if response.get("id") != request_id:
                raise OfficialEngineError("worker response ID mismatch")
            if not response.get("ok"):
                raise OfficialEngineError(response.get("error", "official validator failed"))
            return response["result"]
