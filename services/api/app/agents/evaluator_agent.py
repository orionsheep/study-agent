from __future__ import annotations

from pydantic import BaseModel

from app.agents.base import AgentOutput
from app.database.store import get_store
from app.edumem0.mastery_memory import mastery_memory
from app.edumem0.misconception_memory import misconception_memory
from app.schemas.app_protocol import QuizSubmission


class EvaluatorAgentInput(BaseModel):
    student_id: str
    question_id: str
    answer: object
    course_id: str = "ai-course"


class EvaluatorAgent:
    name = "evaluator_agent"

    def run(self, data: EvaluatorAgentInput) -> AgentOutput:
        store = get_store()
        question = store.get_quiz_question(data.question_id)
        if not question:
            return AgentOutput(summary="题目不存在。", payload={"error": "question_missing"}, trace=["question_missing"])
        is_correct = data.answer == question.answer
        evaluation = {
            "expected": question.answer,
            "explanation": question.explanation,
            "misconception_tags": [] if is_correct else question.misconception_tags,
        }
        submission = QuizSubmission(student_id=data.student_id, question_id=data.question_id, answer=data.answer, is_correct=is_correct, evaluation=evaluation)
        store.save_quiz_submission(submission)
        score = store.upsert_mastery(
            data.student_id,
            data.course_id,
            question.knowledge_point_id or "kp-optimization",
            0.12 if is_correct else -0.1,
            evaluation,
        )
        memories = [mastery_memory(data.student_id, question.knowledge_point_id or "kp-optimization", score, course_id=data.course_id)]
        if not is_correct:
            memories.append(
                misconception_memory(
                    data.student_id,
                    question.knowledge_point_id or "kp-optimization",
                    question.misconception_tags,
                    course_id=data.course_id,
                )
            )
        for memory in memories:
            store.create_memory(memory)
        return AgentOutput(
            summary="答对了，掌握度上升。" if is_correct else "这题暴露了学习率稳定性误区，我已更新弱点和复习路径。",
            payload={"submission": submission.model_dump(), "memories": [item.model_dump() for item in memories], "mastery_score": score},
            trace=["graded_quiz", "updated_mastery", "wrote_memory", "triggered_path_refresh"],
        )
