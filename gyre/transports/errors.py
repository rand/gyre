from __future__ import annotations


class TransportError(RuntimeError):
    """Raised when a transport adapter fails after retries."""

    def __init__(self, transport: str, message: str):
        super().__init__(f"{transport}: {message}")
        self.transport = transport
        self.message = message
