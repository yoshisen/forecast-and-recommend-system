# クイック起動スクリプト（事前に backend ディレクトリへ移動し、仮想環境を有効化してください）
# Windows PowerShell

Write-Host "🚀 LUMI 小売分析プラットフォームのバックエンドを起動します..." -ForegroundColor Cyan
Write-Host ""

# backend ディレクトリ上で実行されているか確認
if (!(Test-Path "app")) {
    Write-Host "❌ エラー: このスクリプトは backend ディレクトリで実行してください" -ForegroundColor Red
    Write-Host "実行例: cd backend" -ForegroundColor Yellow
    exit 1
}

# 仮想環境を確認
if (!(Test-Path "dataanalysisproject")) {
    Write-Host "⚠️  仮想環境が見つからないため作成します..." -ForegroundColor Yellow
    python -m venv dataanalysisproject
    Write-Host "✅ 仮想環境の作成が完了しました" -ForegroundColor Green
}

# 仮想環境を有効化
Write-Host "🔧 仮想環境を有効化します..." -ForegroundColor Yellow
.\dataanalysisproject\Scripts\Activate.ps1

# 依存関係を確認
Write-Host "📦 依存パッケージを確認します..." -ForegroundColor Yellow
pip list | Select-String "fastapi" > $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  依存パッケージが未インストールのため、インストールします..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

# サーバーを起動
Write-Host ""
Write-Host "🚀 FastAPI サーバーを起動します..." -ForegroundColor Green
Write-Host "📍 API ドキュメント: http://localhost:8000/api/docs" -ForegroundColor Cyan
Write-Host "📍 ヘルスチェック: http://localhost:8000/api/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "Ctrl+C でサーバーを停止できます" -ForegroundColor Yellow
Write-Host ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
