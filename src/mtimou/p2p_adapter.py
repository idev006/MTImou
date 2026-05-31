from __future__ import annotations

import importlib
from typing import Iterable, Protocol

from .models import CameraCredentials


class P2PClient(Protocol):
    def connect(self, credentials: CameraCredentials) -> None:
        ...

    def read_stream_chunks(self) -> Iterable[bytes]:
        ...

    def close(self) -> None:
        ...


class PlaceholderDhP2PClient:
    """
    Adaptive adapter for dh-p2p style libraries.
    This keeps our runner stable while we bind to a concrete package API.
    """
    def __init__(self) -> None:
        self._client = None

    def connect(self, credentials: CameraCredentials) -> None:
        mod = self._load_module()
        self._client = self._create_client(mod, credentials)

        # Try common connect/login method names used by reverse-engineered libs.
        for method_name in ("connect", "login", "start", "open"):
            method = getattr(self._client, method_name, None)
            if callable(method):
                try:
                    method()
                    return
                except TypeError:
                    # Some libs require credentials at connect-time.
                    try:
                        method(
                            serial_number=credentials.serial_number,
                            safety_code=credentials.safety_code,
                        )
                        return
                    except TypeError:
                        continue
        raise RuntimeError(
            "Could not connect using known dh-p2p method names. "
            "Please map your library's concrete API in p2p_adapter.py."
        )

    def read_stream_chunks(self) -> Iterable[bytes]:
        if self._client is None:
            raise RuntimeError("Client not connected")

        # Common streaming iterator method names.
        for method_name in ("iter_stream", "stream", "read_stream", "video_stream"):
            method = getattr(self._client, method_name, None)
            if callable(method):
                for item in method():
                    if isinstance(item, (bytes, bytearray)):
                        yield bytes(item)
                return

        # Common pull-based read method names.
        for method_name in ("read", "recv", "recv_packet", "read_packet"):
            method = getattr(self._client, method_name, None)
            if callable(method):
                while True:
                    data = method()
                    if not data:
                        break
                    if isinstance(data, (bytes, bytearray)):
                        yield bytes(data)
                return

        raise RuntimeError(
            "Could not find stream read method on dh-p2p client. "
            "Please map concrete method names in p2p_adapter.py."
        )

    def close(self) -> None:
        if self._client is None:
            return None
        for method_name in ("close", "disconnect", "stop", "logout"):
            method = getattr(self._client, method_name, None)
            if callable(method):
                method()
                return None
        return None

    @staticmethod
    def _load_module():
        candidates = ("dh_p2p", "dhp2p", "dahua_p2p")
        for name in candidates:
            try:
                return importlib.import_module(name)
            except ModuleNotFoundError:
                continue
        raise RuntimeError(
            "dh-p2p module not found. Install your selected wrapper in this venv first."
        )

    @staticmethod
    def _create_client(mod, credentials: CameraCredentials):
        # Try common class names first.
        class_names = ("Client", "P2PClient", "DhP2PClient", "DahuaClient")
        for class_name in class_names:
            cls = getattr(mod, class_name, None)
            if cls is None:
                continue
            try:
                return cls(
                    serial_number=credentials.serial_number,
                    safety_code=credentials.safety_code,
                )
            except TypeError:
                try:
                    return cls(credentials.serial_number, credentials.safety_code)
                except TypeError:
                    try:
                        return cls()
                    except TypeError:
                        continue

        # Fallback: module-level factory.
        for factory_name in ("create_client", "new_client", "get_client"):
            factory = getattr(mod, factory_name, None)
            if callable(factory):
                try:
                    return factory(
                        serial_number=credentials.serial_number,
                        safety_code=credentials.safety_code,
                    )
                except TypeError:
                    try:
                        return factory(credentials.serial_number, credentials.safety_code)
                    except TypeError:
                        continue

        raise RuntimeError(
            "Could not instantiate dh-p2p client. "
            "Please map exact class/factory names in p2p_adapter.py."
        )
