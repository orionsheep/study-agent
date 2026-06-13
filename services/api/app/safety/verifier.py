from __future__ import annotations

from typing import Any

from app.safety.prompt_guard import PromptGuard
from app.schemas.app_protocol import LearningResource, VerifierResult


class ResourceVerifier:
    def __init__(self) -> None:
        self.guard = PromptGuard()

    def verify_source_refs(self, source_refs: list[dict[str, Any]]) -> tuple[bool, list[str], float]:
        if not source_refs:
            return False, ["missing_source_refs"], 0.0
        confidence = sum(float(ref.get("confidence", 0)) for ref in source_refs) / len(source_refs)
        invalid = [ref for ref in source_refs if not ref.get("document_id") or not ref.get("chunk_id") or not ref.get("course_id")]
        if invalid:
            return False, ["invalid_source_ref"], round(confidence, 3)
        return True, [], round(min(1.0, confidence), 3)

    def verify_quiz_consistency(self, resource: LearningResource) -> tuple[bool, list[str]]:
        if resource.type != "quiz":
            return True, []
        questions = resource.content.get("questions", [])
        issues: list[str] = []
        for question in questions:
            if question.get("answer") is None or not question.get("explanation"):
                issues.append("quiz_answer_or_explanation_missing")
        return len(issues) == 0, issues

    def verify_code_safety(self, text: str) -> tuple[bool, list[str]]:
        blocked, issues = self.guard.check(text)
        dangerous = [term for term in ["subprocess", "os.system", "eval(", "exec("] if term in text]
        return blocked and not dangerous, issues + dangerous

    def verify(self, resource: LearningResource) -> VerifierResult:
        ok_refs, ref_issues, coverage = self.verify_source_refs(resource.source_refs)
        ok_quiz, quiz_issues = self.verify_quiz_consistency(resource)
        ok_guard, guard_issues = self.guard.check(str(resource.content))
        ok_code, code_issues = self.verify_code_safety(str(resource.content)) if resource.type == "code_practice" else (True, [])
        issues = ref_issues + quiz_issues + guard_issues + code_issues
        passed = ok_refs and ok_quiz and ok_guard and ok_code
        score = 0.92 if passed else 0.32
        return VerifierResult(
            passed=passed,
            score=score,
            issues=issues,
            source_coverage=coverage,
            profile_fit=0.86 if passed else 0.4,
            safety="pass" if passed else "fail",
        )
