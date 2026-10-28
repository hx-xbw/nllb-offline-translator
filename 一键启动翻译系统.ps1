# 一键修复 + 启动（右键 → 以 PowerShell 运行）
Write-Host "正在清理残留进程..." -ForegroundColor Green
taskkill /F /IM python.exe /T 2>$null ; taskkill /F /IM pythonw.exe /T 2>$null
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { taskkill /F /PID $_.OwningProcess }

Write-Host "正在修复 numpy 冲突..." -ForegroundColor Green
pip install "numpy<2" --force-reinstall -q

Write-Host "正在启动 AI 翻译系统..." -ForegroundColor Yellow
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload