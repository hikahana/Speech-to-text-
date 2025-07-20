import os
import subprocess
import shutil
from flask import Flask, render_template, request, jsonify, send_file, flash, make_response
from werkzeug.utils import secure_filename
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# 設定
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
TEMP_FOLDER = 'temp'
ALLOWED_EXTENSIONS = {'m4a', 'mp4', 'wav', 'mp3'}
SEGMENT_DURATION = 2100  # 35分 = 2100秒

# ディレクトリが存在しない場合は作成
for folder in [UPLOAD_FOLDER, RESULTS_FOLDER, TEMP_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB制限

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def split_audio(input_file, output_dir):
    """音声ファイルを35分ごとに分割"""
    cmd = [
        'ffmpeg', '-i', input_file,
        '-f', 'segment',
        '-segment_time', str(SEGMENT_DURATION),
        '-c', 'copy',
        os.path.join(output_dir, 'part_%02d.m4a')
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"FFmpeg error: {result.stderr}")

        # 分割されたファイル一覧を取得
        parts = []
        i = 0
        while True:
            part_file = os.path.join(output_dir, f'part_{i:02d}.m4a')
            if os.path.exists(part_file):
                parts.append(part_file)
                i += 1
            else:
                break

        return parts
    except Exception as e:
        raise Exception(f"音声分割エラー: {str(e)}")

def fix_timestamp(input_file, output_file):
    """タイムスタンプを修正"""
    cmd = [
        'ffmpeg', '-i', input_file,
        '-c', 'copy',
        '-avoid_negative_ts', 'make_zero',
        output_file
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"FFmpeg timestamp fix error: {result.stderr}")
        return output_file
    except Exception as e:
        raise Exception(f"タイムスタンプ修正エラー: {str(e)}")

def transcribe_with_whisper(audio_file):
    """Whisper APIで文字起こし"""
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise Exception("OPENAI_API_KEYが設定されていません")

    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    with open(audio_file, 'rb') as f:
        files = {
            'file': f,
        }
        data = {
            'model': 'whisper-1',
            'language': 'ja',
            'response_format': 'text'
        }

        response = requests.post(url, headers=headers, files=files, data=data)

        if response.status_code == 200:
            return response.text
        else:
            raise Exception(f"Whisper API エラー: {response.status_code} - {response.text}")

def improve_japanese_text(text):
    """GPT APIを使用して日本語テキストを改善"""
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise Exception("OPENAI_API_KEYが設定されていません")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
以下の音声文字起こしの結果を自然な日本語に修正してください。
句読点を適切に配置し、敬語を統一し、聞き取れなかった部分を文脈から推測して補完してください。
元の意味を保持しながら、読みやすい文章にしてください。

文字起こし結果:
{text}

修正された日本語:
"""

    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": "あなたは日本語の文章校正の専門家です。音声文字起こしの結果を自然で読みやすい日本語に修正してください。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 2000,
        "temperature": 0.3
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        else:
            raise Exception(f"GPT API エラー: {response.status_code} - {response.text}")
    except Exception as e:
        # GPT APIが失敗した場合は元のテキストを返す
        print(f"日本語改善エラー: {e}")
        return text

def cleanup_uploads():
    """uploadsディレクトリの古いファイルをクリーンアップ"""
    try:
        current_time = time.time()
        for filename in os.listdir(UPLOAD_FOLDER):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            # 1時間以上古いファイルを削除
            if os.path.isfile(filepath) and (current_time - os.path.getmtime(filepath)) > 3600:
                try:
                    os.remove(filepath)
                    print(f"古いファイルを削除: {filename}")
                except Exception as e:
                    print(f"ファイル削除エラー: {e}")
    except Exception as e:
        print(f"クリーンアップエラー: {e}")

@app.route('/')
def index():
    # ページアクセス時にクリーンアップ実行
    cleanup_uploads()
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'ファイルが選択されていません'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'ファイルが選択されていません'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        return jsonify({
            'success': True,
            'filename': filename,
            'message': 'ファイルがアップロードされました'
        })

    return jsonify({'error': '無効なファイル形式です。m4a, mp4, wav, mp3のみ対応しています'}), 400

@app.route('/process', methods=['POST'])
def process_file():
    try:
        data = request.get_json()
        filename = data.get('filename')
        improve_text = data.get('improve_text', True)  # デフォルトで改善を有効

        if not filename:
            return jsonify({'error': 'ファイル名が指定されていません'}), 400

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'ファイルが見つかりません'}), 400

        # 一時ディレクトリを作成
        temp_dir = os.path.join(TEMP_FOLDER, filename.split('.')[0])
        os.makedirs(temp_dir, exist_ok=True)

        # ステップ1: 音声ファイルを分割
        parts = split_audio(filepath, temp_dir)

        # ステップ2: 各パートのタイムスタンプを修正し、文字起こし実行
        transcript_parts = []

        for i, part in enumerate(parts):
            # タイムスタンプ修正
            fixed_part = os.path.join(temp_dir, f'fixed_part_{i:02d}.m4a')
            fix_timestamp(part, fixed_part)

            # Whisper APIで文字起こし
            transcript = transcribe_with_whisper(fixed_part)

            # 日本語改善が有効な場合
            if improve_text:
                try:
                    improved_transcript = improve_japanese_text(transcript.strip())
                    transcript_parts.append({
                        'part': i + 1,
                        'duration_start': i * SEGMENT_DURATION,
                        'original_text': transcript.strip(),
                        'improved_text': improved_transcript
                    })
                except Exception as e:
                    print(f"パート{i+1}の日本語改善エラー: {e}")
                    transcript_parts.append({
                        'part': i + 1,
                        'duration_start': i * SEGMENT_DURATION,
                        'original_text': transcript.strip(),
                        'improved_text': transcript.strip()
                    })
            else:
                transcript_parts.append({
                    'part': i + 1,
                    'duration_start': i * SEGMENT_DURATION,
                    'original_text': transcript.strip(),
                    'improved_text': transcript.strip()
                })

        # 結果テキストを生成（一意性を保つためタイムスタンプを含む）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        original_filename = filename.split('_', 1)[1] if '_' in filename else filename
        result_filename = f"{timestamp}_{original_filename.split('.')[0]}_transcript.txt"

        # 結果テキストを構築
        result_content = f"=== {original_filename} の文字起こし結果 ===\n"
        result_content += f"処理日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        result_content += f"日本語改善: {'有効' if improve_text else '無効'}\n\n"

        for part in transcript_parts:
            start_min = part['duration_start'] // 60
            result_content += f"=== パート{part['part']} ({start_min}分頃から) ===\n"

            if improve_text and part['original_text'] != part['improved_text']:
                result_content += "【改善前】\n"
                result_content += part['original_text']
                result_content += "\n\n【改善後】\n"
                result_content += part['improved_text']
            else:
                result_content += part['improved_text']

            result_content += "\n\n"

        # 一時ファイルを削除
        shutil.rmtree(temp_dir)

        # アップロードされた音楽ファイルを削除
        try:
            os.remove(filepath)
        except Exception as e:
            print(f"アップロードファイル削除エラー: {e}")

        return jsonify({
            'success': True,
            'result_filename': result_filename,
            'result_content': result_content,
            'parts_count': len(transcript_parts),
            'improve_text': improve_text,
            'message': '文字起こしと日本語改善が完了しました' if improve_text else '文字起こしが完了しました'
        })

    except Exception as e:
        # エラーが発生してもアップロードファイルを削除
        try:
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
        except Exception as del_error:
            print(f"エラー時のファイル削除エラー: {del_error}")

        return jsonify({'error': f'処理エラー: {str(e)}'}), 500

@app.route('/download', methods=['POST'])
def download_file():
    try:
        data = request.get_json()
        filename = data.get('filename')
        content = data.get('content')

        if not filename or not content:
            return jsonify({'error': 'ファイル名またはコンテンツが指定されていません'}), 400

        # レスポンスとしてファイルをダウンロード
        response = make_response(content)
        response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response
    except Exception as e:
        return jsonify({'error': f'ダウンロードエラー: {str(e)}'}), 500

@app.route('/results')
def list_results():
    # 結果ファイルは保存しないため、常に空のリストを返す
    return jsonify([])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
