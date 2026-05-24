@echo off
setlocal EnableDelayedExpansion

cd /d "C:\Users\jnpei\Documents\stock-chart"

set PYTHON=C:\Users\jnpei\AppData\Local\Programs\Python\Python314\python.exe
set LOG=data\auto_run_log.txt
set ERR=0

if not exist data mkdir data

echo ==================================================
echo   StockChart Weekly Runner
echo ==================================================
echo Working dir : %CD%
echo Python path : %PYTHON%
if not exist "%PYTHON%" (
    echo [ERROR] Python not found^^!
    pause
    exit /b 1
)
"%PYTHON%" --version
echo Log file    : %CD%\%LOG%
echo.

echo. >> "%LOG%"
echo ================================================== >> "%LOG%"
echo [WEEKLY START] %date% %time% >> "%LOG%"
echo ================================================== >> "%LOG%"

echo [1/3] download_prices.py ...
echo [1/3] download_prices.py ... >> "%LOG%"
"%PYTHON%" download_prices.py >> "%LOG%" 2>&1
set RC=%ERRORLEVEL%
if %RC% EQU 0 (
    echo [1/3] download_prices.py: OK
    echo [1/3] download_prices.py: OK >> "%LOG%"
) else (
    echo [1/3] download_prices.py: FAILED  code=%RC%
    echo [1/3] download_prices.py: FAILED  code=%RC% >> "%LOG%"
    set ERR=1
)

echo [2/3] merge_prices.py ...
echo [2/3] merge_prices.py ... >> "%LOG%"
"%PYTHON%" merge_prices.py >> "%LOG%" 2>&1
set RC=%ERRORLEVEL%
if %RC% EQU 0 (
    echo [2/3] merge_prices.py: OK
    echo [2/3] merge_prices.py: OK >> "%LOG%"
) else (
    echo [2/3] merge_prices.py: FAILED  code=%RC%
    echo [2/3] merge_prices.py: FAILED  code=%RC% >> "%LOG%"
    set ERR=1
)

echo [3/3] create_weekly_merged.py ...
echo [3/3] create_weekly_merged.py ... >> "%LOG%"
"%PYTHON%" create_weekly_merged.py >> "%LOG%" 2>&1
set RC=%ERRORLEVEL%
if %RC% EQU 0 (
    echo [3/3] create_weekly_merged.py: OK
    echo [3/3] create_weekly_merged.py: OK >> "%LOG%"
) else (
    echo [3/3] create_weekly_merged.py: FAILED  code=%RC%
    echo [3/3] create_weekly_merged.py: FAILED  code=%RC% >> "%LOG%"
    set ERR=1
)

echo.
if !ERR! EQU 0 (
    echo [END] All done.
    echo [END] All done. %date% %time% >> "%LOG%"
) else (
    echo [END] Finished with errors.
    echo [END] Finished with errors. %date% %time% >> "%LOG%"
)
echo.
echo Log saved to: %CD%\%LOG%
echo.
endlocal
exit /b 0