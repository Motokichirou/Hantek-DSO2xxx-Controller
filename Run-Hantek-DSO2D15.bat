@echo off
rem ── Лаунчер десктоп-клиента Hantek DSO2D15 ──
rem Запускает приложение из venv проекта. Окно консоли остаётся открытым
rem при ошибке запуска, чтобы был виден traceback/лог.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ОШИБКА] Не найден venv: .venv\Scripts\python.exe
    echo Создайте окружение и установите зависимости перед запуском.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m hantek_dso2d15.app
if errorlevel 1 (
    echo.
    echo [Приложение завершилось с ошибкой; код %errorlevel%]
    pause
)
endlocal
