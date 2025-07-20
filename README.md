# 🎤 Whisper API 文字起こし Web サービス

WSL Ubuntu 環境で音声ファイル（.m4a, .mp4, .wav, .mp3）をアップロードして、OpenAI Whisper API を使用した文字起こしを実行できる Web アプリケーションです。

## 📋 機能

- **音声ファイルアップロード**: ドラッグ&ドロップまたはファイル選択
- **自動分割**: 35 分ごとに音声を分割して Whisper API の制限に対応
- **タイムスタンプ修正**: FFmpeg を使用したメタデータの最適化
- **並列処理**: 複数のパートを順次処理
- **結果管理**: 過去の結果ファイルの一覧・ダウンロード
- **レスポンシブ UI**: モダンな Web インターフェース

## 🚀 セットアップ手順

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd speech-to-text
```

### 2. 環境変数の設定

`.env.example`をコピーして`.env`ファイルを作成し、OpenAI API キーを設定してください：

```bash
cp .env.example .env
```

`.env`ファイルを編集：

```env
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
SECRET_KEY=your-random-secret-key-here
```

### 3. Docker 環境での起動

```bash
# Docker Composeでアプリケーションを起動
docker-compose up --build
```

### 4. アプリケーションへのアクセス

ブラウザで `http://localhost:5000` にアクセスしてください。

## 💻 使い方

1. **ファイルアップロード**

   - 対応形式：.m4a, .mp4, .wav, .mp3
   - ドラッグ&ドロップまたは「ファイルを選択」ボタンをクリック

2. **文字起こし実行**

   - 「文字起こしを開始」ボタンをクリック
   - 処理時間は音声の長さによって異なります（35 分あたり約 2-3 分）

3. **結果のダウンロード**
   - 処理完了後、結果を直接ダウンロード
   - ローカルに保存されないため、プライバシー保護

## 🛠 技術仕様

### バックエンド

- **Flask**: Python Web フレームワーク
- **FFmpeg**: 音声分割・タイムスタンプ修正
- **OpenAI Whisper API**: 文字起こしエンジン
- **Docker**: 環境の標準化

### フロントエンド

- **HTML5**: セマンティックマークアップ
- **CSS3**: レスポンシブデザイン・アニメーション
- **JavaScript**: ファイルアップロード・API 通信

### 処理フロー

1. 音声ファイルアップロード（最大 1GB）
2. 35 分（2100 秒）ごとに分割
3. 各パートのタイムスタンプ修正
4. Whisper API で文字起こし実行
5. **結果を直接ダウンロード**（ローカル保存なし）
6. **アップロードファイルを自動削除**（プライバシー保護）

## 📁 ディレクトリ構成

```
speech-to-text/
├── Dockerfile              # Docker設定
├── docker-compose.yml      # Docker Compose設定
├── app.py                  # メインアプリケーション
├── requirements.txt        # Python依存関係
├── .env.example           # 環境変数サンプル
├── .env                   # 実際の環境変数（要作成）
├── templates/
│   └── index.html         # メインページ
├── static/
│   ├── style.css          # スタイルシート
│   └── script.js          # JavaScript
├── uploads/               # アップロードファイル
├── results/               # 結果ファイル
└── temp/                  # 一時ファイル
```

## ⚠️ 注意事項

- OpenAI API キーが必要です
- インターネット接続が必要です
- 大容量ファイルの処理には時間がかかります
- Docker 環境で実行することを推奨します

## 🔧 開発・カスタマイズ

### 分割時間の変更

`app.py`の`SEGMENT_DURATION`を変更してください：

```python
SEGMENT_DURATION = 1800  # 30分に変更
```

### 対応ファイル形式の追加

`ALLOWED_EXTENSIONS`に拡張子を追加：

```python
ALLOWED_EXTENSIONS = {'m4a', 'mp4', 'wav', 'mp3', 'flac', 'ogg'}
```

## 📄 ライセンス

MIT License

## 🤝 貢献

Issue 報告やプルリクエストを歓迎します。
