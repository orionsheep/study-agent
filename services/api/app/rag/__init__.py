from __future__ import annotations

from typing import Any

__all__ = ["CourseRetriever"]


def __getattr__(name: str) -> Any:
    if name == "CourseRetriever":
        from .retriever import CourseRetriever

        return CourseRetriever
    raise AttributeError(name)
