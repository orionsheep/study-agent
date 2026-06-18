import os

from app.core.config import load_dotenv_file


def test_load_dotenv_file_reads_local_values_without_overriding(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "# local development secrets",
                "GEMINI_API_KEY=local-key",
                'GEMINI_TEXT_MODEL="gemini-local-test"',
                "GEMINI_IMAGE_MODEL=gemini-local-image",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_IMAGE_MODEL", raising=False)
    monkeypatch.setenv("GEMINI_TEXT_MODEL", "gemini-existing-test")

    load_dotenv_file(env_file)

    assert os.environ["GEMINI_API_KEY"] == "local-key"
    assert os.environ["GEMINI_TEXT_MODEL"] == "gemini-existing-test"
    assert os.environ["GEMINI_IMAGE_MODEL"] == "gemini-local-image"
