import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from dotenv import load_dotenv

load_dotenv()

def send_reminder_email(title, start_time, location):
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    try:
        smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    except:
        smtp_port = 465
        
    sender_email = os.environ.get("SMTP_EMAIL")
    sender_password = os.environ.get("SMTP_PASSWORD")
    receiver_email = os.environ.get("RECEIVER_EMAIL", "moray.huang@gmail.com")
    
    if not sender_email or not sender_password:
        print("Error: SMTP_EMAIL or SMTP_PASSWORD is not set in environment variables.")
        return False

    # 郵件內容
    subject = f"【AI管家行程提醒】「{title}」即將在兩小時後開始"
    body = f"""主人，您好：

提醒您，您有一個登記的行程即將在兩小時後開始！

📌 行程名稱：{title}
📍 行程地點：{location}
⏰ 開始時間：{start_time}

請您提前做好相關準備。

祝您順心，
您的 AI 行程管家 🎩
"""

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = sender_email
    msg["To"] = receiver_email

    try:
        if smtp_port == 465:
            # 使用 SSL
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            # 使用 STARTTLS (通常是 Port 587)
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, [receiver_email], msg.as_string())
        server.quit()
        print(f"Email sent successfully to {receiver_email} for task: '{title}' at '{location}'")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

if __name__ == "__main__":
    # 本地測試發信
    print("正在測試發信功能...")
    test_title = "測試行程 (開會)"
    test_time = "2026-05-27 16:00:00"
    test_loc = "海洋大學資工系館"
    success = send_reminder_email(test_title, test_time, test_loc)
    if success:
        print("測試信發送成功！")
    else:
        print("測試信發送失敗，請檢查 .env 檔案設定。")
