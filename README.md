# 株式ポートフォリオ管理Webアプリ

## 概要
PythonとStreamlitを使用した株式ポートフォリオ管理Webアプリケーションです。
CSVファイルからポートフォリオデータを読み込み、リアルタイムの株価データを取得して、
損益計算とリスク分析を行います。

## 機能
- CSVファイルからのポートフォリオデータインポート
- リアルタイム株価取得（Yahoo Finance）
- 多通貨対応（すべて日本円ベースで評価）
- 損益計算と可視化
- リスク指標計算（VaR、CVaR、ボラティリティ等）
- インタラクティブなダッシュボード

## インストール

### 前提条件
- Python 3.8以上
- Git

### セットアップ
```bash
# リポジトリのクローン
git clone https://github.com/yourusername/portfolio-management-app.git
cd portfolio-management-app

# 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Linux/macOS
# または
venv\Scripts\activate  # Windows

# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
```

## 使用方法
```bash
# アプリケーションの起動
streamlit run app.py
```

ブラウザで http://localhost:8501 にアクセスしてください。

## CSVファイル形式
```csv
Ticker,Shares,AvgCostJPY
AAPL,100,15000
MSFT,50,25000
7203.T,1000,800
```

## ライセンス
MIT License