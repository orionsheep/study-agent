from __future__ import annotations


class ModelGatewayError(RuntimeError):
    pass


class ProviderBlocked(ModelGatewayError):
    def __init__(self, code: str, reason: str) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason


class StructuredOutputError(ModelGatewayError):
    pass
