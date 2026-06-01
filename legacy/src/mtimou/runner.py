from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Callable

from .config import AppConfig
from .p2p_adapter import P2PClient


def _log(event: str, **fields: object) -> None:
    payload = {
        "ts_utc": datetime.now(tz=timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    print(json.dumps(payload, ensure_ascii=True))


def run_stream_probe(config: AppConfig, client_factory: Callable[[], P2PClient]) -> None:
    attempt = 0
    backoff = config.backoff_initial_sec
    started = time.time()
    frames_or_chunks = 0

    while attempt < config.max_retries:
        attempt += 1
        client = client_factory()
        try:
            _log("handshake_start", attempt=attempt)
            client.connect(config.credentials)
            _log("handshake_ok", attempt=attempt)

            for chunk in client.read_stream_chunks():
                frames_or_chunks += 1
                _log("stream_chunk", size=len(chunk), count=frames_or_chunks)
                if time.time() - started >= config.stream_probe_seconds:
                    _log("probe_success", total_chunks=frames_or_chunks)
                    client.close()
                    return
            raise RuntimeError("Stream ended unexpectedly")
        except Exception as exc:  # noqa: BLE001
            _log("stream_error", attempt=attempt, error=str(exc))
            try:
                client.close()
            except Exception:  # noqa: BLE001
                pass
            if attempt >= config.max_retries:
                break
            time.sleep(backoff)
            backoff = min(backoff * 2, config.backoff_max_sec)

    raise RuntimeError("Probe failed: max reconnect attempts reached")

