import pytest

from ai_news.config import ModelSpec, Settings, load_dotenv


def test_model_spec_parse():
    spec = ModelSpec.parse("anthropic:claude-opus-4-8")
    assert spec.provider == "anthropic"
    assert spec.model == "claude-opus-4-8"
    assert str(spec) == "anthropic:claude-opus-4-8"


@pytest.mark.parametrize("bad", ["", "anthropic", "anthropic:", "azure:gpt-4", ":model"])
def test_model_spec_parse_rejects_invalid(bad):
    with pytest.raises(ValueError):
        ModelSpec.parse(bad)


def test_settings_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SUMMARIZER_MODEL", "google:gemini-3.1-pro-preview")
    monkeypatch.setenv("REPORT_TZ", "Asia/Taipei")
    settings = Settings.from_env(tmp_path, window_hours=24)
    assert settings.model.provider == "google"
    assert settings.timezone == "Asia/Taipei"
    assert settings.window_hours == 24
    assert settings.reports_dir == tmp_path / "reports"


def test_load_dotenv_does_not_override_existing(monkeypatch, tmp_path):
    monkeypatch.setenv("FOO_KEY", "from-env")
    (tmp_path / ".env").write_text('FOO_KEY=from-file\nBAR_KEY="quoted"\n# comment\n')
    load_dotenv(tmp_path)
    import os
    assert os.environ["FOO_KEY"] == "from-env"
    assert os.environ["BAR_KEY"] == "quoted"
