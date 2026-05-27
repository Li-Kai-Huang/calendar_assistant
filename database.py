import sqlite3
import os

DB_NAME = "calendar_data.db"

def get_db_path():
    # 確保資料庫在專案目錄下建立
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, DB_NAME)

def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            start_time TEXT NOT NULL,
            reminder_time TEXT NOT NULL,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def add_task(title, start_time, reminder_time):
    db_path = get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (title, start_time, reminder_time, status)
            VALUES (?, ?, ?, 'pending')
        """, (title, start_time, reminder_time))
        conn.commit()
        
        # 驗證是否寫入成功
        last_id = cursor.lastrowid
        cursor.execute("SELECT id, title, start_time, reminder_time FROM tasks WHERE id = ?", (last_id,))
        record = cursor.fetchone()
        conn.close()
        
        if record:
            return True, record
        return False, None
    except Exception as e:
        print(f"Error adding task: {e}")
        return False, None

def check_conflict(start_time_str):
    """
    檢查指定時間前後 1 小時 (3600 秒) 內是否有其他行程衝突。
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查詢是否有行程在 target time 前後 3600 秒內
    # sqlite3 支援 strftime('%s', start_time) 來取得 timestamp (Unix time)
    cursor.execute("""
        SELECT title, start_time FROM tasks
        WHERE abs(strftime('%s', start_time) - strftime('%s', ?)) < 3600
    """, (start_time_str,))
    
    conflicts = cursor.fetchall()
    conn.close()
    
    # conflicts 是一個 list of tuples: [(title, start_time), ...]
    return conflicts

def get_all_tasks():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, start_time, reminder_time, status FROM tasks ORDER BY start_time ASC")
    tasks = cursor.fetchall()
    conn.close()
    return tasks

if __name__ == "__main__":
    init_db()
