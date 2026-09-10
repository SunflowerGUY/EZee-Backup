import json
import importlib.util
from types import SimpleNamespace
from pathlib import Path

import pytest

APP_PATH = Path(__file__).with_name("ezee-backup.py")
APP_SPEC = importlib.util.spec_from_file_location("ezee_backup", APP_PATH)
app = importlib.util.module_from_spec(APP_SPEC)
APP_SPEC.loader.exec_module(app)


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
    assert app.folder_dialog_initialdir(str(tmp_path / "missing")) is None


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
    monkeypatch.setattr(app, "load_jobs", lambda _path: reload_jobs)

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


def test_version_is_v2_5():
    assert app.VERSION == "2.5"


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
