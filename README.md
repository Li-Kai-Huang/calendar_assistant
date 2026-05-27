# AI 行程管家 LINE Bot (Calendar Assistant)

本專案是一個基於 Python Flask 框架與 LINE Messaging API 的「AI 行程管家」。它結合了 **Google Gemini API** 的自然語言處理能力，能直接讀懂主人的指令（例如「明天下午兩點去開會」），自動將模糊時間轉換為精確的格式、偵測行程時間衝突，並在行程**開始前兩小時**自動計算並設定提醒時間，最後安全儲存於本地的 **SQLite** 資料庫中。

---

## 📂 專案結構說明

* 📄 `app.py`: Flask 主伺服器，處理 LINE Webhook 請求、控制 Gemini AI 意圖解析與排程衝突邏輯。
* 📄 `database.py`: 本地 SQLite 資料庫封裝模組，負責初始化 `tasks` 資料表及所有資料庫 CRUD 操作。
* 📄 `requirements.txt`: 專案所需的 Python 依賴套件。
* 📄 `.gitignore`: Git 排除清單，防止本地資料庫檔案 `calendar_data.db`、金鑰設定 `.env` 與虛擬環境被上傳至 GitHub。
* 📄 `.env` 與 `.env.example`: 本地執行設定檔（存放金鑰憑證）。

---

## 🛠️ 開發環境準備

### 1. 建立並啟用 Python 虛擬環境 (`venv`)
請在專案根目錄下執行以下指令：
```bash
# 建立虛擬環境
python -m venv venv

# 啟用虛擬環境 (Windows PowerShell)
.\venv\Scripts\Activate.ps1
```

### 2. 安裝相依套件
在啟用的虛擬環境中執行以下指令進行安裝：
```bash
pip install -r requirements.txt
```

---

## 🔑 金鑰設定說明 (`.env`)

請複製 `.env.example` 並重新命名為 `.env`，接著填入以下資訊：

```ini
# LINE Bot 憑證 (請在 LINE Developers 取得)
LINE_CHANNEL_SECRET=您的_LINE_Channel_Secret
LINE_CHANNEL_ACCESS_TOKEN=您的_LINE_Channel_Access_Token

# Gemini API 金鑰 (用於智慧解析行程)
GEMINI_API_KEY=您的_Gemini_API_Key

# Email SMTP 設定 (預設以 Gmail 為例)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
SMTP_EMAIL=您的發信Gmail信箱 (例如: test@gmail.com)
SMTP_PASSWORD=您的發信Gmail「應用程式密碼」(16位英文字母)

# 接收提醒通知的信箱
RECEIVER_EMAIL=您的收信信箱 (例如: moray.huang@gmail.com)
```

