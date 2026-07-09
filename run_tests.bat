@echo off
:: run_tests.bat
:: Repeat CLEAR benchmark evaluation N times
::
:: Usage:
:: run_tests.bat
::
:: Example:
:: run_tests.bat --models qwen2.5-coder:7b --types logic


set RUNS=3


call .venv\Scripts\activate.bat


echo ====================================================
echo Starting CLEAR Master Batch Evaluation
echo Total Runs Scheduled: %RUNS%
echo Start Time: %time%
echo ====================================================


for /L %%i in (1,1,%RUNS%) do (

    echo.
    echo ===== Run %%i of %RUNS% =====
    echo Started: %time%

    python -m run_benchmarks %* >> batch_master.log 2>&1


    if errorlevel 1 (
        echo [WARNING] Run %%i FAILED
    ) else (
        echo Run %%i completed successfully
    )


    echo Cooling down Ollama...
    timeout /t 5 >nul
)


echo.
echo ====================================================
echo Finished all %RUNS% runs.
echo End Time: %time%
echo ====================================================


rundll32 user32.dll,MessageBeep

pause