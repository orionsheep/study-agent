from __future__ import annotations


class PromptGuard:
    blocked_terms = ["ignore previous", "泄露系统提示", "sudo rm", "rm -rf /", "curl http://", "wget http://"]

    def check(self, text: str) -> tuple[bool, list[str]]:
        lowered = text.lower()
        issues = [term for term in self.blocked_terms if term in lowered]
        return len(issues) == 0, issues
