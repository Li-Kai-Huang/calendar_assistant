import os
from linebot import LineBotApi
from linebot.models import TextSendMessage
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# 測試 LINE
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
user_id = "U74279e1320a83db1fccd1fd25b9ff830" # 從先前 log 中取得的使用者 LINE userId

print("=== 1. 測試 LINE Push Message ===")
if not LINE_CHANNEL_ACCESS_TOKEN:
    print("錯誤: 找不到 LINE_CHANNEL_ACCESS_TOKEN!")
else:
    try:
        line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
        line_bot_api.push_message(user_id, TextSendMessage(text="🎩 主人，這是來自 AI 管家的連線測試訊息！若您收到此訊息，代表 LINE Bot 憑證正常。"))
        print("成功: LINE Push Message 已發送，請檢查手機！")
    except Exception as e:
        print(f"失敗: LINE 發送失敗，錯誤為: {e}")

# 測試 Gemini
print("\n=== 2. 測試 Gemini API ===")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("錯誤: 找不到 GEMINI_API_KEY!")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content("哈囉，請回覆『Gemini 測試成功！』")
        print(f"成功: Gemini API 回覆: {response.text.strip()}")
    except Exception as e:
        print(f"失敗: Gemini API 呼叫失敗，錯誤為: {e}")
