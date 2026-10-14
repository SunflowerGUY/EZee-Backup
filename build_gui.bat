@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem If the app is running, ask before closing it (it holds the EXE open).
tasklist /FI "IMAGENAME eq EZee-Backup.exe" | find /I "EZee-Backup.exe" >nul
if errorlevel 1 goto :app_closed
echo EZee-Backup is currently running.
echo Closing it will stop any backup that is in progress.
choice /c YN /n /m "Close EZee-Backup now and continue the build? [Y/N] "
rem Errorlevel 1 = Y. Anything else (N, or no keyboard input) cancels.
if errorlevel 2 goto :cancel_build
if not errorlevel 1 goto :cancel_build
echo Asking EZee-Backup to close...
taskkill /t /im EZee-Backup.exe >nul 2>&1
rem Give it up to 10 seconds to close (it may ask about unsaved changes).
for /l %%N in (1,1,10) do (
    tasklist /FI "IMAGENAME eq EZee-Backup.exe" | find /I "EZee-Backup.exe" >nul || goto :app_closed
    ping -n 2 127.0.0.1 >nul
)
goto :app_closed

:cancel_build
echo Build cancelled. EZee-Backup was left running.
pause
exit /b 1

:app_closed

rem Read the version straight from the app, e.g. VERSION = "4.1"
set "APP_VERSION=?"
if exist "ezee-backup.py" (
    for /f tokens^=2^ delims^=^" %%V in ('findstr /b /c:"VERSION = " "ezee-backup.py"') do set "APP_VERSION=%%V"
)

echo ============================================
echo  EZee-Backup v%APP_VERSION% - PyInstaller Build
echo ============================================
echo.

if not exist "ezee-backup.py" (
    echo ERROR: ezee-backup.py was not found in this folder.
    pause
    exit /b 1
)
if not exist "ezee-backup.spec" (
    echo ERROR: ezee-backup.spec was not found in this folder.
    pause
    exit /b 1
)
if not exist "coffee_support.py" (
    echo ERROR: coffee_support.py was not found in this folder.
    pause
    exit /b 1
)
if not exist "EZeeBACK Logo.jpg" (
    echo ERROR: EZeeBACK Logo.jpg was not found in this folder.
    pause
    exit /b 1
)
if not exist "ezee-backup.ico" (
    echo ERROR: ezee-backup.ico was not found in this folder.
    pause
    exit /b 1
)
if not exist "backup-info.png" (
    echo ERROR: backup-info.png was not found in this folder.
    pause
    exit /b 1
)
if not exist "EZ-guitar.wav" (
    echo ERROR: EZ-guitar.wav was not found in this folder.
    pause
    exit /b 1
)
if not exist "EZ-error.wav" (
    echo ERROR: EZ-error.wav was not found in this folder.
    pause
    exit /b 1
)
if not exist "EZ-short-alert1.wav" (
    echo ERROR: EZ-short-alert1.wav was not found in this folder.
    pause
    exit /b 1
)

tasklist /FI "IMAGENAME eq EZee-Backup.exe" | find /I "EZee-Backup.exe" >nul
if %ERRORLEVEL% equ 0 (
    echo ERROR: EZee-Backup.exe is currently running.
    echo Close every running copy of the app, then run this script again.
    pause
    exit /b 1
)

rem Build with the project's own .venv so only the app's real dependencies are bundled
rem (the main Python install has extras such as numpy that bloat the EXE).
set "PYTHON=.venv\Scripts\python.exe"
set "REQ_STAMP=.venv\requirements.installed.txt"

echo [1/4] Checking build environment...
if exist "%PYTHON%" goto :venv_ready
echo Creating .venv ...
call :find_base_python
if errorlevel 1 exit /b 1
call %BASE_PYTHON% -m venv .venv
if errorlevel 1 (
    echo ERROR: Could not create the .venv folder.
    pause
    exit /b 1
)
if exist "%REQ_STAMP%" del /q "%REQ_STAMP%"
:venv_ready

