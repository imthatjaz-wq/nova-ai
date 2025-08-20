from __future__ import annotations

from commands.handlers import create_file
from commands import handlers
from commands.registry import populate_defaults, get
from nova import scheduler


def test_create_file_denied(monkeypatch, tmp_path) -> None:
    # Simulate noninteractive deny
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")
    target = tmp_path / "demo.txt"
    msg = create_file(str(target), content="hello")
    assert msg.startswith("[denied]")
    assert not target.exists()


def test_create_file_approved_dry_run(monkeypatch, tmp_path) -> None:
    # Simulate approval; still dry-run in Segment 2
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "approve")
    target = tmp_path / "demo.txt"
    msg = create_file(str(target), content="hello")
    assert msg.startswith("[approved]")
    assert "Would create" in msg
    assert not target.exists()


def test_open_app_and_url(monkeypatch) -> None:
    msg1 = handlers.open_url("https://example.com")
    assert "Would open URL" in msg1
    msg2 = handlers.open_app("python")
    assert msg2.startswith("[dry-run]") or msg2.startswith("[error]")


def test_search_local_files(tmp_path) -> None:
    f1 = tmp_path / "note.txt"
    f1.write_text("x")
    f2 = tmp_path / "sub" / "note.txt"
    f2.parent.mkdir(parents=True, exist_ok=True)
    f2.write_text("y")
    msg = handlers.search_local_files(str(tmp_path), "*.txt")
    assert "note.txt" in msg


def test_set_reminder_and_show_logs(monkeypatch) -> None:
    count_before = len(scheduler.list_scheduled())
    msg = handlers.set_reminder(5, "ping")
    assert msg.startswith("[scheduled]")
    count_after = len(scheduler.list_scheduled())
    assert count_after == count_before + 1
    # show_logs should not fail even if logs dir missing
    out = handlers.show_logs()
    assert out.startswith("[ok]") or out.endswith(".log")


def test_registry_population() -> None:
    populate_defaults()
    assert get("open_url") is not None
    assert get("create_file") is not None
