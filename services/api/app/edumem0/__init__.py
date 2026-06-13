from .schemas import EduMemoryItem, MemoryConflictDecision, MemorySearchRequest


def __getattr__(name: str):
    if name == "EduMem0Client":
        from .client import EduMem0Client

        return EduMem0Client
    raise AttributeError(name)


__all__ = ["EduMem0Client", "EduMemoryItem", "MemoryConflictDecision", "MemorySearchRequest"]