> 💡 **如何取得 Gemini API Key？**
> 1. 前往 [Google AI Studio](https://aistudio.google.com/)。
> 2. 登入您的 Google 帳號。
> 3. 點擊 **Get API key**，並建立一個新的 API Key。它具備免費額度，足以應付開發與測試需求！

> 📧 **如何取得 Gmail 的「應用程式密碼」？**
> 由於 Google 已經停用「低安全性應用程式存取權」，直接填寫 Gmail 登入密碼是行不通的。請按照以下步驟申請專門的 16 位密碼：
> 1. 開啟您的 [Google 帳戶安全設定](https://myaccount.google.com/security)。
> 2. 確保您的帳戶已經啟用 **「兩步驟驗證」**。
> 3. 在兩步驟驗證設定頁面的最下方，找到 **「應用程式密碼 (App Passwords)」**。
> 4. 在「選取應用程式」中選擇 `郵件`，「選取裝置」選擇 `其他 (自訂名稱)` 並輸入例如 `LINE Bot Calendar`。
> 5. 點擊 **「產生」**，畫面會出現一組 **16 位英文字母** 的黃色方格密碼。
> 6. 複製該組 16 位密碼（不含空格），並填入 `.env` 的 `SMTP_PASSWORD` 中。

---

## 🚀 專案啟動與串接

### Step 1. 啟動 Flask 伺服器
在啟用虛擬環境的狀態下，於專案根目錄執行：
```bash
python app.py
```
伺服器將在本地 `http://127.0.0.1:5000` 啟動，並自動在目錄下初始化 `calendar_data.db`。

### Step 2. 使用 Ngrok 建立公開通道
開啟另一個命令提示字元視窗，執行以下指令將本地 5000 Port 對外開放：
```bash
ngrok http 5000
```
複製產生的 HTTPS 網址（例如 `https://xxxx-xxx-xxx.ngrok-free.app`）。

### Step 3. 設定 LINE Webhook
1. 登入 [LINE Developers Console](https://developers.line.biz/)。
2. 選擇您的 Channel，切換至 **Messaging API** 頁籤。
3. 在 **Webhook URL** 欄位貼上剛才複製的 HTTPS 網址，並在尾端加上 `/callback`（例如：`https://xxxx-xxx-xxx.ngrok-free.app/callback`）。
4. 點選 **Update**，並點擊 **Verify**，若顯示 **Success** 即表示連線成功！
5. **重要**：請將頁面底下的 **Use webhook** 功能開啟。
6. **建議**：請在同一頁面下方的「LINE Official Account features」中，將 **Auto-reply messages** (自動回覆訊息) 設定為 **Disabled** (停用)，否則 LINE 官方會搶先發送罐頭回覆。

---

## 🤖 互動指令與管家語氣示範

### 1. 新增行程 (模糊時間自動轉換)
您可以用最自然的說法向管家提出要求，系統會自動在**行程開始前兩小時**設定提醒：
* **使用者**：「幫我記下明天下午三點去開會」
* **AI 管家**：「📋 已新增行程：去開會  
⏰ 時間：2026-05-28 15:00:00  
🔔 提醒設定為：2026-05-28 13:00:00 (行程前兩小時)  
  
主人，我已確認該行程與提醒成功寫入資料庫，已為您安排妥當。」

### 2. 資訊遺漏提示
若輸入的指令不完整（例如沒有提到日期或時間）：
* **使用者**：「我要去看牙醫」
* **AI 管家**：「主人，您想新增行程，但似乎缺少日期與時間。可以請您提供完整的行程名稱、日期與時間嗎？」

### 3. 時間衝突警告
若您預約的時段與現有行程（**前後 1 小時內**）重疊：
* **使用者**：「明天下午三點半要去運動」
* **AI 管家**：「⚠️ 主人，偵測到行程時間衝突！  
在該時段附近已有以下行程：  
• 去開會 (2026-05-28 15:00:00)  
  
請確認是否需要調整新行程的安排？」

### 4. 查詢行程
* **使用者**：「我有哪些行程？」
* **AI 管家**：「📋 主人，您目前已登記的行程清單如下：  
  
📌 去開會  
   時間: 2026-05-28 15:00:00  
   提醒: 2026-05-28 13:00:00」

### 5. 閒聊與說明
若說了其他無關行程的話：
* **使用者**：「哈囉！」
* **AI 管家**：「您好，我是您的 AI 行程管家。🎩  
  
您可以對我說：  
✍️ 「幫我記下明天下午三點去開會」來新增行程。  
📅 「我這週有什麼行程嗎？」來查詢您的行程表。  
  
我會自動為您在行程開始前兩小時設定提醒，並為您把關時間衝突。請問有什麼我可以為您效勞的嗎？」

---

## ☁️ 雲端部署指南 (永久免費方案)

如果您希望本專案能夠 24 小時永久運行，且不會因為關閉本機電腦而中斷服務，您可以將其部署至 **Render**，並使用 **Supabase** 作為免費的資料庫儲存。

### Step 1. 建立免費 Supabase PostgreSQL 資料庫
由於 Render 的免費磁碟是臨時的（伺服器重啟或休眠喚醒後 SQLite 會被還原），我們需要一個免費的線上資料庫：
1. 註冊並登入 [Supabase](https://supabase.com/)。
2. 建立一個新專案 (Project)，設定資料庫密碼。
3. 建立完成後，在左側選單進入 **Project Settings** -> **Database**。
4. 找到 **Connection string**，選擇 **URI** 格式。
5. 複製這串以 `postgres://...` 開頭的連線網址（記住將其中的 `[YOUR-PASSWORD]` 替換為您當初設定的密碼），這就是您的 `DATABASE_URL`。

### Step 2. 將專案推送到 GitHub
1. 在 GitHub 上建立一個新的儲存庫。
2. 開啟您的 GitHub Desktop，將 `calendar_assistant` 資料夾導入 (Add local repository) 並發布 (Publish) 到您的 GitHub 帳號。

### Step 4. 在 Render 上建立 Web Service
1. 註冊並登入 [Render](https://render.com/)。
2. 點擊 **New +** -> **Web Service**，選擇您剛才上傳的 `calendar_assistant` 儲存庫。
3. 進行以下設定：
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: 選擇 `Free`

---

### Step 5. 設定 Render 環境變數 (Environment Variables)
在 Render Web Service 的設定頁面中，切換到 **Environment** 標籤，點擊 **Add Environment Variable**，並新增以下變數：
- `TZ`: `Asia/Taipei` *(確保排程器與 Gemini 均使用台北時間)*
- `DATABASE_URL`: 您在 Step 1 取得的 Supabase PostgreSQL 連線網址
- `LINE_CHANNEL_SECRET`: 您的 LINE Secret
- `LINE_CHANNEL_ACCESS_TOKEN`: 您的 LINE Access Token
- `GEMINI_API_KEY`: 您的 Gemini API Key
- `GOOGLE_CLIENT_ID`: 您在 Step 2 取得的 Google Client ID
- `GOOGLE_CLIENT_SECRET`: 您在 Step 2 取得的 Google Client Secret
- `OAUTH_REDIRECT_BASE`: 您的 Render 網址 (如 `https://calendar-assistant-xxxx.onrender.com`，最後面不要帶斜線)
- `SMTP_SERVER`: `smtp.gmail.com`
- `SMTP_PORT`: `465`
- `SMTP_EMAIL`: 您的發信 Gmail (`0126c024@email.ntou.edu.tw`)
- `SMTP_PASSWORD`: 您的 Gmail 應用程式密碼
- `RECEIVER_EMAIL`: 您的收信信箱

設定完成後，Render 會自動啟動部署。部署成功後，您會在 Render Console 左上方取得您的 HTTPS 網址。

### Step 6. 更新 LINE Webhook URL
將您的 Render HTTPS 網址加上 `/callback`（例如：`https://calendar-assistant-xxxx.onrender.com/callback`），填入 LINE Developers 後台的 **Webhook URL** 並儲存啟用。點選 **Verify** 測試，成功後開啟 **Use webhook** 功能。

---

### Step 7. (重要) 使用 UptimeRobot 維持服務活躍，防止排程失效
由於 Render 的 Free 方案在 15 分鐘無流量時會自動進入休眠 (Spin Down)，休眠期間背景發信排程器會停止運作。若要維持 24 小時準時的 Email 提醒：
1. 註冊並登入免費的 [UptimeRobot](https://uptimerobot.com/)。
2. 點擊 **Add New Monitor**。
3. **Monitor Type** 選擇 `HTTP(s)`。
4. **Friendly Name** 可以填入 `Calendar Assistant`。
5. **URL (or IP)** 填入您的 Render 網址 (例如：`https://calendar-assistant-xxxx.onrender.com/`)。
6. **Monitoring Interval** 設定為每 `5 minutes` (5 分鐘) 一次。
7. 點擊 **Create Monitor**。這會讓 UptimeRobot 每 5 分鐘請求一次網頁，使 Render 服務保持喚醒狀態，發信提醒功能即可 24 小時正常運作！

