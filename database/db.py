import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "database"
DB_PATH = DB_DIR / "company.db"


def get_connection():
    """Veritabanı bağlantısı oluştur ve yapılandır."""
    DB_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    conn.execute("PRAGMA foreign_keys = ON")

    conn.row_factory = sqlite3.Row

    return conn


def init_db():
    """Veritabanını başlat ve tabloları oluştur."""
    conn = get_connection()
    cursor = conn.cursor()

    # ÇALIŞANLAR TABLOSU

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (

        employee_id INTEGER PRIMARY KEY AUTOINCREMENT,

        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,

        email TEXT UNIQUE NOT NULL,

        department TEXT,
        position TEXT,

        hourly_rate REAL NOT NULL,

        active INTEGER NOT NULL DEFAULT 1,

        is_admin INTEGER NOT NULL DEFAULT 0,

        password_hash TEXT NOT NULL
    )
    """)

    # YOKLAMA TABLOSU

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (

        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,

        employee_id INTEGER NOT NULL,

        work_date TEXT NOT NULL,

        status TEXT NOT NULL
        CHECK(status IN ('present', 'absent', 'leave')),

        work_hours REAL NOT NULL DEFAULT 0,

        overtime_hours REAL NOT NULL DEFAULT 0,

        UNIQUE(employee_id, work_date),

        FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
    )
    """)

    conn.commit()
    conn.close()