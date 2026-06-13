# EduMem0 Adapter

Mem0 is used as the design base. The project includes `Mem0CompatibleAdapter` with `add`, `search`, `update`, and `delete` shaped operations over the persistent EduMem0 store.

This local adapter is used because the real external Mem0 dependency is not required for the runnable product contract. It preserves the expected semantics while adding education-specific confidence, evidence, conflict, and decay policies.
