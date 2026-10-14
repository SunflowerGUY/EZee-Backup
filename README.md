# EZee-Backup

EZee-Backup is a lightweight Windows backup tool designed for fast, repeatable folder-to-folder operations. It uses ROBOCOPY under the hood to copy, synchronize, move, or compare directories from a simple dark-themed desktop interface.

The app is built for users who want a no-fuss way to back up important folders without needing Python installed on the target machine. It supports saved jobs, grouped job profiles, source and destination browsing, logging modes, and a portable EXE build for easy deployment.

**Current version: 4.4.** The version is set by `VERSION` in `ezee-backup.py`; it appears in the window title and About box, and names the numbered build copy (see [Building the Application](#building-the-application)). `build_gui.bat` keeps this line up to date automatically.

## Screenshots

![EZee-Backup main window](docs/EZee-Backup-screenshot-1.jpg)

![EZee-Backup job management view](docs/EZee-Backup-screenshot-2.jpg)

## Features

- Portable Windows executable built with PyInstaller.
- Dark-themed graphical user interface.
- Backup, Mirror, Move, Compare, and two-way Sync modes.
- Source and Destination folder selectors, with an Include Sub Folders option.
- `Browse` opens at the folder already typed in the Source or Destination box (or its nearest existing parent folder).
- Visible Source and Destination file panes with:
  - File and folder names.
  - File sizes.
  - Folder refresh control.
  - Vertical scrolling.
- "Groups & Jobs" sidebar tree for saved job profiles:
  - `All Jobs` lists every job; jobs can also be organised into named groups.
  - Run a single job, or a whole group in one go.
  - Right-click to Rename, Duplicate, Add to Group, Remove from Group, or Delete Group.
- Save as New Job, Delete Job, Save Changes, Forget Changes, Restore Master Jobs Profile from History, and Import Master Jobs Profile (JSON) for job profiles. Each job remembers its folders, mode, and Include Sub Folders setting.
- Drive monitoring: warns (with a sound and popup) when a drive used by a job is offline, disables RUN for that job, and skips affected jobs when running a group.
- Pause and Abort controls while an operation is running.
- Jobs stored in `ezee_backup_jobs.json` beside the executable, kept read-only between saves, with two automatic safety copies (one beside it, one in `%APPDATA%`), dated older copies, recovery, and an integrity log (see [Job File Safety](#job-file-safety)).
- Simple, Verbose, and No Logs output modes.
- Splash screen with the EZee-Backup logo and project information.
- Application icon generated from the supplied EZee-Backup logo.
- About and Exit buttons in the main window.
- Uses Windows `ROBOCOPY`, which is included with modern Windows installations.

## Backup Modes

Click the info icon beside the mode buttons (or Help > Backup Mode Info) for these descriptions inside the app.

### Backup

Copies new and changed files from the source folder to the destination folder. Nothing is deleted.

### Mirror

Makes the destination an exact copy of the source using `ROBOCOPY /MIR`, **including deletions**: files in the destination that are not in the source are removed. The source is the master reference. Useful when a large project is finished, to clear old temp or scratch files out of the destination. Use it carefully.

### Move

Copies files to the destination and removes them from the source (`ROBOCOPY /MOV`).

### Compare

Lists what would be copied without changing either folder (`ROBOCOPY /L`).

### Sync (two-way)

Copies new and changed files in **both** directions and carries deletions across, using each job's saved history from its last successful sync (stored in the `sync_state` folder beside the executable). This history lets Sync tell a genuine deletion apart from a file that simply has not reached the other side yet.

- Deleted files go to the Windows Recycle Bin, not straight to permanent deletion.
- If a file changed on both sides, the newer version keeps its name and the older version is kept alongside it, on both sides, as `name (Sync Conflict - date).ext`. For example: `report.docx` → `report (Sync Conflict - 2026-09-24).docx`.

Sync uses its own Python engine rather than Robocopy, because Robocopy has no two-way mode.

## Requirements

### To run the compiled application

- Windows 10 or later is recommended.
- Windows `ROBOCOPY` must be available.
- No Python installation is required to run the compiled executable.

### To build from source

- Windows.
- Python 3.10 or newer.
- Python's Tkinter support.
- Internet access for installing Python packages (first build, or after `requirements.txt` changes).

Python 3.10 or newer is required because the source uses modern type annotation syntax.

## Building the Application

The repository includes `build_gui.bat` for a repeatable Windows build.

1. Open the project folder.
2. Double-click `build_gui.bat`, or run it from Command Prompt.
3. If EZee-Backup is running, the script asks whether to close it. Answer `Y` to close it and continue, or `N` to cancel the build.
4. The compiled application is created at `dist\ezee-backup.exe`, and a numbered copy is saved beside it:

```text
dist\ezee-backup.exe
dist\ezee-backup - (V4.4).exe
```

The build script:

- Reads the version number from `VERSION` in `ezee-backup.py` and shows it in its banner.
- Asks before closing a running copy of EZee-Backup. It asks the app to close normally (so any "unsaved changes" prompt can be answered), and stops if the app is still open after 10 seconds.
- Checks that the required source and asset files are present.
- Builds with the project's own `.venv`, creating it from your Python 3 install if it is missing. This keeps the executable small by bundling only the app's real dependencies.
- Installs `requirements.txt` (plus `pytest`) only when `requirements.txt` has changed since the last install.
- Runs the test suite (`test_app.py`) and stops if any test fails.
- Removes the `build` folder and the previous `dist\ezee-backup.exe` only. The rest of `dist` is kept: older numbered executables, the job file with its safety copy and integrity log, and the `sync_state` history.
- Runs PyInstaller using `ezee-backup.spec`.
- Saves the numbered copy `dist\ezee-backup - (V<version>).exe`. Rebuilding the same version replaces that version's copy; changing `VERSION` starts a new one.
- Updates the version shown in this README (the "Current version" line and the numbered-copy example above) to match `VERSION`, using `update_readme_version.py`. If that fails, it shows a warning; the build still counts as successful.
- Copies `ezee_backup_jobs.json` into `dist` only if `dist` does not already have one, so job profiles saved by the executable are never overwritten.

The PyInstaller specification bundles the application icon, logo, info icon, and the three sounds (`EZ-guitar.wav`, `EZ-error.wav`, `EZ-short-alert1.wav`) into the executable.

## Manual Build

To build manually using the project's virtual environment:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt pytest
.venv\Scripts\python.exe -m pytest -q test_app.py
.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm ezee-backup.spec
```

The result is written to `dist\ezee-backup.exe`. A manual build does not save the numbered copy; copy it yourself if you want one.

## Running From Source

Install the dependencies and start the application with:

```powershell
python ezee-backup.py
```

## Using EZee-Backup

1. Start the application. The "Groups & Jobs" sidebar opens with every node collapsed; expand `All Jobs` or a group to see its jobs.
2. Select a saved job in the sidebar, or enter source and destination folders manually.
3. Use `Browse` to select the Source Folder. The folder picker opens at the folder already in the Source box, or at its nearest existing parent if that folder has been moved or renamed.
4. Use `Browse` to select the Destination Folder (it opens the same way).
5. Tick or untick `Include Sub Folders` as needed.
6. Review the visible folder panes (`Refresh Folders` updates them).
7. Select a mode: Backup, Mirror, Move, Compare, or Sync.
8. Choose a Log setting: Simple, Verbose, or No Logs.
9. Click `RUN`. While it runs, use `Pause` to pause and resume, or `Abort` to stop (you will be asked to confirm).

To run every job in a group, select the group in the sidebar and click `RUN`. Its jobs run one after another, each with its own saved mode; jobs whose drives are offline are skipped and listed in the report. `All Jobs` cannot be run directly; select a job or a group instead.

To keep changes to a job, use `Save Changes` (Ctrl+S), or `Save as New Job` to save them as a new profile. `Forget Changes` discards unsaved edits and reloads the saved profiles.

Use Compare before a Mirror or Sync when you want to inspect the expected operation first.

## Job File Safety

Job profiles are stored in `ezee_backup_jobs.json` beside the executable. These extra files protect it:

| File | Purpose |
| --- | --- |
| `ezee_backup_jobs.safety.json` | An identical safety copy beside the job file, rewritten every time the job file is saved. |
| `%APPDATA%\EZee-Backup\<folder>-<id>\ezee_backup_jobs.safety.json` | A second identical safety copy outside the app folder (see below). |
| `%APPDATA%\EZee-Backup\<folder>-<id>\history\ezee_backup_jobs_<date>_<time>.json` | Dated older copies of the job file (see below). |
| `ezee_backup_jobs_integrity.log` | A record of every save, load, and recovery for all three files, with file size, job count, group count, and SHA-256 fingerprint. |
| `ezee_backup_jobs.corrupt-<date-time>.json` | Only created if a damaged job file or safety copy is found. The damaged file is kept for inspection rather than overwritten. |

**The AppData safety copy.** The second safety copy lives in your Windows user profile, for example `C:\Users\<you>\AppData\Roaming\EZee-Backup\dist-1a2b3c4d\`. Because it is outside the app folder, it survives if the app folder itself is deleted or lost. Each app folder gets its own sub-folder, named after the folder plus a short code made from its full path, so separate copies of EZee-Backup never share or overwrite each other's job profiles. A `copy_of.txt` file in each sub-folder records which job file it belongs to.

Automatic recovery from the AppData copy works when EZee-Backup runs from the same folder path as before. If you put the executable somewhere new, it gets a new sub-folder; to bring your old job profiles across, copy the old `ezee_backup_jobs.safety.json` from AppData into the new app folder as `ezee_backup_jobs.json` (clear read-only on the copy first, or let the app do it).

**Dated older copies.** Each time the job file is saved with changes, a dated copy is added to the `history` folder beside the AppData safety copy, for example `ezee_backup_jobs_2026-10-14_15-20-03.json`. Saving identical contents does not add another copy. These let you go back to an earlier version after a save that was valid but wrong, such as jobs deleted or changed by mistake. The app keeps:

- the 20 most recent dated copies, and
- the newest copy from each of the last 30 days.

Older ones are removed automatically, so a burst of edits in one day cannot push out last week's version. Dated copies are read-only, and if AppData is unavailable they are kept in an `ezee_backup_jobs_history` folder beside the job file instead.

**Restoring the Master Jobs Profile from history.** Use **Edit > Restore Master Jobs Profile from History...**. It lists every dated copy, newest first, with its date and time, job and group counts, and what restoring it would do compared with your current profiles (for example "Brings back: Music | Removes: Test | Changes 1 job"). The current version is marked, and damaged copies are shown but cannot be chosen. Select a version and click `Restore` (or double-click it), then confirm.

Before restoring, your current profiles are kept as a dated copy, so a restore can itself be undone from the same list. The restore is saved like any other change (safety copies and a new dated copy are written, and a `RESTORED` line is added to the integrity log). It is not available while a backup is running, and any unsaved changes to the current job are lost (the confirmation warns you). `Open Folder` opens the folder holding the dated copies.

**Importing a job file (e.g. after rebuilding your PC).** Use **File > Import Master Jobs Profile (JSON)...** and pick any job file: one from an external backup, a safety copy, or a dated copy. It does not need to be called `ezee_backup_jobs.json`. The app checks the file and shows how many job profiles and groups it holds, and what it would change compared with your current profiles, before you confirm. The import replaces your current profiles; they are kept as a dated copy first, so it can be undone with Edit > Restore Master Jobs Profile from History. The imported file is saved like any other change (safety copies, a dated copy, read-only, and an `IMPORTED` line in the integrity log), and the file you picked is left where it was. A file that is not a valid job file is refused and nothing changes. After importing, the app checks the drives the imported jobs use and warns about any that are offline.

When rebuilding a PC, also restore the `sync_state` folder beside the executable if you use Sync. It is not part of the job file: without it, the first Sync for each job deletes nothing but cannot tell which files were deleted before, so files deleted on one side may come back and files that differ get conflict copies.

To restore by hand instead: close EZee-Backup, clear read-only on `ezee_backup_jobs.json`, copy the dated file you want over it (keeping the name `ezee_backup_jobs.json`), and start the app. It re-applies read-only and brings the safety copies in line.

**Saving.** The job file is written to a temporary file first and then swapped into place, so a crash or power cut cannot leave a half-written file. It is read back and checked, then each safety copy is written and checked the same way. If a safety copy cannot be written (for example, AppData is unavailable), the save still succeeds and the problem is recorded in the integrity log.

**Read-only protection.** Between saves, the job file and both safety copies are marked read-only. Each save switches read-only off, writes the file, and switches it straight back on, so the files are only writable for a moment while the app saves. If a save fails, the old file is left in place, still read-only. At startup, the app switches read-only back on if it finds it off (recorded as `PROTECTED` in the integrity log).

Read-only stops programs and scripts from deleting or overwriting the files by accident, and stops a text editor saving over them. It does not stop a delete in File Explorer, a forced delete, or deleting the whole folder. To edit the job file by hand, first clear read-only (right-click the file > Properties > untick Read-only); the app turns it back on the next time it starts.

**Loading.** At startup (and when using Forget Changes) the job file is checked:

- If it is missing or damaged, it is restored from the first usable copy, in this order: the safety copy beside it, the AppData safety copy, then the newest valid dated copy. A warning in a popup and in the Activity Log says which copy was used.
- If the job file, both safety copies, and every dated copy are unusable, any damaged ones are kept aside as `.corrupt-` files and the app starts with an empty job list.
- If the job file is fine but has no matching dated copy yet, one is added.
- If the job file is fine but a safety copy is missing, damaged, or out of date, that safety copy is quietly rebuilt.
- A valid but empty job file never overwrites a safety copy that still holds job profiles.

**Checking a safety copy by hand.** Compare its SHA-256 fingerprint with the latest `SAVE OK` or `LOAD OK` line in the integrity log. In PowerShell:

```powershell
Get-FileHash 'ezee_backup_jobs.safety.json' -Algorithm SHA256
```

If the fingerprints match, the copy is exactly the file that was last saved. The integrity log starts a new file (keeping one previous log as `.log.1`) when it passes 512 KB.

The first safety copy protects against a damaged or deleted job file; the AppData copy also protects against losing the whole app folder. Both are on the same PC, so neither protects against losing the drive or the PC itself. Keep the app folder in your regular backups too.

## Log Actions

Right-click inside the Activity Log panel to access quick clipboard actions:

- `Copy Selected` copies only the currently highlighted log text.
- `Copy Logs` copies the complete log contents to the clipboard.
- `Copy Logs and Launch NOTEPAD` copies the log and opens it in Notepad.
- `Clear Log` resets the log panel back to the default ready message.

This is useful for saving backup output, raising a support issue, or quickly copying the result of a previous operation.

## Understanding Robocopy Log Entries

The Activity Log shows the raw output from Windows `ROBOCOPY`, so a few status words are helpful to understand:

- `Same` means the source file and destination file already match. Nothing needs to be copied.
- `Added` or `New File` style entries mean the file was copied because it did not exist in the destination.
- `Updated` or `Changed` entries mean the destination version differed and was replaced.
- `Skipped` usually means the file was not processed for a reason such as an access issue, a locked file, or a path problem.

So in normal use, `Same` is not an error or a failed copy. It is just Robocopy confirming that no action was required.

## Project Files

| File | Purpose |
| --- | --- |
| `ezee-backup.py` | Main application source. |
| `ezee-backup.spec` | PyInstaller build specification. |
| `build_gui.bat` | Windows build script for GitHub users. |
| `update_readme_version.py` | Run by `build_gui.bat` to keep the README's version number in line with `VERSION`. |
| `requirements.txt` | Python build and runtime dependencies. |
| `test_app.py` | Automated tests for core application behavior. |
| `EZeeBACK Logo.jpg` | Application logo asset. |
| `ezee-backup.ico` | Windows application icon. |
| `backup-info.png` | Info icon shown in the app. |
| `EZ-guitar.wav`, `EZ-error.wav`, `EZ-short-alert1.wav` | Success, error, and repeat-reminder sounds. |
| `ezee_backup_jobs.json` | Saved job profiles (see [Job File Safety](#job-file-safety) for its safety copies and integrity log). |
| `Early DEV Versions\` | Older versions, notes, and unused assets kept for reference. Not used by the build. |

## Testing

Run the tests with:

```powershell
.venv\Scripts\python.exe -m pytest -q test_app.py
```

The tests cover core command construction, job persistence, the job file safety copies (including the AppData copy), dated copies, their clean-up and restoring them, importing a job file, recovery, and read-only protection, executable-directory job storage, the Browse starting folder, sync planning, the application version, and the README version updater.

## Windows 10 Deployment Checklist

Use this checklist before installing or distributing EZee-Backup on a Windows 10 PC.

- Windows 10 or newer is supported.
- `ROBOCOPY` must be available on the target machine.
- Confirm the command works in Command Prompt:

```cmd
robocopy /?
```

- Check permission to read the source folder.
- Check permission to write to the destination folder.
- Ensure the source and destination paths exist and are valid folders.
- Avoid protected or locked-down locations unless the user has the required rights.
- Do not point the source and destination at the same folder.
- Ensure external drives or network shares are connected and mapped correctly.
- Verify no file locks are blocking the backup process.
- Run the app under a normal user session with valid access to both folders.
- Test a simple copy manually before relying on the backup tool:

```cmd
robocopy "C:\SampleSource" "D:\BackupTarget" /E
```

If `robocopy` runs successfully in Command Prompt, the Windows environment is generally suitable for EZee-Backup.

Common issues are permission problems, invalid paths, locked files, or restricted corporate policies rather than app-level incompatibility with Windows 10.

## Safety Notes

- Always verify Source and Destination before clicking `RUN`.
- `Mirror` removes destination files that are not in the source.
- `Sync` carries deletions in both directions (deleted files go to the Recycle Bin).
- `Move` removes files from the source after copying them.
- Use `Compare` to preview the expected copy operation first.
- Keep independent backups of important data.

## License

No license has been specified for this project yet. Add a license file before accepting or encouraging external redistribution.
