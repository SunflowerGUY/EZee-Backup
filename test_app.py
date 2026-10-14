import json
import importlib.util
import queue
import threading
from types import SimpleNamespace
from pathlib import Path

import pytest

APP_PATH = Path(__file__).with_name("ezee-backup.py")
APP_SPEC = importlib.util.spec_from_file_location("ezee_backup", APP_PATH)
app = importlib.util.module_from_spec(APP_SPEC)
APP_SPEC.loader.exec_module(app)


@pytest.fixture(autouse=True)
def isolated_appdata(tmp_path, monkeypatch):
    """Point %APPDATA% at a temp folder so tests never touch the real AppData safety copies."""
    appdata = tmp_path / "appdata"
    monkeypatch.setenv("APPDATA", str(appdata))
    return appdata


def test_job_file_path_is_in_exe_directory(tmp_path):
    exe_dir = tmp_path / "compiled"
    exe_dir.mkdir()
    path = app.job_file_path(exe_dir)
    assert path == exe_dir / "ezee_backup_jobs.json"


def test_build_robocopy_command_for_compare_mode():
    cmd = app.build_robocopy_command("C:/src", "D:/dst", "compare", verbose=True)
    assert cmd[0].lower() == "robocopy"
    assert "/L" in cmd
    assert "/E" in cmd


def test_build_robocopy_command_can_exclude_subfolders():
    cmd = app.build_robocopy_command("C:/src", "D:/dst", "backup", include_subfolders=False)
    assert "/E" not in cmd


def test_percentage_progress_lines_are_not_logged():
    should_log = app.EZeeBackupApp._should_log_line

    assert should_log(None, "0.7%") is False
    assert should_log(None, "100.0%") is False
    assert should_log(None, "New File 0.7%") is True


def test_folder_pair_requires_source_and_destination():
    assert app.has_valid_folder_pair("C:/source", "D:/destination")
    assert not app.has_valid_folder_pair("", "D:/destination")
    assert not app.has_valid_folder_pair("C:/source", "")
    assert not app.has_valid_folder_pair("  ", "D:/destination")


def test_folder_dialog_initialdir_uses_existing_folder(tmp_path):
    assert app.folder_dialog_initialdir(str(tmp_path)) == str(tmp_path)
    assert app.folder_dialog_initialdir(tmp_path.as_posix()) == str(tmp_path)
    assert app.folder_dialog_initialdir(f'  "{tmp_path}"  ') == str(tmp_path)
    assert app.folder_dialog_initialdir("") is None


def test_folder_dialog_initialdir_falls_back_to_nearest_existing_parent(tmp_path):
    missing = tmp_path / "renamed" / "deeper"
    assert app.folder_dialog_initialdir(str(missing)) == str(tmp_path)
    assert app.folder_dialog_initialdir(missing.as_posix()) == str(tmp_path)


def test_robocopy_success_exit_codes_include_standard_and_warning_results():
    assert app.is_successful_robocopy_exit_code(0)
    assert app.is_successful_robocopy_exit_code(7)
    assert not app.is_successful_robocopy_exit_code(8)


def test_sidebar_selection_runs_one_job_or_the_selected_group():
    jobs = [
        {"name": "Music", "group": "Workflows"},
        {"name": "Video", "group": "Workflows"},
        {"name": "Personal"},
    ]

    assert app.jobs_for_sidebar_selection(jobs, "job", "1") == [jobs[1]]
    assert app.jobs_for_sidebar_selection(jobs, "group", "Workflows") == jobs[:2]
    assert app.jobs_for_sidebar_selection(jobs, "all", "") == []
    assert app.jobs_for_sidebar_selection(jobs, "group", "Personal") == []


