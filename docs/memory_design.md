# EduMem0 Memory Design

EduMem0 is an education-specific persistent memory wrapper inspired by Mem0-style add/search/update/delete operations. It stores profile, mastery, misconception, resource preference, learning event, path, agent state, spatial layout, app interaction, resource feedback, session summary, and tutor pedagogy memories.

Every memory item includes student/course linkage, memory type, structured payload, confidence, importance, decay rate, evidence type, source event, source agent, validity window, tags, timestamps, and version.

Policy coverage:

- Chat evidence starts low confidence; repeated evidence rises.
- Quiz and teacher-confirmed evidence carry higher confidence.
- Contradictions lower stale confidence and produce conflict decisions.
- Mastery/misconception decay over time; stable profile and spatial layout do not decay aggressively.
- Task-specific retrieval serves profile, planner, tutor, resource generation, dashboard, and canvas contexts.
