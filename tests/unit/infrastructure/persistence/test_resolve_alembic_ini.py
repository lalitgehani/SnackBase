"""Alembic config must resolve when cwd has no alembic.ini (pip-installed binary)."""

from pathlib import Path

from alembic.config import Config

from snackbase.infrastructure.persistence.migration_service import resolve_alembic_ini


def test_resolve_alembic_ini_without_cwd_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SNACKBASE_ALEMBIC_INI", raising=False)
    path = resolve_alembic_ini()
    assert path.is_file()
    assert path.name == "alembic.ini"
    versions = path.parent / "alembic" / "versions"
    assert versions.is_dir()
    assert any(versions.glob("*.py"))


def test_resolve_alembic_ini_env_override(tmp_path, monkeypatch):
    custom = tmp_path / "custom.ini"
    custom.write_text("[alembic]\nscript_location = alembic\n")
    monkeypatch.setenv("SNACKBASE_ALEMBIC_INI", str(custom))
    assert resolve_alembic_ini() == custom.resolve()


def test_resolved_ini_loads_script_location(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SNACKBASE_ALEMBIC_INI", raising=False)
    ini = resolve_alembic_ini()
    cfg = Config(str(ini))
    script = cfg.get_main_option("script_location")
    assert script
    script_path = Path(script)
    if not script_path.is_absolute():
        script_path = ini.parent / script_path
    assert script_path.exists() or (ini.parent / "alembic").is_dir()
