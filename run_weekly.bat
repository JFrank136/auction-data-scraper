@echo off
REM BidFTA Auction Scraper - Weekly Batch Runner
REM Used with Windows Task Scheduler
REM Logs both scheduler activity and Python output to log\ folder

REM ── Setup dated log file ──────────────────────────────
REM Build a YYYY-MM-DD timestamp for the log filename
for /f "tokens=1-3 delims=/ " %%a in ("%date%") do (
    set MM=%%a
    set DD=%%b
    set YYYY=%%c
)
set LOG_DATE=%YYYY%-%MM%-%DD%
set LOG_DIR=%~dp0log
set LOG_FILE=%LOG_DIR%\scheduler_%LOG_DATE%.log

REM Create log directory if it doesn't exist
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Redirect all output (stdout + stderr) to the log file AND the console
REM Everything below this line is captured
call :main >> "%LOG_FILE%" 2>&1
exit /b %errorlevel%

:main
echo ====================================
echo BidFTA Auction Scraper - Task Scheduler Run
echo Date: %date%
echo Time: %time%
echo Log file: %LOG_FILE%
echo ====================================

REM Change to the script directory
cd /d "%~dp0"
echo Working directory: %cd%

REM ── Prune old scheduler logs (keep last 8) ────────────
echo Checking for old scheduler logs to prune...
set COUNT=0
for /f "tokens=*" %%f in ('dir /b /o:d "%LOG_DIR%\scheduler_*.log" 2^>nul') do (
    set /a COUNT+=1
    set OLDEST=%%f
)
REM Delete oldest files until we're at or under 8
:prune_loop
if %COUNT% GTR 8 (
    echo Pruning old log: %OLDEST%
    del "%LOG_DIR%\%OLDEST%"
    set /a COUNT-=1
    REM Re-find the new oldest
    for /f "tokens=*" %%f in ('dir /b /o:d "%LOG_DIR%\scheduler_*.log" 2^>nul') do (
        set OLDEST=%%f
        goto :prune_check
    )
    :prune_check
    goto :prune_loop
)
echo Log count OK: %COUNT% scheduler log(s) in %LOG_DIR%

REM ── Verify Python is available ────────────────────────
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python ^(py^) is not installed or not in PATH
    echo Task Scheduler may be running with a different user environment
    echo Try using the full path to python.exe in Task Scheduler action
    goto :error_exit
)

echo Python found:
py --version

REM ── Verify required files exist ───────────────────────
if not exist "main.py" (
    echo ERROR: main.py not found in %cd%
    echo Check that the Task Scheduler Start In directory is set correctly
    goto :error_exit
)

if not exist "config.py" (
    echo ERROR: config.py not found in %cd%
    goto :error_exit
)

REM ── Run the scraper ───────────────────────────────────
echo.
echo Starting Python scraper...
echo Time: %time%
echo.

py main.py

set EXIT_CODE=%errorlevel%

echo.
if %EXIT_CODE% equ 0 (
    echo ====================================
    echo SUCCESS: Scraper completed - exit code 0
    echo Date: %date%
    echo Time: %time%
    echo ====================================
    goto :success_exit
) else (
    echo ====================================
    echo ERROR: Scraper failed - exit code %EXIT_CODE%
    echo Check the Python log in: %LOG_DIR%\scraper_%LOG_DATE%.log
    echo Date: %date%
    echo Time: %time%
    echo ====================================
    goto :error_exit
)

:success_exit
REM Keep system awake briefly after completion
timeout /t 120 /nobreak >nul
exit /b 0

:error_exit
timeout /t 60 /nobreak >nul
exit /b 1