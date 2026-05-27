import sqlite3
import os

DB_NAME = "calendar_data.db"
DATABASE_URL = os.environ.get("DATABASE_URL")
IS_POSTGRES = DATABASE_URL is not None

def get_db_path():
    # 確保 SQLite 資料庫在專案目錄下建立
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, DB_NAME)

def get_connection():
    if IS_POSTGRES:
        import psycopg2
        db_url = DATABASE_URL
        # Render/Supabase 通常提供 postgres:// 形式網址，psycopg2 需要相容
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(db_url)
    else:
        db_path = get_db_path()
        return sqlite3.connect(db_path)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        # PostgreSQL 資料表建立語法
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                start_time TIMESTAMP NOT NULL,
                reminder_time TIMESTAMP NOT NULL,
                status VARCHAR(50) DEFAULT 'pending'
            )
        """)
    else:
        # SQLite 資料表建立語法
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
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO tasks (title, start_time, reminder_time, status)
                VALUES (%s, %s, %s, 'pending')
                RETURNING id, title, start_time, reminder_time
            """, (title, start_time, reminder_time))
            record = cursor.fetchone()
            conn.commit()
            if record:
                # 轉成字串以保持與原本代碼相容
                record = (
                    record[0],
                    record[1],
                    record[2].strftime("%Y-%m-%d %H:%M:%S"),
                    record[3].strftime("%Y-%m-%d %H:%M:%S")
                )
        else:
            cursor.execute("""
                INSERT INTO tasks (title, start_time, reminder_time, status)
                VALUES (?, ?, ?, 'pending')
            """, (title, start_time, reminder_time))
            conn.commit()
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
    conn = get_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        # PostgreSQL 時間差計算
        cursor.execute("""
            SELECT title, start_time FROM tasks
            WHERE abs(extract(epoch from start_time) - extract(epoch from %s::timestamp)) < 3600
        """, (start_time_str,))
        rows = cursor.fetchall()
        conflicts = [(r[0], r[1].strftime("%Y-%m-%d %H:%M:%S")) for r in rows]
    else:
        # SQLite 時間差計算
        cursor.execute("""
            SELECT title, start_time FROM tasks
            WHERE abs(strftime('%s', start_time) - strftime('%s', ?)) < 3600
        """, (start_time_str,))
        conflicts = cursor.fetchall()
        
    conn.close()
    return conflicts

def get_all_tasks():
    conn = get_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("SELECT id, title, start_time, reminder_time, status FROM tasks ORDER BY start_time ASC")
        rows = cursor.fetchall()
        tasks = []
        for r in rows:
            tasks.append((
                r[0],
                r[1],
                r[2].strftime("%Y-%m-%d %H:%M:%S"),
                r[3].strftime("%Y-%m-%d %H:%M:%S"),
                r[4]
            ))
    else:
        cursor.execute("SELECT id, title, start_time, reminder_time, status FROM tasks ORDER BY start_time ASC")
        tasks = cursor.fetchall()
    conn.close()
    return tasks

def get_pending_reminders(current_time_str):
    conn = get_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("""
            SELECT id, title, start_time, reminder_time, status FROM tasks 
            WHERE reminder_time <= %s::timestamp AND status = 'pending'
        """, (current_time_str,))
        rows = cursor.fetchall()
        tasks = []
        for r in rows:
            tasks.append((
                r[0],
                r[1],
                r[2].strftime("%Y-%m-%d %H:%M:%S"),
                r[3].strftime("%Y-%m-%d %H:%M:%S"),
                r[4]
            ))
    else:
        cursor.execute("""
            SELECT id, title, start_time, reminder_time, status FROM tasks 
            WHERE reminder_time <= ? AND status = 'pending'
        """, (current_time_str,))
        tasks = cursor.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id, status):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("UPDATE tasks SET status = %s WHERE id = %s", (status, task_id))
        else:
            cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating task status: {e}")
        return False

if __name__ == "__main__":
    init_db()
