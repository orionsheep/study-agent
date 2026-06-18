from __future__ import annotations

import pytest

from app.hermes_runtime.task_executor import HermesTaskExecutor


@pytest.mark.asyncio
async def test_invoke_hermes_streams_stderr_without_double_reading(tmp_path):
    command = tmp_path / "fake_hermes.py"
    command.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('stderr progress 1', file=sys.stderr, flush=True)\n"
        "print('stderr progress 2', file=sys.stderr, flush=True)\n"
        "print('{\"summary\":\"ok\"}', flush=True)\n",
        encoding="utf-8",
    )
    command.chmod(0o755)

    seen: list[str] = []

    async def on_stderr(line: str) -> None:
        seen.append(line)

    returncode, output, error = await HermesTaskExecutor()._invoke_hermes(
        str(command),
        prompt="hello",
        provider="gemini",
        model="gemini-test",
        toolsets="",
        skills=[],
        on_stderr_line=on_stderr,
    )

    assert returncode == 0
    assert output == '{"summary":"ok"}'
    assert seen == ["stderr progress 1", "stderr progress 2"]
    assert error == "stderr progress 1\nstderr progress 2"
