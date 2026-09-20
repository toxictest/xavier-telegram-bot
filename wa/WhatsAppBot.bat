@echo off
title Xavier WhatsApp Bot
cd /d "%~dp0"

:checknode
where node >nul 2>nul
if errorlevel 1 (
  echo.
  echo [ERROR] Node.js install nahi hai!
  echo Pehle Node.js install karo: https://nodejs.org  (LTS version, saari settings default)
  echo Install hone ke baad yehi WhatsAppBot.bat dobara double-click karo.
  echo.
  pause
  exit /b 1
)

if not exist node_modules (
  echo [SETUP] Pehli baar chala rahe ho - packages install kar raha hoon (2-3 min, ek baar hi)...
  call npm install
  echo [SETUP] Packages ready!
  echo.
)

:run
echo ============================================
echo   XAVIER WHATSAPP BOT - CHAL RAHA HAI
echo   Is window ko BAND MAT KARNA.
echo   PC on rahega = bot 24/7 jaagta rahega.
echo   PC sleep/hibernate mat karna (Power settings).
echo ============================================
echo.
node wa-bot.js
echo.
echo [WARN] Bot band ho gaya - 5 sec me dobara start ho raha hai...
timeout /t 5 /nobreak >nul
goto run
