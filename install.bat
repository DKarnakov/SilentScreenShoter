@echo off
chcp 65001 >nul
title Установка SilentScreenShoter

:: Проверка на права администратора
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Запрос прав администратора...
    powershell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit /b
)

:: Скачивание и установка Python
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Python не найден. Начинаю загрузку...
    curl -L -o "%TEMP%\python_installer.exe" "https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe"
    
    echo [>] Установка Python (это может занять несколько минут)...
    "%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del "%TEMP%\python_installer.exe"
    echo [+] Python установлен

    :: Обновляем PATH в текущем сеансе
    for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path') do set "PATH=%%B;%PATH%"
) else (
    echo [OK] Python установлен
)

:: Скачивание и установка Tesseract OCR
if not exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo [!] Tesseract OCR не найден. Начинаю загрузку...
    curl -L -o "%TEMP%\tesseract_installer.exe" "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
    
    echo [>] Установка Tesseract OCR...
    "%TEMP%\tesseract_installer.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="C:\Program Files\Tesseract-OCR"
    del "%TEMP%\tesseract_installer.exe"
    echo [+] Tesseract OCR установлен
) else (
    echo [OK] Tesseract OCR установлен
)

:: Установка модулей из requirements.txt
if exist "%~dp0requirements.txt" (
    echo [>] Установка необходимых библиотек...
    pip install -r "%~dp0requirements.txt"
) else (
    echo [!] Файл requirements.txt не найден!
)

:: Создание папки в Program Files
set "INSTALL_DIR=%ProgramFiles%\SilentScreenShoter"
echo [>] Создание директории %INSTALL_DIR%...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Копирование файлов с исключениями
echo [ИНФО] Копирование файлов программы...
robocopy "%~dp0." "%INSTALL_DIR%" /E /XF "install.bat" "requirements.txt" >nul

:: Логика выбора режима запуска
echo.
set "USER_ARGS="
set /p SILENT_CHOICE="[?] Активировать программу при старте Windows? [y/n]: "

if /i "%SILENT_CHOICE%"=="y" (
    echo [!] Выбран обычный режим. Для запуска программы нажмите левую и правую клавишу мыши одновременно
) else (
    set "USER_ARGS=--silent"
    echo [!] Выбран тихий режим. Для активации программы нажмите одновременно обе клавиши мыши и колесо
)

:: Создание ярлыка в автозагрузке
echo [>] Создание ярлыка в Автозагрузке...
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_DIR%\3S.lnk"
set "TARGET_PATH=%INSTALL_DIR%\main.pyw"

powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%'); $Shortcut.TargetPath = '%TARGET_PATH%'; $Shortcut.Arguments = '%USER_ARGS%'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Save()"

echo.
echo [!] Установка успешно завершена
pause
