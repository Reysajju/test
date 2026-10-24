@echo off
title Push Dental Scraper to GitHub
cd /d "%~dp0"

echo ======================================================================
echo    PUSH DENTAL CLINIC SCRAPER TO GITHUB (FREE 24/7 CLOUD RUNNER)
echo ======================================================================
echo.
echo Option 1: Press ENTER to push to your existing repository:
echo           https://github.com/Reysajju/test.git
echo.
echo Option 2: Or paste another GitHub repository URL below
echo.
set "TARGET_URL=https://github.com/Reysajju/test.git"
set "USER_INPUT="
set /p USER_INPUT="Enter GitHub Repository URL [Press ENTER for test.git]: "

if not "%USER_INPUT%"=="" (
    set "TARGET_URL=%USER_INPUT%"
)

echo.
echo Connecting to: %TARGET_URL%
echo.

git remote remove origin 2>nul
git remote add origin %TARGET_URL%
git branch -M main

echo Starting push to GitHub...
git push -u origin main

if %ERRORLEVEL% equ 0 (
    echo.
    echo ======================================================================
    echo    SUCCESS! YOUR REPOSITORY IS LIVE ON GITHUB!
    echo ======================================================================
    echo  1. Go to your repository on GitHub.
    echo  2. Click on the 'Actions' tab.
    echo  3. Click 'Run workflow' to start the 24/7 scraper!
    echo ======================================================================
) else (
    echo.
    echo ======================================================================
    echo  Push notice: If Git prompted for browser sign-in, please complete
    echo  the login and re-run this script.
    echo ======================================================================
)

pause
