@echo off
title Push Dental Scraper to GitHub
cd /d "%~dp0"

echo ======================================================================
echo    PUSH DENTAL CLINIC SCRAPER TO GITHUB (FREE 24/7 CLOUD RUNNER)
echo ======================================================================
echo.
echo Option 1: Press ENTER to push to your repository:
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

echo Uploading to GitHub...
git push -u origin main --force

if %ERRORLEVEL% equ 0 (
    echo.
    echo ======================================================================
    echo    SUCCESS! YOUR REPOSITORY IS LIVE ON GITHUB!
    echo ======================================================================
    echo  1. Open: https://github.com/Reysajju/test/actions
    echo  2. You will see '24/7 Dental Clinic Scraper (Free Forever)'
    echo  3. It will now run in the cloud automatically every 4 hours!
    echo ======================================================================
) else (
    echo.
    echo ======================================================================
    echo  Notice: If prompted, complete the GitHub sign-in and run again.
    echo ======================================================================
)

pause
