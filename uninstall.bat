@echo off
chcp 65001 >nul
title Удаление SilentScreenShoter

:: Проверка на права администратора
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Запрjc прав администратора...
    powershell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit /b
)

echo [!] Проверка запущенных экземпляров программы...

:: Поиск и завершение процессов python/pythonw, содержащих в командной строке имя нашего скрипта
powershell -Command ^
    "$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*main.pyw*' -or $_.CommandLine -like '*SilentScreenShoter*' }; " ^
    "if ($procs) { " ^
    "    Write-Host '[!] Программа запущена. Закрытие процессов...'; " ^
    "    $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; " ^
    "}"

:: Пауза, чтобы операционная система успела освободить файлы в памяти
timeout /t 2 /nobreak >nul

:: Удаление ярлыка из Автозагрузки
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP_DIR%\3S.lnk" (
    echo [!] Удаление из Автозагрузки...
    del /f /q "%STARTUP_DIR%\3S.lnk"
    echo [OK] Ярлык успешно удален
) else (
    echo [!] Ярлык в Автозагрузке не найден
)

:: Удаление папки из Program Files
set "INSTALL_DIR=%ProgramFiles%\SilentScreenShoter"
if exist "%INSTALL_DIR%" (
    echo [!] Удаление файлов и папки %INSTALL_DIR%...
    rmdir /s /q "%INSTALL_DIR%"
    echo [OK] Папка программы успешно удалена
) else (
    echo [!] Директория программы в Program Files не найдена
)

echo.
echo [!] Программа SilentScreenShoter полностью удалена
pause
