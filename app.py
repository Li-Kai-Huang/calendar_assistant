import os
import datetime
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv
import google.generativeai as genai

import database

# 讀取環境變數
load_dotenv()

app = Flask(__name__)

# 初始化資料庫
database.init_db()

# LINE Bot 設定
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Gemini API 設定
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("Warning: GEMINI_API_KEY is missing!")

def extract_intent_via_gemini(user_text):
    """
    呼叫 Gemini API 解析用戶意圖與提取行程時間
    """
    if not GEMINI_API_KEY:
        return {
            "intent": "error",
            "error_msg": "您好，我是您的行程管家。目前系統尚未設定 GEMINI_API_KEY，請在 .env 檔案中配置此 Key 以便啟用智慧行程解析功能。"
        }
    
    now = datetime.datetime.now()
    current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    weekday_str = now.strftime("%A")
    
    prompt = f"""
    你是一個專業、貼心且高效的 AI 行程管理管家。請從用戶的輸入中提取行程名稱、日期、時間，並判斷其意圖，最後以 JSON 格式回傳。
    
    當前本機系統時間為: {current_time_str} ({weekday_str})。
    請根據當前系統時間，將用戶提到的任何相對時間（如「明天下午三點」、「下週五早上九點」、「後天早上」）轉換為絕對的 "YYYY-MM-DD HH:MM:SS" 格式。
    
    支援判斷的意圖 (intent)：
    1. "add": 用戶想要新增行程 (例如:「幫我記下明天早上十點開會」、「明天要去看牙醫」)
    2. "query": 用戶想要查詢行程 (例如:「我今天有什麼行程？」、「查一下這週行程」)
    3. "other": 普通的打招呼、閒聊或與行程無關的對話 (例如:「你好」、「謝謝」)
    
    請務必僅回傳一個 JSON 字串，不要使用 Markdown 格式的 ```json 標記包裝，也不要有任何其他文字。
    JSON 格式要求如下：
    {{
      "intent": "add" | "query" | "other",
      "title": "行程名稱 (若意圖為 add 且可提取則填寫，否則為 null)",
      "start_time": "YYYY-MM-DD HH:MM:SS (若意圖為 add 且可提取絕對時間則填寫，否則為 null)",
      "missing_info": "如果意圖為 add 且缺少行程名稱、日期或時間，請具體說明遺漏了什麼，例如『缺少時間』、『缺少日期』，如果不缺少則為 null"
    }}
    
    用戶輸入: "{user_text}"
    """
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # 移除 markdown 包裝 (以防 Gemini 還是加上了)
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        data = json.loads(text)
        return data
    except Exception as e:
        print(f"Gemini API error: {e}")
        return {
            "intent": "error",
            "error_msg": "AI 解析失敗，請提供更清晰的格式（例如：開會 2026-05-28 14:00）或聯絡管理員設定金鑰。"
        }

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    
    # 記錄請求主體以便調試
    app.logger.info("Request body: " + body)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text.strip()
    
    # 呼叫 Gemini AI 進行意圖提取
    result = extract_intent_via_gemini(user_text)
    
    intent = result.get("intent", "other")
    
    if intent == "error":
        # 發生錯誤，回覆錯誤提示
        reply_text = f"主人，系統發生了一點狀況：\n{result.get('error_msg')}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        return
        
    if intent == "add":
        title = result.get("title")
        start_time_str = result.get("start_time")
        missing_info = result.get("missing_info")
        
        if missing_info:
            # 資訊不完整，詢問使用者補充
            reply_text = f"主人，您想新增行程，但似乎{missing_info}。可以請您提供完整的行程名稱、日期與時間嗎？"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
            return
            
        if not title or not start_time_str:
            reply_text = "主人，抱歉，我無法從您的輸入中明確提取行程名稱或時間。請重新輸入，例如：「明天下午三點 去開會」"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
            return
            
        # 1. 檢查衝突 (前後 1 小時)
        conflicts = database.check_conflict(start_time_str)
        if conflicts:
            conflict_details = "\n".join([f"• {c[0]} ({c[1]})" for c in conflicts])
            reply_text = f"⚠️ 主人，偵測到行程時間衝突！\n在該時段附近已有以下行程：\n{conflict_details}\n\n請確認是否需要調整新行程的安排？"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
            return
            
        # 2. 計算提醒時間 (start_time - 2 hours)
        try:
            start_dt = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
            reminder_dt = start_dt - datetime.timedelta(hours=2)
            reminder_time_str = reminder_dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            reply_text = f"主人，時間格式轉換出錯，無法寫入資料庫：{e}"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
            return
            
        # 3. 寫入資料庫並做寫入確認
        success, record = database.add_task(title, start_time_str, reminder_time_str)
        if success:
            # 驗證成功回報
            # record: (id, title, start_time, reminder_time)
            reply_text = f"📋 已新增行程：{record[1]}\n⏰ 時間：{record[2]}\n🔔 提醒設定為：{record[3]} (行程前兩小時)\n\n主人，我已確認該行程與提醒成功寫入資料庫，已為您安排妥當。"
        else:
            reply_text = "主人，非常抱歉，確認寫入資料庫時似乎發生了錯誤，請再試一次。"
            
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        
    elif intent == "query":
        # 查詢所有行程
        tasks = database.get_all_tasks()
        if not tasks:
            reply_text = "主人，您目前沒有任何已排定的行程。"
        else:
            task_list = []
            for t in tasks:
                # t: (id, title, start_time, reminder_time, status)
                task_list.append(f"📌 {t[1]}\n   時間: {t[2]}\n   提醒: {t[3]}")
            reply_text = "📋 主人，您目前已登記的行程清單如下：\n\n" + "\n\n".join(task_list)
            
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        
    else: # intent == "other"
        # 閒聊或普通對話，用管家語氣回應，並提示功能
        reply_text = (
            "您好，我是您的 AI 行程管家。🎩\n\n"
            "您可以對我說：\n"
            "✍️ 「幫我記下明天下午三點去開會」來新增行程。\n"
            "📅 「我這週有什麼行程嗎？」來查詢您的行程表。\n\n"
            "我會自動為您在行程開始前兩小時設定提醒，並為您把關時間衝突。請問有什麼我可以為您效勞的嗎？"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

def start_reminder_scheduler():
    import threading
    import time
    import email_sender

    def job():
        print("背景提醒排程器已啟動...")
        while True:
            try:
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # 查詢符合提醒時間 (reminder_time <= 當前時間) 且 status = 'pending' 的所有任務
                pending_reminders = database.get_pending_reminders(now_str)
                for task in pending_reminders:
                    task_id, title, start_time, reminder_time, _ = task
                    print(f"發現符合提醒時間的行程: '{title}' (開始時間: {start_time})，開始發送 Email...")
                    
                    # 發送 Email
                    success = email_sender.send_reminder_email(title, start_time)
                    if success:
                        # 更新資料庫狀態為 'sent'
                        database.update_task_status(task_id, 'sent')
                        print(f"行程 '{title}' 的 Email 提醒發送成功，已更新資料庫狀態為已發送。")
                    else:
                        print(f"行程 '{title}' 的 Email 提醒發送失敗，將於下個週期重試。")
            except Exception as e:
                print(f"排程器執行出錯: {e}")
            time.sleep(60) # 每分鐘檢查一次

    scheduler_thread = threading.Thread(target=job, daemon=True)
    scheduler_thread.start()

if __name__ == "__main__":
    start_reminder_scheduler()
    app.run(host="0.0.0.0", port=5000)
