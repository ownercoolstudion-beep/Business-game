@echo off
title Business Empire Server
color 0A

echo.
echo  ╔══════════════════════════════════╗
echo  ║  🏢  BUSINESS EMPIRE SERVER      ║
echo  ╚══════════════════════════════════╝
echo.

:: Python suchen
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 goto :start

python3 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 goto :start

echo  ❌ Python ist nicht installiert!
echo.
echo  📥 https://www.python.org/downloads/
echo  Haken bei "Add to PATH" setzen!
echo.
pause
start https://www.python.org/downloads/
exit /b 1

:start
if not exist "index.html" (
    echo  ⚠️  index.html fehlt im Ordner!
    pause
    exit /b 1
)
timeout /t 2 /nobreak >nul
start http://localhost:3000
python server.py

:: Check if Node.js is installed
node --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  ❌ Node.js ist NICHT installiert!
    echo.
    echo  📥 Bitte Node.js installieren:
    echo     https://nodejs.org  --^> LTS Version downloaden
    echo.
    echo  Nach der Installation diese Datei erneut starten.
    echo.
    pause
    start https://nodejs.org
    exit /b 1
)

echo  ✅ Node.js gefunden:
node --version
echo.

:: Check if npm packages are installed
if not exist "node_modules" (
    echo  📦 Pakete werden installiert...
    echo     (nur beim ersten Start, dauert ~30 Sekunden)
    echo.
    npm install
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo  ❌ Installation fehlgeschlagen!
        echo     Prüfe deine Internetverbindung.
        pause
        exit /b 1
    )
    echo.
    echo  ✅ Installation erfolgreich!
    echo.
)

:: Check if index.html exists
if not exist "index.html" (
    echo  ⚠️  WARNUNG: index.html nicht gefunden!
    echo.
    echo  Bitte die Spiel-Datei (business_empire_v6.html)
    echo  umbenennen zu: index.html
    echo.
    echo  Danach diese Datei erneut starten.
    echo.
    pause
    exit /b 1
)

:: Get IP address
echo  🌐 Netzwerk-Adresse:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set IP=%%a
    goto :found_ip
)
:found_ip
set IP=%IP: =%

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║       SERVER STARTET...                          ║
echo  ╠══════════════════════════════════════════════════╣
echo  ║                                                  ║
echo  ║  Dein PC:    http://localhost:3000               ║
echo  ║  Netzwerk:   http://%IP%:3000             ║
echo  ║                                                  ║
echo  ║  Andere Spieler geben die Netzwerk-URL ein!      ║
echo  ║  Stoppen: Dieses Fenster schließen               ║
echo  ║                                                  ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: Open browser automatically
timeout /t 2 /nobreak >nul
start http://localhost:3000

:: Start server
node server.js

pause
