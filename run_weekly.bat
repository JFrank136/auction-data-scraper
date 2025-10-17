@echo off
REM BidFTA Auction Scraper - Weekly Batch Runner with Wake Support
REM This batch file can be used with Windows Task Scheduler
REM It includes logging and error handling

echo ====================================
echo BidFTA Auction Scraper Starting
echo Date: %date%
echo Time: %time%
echo ====================================

REM Change to the script directory (where this batch file is located)
cd /d "%~dp0"

REM Log the current directory
echo Current directory: %cd%

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python and try again
    goto :error_exit
)

REM Check if required files exist
if not exist "main.py" (
    echo ERROR: main.py not found in current directory
    goto :error_exit
)

if not exist "config.py" (
    echo ERROR: config.py not found in current directory
    goto :error_exit
)

echo Python found, running auction scraper...

REM Run the Python scraper
py main.py

REM Check the exit code from Python script
if %errorlevel% equ 0 (
    echo.
    echo ====================================
    echo SUCCESS: Auction scraper completed successfully!
    echo Date: %date%
    echo Time: %time%
    echo ====================================
    goto :success_exit
) else (
    echo.
    echo ====================================
    echo ERROR: Auction scraper failed with error code %errorlevel%
    echo Check the log file for details: auction_scraper.log
    echo Date: %date%
    echo Time: %time%
    echo ====================================
    goto :error_exit
)

:success_exit
REM Keep computer awake for a few more minutes after completion
echo Keeping system awake for 2 more minutes...
timeout /t 120 /nobreak >nul
exit /b 0

:error_exit
REM Keep computer awake for a few more minutes to ensure logging completes
timeout /t 60 /nobreak >nul
exit /b 1