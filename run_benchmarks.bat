@echo off
setlocal enabledelayedexpansion

:: ==============================================================================
:: CLEAR Master Batch Evaluation Script
:: ==============================================================================
:: Description: 
::   Automates multiple sequential executions of the CLEAR benchmark suite.
::   Ensures clean environment activation, forwards CLI arguments to the Python 
::   orchestrator, tracks failure counts, and provides sufficient VRAM flush time
::   between runs to prevent Out-Of-Memory (OOM) exceptions.
::
:: Usage:
::   run_tests.bat [args]
::
:: Examples:
::   run_tests.bat                                   (Runs default suite 3 times)
::   run_tests.bat --models qwen2.5-coder:7b         (Runs specific model 3 times)
:: ==============================================================================

:: -----------------------------------------------------
:: Configuration
:: -----------------------------------------------------
:: Define the number of full evaluation loops to execute
set RUNS=3


:: -----------------------------------------------------
:: 1. Environment Verification & Activation
:: -----------------------------------------------------
:: Ensures the script is running within the correct Python virtual environment.
:: If the environment is missing, it fails fast with setup instructions.
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at .venv
    echo Run: python -m venv .venv ^&^& pip install -e .
    exit /b 1
)

:: Activate the virtual environment for the current session
call .venv\Scripts\activate.bat


:: -----------------------------------------------------
:: 2. Initialization & Logging
:: -----------------------------------------------------
echo ====================================================
echo Starting CLEAR Master Batch Evaluation
echo Total Runs Scheduled: %RUNS%
echo Arguments: %*
echo Start Time: %time%
echo ====================================================

:: Initialize failure counter
:: (Requires enabledelayedexpansion to update dynamically inside the loop)
set FAILED=0


:: -----------------------------------------------------
:: 3. Execution Loop
:: -----------------------------------------------------
for /L %%i in (1,1,%RUNS%) do (

    echo.
    echo ===== Run %%i of %RUNS% =====
    echo Started: !time!

    REM Execute the Python orchestrator.
    REM %* forwards any arguments passed to this batch script directly to Python.
    REM Output is NOT redirected to a file here so the terminal UI remains visible.
    REM (Python handles its own file logging internally).
    python -m run_benchmarks %*

    REM Check the exit code of the Python process
    if errorlevel 1 (
        echo [WARNING] Run %%i FAILED
        REM Increment the failure counter using delayed expansion
        set /a FAILED+=1
    ) else (
        echo Run %%i completed successfully
    )

    echo.
    echo [SYSTEM] Flushing VRAM and cooling down Ollama...
    REM Enforce a 15-second blocking delay.
    REM This is critical to allow local LLMs to fully unload from GPU memory
    REM before the next iteration attempts to allocate space.
    timeout /t 15 /nobreak >nul
)


:: -----------------------------------------------------
:: 4. Teardown & Reporting
:: -----------------------------------------------------
echo.
echo ====================================================
echo Finished all %RUNS% runs.
echo Failed runs: !FAILED! of %RUNS%
echo End Time: !time!
echo ====================================================

:: Trigger a Windows system beep to alert the user that the batch has finished
rundll32 user32.dll,MessageBeep

:: Keep the terminal open so the user can review the final summary
pause

:: Safely terminate local variable scope
endlocal