rem Only run pip when requirements.txt has changed since the last install.
set "NEED_INSTALL=1"
if exist "%REQ_STAMP%" (
    fc /b "requirements.txt" "%REQ_STAMP%" >nul 2>&1 && set "NEED_INSTALL="
)
if defined NEED_INSTALL (
    echo Installing dependencies...
    "%PYTHON%" -m pip install -r requirements.txt pytest
    if errorlevel 1 (
        echo ERROR: Dependency installation failed.
        pause
        exit /b 1
    )
    copy /y "requirements.txt" "%REQ_STAMP%" >nul
) else (
    echo Dependencies are up to date - skipping pip.
)
echo Using Python: %PYTHON%
echo.

echo [2/4] Running tests...
"%PYTHON%" -m pytest -q test_app.py
if %ERRORLEVEL% neq 0 (
    echo ERROR: Tests failed. The executable was not built.
    pause
    exit /b 1
)
echo.

echo [3/4] Cleaning old build artifacts...
rem Only the build folder and the old EXE are removed. The rest of dist is kept:
rem it holds older versioned EXEs, the JOB file, its safety copy and integrity
rem log, and the sync_state history.
if exist "build" rmdir /s /q "build"
if exist "build" (
    echo ERROR: The build folder could not be removed.
    echo Close any programs using files in the build folder and try again.
    pause
    exit /b 1
)
if exist "dist\EZee-Backup.exe" del /f /q "dist\EZee-Backup.exe" >nul 2>&1
if exist "dist\EZee-Backup.exe" (
    echo ERROR: dist\EZee-Backup.exe is locked or protected.
    echo Close EZee-Backup and any Explorer preview window, then try again.
    echo Windows Security may also be scanning or quarantining this file.
    pause
    exit /b 1
)
echo.

echo [4/4] Building EZee-Backup.exe...
"%PYTHON%" -m PyInstaller --clean --noconfirm ezee-backup.spec
if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)
echo.

rem Keep a numbered copy of this build, e.g. dist\ezee-backup - (V4.2).exe
rem A rebuild of the same version replaces that version's copy.
set "VERSIONED_EXE="
if "%APP_VERSION%"=="?" (
    echo WARNING: Could not read VERSION from ezee-backup.py - no numbered copy was saved.
) else (
    set "VERSIONED_EXE=dist\ezee-backup - (V%APP_VERSION%).exe"
)
if defined VERSIONED_EXE (
    copy /y "dist\ezee-backup.exe" "%VERSIONED_EXE%" >nul
    if errorlevel 1 (
        echo WARNING: Could not save "%VERSIONED_EXE%". Is that file open or locked?
        set "VERSIONED_EXE="
    )
)

rem Keep the version shown in README.md in step with VERSION in ezee-backup.py.
rem A problem here is reported as a warning; the build itself has already succeeded.
"%PYTHON%" update_readme_version.py

echo ============================================
echo  Build complete!
echo ============================================
echo.
echo Output: dist\ezee-backup.exe
if defined VERSIONED_EXE echo Numbered copy: %VERSIONED_EXE%
echo.
echo The build is windowed and includes the application icon, logo, info icon, success sound, and error sound.
echo The target machine needs Windows and Python is not required to run the EXE.
echo ROBOCOPY is supplied by Windows and is used by the backup operation.
echo.
rem Seed dist with the JOB file only if it has none, so the EXE's own job profiles are never overwritten.
if not exist "dist\ezee_backup_jobs.json" copy ezee_backup_jobs.json .\dist
exit /b 0


:find_base_python
rem Find a Python 3 install to create the .venv from.
set "BASE_PYTHON="
where py >nul 2>nul && set "BASE_PYTHON=py -3"
if not defined BASE_PYTHON where python >nul 2>nul && set "BASE_PYTHON=python"
if not defined BASE_PYTHON (
    echo ERROR: Python 3 was not found on PATH.
    echo Install Python 3 from https://www.python.org/downloads/windows/
    echo Ensure "Add Python to PATH" is enabled, then run this file again.
    pause
    exit /b 1
)
exit /b 0
