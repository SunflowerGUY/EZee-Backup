@echo off
setlocal EnableExtensions
cd /d "%~dp0"

taskkill /f /t /im EZee-Backup.exe >nul 2>&1

echo ============================================
echo  EZee-Backup v2.5 - PyInstaller Build
echo ============================================
echo.

rem Find a usable Python command.
set "PYTHON="
where py >nul 2>nul
if %ERRORLEVEL% equ 0 set "PYTHON=py -3"
if not defined PYTHON (
    where python >nul 2>nul
    if %ERRORLEVEL% equ 0 set "PYTHON=python"
)
if not defined PYTHON (
    echo ERROR: Python 3 was not found on PATH.
    echo Install Python 3 from https://www.python.org/downloads/windows/
    echo Ensure "Add Python to PATH" is enabled, then run this file again.
    pause
    exit /b 1
)

echo Using Python: %PYTHON%
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

tasklist /FI "IMAGENAME eq EZee-Backup.exe" | find /I "EZee-Backup.exe" >nul
if %ERRORLEVEL% equ 0 (
    echo ERROR: EZee-Backup.exe is currently running.
    echo Close every running copy of the app, then run this script again.
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
%PYTHON% -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)
echo.

echo [2/4] Running tests...
%PYTHON% -m pytest -q
if %ERRORLEVEL% neq 0 (
    echo ERROR: Tests failed. The executable was not built.
    pause
    exit /b 1
)
echo.

echo [3/4] Cleaning old build artifacts...
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
if exist "dist" rmdir /s /q "dist"
if exist "dist" (
    echo ERROR: The dist folder could not be removed.
    echo Close any programs using files in the dist folder and try again.
    pause
    exit /b 1
)
echo.

echo [4/4] Building EZee-Backup.exe...
%PYTHON% -m PyInstaller --clean --noconfirm ezee-backup.spec
if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)
echo.

echo ============================================
echo  Build complete!
echo ============================================
echo.
echo Output: dist\EZee-Backup.exe
echo.
echo The build is windowed and includes the application icon, logo, info icon, success sound, and error sound.
echo The target machine needs Windows and Python is not required to run the EXE.
echo ROBOCOPY is supplied by Windows and is used by the backup operation.
echo.
copy ezee_backup_jobs.json .\dist
exit /b 0
