import os

from app.core.config import load_dotenv_file


def test_load_dotenv_file_reads_local_values_without_overriding(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "# local development secrets",
                "MIMO_API_KEY=local-key",
                'MIMO_BASE_URL="https://local.example/v1"',
                "IMAGE2_BASE_URL=https://image.example/v1",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("MIMO_API_KEY", raising=False)
    monkeypatch.setenv("MIMO_BASE_URL", "https://already-set.example/v1")

    load_dotenv_file(env_file)

    assert os.environ["MIMO_API_KEY"] == "local-key"
    assert os.environ["MIMO_BASE_URL"] == "https://already-set.example/v1"
    assert os.environ["IMAGE2_BASE_URL"] == "https://image.example/v1"
