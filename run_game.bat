@echo off
chcp 65001 > nul
title naRou - Masterpiece Edition ^& Multi-World
cd /d "%~dp0"

echo ========================================================
echo   🌌 naRou: Masterpiece Edition ^& A-World (Skill Eater)
echo ========================================================
echo.
echo  [1] ゲーム本体を起動 (Python / main.py)
echo  [2] Aの世界 Webショーケースをブラウザで開く (HTML Showcase)
echo  [3] Aの世界 統合テストを実行 (43 Tests)
echo  [4] 終了
echo.
echo ========================================================
set /p choice="実行する番号を入力してください (1-4) [デフォルト: 1]: "

if "%choice%"=="" set choice=1

if "%choice%"=="1" (
    echo.
    echo ゲームを起動しています...
    python main.py
    if errorlevel 1 (
        echo.
        echo [!] エラーが発生したため game.py で再試行します...
        python game.py
    )
    goto end
)

if "%choice%"=="2" (
    echo.
    echo Webショーケースをブラウザで開いています...
    start "" "demos\demo_skill_eater_showcase.html"
    goto end
)

if "%choice%"=="3" (
    echo.
    echo 統合テストを実行しています...
    python -m unittest tests/test_skill_eater_presentation_integration.py
    goto end
)

if "%choice%"=="4" (
    exit /b 0
)

echo [!] 無効な入力です。
goto end

:end
echo.
echo ========================================================
pause
