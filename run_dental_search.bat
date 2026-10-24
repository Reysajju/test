@echo off
title Dental Clinic Lead Scraper (USA & Canada - No Website)
chcp 65001 >nul
cd /d "%~dp0"
echo ======================================================================
echo   Launching Autonomous Dental Clinic Scraper (USA & Canada)
echo   Saving into: "Sajjad data"
echo ======================================================================
node start_dental_scraper.js
pause
