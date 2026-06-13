from __future__ import annotations


class PrivacyPolicy:
    sensitive_keys = {"phone", "address", "id_number", "api_key", "password"}

    def redact(self, payload: dict) -> dict:
        return {key: ("[redacted]" if key in self.sensitive_keys else value) for key, value in payload.items()}
