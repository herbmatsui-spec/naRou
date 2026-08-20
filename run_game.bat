@echo off
setlocal
cd /d "%~dp0"
title naRou - Masterpiece Edition and Multi-World

echo ========================================================
echo   naRou: Masterpiece Edition and A-World (Skill Eater)
echo ========================================================
echo.
echo  [1] Launch Main Game (python main.py)
echo  [2] Open Web Showcase (HTML Showcase)
echo  [3] Run Integration Tests (43 Tests)
echo  [4] Exit
echo.
echo ========================================================
set choice=1
set /p choice="Select Option (1-4) [Default: 1]: "

if "%choice%"=="1" goto launch_game
if "%choice%"=="2" goto open_web
if "%choice%"=="3" goto run_tests
if "%choice%"=="4" goto exit_app

echo [!] Invalid option.
goto end

:launch_game
echo.
echo Launching game...
python main.py
if %errorlevel% neq 0 (
    echo.
    echo [!] main.py exited with error, falling back to game.py...
    python game.py
)
goto end

:open_web
echo.
echo Opening Web Showcase in browser...
start "" "demos\demo_skill_eater_showcase.html"
goto end

:run_tests
echo.
echo Running integration tests...
python -m unittest tests\test_skill_eater_presentation_integration.py
goto end

:exit_app
exit /b 0

:end
echo.
echo ========================================================
pause
