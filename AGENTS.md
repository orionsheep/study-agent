## Global Output Rule

- When the user asks to generate an HTML report, save the `.html` file under `/Users/mychanging/Desktop/HTML报告/` by default.
- If that folder does not exist, create it first.
- Unless the user explicitly specifies another output path, do not place generated HTML reports on the desktop root or in the current working directory.

## WeChat Chat History Rule（微信聊天记录规则）

**ONLY use `wechat-cli` for WeChat chat history. Never start a FastAPI backend or decrypt SQLCipher databases manually.**

- CLI path: `/Users/mychanging/.npm-global/bin/wechat-cli`
- Commands: `sessions`, `history`, `search`, `export`, `contacts`, `members`, `new-messages`

```bash
wechat-cli history "联系人名" --limit 200
wechat-cli contacts --query "名字"
wechat-cli sessions --limit 10
```

If a new database (message_1.db, etc.) is missing its key, run:

```bash
echo "320981" | sudo -S wechat-cli init --force
```

Then retry the original command. Do NOT fall back to the FastAPI backend.

## General Agent Rule（通用 Agent 规则）

- Do not fix generation failures by overfitting to one prompt, one subject, one screenshot, or one demo topic.
- LearnForge is a general agent system: fixes must improve the contract, planner, prompt, parser, verifier, materializer, or runtime path for the whole capability class.
- Topic-specific examples may appear only in prompts, tests, or quality criteria when they protect against known regressions; they must not become hardcoded product logic unless the capability itself is explicitly topic-specific.
- If an artifact is missing, first investigate why the upstream planner/runtime/model/parser failed to produce it. Fallback generation is only a last-resort reliability guard, not the primary solution.

## Hermes-First Core Agent Rule（核心 Agent 规则）

- All core Agent decisions and generation tasks must be executed by Hermes: intent interpretation, capability choice, skill selection, planning, and real-time artifact generation.
- Do not add or expand an outer Python product-intent router for chat requests. Python may only provide service shell responsibilities: API/SSE/session handling, memory/context loading, tool adapters, persistence, validation gates, and unavoidable script integrations after Hermes has chosen a capability.
- Explicit skill requests must stay inside the Hermes-selected capability. PPT/幻灯片/课件 requests must produce PPT deck artifacts; dynamic/interactive requests must produce interactive models; image requests must produce image artifacts; video-search requests must search videos; direct questions must remain text answers.
- Downstream Python code must not re-route a Hermes-selected capability, cross-fallback to another artifact type, or publish a mismatched artifact. Type mismatch means same-capability retry or honest failure.
- Do not use static templates, hardcoded demo payloads, fake search results, or locally synthesized "temporary" artifacts as final outputs for PPT, image, video, or interactive-model skills.
- Generated artifacts must be validated before they are written to canvas/resources. Failed, missing, fallback, or wrong-type artifacts must be discarded and reported honestly instead of being shown as completed work.
