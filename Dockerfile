FROM python:3.11-slim

# システムパッケージをインストール
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを設定
WORKDIR /app

# Python依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルをコピー
COPY . .

# アップロード・結果ディレクトリを作成
RUN mkdir -p uploads results temp

# ポートを公開
EXPOSE 5000

# アプリケーションを起動
CMD ["python", "app.py"]
