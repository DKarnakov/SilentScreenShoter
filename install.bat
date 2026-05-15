@echo off
chcp 65001 > nul

set "TARGET_DIR=%ProgramFiles%\SilentScreenShoter"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SCRIPT_NAME=main.pyw"
set "SHORTCUT_NAME=3S.lnk"

echo [1/3] Проверка и создание целевой папки...
if not exist "%TARGET_DIR%" (
    mkdir "%TARGET_DIR%"
    echo Создана папка: %TARGET_DIR%
) else (
    echo Копирование файлов в существующую папку
)

echo.
echo [2/3] Копирование файлов...
xcopy "%~dp0*" "%TARGET_DIR%\" /E /Y /I /EXCLUDE:%~nx0

echo.
echo [3/3] Создание ярлыка в Автозагрузке...

set "VBS_SCRIPT=%TEMP%\CreateShortcut.vbs"

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_SCRIPT%"
echo sLinkFile = "%STARTUP_DIR%\%SHORTCUT_NAME%" >> "%VBS_SCRIPT%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS_SCRIPT%"
echo oLink.TargetPath = "%TARGET_DIR%\%SCRIPT_NAME%" >> "%VBS_SCRIPT%"
echo oLink.WorkingDirectory = "%TARGET_DIR%" >> "%VBS_SCRIPT%"
echo oLink.Save >> "%VBS_SCRIPT%"

cscript //nologo "%VBS_SCRIPT%"
del "%VBS_SCRIPT%"

echo Ярлык "%SHORTCUT_NAME%" успешно создан в Автозагрузке.
echo.
echo Установка завершена!
pause