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
        # PostgreSQL
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                start_time TIMESTAMP NOT NULL,
                reminder_time TIMESTAMP NOT NULL,
                location VARCHAR(255),
                status VARCHAR(50) DEFAULT 'pending'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_tokens (
                line_user_id VARCHAR(255) PRIMARY KEY,
                google_email VARCHAR(255),
                refresh_token TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 自動遷移升級 (若是從舊版升級)
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN location VARCHAR(255)")
            conn.commit()
            print("Successfully added location column to PostgreSQL.")
        except:
            # 欄位已存在
            pass
    else:
        # SQLite
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_time TEXT NOT NULL,
                reminder_time TEXT NOT NULL,
                location TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_tokens (
                line_user_id TEXT PRIMARY KEY,
                google_email TEXT,
                refresh_token TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 自動遷移升級 (若是從舊版升級)
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN location TEXT")
            conn.commit()
            print("Successfully added location column to SQLite.")
        except:
            # 欄位已存在
            pass
            
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def add_task(title, start_time, reminder_time, location):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO tasks (title, start_time, reminder_time, location, status)
                VALUES (%s, %s, %s, %s, 'pending')
                RETURNING id, title, start_time, reminder_time, location
            """, (title, start_time, reminder_time, location))
            record = cursor.fetchone()
            conn.commit()
            if record:
                record = (
                    record[0],
                    record[1],
                    record[2].strftime("%Y-%m-%d %H:%M:%S"),
                    record[3].strftime("%Y-%m-%d %H:%M:%S"),
                    record[4]
                )
        else:
            cursor.execute("""
                INSERT INTO tasks (title, start_time, reminder_time, location, status)
                VALUES (?, ?, ?, ?, 'pending')
            """, (title, start_time, reminder_time, location))
            conn.commit()
            last_id = cursor.lastrowid
            cursor.execute("SELECT id, title, start_time, reminder_time, location FROM tasks WHERE id = ?", (last_id,))
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
        cursor.execute("""
            SELECT title, start_time FROM tasks
            WHERE abs(extract(epoch from start_time) - extract(epoch from %s::timestamp)) < 3600
        """, (start_time_str,))
        rows = cursor.fetchall()
        conflicts = [(r[0], r[1].strftime("%Y-%m-%d %H:%M:%S")) for r in rows]
    else:
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
        cursor.execute("SELECT id, title, start_time, reminder_time, location, status FROM tasks ORDER BY start_time ASC")
        rows = cursor.fetchall()
        tasks = []
        for r in rows:
            tasks.append((
                r[0],
                r[1],
                r[2].strftime("%Y-%m-%d %H:%M:%S"),
                r[3].strftime("%Y-%m-%d %H:%M:%S"),
                r[4],
                r[5]
            ))
    else:
        cursor.execute("SELECT id, title, start_time, reminder_time, location, status FROM tasks ORDER BY start_time ASC")
        tasks = cursor.fetchall()
    conn.close()
    return tasks

def get_pending_reminders(current_time_str):
    conn = get_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("""
            SELECT id, title, start_time, reminder_time, location, status FROM tasks 
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
                r[4],
                r[5]
            ))
    else:
        cursor.execute("""
            SELECT id, title, start_time, reminder_time, location, status FROM tasks 
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

def save_user_token(line_user_id, google_email, refresh_token):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO user_tokens (line_user_id, google_email, refresh_token)
                VALUES (%s, %s, %s)
                ON CONFLICT (line_user_id) DO UPDATE
                SET google_email = EXCLUDED.google_email,
                    refresh_token = EXCLUDED.refresh_token,
                    created_at = CURRENT_TIMESTAMP
            """, (line_user_id, google_email, refresh_token))
        else:
            cursor.execute("""
                INSERT INTO user_tokens (line_user_id, google_email, refresh_token)
                VALUES (?, ?, ?)
                ON CONFLICT (line_user_id) DO UPDATE SET
                    google_email = excluded.google_email,
                    refresh_token = excluded.refresh_token,
                    created_at = CURRENT_TIMESTAMP
            """, (line_user_id, google_email, refresh_token))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving user token: {e}")
        return False

def get_user_token(line_user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("SELECT google_email, refresh_token FROM user_tokens WHERE line_user_id = %s", (line_user_id,))
        else:
            cursor.execute("SELECT google_email, refresh_token FROM user_tokens WHERE line_user_id = ?", (line_user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"email": row[0], "refresh_token": row[1]}
        return None
    except Exception as e:
        print(f"Error getting user token: {e}")
        return None

def delete_user_token(line_user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("DELETE FROM user_tokens WHERE line_user_id = %s", (line_user_id,))
        else:
            cursor.execute("DELETE FROM user_tokens WHERE line_user_id = ?", (line_user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting user token: {e}")
        return False

if __name__ == "__main__":
    init_db()
