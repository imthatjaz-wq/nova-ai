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
    # Capture alerts via a sink and fast-fire
    fired = {"count": 0, "last": ""}
    def sink(msg: str) -> None:
        fired["count"] += 1
        fired["last"] = msg
    scheduler.set_alert_sink(sink)
    count_before = len(scheduler.list_scheduled())
    msg = handlers.set_reminder(0, "ping")
    assert msg.startswith("[scheduled]")
    # Give the Timer a moment
    import time
    time.sleep(0.05)
    count_after = len(scheduler.list_scheduled())
    assert count_after == count_before + 1
    assert fired["count"] >= 1
    assert fired["last"] == "ping"
    # show_logs should not fail even if logs dir missing
    out = handlers.show_logs()
    assert out.startswith("[ok]") or out.endswith(".log")


def test_registry_population() -> None:
    populate_defaults()
    assert get("open_url") is not None
    assert get("create_file") is not None
    assert get("open_file") is not None
    assert get("copy_file") is not None
    assert get("move_file") is not None
    assert get("delete_file") is not None


def test_open_and_copy_move_delete(monkeypatch, tmp_path) -> None:
    # create a source file
    src = tmp_path / "a.txt"
    src.write_text("x")
    # open_file
    msg_open = handlers.open_file(str(src))
    assert msg_open.startswith("[dry-run]")
    # copy denied
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")
    msg_copy_denied = handlers.copy_file(str(src), str(tmp_path / "b.txt"))
    assert msg_copy_denied.startswith("[denied]")
    # copy approved (still dry-run)
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "approve")
    msg_copy_appr = handlers.copy_file(str(src), str(tmp_path / "b.txt"))
    assert msg_copy_appr.startswith("[approved]")
    # move approved (dry-run)
    msg_move_appr = handlers.move_file(str(src), str(tmp_path / "c.txt"))
    assert msg_move_appr.startswith("[approved]")
    # delete double-confirm: default deny in noninteractive
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "approve")
    # For second confirm (interactive_prompt), with noninteractive=1 and default=False, it should return False
    msg_del = handlers.delete_file(str(tmp_path / "c.txt"))
    # c.txt does not actually exist (move was dry-run), so adjust target to src
    msg_del2 = handlers.delete_file(str(src)) if src.exists() else "[error] file not found"
    assert msg_del.startswith("[error]") or msg_del.startswith("[cancelled]")
    if msg_del2 != "[error] file not found":
        assert msg_del2.startswith("[cancelled]")
