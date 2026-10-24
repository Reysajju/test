@echo off
title Push Dental Scraper to GitHub
chcp 65001 >nul
cd /d "%~dp0"
echo ======================================================================
echo    🚀 PUSH DENTAL CLINIC SCRAPER TO GITHUB (FREE 24/7 CLOUD RUNNER)
echo ======================================================================
echo.
echo Step 1: Create a new repository on GitHub (https://github.com/new)
echo         - Name it: dental-scraper (or any name you like)
echo         - Choose Private or Public
echo.
set /p REPO_URL="Step 2: Paste your GitHub repository URL here (e.g. https://github.com/Reysajju/dental-scraper.git): "

if "%REPO_URL%"=="" (
    echo Error: Repository URL cannot be empty.
    pause
    exit /b
)

git remote remove origin 2>nul
git remote add origin %REPO_URL%
git branch -M main
git push -u origin main

echo.
echo ======================================================================
echo    ✅ SUCCESS! YOUR REPOSITORY IS LIVE ON GITHUB!
echo ======================================================================
echo  1. Go to your repository on GitHub.
echo  2. Click on the 'Actions' tab.
echo  3. Enable Workflows if prompted, and click 'Run workflow'.
echo  4. It will now run in the cloud automatically and update your Excel file!
echo ======================================================================
pause
