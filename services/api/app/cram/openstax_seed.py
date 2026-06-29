from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ExamMode = Literal["conceptual_cram", "practice_heavy"]


class OpenStaxCramBook(BaseModel):
    slug: str
    title: str
    subject: str
    provider: str = "openstax"
    exam_mode: ExamMode
    details_url: str
    web_url: str
    pdf_url: str
    license: str = "OpenStax open textbook"
    tags: list[str] = Field(default_factory=list)


def _book(slug: str, title: str, subject: str, exam_mode: ExamMode, web_path: str, pdf_name: str, tags: list[str]) -> OpenStaxCramBook:
    return OpenStaxCramBook(
        slug=slug,
        title=title,
        subject=subject,
        exam_mode=exam_mode,
        details_url=f"https://openstax.org/details/books/{slug}",
        web_url=f"https://openstax.org/books/{slug}/pages/{web_path}",
        pdf_url=f"https://assets.openstax.org/oscms-prodcms/media/documents/{pdf_name}",
        tags=tags,
    )


OPENSTAX_CRAM_BOOKS: list[OpenStaxCramBook] = [
    _book("principles-management", "Principles of Management", "Business", "conceptual_cram", "1-introduction", "principles-management_-_WEB.pdf", ["management", "case_analysis"]),
    _book("organizational-behavior", "Organizational Behavior", "Business", "conceptual_cram", "1-introduction", "organizational-behavior_-_WEB.pdf", ["management", "psychology"]),
    _book("business-ethics", "Business Ethics", "Business", "conceptual_cram", "1-introduction", "business-ethics_-_WEB.pdf", ["ethics", "case_analysis"]),
    _book("introduction-business", "Introduction to Business", "Business", "conceptual_cram", "1-introduction", "IntroductionToBusiness-OP_8D04gAa.pdf", ["business", "survey"]),
    _book("psychology-2e", "Psychology 2e", "Social Sciences", "conceptual_cram", "1-introduction", "Psychology2e_WEB.pdf", ["psychology", "concepts"]),
    _book("introduction-sociology-3e", "Introduction to Sociology 3e", "Social Sciences", "conceptual_cram", "1-introduction", "introduction-sociology-3e_-_WEB.pdf", ["sociology", "theory"]),
    _book("american-government-3e", "American Government 3e", "Social Sciences", "conceptual_cram", "1-introduction", "AmericanGovernment3e-WEB.pdf", ["politics", "definitions"]),
    _book("principles-economics-3e", "Principles of Economics 3e", "Social Sciences", "conceptual_cram", "1-introduction", "principles-economics-3e_-_WEB.pdf", ["economics", "mixed"]),
    _book("principles-macroeconomics-3e", "Principles of Macroeconomics 3e", "Business", "conceptual_cram", "1-introduction", "principles-macroeconomics-3e_-_WEB.pdf", ["economics", "graphs"]),
    _book("principles-microeconomics-3e", "Principles of Microeconomics 3e", "Business", "conceptual_cram", "1-introduction", "principles-microeconomics-3e_-_WEB.pdf", ["economics", "graphs"]),
    _book("biology-2e", "Biology 2e", "Science", "conceptual_cram", "1-introduction", "Biology-2e_-_WEB.pdf", ["biology", "terms"]),
    _book("anatomy-and-physiology-2e", "Anatomy and Physiology 2e", "Science", "conceptual_cram", "1-introduction", "anatomy-and-physiology-2e_-_WEB.pdf", ["medicine", "memory"]),
    _book("microbiology", "Microbiology", "Science", "conceptual_cram", "1-introduction", "microbiology_-_WEB.pdf", ["medicine", "terms"]),
    _book("chemistry-2e", "Chemistry 2e", "Science", "practice_heavy", "1-introduction", "chemistry-2e_-_WEB.pdf", ["chemistry", "calculation"]),
    _book("university-physics-volume-1", "University Physics Volume 1", "Science", "practice_heavy", "1-introduction", "university-physics-volume-1_-_WEB.pdf", ["physics", "calculation"]),
    _book("university-physics-volume-2", "University Physics Volume 2", "Science", "practice_heavy", "1-introduction", "university-physics-volume-2_-_WEB.pdf", ["physics", "calculation"]),
    _book("university-physics-volume-3", "University Physics Volume 3", "Science", "practice_heavy", "1-introduction", "university-physics-volume-3_-_WEB.pdf", ["physics", "calculation"]),
    _book("college-physics-2e", "College Physics 2e", "Science", "practice_heavy", "1-introduction-to-science-and-the-realm-of-physics-physical-quantities-and-units", "college-physics-2e_-_WEB.pdf", ["physics", "practice"]),
    _book("calculus-volume-1", "Calculus Volume 1", "Math", "practice_heavy", "1-introduction", "calculus-volume-1_-_WEB.pdf", ["math", "proof"]),
    _book("calculus-volume-2", "Calculus Volume 2", "Math", "practice_heavy", "1-introduction", "calculus-volume-2_-_WEB.pdf", ["math", "proof"]),
    _book("calculus-volume-3", "Calculus Volume 3", "Math", "practice_heavy", "1-introduction", "calculus-volume-3_-_WEB.pdf", ["math", "proof"]),
    _book("college-algebra-2e", "College Algebra 2e", "Math", "practice_heavy", "1-introduction-to-prerequisites", "college-algebra-2e_-_WEB.pdf", ["math", "practice"]),
    _book("statistics", "Statistics", "Math", "practice_heavy", "1-introduction", "high-school-statistics_-_WEB.pdf", ["statistics", "practice"]),
    _book("introduction-philosophy", "Introduction to Philosophy", "Humanities", "conceptual_cram", "1-introduction", "Introduction_to_Philosophy-WEB.pdf", ["philosophy", "essay"]),
]


def openstax_book_seed_payload() -> list[dict[str, Any]]:
    return [book.model_dump() for book in OPENSTAX_CRAM_BOOKS]
