// DOM要素の取得
const uploadArea = document.getElementById("upload-area");
const fileInput = document.getElementById("file-input");
const selectBtn = document.getElementById("select-btn");
const fileInfo = document.getElementById("file-info");
const processBtn = document.getElementById("process-btn");
const progress = document.getElementById("progress");
const results = document.getElementById("results");
const resultsList = document.getElementById("results-list");
const alert = document.getElementById("alert");

// グローバル変数
let uploadedFileName = null;

// 初期化
document.addEventListener("DOMContentLoaded", function () {
  setupEventListeners();
});

// イベントリスナーの設定
function setupEventListeners() {
  // ファイル選択ボタン
  selectBtn.addEventListener("click", () => fileInput.click());

  // ファイル入力変更
  fileInput.addEventListener("change", handleFileSelect);

  // ドラッグ&ドロップ
  uploadArea.addEventListener("dragover", handleDragOver);
  uploadArea.addEventListener("dragleave", handleDragLeave);
  uploadArea.addEventListener("drop", handleDrop);
  uploadArea.addEventListener("click", () => fileInput.click());

  // 処理ボタン
  processBtn.addEventListener("click", startProcessing);
}

// ファイル選択処理
function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) {
    displayFileInfo(file);
    uploadFile(file);
  }
}

// ドラッグオーバー処理
function handleDragOver(event) {
  event.preventDefault();
  uploadArea.classList.add("dragover");
}

// ドラッグリーブ処理
function handleDragLeave(event) {
  event.preventDefault();
  uploadArea.classList.remove("dragover");
}

// ドロップ処理
function handleDrop(event) {
  event.preventDefault();
  uploadArea.classList.remove("dragover");

  const files = event.dataTransfer.files;
  if (files.length > 0) {
    const file = files[0];
    displayFileInfo(file);
    uploadFile(file);
  }
}

// ファイル情報表示
function displayFileInfo(file) {
  const fileSize = (file.size / (1024 * 1024)).toFixed(2);
  fileInfo.innerHTML = `
        <h4>📄 選択されたファイル</h4>
        <p><strong>ファイル名:</strong> ${file.name}</p>
        <p><strong>サイズ:</strong> ${fileSize} MB</p>
        <p><strong>種類:</strong> ${file.type || "不明"}</p>
    `;
  fileInfo.style.display = "block";
}

// ファイルアップロード
async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  try {
    showAlert("ファイルをアップロード中...", "success");

    const response = await fetch("/upload", {
      method: "POST",
      body: formData,
    });

    const result = await response.json();

    if (result.success) {
      uploadedFileName = result.filename;
      processBtn.disabled = false;
      showAlert(result.message, "success");
    } else {
      showAlert(result.error, "error");
    }
  } catch (error) {
    console.error("Upload error:", error);
    showAlert("アップロードに失敗しました", "error");
  }
}

// 処理開始
async function startProcessing() {
  if (!uploadedFileName) {
    showAlert("ファイルが選択されていません", "error");
    return;
  }

  processBtn.disabled = true;
  progress.style.display = "block";
  results.innerHTML = "";

  // プログレス表示の初期化
  const progressPercentage = progress.querySelector(".progress-percentage");
  const progressText = progress.querySelector(".progress-text");

  // プログレス更新のシミュレーション
  let currentProgress = 0;
  const progressInterval = setInterval(() => {
    currentProgress += Math.random() * 15; // ランダムに進捗
    if (currentProgress > 95) currentProgress = 95; // 95%で止める
    progressPercentage.textContent = Math.floor(currentProgress) + "%";

    // 進捗に応じてメッセージを変更
    if (currentProgress < 30) {
      progressText.textContent = "音声ファイルを分割中...";
    } else if (currentProgress < 60) {
      progressText.textContent = "タイムスタンプを修正中...";
    } else if (currentProgress < 90) {
      progressText.textContent = "Whisper APIで文字起こし中...";
    } else {
      progressText.textContent = "結果を保存中...";
    }
  }, 500);

  try {
    const response = await fetch("/process", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        filename: uploadedFileName,
      }),
    });

    const result = await response.json();

    // 処理完了
    clearInterval(progressInterval);
    progressPercentage.textContent = "100%";
    progressText.textContent = "完了！";

    if (result.success) {
      displayResult(result);
      showAlert(result.message, "success");
    } else {
      displayError(result.error);
      showAlert(result.error, "error");
    }
  } catch (error) {
    console.error("Processing error:", error);
    clearInterval(progressInterval);
    displayError("処理中にエラーが発生しました");
    showAlert("処理中にエラーが発生しました", "error");
  } finally {
    // 少し待ってからプログレスを非表示
    setTimeout(() => {
      progress.style.display = "none";
      processBtn.disabled = false;
    }, 1000);
  }
}

// 結果表示（成功）
function displayResult(result) {
  results.innerHTML = `
        <div class="result-success">
            <h4>✅ 文字起こし完了</h4>
            <p><strong>ファイル:</strong> ${result.result_filename}</p>
            <p><strong>分割数:</strong> ${result.parts_count}パート</p>
            <p><strong>処理時間:</strong> 約${
              result.parts_count * 35
            }分の音声</p>
            <button onclick="downloadResult('${
              result.result_filename
            }', \`${result.result_content.replace(
    /`/g,
    "\\`"
  )}\`)" class="download-btn">📥 結果をダウンロード</button>
        </div>
    `;
}

// エラー表示
function displayError(errorMessage) {
  results.innerHTML = `
        <div class="result-error">
            <h4>❌ エラーが発生しました</h4>
            <p>${errorMessage}</p>
        </div>
    `;
}

// アラート表示
function showAlert(message, type) {
  alert.textContent = message;
  alert.className = `alert ${type}`;
  alert.style.display = "block";

  // 3秒後に非表示
  setTimeout(() => {
    alert.style.display = "none";
  }, 3000);
}

// ダウンロード機能
async function downloadResult(filename, content) {
  try {
    const response = await fetch("/download", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        filename: filename,
        content: content,
      }),
    });

    if (response.ok) {
      // ファイルをダウンロード
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      showAlert("ダウンロードが完了しました", "success");
    } else {
      const error = await response.json();
      showAlert(error.error || "ダウンロードに失敗しました", "error");
    }
  } catch (error) {
    console.error("Download error:", error);
    showAlert("ダウンロードに失敗しました", "error");
  }
}

// ファイルサイズのフォーマット
function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";

  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}
