@echo off
setlocal EnableDelayedExpansion
cd /d "C:\Users\jnpei\Documents\stock-chart"

set PYTHON=C:\Users\jnpei\AppData\Local\Programs\Python\Python314\python.exe
set LOG=data\auto_run_log.txt
set ERR=0

if not exist data mkdir data

echo. >> "%LOG%"
echo ================================================== >> "%LOG%"
echo [START] %date% %time% >> "%LOG%"
echo ================================================== >> "%LOG%"

echo [1/2] download_prices.py ... >> "%LOG%"
"%PYTHON%" download_prices.py >> "%LOG%" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [1/2] download_prices.py: OK >> "%LOG%"
) else (
    echo [1/2] download_prices.py: FAILED ^(code=%ERRORLEVEL%^) >> "%LOG%"
    set ERR=1
)

echo [2/2] merge_prices.py ... >> "%LOG%"
"%PYTHON%" merge_prices.py >> "%LOG%" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [2/2] merge_prices.py: OK >> "%LOG%"
) else (
    echo [2/2] merge_prices.py: FAILED ^(code=%ERRORLEVEL%^) >> "%LOG%"
    set ERR=1
)

if !ERR! EQU 0 (
    echo [END] All done. %date% %time% >> "%LOG%"
) else (
    echo [END] Finished with errors. %date% %time% >> "%LOG%"
)

endlocal
exit /b 0