def test_save_and_load_jobs_round_trip(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    original = [{"name": "Daily", "source": "A", "destination": "B", "mode": "sync"}]
    app.save_jobs(original, jobs_path)
    loaded = app.load_jobs(jobs_path)
    assert loaded == [{**original[0], "include_subfolders": True}]
    saved_data = json.loads(jobs_path.read_text(encoding="utf-8"))
    assert saved_data["version"] == 2
    assert saved_data["groups"] == {}
    assert saved_data["jobs"] == loaded


def test_save_jobs_writes_identical_safety_copy_and_logs_fingerprint(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    app.save_jobs([{"name": "Daily", "source": "A", "destination": "B"}], jobs_path)

    safety = tmp_path / "ezee_backup_jobs.safety.json"
    assert safety.read_bytes() == jobs_path.read_bytes()
    log_text = (tmp_path / "ezee_backup_jobs_integrity.log").read_text(encoding="utf-8")
    sha = app.hashlib.sha256(jobs_path.read_bytes()).hexdigest()
    assert "SAVE OK" in log_text and "SAFETY OK" in log_text
    assert f"sha256={sha}" in log_text
    assert not list(tmp_path.glob("*.tmp"))
    assert [p.name for p in tmp_path.glob("*.log")] == ["ezee_backup_jobs_integrity.log"]


def make_writable(path):
    """Clear read-only, as a person or program would have to before changing a protected JOB file."""
    app.set_read_only(path, False)


def test_saved_job_file_and_safety_copy_are_read_only(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    app.save_jobs([{"name": "Daily", "include_subfolders": True}], jobs_path)
    safety = tmp_path / "ezee_backup_jobs.safety.json"

    assert app.is_read_only(jobs_path)
    assert app.is_read_only(safety)
    with pytest.raises(PermissionError):
        jobs_path.unlink()
    with pytest.raises(PermissionError):
        jobs_path.write_text("overwritten", encoding="utf-8")


def test_saving_again_over_read_only_files_works_and_keeps_them_read_only(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    app.save_jobs([{"name": "First", "include_subfolders": True}], jobs_path)
    app.save_jobs([{"name": "Second", "include_subfolders": True}], jobs_path)

    assert [job["name"] for job in app.load_jobs(jobs_path)] == ["Second"]
    safety = tmp_path / "ezee_backup_jobs.safety.json"
    assert safety.read_bytes() == jobs_path.read_bytes()
    assert app.is_read_only(jobs_path) and app.is_read_only(safety)
    assert not list(tmp_path.glob("*.tmp"))


def test_load_reapplies_read_only_when_it_was_cleared(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    app.save_jobs([{"name": "Daily", "include_subfolders": True}], jobs_path)
    safety = tmp_path / "ezee_backup_jobs.safety.json"
    make_writable(jobs_path)
    make_writable(safety)

    jobs, notice = app.load_jobs_with_report(jobs_path)

    assert notice is None
    assert app.is_read_only(jobs_path) and app.is_read_only(safety)
    log_text = (tmp_path / "ezee_backup_jobs_integrity.log").read_text(encoding="utf-8")
    assert log_text.count("PROTECTED") == 2


def test_failed_save_restores_read_only_on_existing_file(tmp_path, monkeypatch):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    app.save_jobs([{"name": "Daily", "include_subfolders": True}], jobs_path)
    before = jobs_path.read_bytes()

    def failing_replace(_src, _dst):
        raise OSError("disk full")

    monkeypatch.setattr(app.os, "replace", failing_replace)
    with pytest.raises(OSError):
        app.save_jobs([{"name": "Lost", "include_subfolders": True}], jobs_path)
    monkeypatch.undo()

    assert jobs_path.read_bytes() == before
    assert app.is_read_only(jobs_path)
    assert not list(tmp_path.glob("*.tmp"))


def test_read_only_corrupted_file_is_still_quarantined_and_recovered(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    original = [{"name": "Daily", "include_subfolders": True}]
    app.save_jobs(original, jobs_path)
    make_writable(jobs_path)
    jobs_path.write_text("damaged", encoding="utf-8")
    app.set_read_only(jobs_path, True)

    jobs, notice = app.load_jobs_with_report(jobs_path)

    assert jobs == original
    assert notice and "recovered" in notice
    assert len(list(tmp_path.glob("ezee_backup_jobs.corrupt-*.json"))) == 1
    assert app.is_read_only(jobs_path)


def test_save_jobs_writes_read_only_appdata_copy(tmp_path, isolated_appdata):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    app.save_jobs([{"name": "Daily", "include_subfolders": True}], jobs_path)

    second = app.appdata_copy_path(jobs_path)
    assert isolated_appdata / "EZee-Backup" in second.parents
    assert second.name == "ezee_backup_jobs.safety.json"
    assert second.read_bytes() == jobs_path.read_bytes()
    assert app.is_read_only(second)
    assert str(jobs_path.resolve()) in (second.parent / "copy_of.txt").read_text(encoding="utf-8")
    log_text = (tmp_path / "ezee_backup_jobs_integrity.log").read_text(encoding="utf-8")
    assert "APPDATA OK" in log_text and str(second) in log_text
    assert not list(isolated_appdata.rglob("*.log"))  # All events go to the one log beside the JOB file


def test_each_app_folder_gets_its_own_appdata_copy(tmp_path):
    first = tmp_path / "install_a" / "ezee_backup_jobs.json"
    second = tmp_path / "install_b" / "ezee_backup_jobs.json"
    first.parent.mkdir()
    second.parent.mkdir()
    app.save_jobs([{"name": "A", "include_subfolders": True}], first)
    app.save_jobs([{"name": "B", "include_subfolders": True}], second)

    assert app.appdata_copy_path(first) != app.appdata_copy_path(second)
    assert app.load_jobs(first)[0]["name"] == "A"
    assert app.load_jobs(second)[0]["name"] == "B"


def test_appdata_copy_recovers_jobs_when_app_folder_files_are_lost(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    original = [{"name": "Daily", "include_subfolders": True}]
    app.save_jobs(original, jobs_path)
    for path in (jobs_path, tmp_path / "ezee_backup_jobs.safety.json"):
        make_writable(path)
        path.unlink()

    jobs, notice = app.load_jobs_with_report(jobs_path)

    assert jobs == original
    assert "AppData safety copy" in notice
    assert app.is_read_only(jobs_path)
    assert (tmp_path / "ezee_backup_jobs.safety.json").read_bytes() == jobs_path.read_bytes()  # Rebuilt


def test_appdata_copy_used_when_main_and_local_safety_copy_are_damaged(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    original = [{"name": "Daily", "include_subfolders": True}]
    app.save_jobs(original, jobs_path)
    local_safety = tmp_path / "ezee_backup_jobs.safety.json"
    for path in (jobs_path, local_safety):
        make_writable(path)
        path.write_text("damaged", encoding="utf-8")

    jobs, notice = app.load_jobs_with_report(jobs_path)

    assert jobs == original
    assert "AppData safety copy" in notice
    assert len(list(tmp_path.glob("*.corrupt-*.json"))) == 2  # Both damaged files kept
    assert local_safety.read_bytes() == jobs_path.read_bytes()


def test_missing_appdata_copy_is_rebuilt_on_load(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    app.save_jobs([{"name": "Daily", "include_subfolders": True}], jobs_path)
    second = app.appdata_copy_path(jobs_path)
    make_writable(second)
    second.unlink()

    jobs, notice = app.load_jobs_with_report(jobs_path)

    assert notice is None
    assert second.read_bytes() == jobs_path.read_bytes()
    assert app.is_read_only(second)


def test_save_still_succeeds_when_appdata_copy_cannot_be_written(tmp_path, monkeypatch):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    blocker = tmp_path / "not_a_folder"
    blocker.write_text("a file where a folder should be", encoding="utf-8")
    monkeypatch.setattr(app, "appdata_copy_path", lambda _path: blocker / "ezee_backup_jobs.safety.json")

    app.save_jobs([{"name": "Daily", "include_subfolders": True}], jobs_path)

    assert app.load_jobs(jobs_path)[0]["name"] == "Daily"
    log_text = (tmp_path / "ezee_backup_jobs_integrity.log").read_text(encoding="utf-8")
    assert "APPDATA FAILED" in log_text


def test_works_without_appdata_variable(tmp_path, monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    app.save_jobs([{"name": "Daily", "include_subfolders": True}], jobs_path)

    assert app.appdata_copy_path(jobs_path) is None
    assert app.load_jobs_with_report(jobs_path) == ([{"name": "Daily", "include_subfolders": True}], None)


def test_each_changed_save_adds_a_read_only_dated_copy(tmp_path, isolated_appdata):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    app.save_jobs([{"name": "First", "include_subfolders": True}], jobs_path)
    app.save_jobs([{"name": "Second", "include_subfolders": True}], jobs_path)

    dated = app.history_files(jobs_path)
    assert len(dated) == 2
    assert app.history_dir(jobs_path) == app.appdata_copy_path(jobs_path).parent / "history"
    assert [app.load_jobs(path)[0]["name"] for _stamp, path in dated] == ["Second", "First"]
    assert all(app.is_read_only(path) for _stamp, path in dated)
    assert "HISTORY OK" in (tmp_path / "ezee_backup_jobs_integrity.log").read_text(encoding="utf-8")


def test_identical_save_does_not_add_another_dated_copy(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    jobs = [{"name": "Daily", "include_subfolders": True}]
    app.save_jobs(jobs, jobs_path)
    app.save_jobs(jobs, jobs_path)
    app.load_jobs(jobs_path)

    assert len(app.history_files(jobs_path)) == 1


def test_load_adds_dated_copy_for_file_saved_before_history_existed(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    jobs_path.write_text(json.dumps({"version": 2, "jobs": [{"name": "Old", "include_subfolders": True}]}), encoding="utf-8")

    app.load_jobs(jobs_path)

    dated = app.history_files(jobs_path)
    assert len(dated) == 1
    assert dated[0][1].read_bytes() == jobs_path.read_bytes()


def test_history_keeps_recent_copies_plus_one_per_day_for_30_days(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    folder = app.history_dir(jobs_path)
    folder.mkdir(parents=True)
    now = app.datetime(2026, 10, 14, 12, 0, 0)

    def add(stamp):
        path = folder / f"ezee_backup_jobs_{stamp.strftime(app.HISTORY_STAMP_FORMAT)}.json"
        path.write_text("{}", encoding="utf-8")
        app.set_read_only(path, True)
        return path

    # 25 saves this morning, 3 saves on each of the 5 previous days, and 2 from 40 days ago.
    today = [add(now - app.timedelta(minutes=i)) for i in range(25)]
    earlier_days = {
        day: [add(now - app.timedelta(days=day, hours=h)) for h in (1, 2, 3)] for day in range(1, 6)
    }
    too_old = [add(now - app.timedelta(days=40, hours=h)) for h in (1, 2)]

    app.prune_history(jobs_path, now)

    remaining = {path for _stamp, path in app.history_files(jobs_path)}
    assert set(today[:20]) <= remaining  # The 20 newest are always kept
    assert not set(today[20:]) & remaining  # Older same-day copies beyond 20 go
    for day, copies in earlier_days.items():
        assert copies[0] in remaining  # Newest copy of each earlier day is kept
        assert not set(copies[1:]) & remaining
    assert not set(too_old) & remaining
    assert len(remaining) == 25


def test_dated_copy_is_last_resort_when_main_and_safety_copies_are_gone(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    original = [{"name": "Daily", "include_subfolders": True}]
    app.save_jobs(original, jobs_path)
    for path in (jobs_path, tmp_path / "ezee_backup_jobs.safety.json", app.appdata_copy_path(jobs_path)):
        make_writable(path)
        path.unlink()

    jobs, notice = app.load_jobs_with_report(jobs_path)

    assert jobs == original
    assert "dated copy from" in notice
    assert app.is_read_only(jobs_path)
    assert (tmp_path / "ezee_backup_jobs.safety.json").exists()  # Safety copies rebuilt


def test_history_sits_beside_job_file_without_appdata(tmp_path, monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    app.save_jobs([{"name": "Daily", "include_subfolders": True}], jobs_path)

    assert app.history_dir(jobs_path) == tmp_path / "ezee_backup_jobs_history"
    assert len(app.history_files(jobs_path)) == 1


def test_summarize_job_changes_describes_what_a_restore_would_do():
    current = [{"name": "Music", "mode": "backup"}, {"name": "Video", "mode": "backup"}, {"name": "New", "mode": "backup"}]
    older = [{"name": "Music", "mode": "sync"}, {"name": "Video", "mode": "backup"}, {"name": "Deleted", "mode": "backup"}]

    summary = app.summarize_job_changes(current, older)

    assert "Brings back: Deleted" in summary
    assert "Removes: New" in summary
    assert "Changes 1 job" in summary
    assert app.summarize_job_changes(current, current) == "Same jobs as now (order or groups may differ)"


def test_restore_history_copy_makes_older_version_current_and_can_be_undone(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    before = [{"name": "Keep", "include_subfolders": True}, {"name": "Accidentally deleted", "include_subfolders": True}]
    after = [{"name": "Keep", "include_subfolders": True}]
    app.save_jobs(before, jobs_path)
    app.save_jobs(after, jobs_path)
    older = app.history_files(jobs_path)[1][1]

    restored = app.restore_history_copy(jobs_path, older)

    assert restored == before
    assert app.load_jobs(jobs_path) == before
    assert app.is_read_only(jobs_path)
    assert (tmp_path / "ezee_backup_jobs.safety.json").read_bytes() == jobs_path.read_bytes()
    dated = app.history_files(jobs_path)
    assert [len(app.load_jobs(path)) for _stamp, path in dated[:2]] == [2, 1]  # Restored version, then the one it replaced
    assert "RESTORED" in (tmp_path / "ezee_backup_jobs_integrity.log").read_text(encoding="utf-8")


def test_restore_history_copy_refuses_damaged_dated_copy(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    app.save_jobs([{"name": "Keep", "include_subfolders": True}], jobs_path)
    damaged = app.history_dir(jobs_path) / "ezee_backup_jobs_2026-01-01_00-00-00.json"
    damaged.write_text("not json", encoding="utf-8")
    before = jobs_path.read_bytes()

    with pytest.raises(ValueError):
        app.restore_history_copy(jobs_path, damaged)
    assert jobs_path.read_bytes() == before


def test_import_job_file_on_fresh_install_accepts_any_file_name(tmp_path):
    backup_drive = tmp_path / "external_backup"
    backup_drive.mkdir()
    imported_file = backup_drive / "ezee_backup_jobs_2026-10-14_15-15-54.json"
    imported_file.write_text(json.dumps({"version": 2, "jobs": [{"name": "From backup", "mode": "backup"}]}), encoding="utf-8")
    app.set_read_only(imported_file, True)
    install = tmp_path / "new_pc"
    install.mkdir()
    jobs_path = install / "ezee_backup_jobs.json"

    jobs = app.import_job_file(jobs_path, imported_file)

    assert jobs == [{"name": "From backup", "mode": "backup", "include_subfolders": True}]
    assert app.load_jobs_with_report(jobs_path) == (jobs, None)
    assert app.is_read_only(jobs_path)
    assert (install / "ezee_backup_jobs.safety.json").exists()
    assert app.appdata_copy_path(jobs_path).exists()
    assert len(app.history_files(jobs_path)) == 1
    assert imported_file.exists()  # The original is left where it was
    log_text = (install / "ezee_backup_jobs_integrity.log").read_text(encoding="utf-8")
    assert "IMPORTED" in log_text and str(imported_file.resolve()) in log_text


def test_import_job_file_keeps_current_profiles_as_dated_copy(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    app.save_jobs([{"name": "Current", "include_subfolders": True}], jobs_path)
    other = tmp_path / "other.json"
    other.write_text(json.dumps([{"name": "Imported", "include_subfolders": True}]), encoding="utf-8")

    app.import_job_file(jobs_path, other)

    dated = app.history_files(jobs_path)
    assert [app.load_jobs(path)[0]["name"] for _stamp, path in dated[:2]] == ["Imported", "Current"]
    app.restore_history_copy(jobs_path, dated[1][1])  # Undo
    assert app.load_jobs(jobs_path)[0]["name"] == "Current"


def test_import_job_file_refuses_unusable_file_without_changing_anything(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    app.save_jobs([{"name": "Current", "include_subfolders": True}], jobs_path)
    before = jobs_path.read_bytes()
    bad = tmp_path / "notes.json"
    bad.write_text('{"something": "else"}', encoding="utf-8")

    with pytest.raises(ValueError, match="no 'jobs' list"):
        app.import_job_file(jobs_path, bad)
    assert jobs_path.read_bytes() == before


def test_load_jobs_recovers_from_safety_copy_when_main_is_corrupted(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    original = [{"name": "Daily", "source": "A", "destination": "B", "include_subfolders": True}]
    app.save_jobs(original, jobs_path)
    make_writable(jobs_path)
    jobs_path.write_text('{"version": 2, "jobs": [', encoding="utf-8")

    jobs, notice = app.load_jobs_with_report(jobs_path)

    assert jobs == original
    assert "recovered from the safety copy" in notice
    assert app.load_jobs(jobs_path) == original  # Main file was restored
    corrupt_copies = list(tmp_path.glob("ezee_backup_jobs.corrupt-*.json"))
    assert len(corrupt_copies) == 1
    assert corrupt_copies[0].read_text(encoding="utf-8") == '{"version": 2, "jobs": ['
    log_text = (tmp_path / "ezee_backup_jobs_integrity.log").read_text(encoding="utf-8")
    assert "LOAD FAILED" in log_text and "QUARANTINED" in log_text and "RECOVERED" in log_text


def test_load_jobs_recovers_from_safety_copy_when_main_is_missing(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    original = [{"name": "Daily", "source": "A", "destination": "B", "include_subfolders": True}]
    app.save_jobs(original, jobs_path)
    make_writable(jobs_path)
    jobs_path.unlink()

    jobs, notice = app.load_jobs_with_report(jobs_path)

    assert jobs == original
    assert notice and "missing" in notice
    assert jobs_path.exists()


def test_load_jobs_reports_when_main_and_safety_copy_are_both_unusable(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    jobs_path.write_text("not json", encoding="utf-8")
    (tmp_path / "ezee_backup_jobs.safety.json").write_text("also not json", encoding="utf-8")

    jobs, notice = app.load_jobs_with_report(jobs_path)

    assert jobs == []
    assert "no usable safety copy" in notice
    assert len(list(tmp_path.glob("*.corrupt-*.json"))) == 2


def test_load_jobs_first_run_has_no_notice(tmp_path):
    assert app.load_jobs_with_report(tmp_path / "ezee_backup_jobs.json") == ([], None)


def test_load_jobs_creates_missing_safety_copy_from_good_main_file(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    app.save_jobs([{"name": "Daily", "include_subfolders": True}], jobs_path)
    safety = tmp_path / "ezee_backup_jobs.safety.json"
    make_writable(safety)
    safety.unlink()

    jobs, notice = app.load_jobs_with_report(jobs_path)

    assert notice is None
    assert safety.read_bytes() == jobs_path.read_bytes()


def test_empty_main_file_does_not_overwrite_safety_copy_with_jobs(tmp_path):
    jobs_path = tmp_path / "ezee_backup_jobs.json"
    app.save_jobs([{"name": "Daily", "include_subfolders": True}], jobs_path)
    safety = tmp_path / "ezee_backup_jobs.safety.json"
    safety_before = safety.read_bytes()
    make_writable(jobs_path)
    jobs_path.write_text('{"version": 2, "groups": {}, "jobs": []}', encoding="utf-8")

    app.load_jobs_with_report(jobs_path)

    assert safety.read_bytes() == safety_before


def test_load_jobs_migrates_legacy_list_format(tmp_path):
    jobs_path = tmp_path / "legacy_jobs.json"
    original = [{"name": "Daily", "source": "A", "destination": "B", "mode": "sync"}]
    jobs_path.write_text(json.dumps(original), encoding="utf-8")

    assert app.load_jobs(jobs_path) == [{**original[0], "include_subfolders": True}]


def test_load_jobs_migrates_missing_subfolder_setting_to_json(tmp_path):
    jobs_path = tmp_path / "missing_subfolders.json"
    jobs_path.write_text(
        json.dumps({"version": 2, "jobs": [{"name": "Daily", "mode": "backup"}]}),
        encoding="utf-8",
    )

    loaded = app.load_jobs(jobs_path)
    saved_data = json.loads(jobs_path.read_text(encoding="utf-8"))

    assert loaded[0]["include_subfolders"] is True
    assert saved_data["jobs"][0]["include_subfolders"] is True


def test_saved_job_profile_preserves_group_when_mode_changes(tmp_path):
    jobs_path = tmp_path / "grouped_jobs.json"
    jobs = [{"name": "Music", "source": "A", "destination": "B", "mode": "backup", "group": "Workflows"}]
    jobs[0].update(mode="sync")
    app.save_jobs(jobs, jobs_path)

    loaded = app.load_jobs(jobs_path)
    assert loaded[0]["mode"] == "sync"
    assert loaded[0]["group"] == "Workflows"


def test_saved_job_profile_preserves_subfolder_setting(tmp_path):
    jobs_path = tmp_path / "subfolders_jobs.json"
    jobs = [{"name": "Files", "source": "A", "destination": "B", "mode": "backup", "include_subfolders": False}]
    app.save_jobs(jobs, jobs_path)

    loaded = app.load_jobs(jobs_path)
    assert loaded[0]["include_subfolders"] is False


def test_mode_change_updates_memory_and_sidebar_tags_without_saving(monkeypatch):
    class FakeTree:
        def __init__(self):
            self.items = {
                "all": {"children": ["all-job"], "values": ("all", "")},
                "group": {"children": ["group-job"], "values": ("group", "Workflows")},
                "all-job": {"children": [], "values": ("job", "0"), "tags": ("backup",)},
                "group-job": {"children": [], "values": ("job", "0"), "tags": ("backup",)},
            }

        def get_children(self, item_id=""):
            if item_id == "":
                return ["all", "group"]
            return self.items[item_id]["children"]

        def item(self, item_id, **kwargs):
            if kwargs:
                self.items[item_id].update(kwargs)
            return self.items[item_id]

    tree = FakeTree()
    app_instance = SimpleNamespace(
        jobs=[{"name": "Music", "mode": "backup"}],
        mode_var=SimpleNamespace(get=lambda: "sync"),
        job_tree=tree,
    )
    app_instance._selected_sidebar_item = lambda: ("job", "0")
    app_instance._update_sidebar_job_mode = lambda index, mode: app.EZeeBackupApp._update_sidebar_job_mode(
        app_instance, index, mode
    )
    app_instance._set_profile_modified = lambda modified: None
    monkeypatch.setattr(app, "save_jobs", lambda *_args, **_kwargs: pytest.fail("mode changes must not save"))

    app.EZeeBackupApp._mode_changed(app_instance)

    assert app_instance.jobs[0]["mode"] == "sync"
    assert tree.items["all-job"]["tags"] == ("sync",)
    assert tree.items["group-job"]["tags"] == ("sync",)


def test_forget_changes_reloads_jobs_and_resets_save_indicator(monkeypatch):
    reload_jobs = [{"name": "Reloaded", "mode": "backup"}]
    app_instance = SimpleNamespace(
        jobs=[{"name": "Unsaved", "mode": "sync"}],
        profile_states=[],
    )
    app_instance._set_profile_modified = lambda modified: app_instance.profile_states.append(modified)
    app_instance.refresh_jobs_list = lambda: None
    app_instance._load_initial_job = lambda: None
    app_instance._log = lambda _message: None
    monkeypatch.setattr(app, "load_jobs_with_report", lambda _path: (reload_jobs, None))

    app.EZeeBackupApp.forget_changes(app_instance)

    assert app_instance.jobs == reload_jobs
    assert app_instance.profile_states == [False]


def test_profile_modified_updates_save_and_forget_button_colors():
    class FakeButton:
        def __init__(self):
            self.options = {}

        def configure(self, **options):
            self.options.update(options)

    class FakeMenu:
        def __init__(self):
            self.options = {}

        def entryconfigure(self, label, **options):
            self.options[label] = options

    app_instance = SimpleNamespace(
        save_changes_button=FakeButton(),
        forget_changes_button=FakeButton(),
        edit_menu=FakeMenu(),
    )

    app.EZeeBackupApp._set_profile_modified(app_instance, True)
    assert app_instance.save_changes_button.options["fg"] == "#ffff00"
    assert app_instance.forget_changes_button.options["fg"] == "#ffa500"
    assert app_instance.save_changes_button.options["state"] == app.tk.NORMAL
    assert app_instance.forget_changes_button.options["state"] == app.tk.NORMAL
    assert app_instance.edit_menu.options["Save Changes"]["state"] == app.tk.NORMAL
    assert app_instance.edit_menu.options["Forget Changes"]["state"] == app.tk.NORMAL

    app.EZeeBackupApp._set_profile_modified(app_instance, False)
    assert app_instance.save_changes_button.options["fg"] == "#ffffff"
    assert app_instance.forget_changes_button.options["fg"] == "#ffffff"
    assert app_instance.save_changes_button.options["state"] == app.tk.DISABLED
    assert app_instance.forget_changes_button.options["state"] == app.tk.DISABLED
    assert app_instance.edit_menu.options["Save Changes"]["state"] == app.tk.DISABLED
    assert app_instance.edit_menu.options["Forget Changes"]["state"] == app.tk.DISABLED


def test_version_is_v4_4():
    assert app.VERSION == "4.4"


README_TOOL_SPEC = importlib.util.spec_from_file_location(
    "update_readme_version", Path(__file__).with_name("update_readme_version.py")
)
readme_tool = importlib.util.module_from_spec(README_TOOL_SPEC)
README_TOOL_SPEC.loader.exec_module(readme_tool)


def test_readme_tool_reads_version_from_app_source():
    assert readme_tool.read_app_version(APP_PATH.read_text(encoding="utf-8")) == app.VERSION


def test_readme_tool_updates_version_line_and_example_but_not_placeholder():
    readme = (
        "**Current version: 4.1.** The version is set by `VERSION`.\n"
        "dist\\ezee-backup - (V4.1).exe\n"
        "Saves the numbered copy `dist\\ezee-backup - (V<version>).exe`.\n"
        "Python 3.10 or newer.\n"
    )

    updated, changed = readme_tool.update_readme_text(readme, "4.3")

    assert "**Current version: 4.3.**" in updated
    assert "dist\\ezee-backup - (V4.3).exe" in updated
    assert "(V<version>).exe" in updated
    assert "Python 3.10 or newer." in updated
    assert changed == 2
    assert readme_tool.update_readme_text(updated, "4.3") == (updated, 0)


def test_readme_tool_reports_missing_version_line():
    with pytest.raises(ValueError):
        readme_tool.update_readme_text("No version line here.\n", "4.3")


def test_copy_logs_and_launch_notepad_copies_text_and_opens_temp_file(monkeypatch):
    launched = {}

    class FakeLogWidget:
        def get(self, _start, _end):
            return "Log line 1\nLog line 2\n"

    app_instance = SimpleNamespace(
        log_widget=FakeLogWidget(),
        clipboard_values=[],
    )
    app_instance.clipboard_clear = lambda: app_instance.clipboard_values.clear()
    app_instance.clipboard_append = app_instance.clipboard_values.append

    def fake_popen(command):
        launched["command"] = command

    monkeypatch.setattr(app.subprocess, "Popen", fake_popen)

    app.EZeeBackupApp._copy_logs_and_launch_notepad(app_instance)

    log_path = Path(launched["command"][1])
    try:
        assert launched["command"][0] == "notepad.exe"
        assert app_instance.clipboard_values == ["Log line 1\nLog line 2"]
        assert log_path.read_text(encoding="utf-8") == "Log line 1\nLog line 2"
    finally:
        log_path.unlink(missing_ok=True)


def test_classify_sync_entries_new_files_copy_toward_missing_side():
    actions = app.classify_sync_entries(
        source_entries={"only_source.txt": (10, 100.0)},
        dest_entries={"only_dest.txt": (20, 200.0)},
        manifest_entries={},
    )
    assert actions == {"only_source.txt": "copy_src_to_dest", "only_dest.txt": "copy_dest_to_src"}


def test_classify_sync_entries_propagates_deletions_using_manifest():
    manifest = {
        "deleted_on_source.txt": {"size": 5, "mtime": 50.0},
        "deleted_on_dest.txt": {"size": 6, "mtime": 60.0},
    }
    actions = app.classify_sync_entries(
        source_entries={"deleted_on_dest.txt": (6, 60.0)},
        dest_entries={"deleted_on_source.txt": (5, 50.0)},
        manifest_entries=manifest,
    )
    assert actions["deleted_on_source.txt"] == "delete_dest"
    assert actions["deleted_on_dest.txt"] == "delete_src"


def test_classify_sync_entries_resolved_deletion_on_both_sides_is_a_noop():
    manifest = {"gone_everywhere.txt": {"size": 5, "mtime": 50.0}}
    actions = app.classify_sync_entries(
        source_entries={},
        dest_entries={},
        manifest_entries=manifest,
    )
    assert actions["gone_everywhere.txt"] == "noop"


def test_classify_sync_entries_detects_conflicts_and_single_side_changes():
    manifest = {
        "changed_on_source.txt": {"size": 10, "mtime": 100.0},
        "changed_on_both.txt": {"size": 10, "mtime": 100.0},
        "unchanged.txt": {"size": 10, "mtime": 100.0},
    }
    actions = app.classify_sync_entries(
        source_entries={
            "changed_on_source.txt": (99, 500.0),
            "changed_on_both.txt": (99, 500.0),
            "unchanged.txt": (10, 100.0),
        },
        dest_entries={
            "changed_on_source.txt": (10, 100.0),
            "changed_on_both.txt": (55, 600.0),
            "unchanged.txt": (10, 100.0),
        },
        manifest_entries=manifest,
    )
    assert actions["changed_on_source.txt"] == "copy_src_to_dest"
    assert actions["changed_on_both.txt"] == "conflict"
    assert actions["unchanged.txt"] == "noop"


def test_classify_sync_entries_first_run_with_overlapping_files():
    actions = app.classify_sync_entries(
        source_entries={"identical.txt": (10, 100.0), "different.txt": (10, 100.0)},
        dest_entries={"identical.txt": (10, 100.0), "different.txt": (99, 999.0)},
        manifest_entries={},
    )
    assert actions["identical.txt"] == "noop"
    assert actions["different.txt"] == "conflict"


def test_scan_folder_snapshot_respects_include_subfolders(tmp_path):
    root = tmp_path / "root"
    (root / "nested").mkdir(parents=True)
    (root / "top.txt").write_text("top", encoding="utf-8")
    (root / "nested" / "deep.txt").write_text("deep", encoding="utf-8")

    flat = app.scan_folder_snapshot(root, include_subfolders=False)
    recursive = app.scan_folder_snapshot(root, include_subfolders=True)

    assert set(flat) == {"top.txt"}
    assert set(recursive) == {"top.txt", "nested/deep.txt"}


def test_sync_manifest_round_trip(tmp_path):
    entries = {"a.txt": {"size": 10, "mtime": 123.0}}
    app.save_sync_manifest("C:/src", "D:/dst", entries, base_dir=tmp_path)
    loaded = app.load_sync_manifest("C:/src", "D:/dst", base_dir=tmp_path)
    assert loaded == entries


def test_run_sync_engine_first_run_copies_both_directions(tmp_path):
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()
    (source / "only_source.txt").write_text("from source", encoding="utf-8")
    (dest / "only_dest.txt").write_text("from dest", encoding="utf-8")

    pause_event = threading.Event()
    pause_event.set()
    abort_event = threading.Event()

    result = app.run_sync_engine(
        str(source), str(dest), True, pause_event, abort_event, queue.Queue(), base_dir=tmp_path
    )

    assert result.success
    assert result.copied_to_dest == 1
    assert result.copied_to_source == 1
    assert (dest / "only_source.txt").read_text(encoding="utf-8") == "from source"
    assert (source / "only_dest.txt").read_text(encoding="utf-8") == "from dest"
    assert app.sync_manifest_path(str(source), str(dest), tmp_path).exists()


def test_run_sync_engine_second_run_is_idempotent(tmp_path):
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()
    (source / "shared.txt").write_text("same content", encoding="utf-8")

    pause_event = threading.Event()
    pause_event.set()
    abort_event = threading.Event()

    first = app.run_sync_engine(
        str(source), str(dest), True, pause_event, abort_event, queue.Queue(), base_dir=tmp_path
    )
    second = app.run_sync_engine(
        str(source), str(dest), True, pause_event, abort_event, queue.Queue(), base_dir=tmp_path
    )

    assert first.copied_to_dest == 1
    assert second.copied_to_dest == 0
    assert second.copied_to_source == 0
    assert second.conflicts == 0


def test_run_sync_engine_propagates_deletion_through_recycle_bin(tmp_path, monkeypatch):
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()
    shared = source / "shared.txt"
    shared.write_text("keep me in sync", encoding="utf-8")

    pause_event = threading.Event()
    pause_event.set()
    abort_event = threading.Event()

    app.run_sync_engine(str(source), str(dest), True, pause_event, abort_event, queue.Queue(), base_dir=tmp_path)
    assert (dest / "shared.txt").exists()

    shared.unlink()  # simulate a deletion on Source since the last sync

    trashed = []

    def fake_send2trash(path):
        trashed.append(path)
        Path(path).unlink()  # a real send2trash also removes it from this location

    monkeypatch.setattr(app, "send2trash", fake_send2trash)

    result = app.run_sync_engine(
        str(source), str(dest), True, pause_event, abort_event, queue.Queue(), base_dir=tmp_path
    )

    assert result.deleted_from_dest == 1
    assert not (dest / "shared.txt").exists()
    assert trashed == [str(dest / "shared.txt")]


@pytest.mark.parametrize(
    "name, ok",
    [
        ("Photos 2026", True),
        ("v1.2 drafts", True),
        ("", False),
        ("a/b", False),
        ("what?", False),
        ("trailing.", False),
        ("trailing ", False),
        ("CON", False),
        ("com1.txt", False),
        ("Console", True),
    ],
)
def test_new_folder_name_problem(name, ok):
    assert (app.new_folder_name_problem(name) is None) == ok
