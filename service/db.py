import os
import logging
import sys
import time
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

from service.db_config import DB_CONFIG, DATABASE_URL

# ==========================================
# DATABASE BACKEND DETECTION
# PostgreSQL is used on Render (when DATABASE_URL is set or PG is reachable).
# SQLite is used as a local fallback when PostgreSQL is not available.
# ==========================================

_use_sqlite = False
_sqlite_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'local_schedules.db')
_last_db_error = None

def _try_postgres():
    """Attempt to connect to PostgreSQL. Returns conn or None."""
    global _last_db_error
    try:
        import psycopg2
        import psycopg2.extras
        if DATABASE_URL:
            conn = psycopg2.connect(
                DATABASE_URL,
                cursor_factory=psycopg2.extras.DictCursor,
                connect_timeout=2
            )
        else:
            conn = psycopg2.connect(
                host=DB_CONFIG['host'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                dbname=DB_CONFIG['database'],
                port=DB_CONFIG['port'],
                cursor_factory=psycopg2.extras.DictCursor,
                connect_timeout=2
            )
        _last_db_error = None
        return conn
    except Exception as e:
        _last_db_error = str(e)
        logger.warning(f"PostgreSQL unavailable: {e}")
        return None

def get_last_db_error():
    return _last_db_error

def get_db_connection():
    """Returns a PostgreSQL connection, or None if unavailable."""
    return _try_postgres()

# ==========================================
# SQLITE FALLBACK HELPERS
# ==========================================

def _get_sqlite_conn():
    """Returns a SQLite connection with row_factory for dict-like access."""
    os.makedirs(os.path.dirname(_sqlite_path), exist_ok=True)
    conn = sqlite3.connect(_sqlite_path)
    conn.row_factory = sqlite3.Row
    return conn

def _setup_sqlite():
    conn = _get_sqlite_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_name TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER NOT NULL,
            exam_date TEXT NOT NULL,
            shift_name TEXT NOT NULL,
            room_name TEXT NOT NULL,
            role TEXT NOT NULL,
            person_name TEXT NOT NULL,
            FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE
        )""")
        conn.commit()
        logger.info("✓ SQLite fallback tables created/verified")
    finally:
        conn.close()

# ==========================================
# TABLE SETUP
# ==========================================

def setup_database():
    """Create PostgreSQL tables if using PostgreSQL."""
    import psycopg2
    conn = get_db_connection()
    if not conn:
        raise ConnectionError(f"Cannot connect to PostgreSQL: {get_last_db_error()}")
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id SERIAL PRIMARY KEY,
                version_name VARCHAR(100) NOT NULL,
                created_at VARCHAR(50)
            )""")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id SERIAL PRIMARY KEY,
                schedule_id INT NOT NULL,
                exam_date VARCHAR(50) NOT NULL,
                shift_name VARCHAR(50) NOT NULL,
                room_name VARCHAR(50) NOT NULL,
                role VARCHAR(50) NOT NULL,
                person_name VARCHAR(255) NOT NULL,
                FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE
            )""")
        conn.commit()
        logger.info("✓ PostgreSQL tables created/verified")
    except Exception as e:
        logger.error(f"Error setting up PostgreSQL tables: {e}")
        raise
    finally:
        conn.close()


def _init_db_with_retry():
    """Try PostgreSQL first. Fall back to SQLite if unavailable.
    On Render (DATABASE_URL set): retry 5 times with delay to handle cold starts.
    Locally (no DATABASE_URL): try once only, then immediately fall back to SQLite."""
    global _use_sqlite
    from service.db_config import DATABASE_URL as _db_url
    max_retries = 5 if _db_url else 1
    delay = 2 if _db_url else 0

    for attempt in range(1, max_retries + 1):
        try:
            setup_database()
            _use_sqlite = False
            logger.info("✓ Using PostgreSQL for schedule storage")
            return
        except Exception as e:
            logger.warning(f"PG init attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time.sleep(delay)

    # PostgreSQL not available — use SQLite locally
    logger.warning("⚠️  PostgreSQL not available. Falling back to SQLite for local development.")
    _setup_sqlite()
    _use_sqlite = True

_init_db_with_retry()


# ==========================================
# DATABASE FILE PATHS (teachers/staff/rooms in flat files)
# ==========================================

DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database')
TEACHERS_FILE = os.path.join(DATABASE_DIR, 'teachers.txt')
STAFF_FILE = os.path.join(DATABASE_DIR, 'staffs.txt')
ROOMS_FILE = os.path.join(DATABASE_DIR, 'rooms.txt')

def ensure_database_dir():
    """Ensure the database directory exists"""
    if not os.path.exists(DATABASE_DIR):
        os.makedirs(DATABASE_DIR)

def read_teachers():
    """Read all teachers from the database"""
    ensure_database_dir()
    if not os.path.exists(TEACHERS_FILE):
        return []
    with open(TEACHERS_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def read_staff():
    """Read all staff from the database"""
    ensure_database_dir()
    if not os.path.exists(STAFF_FILE):
        return []
    with open(STAFF_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def read_rooms():
    """Read all rooms from the database"""
    ensure_database_dir()
    if not os.path.exists(ROOMS_FILE):
        return []
    with open(ROOMS_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def add_teacher(name):
    """Add a teacher to the database"""
    ensure_database_dir()
    teachers = read_teachers()
    if name not in teachers:
        teachers.append(name)
        with open(TEACHERS_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(teachers) + '\n')
        return True
    return False

def add_staff(name):
    """Add a staff member to the database"""
    ensure_database_dir()
    staff = read_staff()
    if name not in staff:
        staff.append(name)
        with open(STAFF_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(staff) + '\n')
        return True
    return False

def add_room(name):
    """Add a room to the database"""
    ensure_database_dir()
    rooms = read_rooms()
    if name not in rooms:
        rooms.append(name)
        with open(ROOMS_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(rooms) + '\n')
        return True
    return False

def delete_teacher(name):
    """Delete a teacher from the database"""
    ensure_database_dir()
    teachers = read_teachers()
    if name in teachers:
        teachers.remove(name)
        with open(TEACHERS_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(teachers) + '\n')
        return True
    return False

def delete_staff(name):
    """Delete a staff member from the database"""
    ensure_database_dir()
    staff = read_staff()
    if name in staff:
        staff.remove(name)
        with open(STAFF_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(staff) + '\n')
        return True
    return False

def delete_room(name):
    """Delete a room from the database"""
    ensure_database_dir()
    rooms = read_rooms()
    if name in rooms:
        rooms.remove(name)
        with open(ROOMS_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(rooms) + '\n')
        return True
    return False

def get_all_data():
    """Get all data from database"""
    return {
        'teachers': read_teachers(),
        'staff': read_staff(),
        'rooms': read_rooms()
    }

def delete_all_teachers():
    """Delete all teachers from the database"""
    ensure_database_dir()
    if os.path.exists(TEACHERS_FILE):
        with open(TEACHERS_FILE, 'w', encoding='utf-8') as f:
            f.write('')
        return True
    return False

def delete_all_staff():
    """Delete all staff from the database"""
    ensure_database_dir()
    if os.path.exists(STAFF_FILE):
        with open(STAFF_FILE, 'w', encoding='utf-8') as f:
            f.write('')
        return True
    return False

# ==========================================
# SCHEDULE DB OPERATIONS (PostgreSQL or SQLite)
# ==========================================

def _insert_assignments(cursor, schedule_id, schedule_results, placeholder='%s'):
    """Shared logic to insert assignment rows."""
    for row in schedule_results:
        exam_date = row.get("Date")
        shift_name = row.get("Shift")
        room_name = row.get("Room")

        faculties = list(row.get("faculties", []))
        staffs = list(row.get("staffs", []))

        # Legacy fallback
        if not faculties:
            f1 = row.get("Faculty1", row.get("Faculty_1", ""))
            f2 = row.get("Faculty2", row.get("Faculty_2", ""))
            if f1 and f1 != "---": faculties.append(f1)
            if f2 and f2 != "---": faculties.append(f2)
        if not staffs:
            s1 = row.get("Staff", row.get("Staff1", ""))
            if s1 and s1 != "---": staffs.append(s1)

        sql = (f"INSERT INTO assignments (schedule_id, exam_date, shift_name, room_name, role, person_name) "
               f"VALUES ({placeholder},{placeholder},{placeholder},{placeholder},{placeholder},{placeholder})")

        for i, name in enumerate(faculties):
            if name and name not in ("---", "N/A", ""):
                cursor.execute(sql, (schedule_id, exam_date, shift_name, room_name, f'Faculty_{i+1}', name))
        for i, name in enumerate(staffs):
            if name and name not in ("---", "N/A", ""):
                cursor.execute(sql, (schedule_id, exam_date, shift_name, room_name, f'Staff_{i+1}', name))


def save_schedule_to_db(version_name, schedule_results):
    """Saves the schedule into PostgreSQL (production) or SQLite (local dev)."""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            from datetime import timedelta
            # Increment time by 5.5 hours to match IST
            ist_now = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
            cur.execute("INSERT INTO schedules (version_name, created_at) VALUES (?, ?)", (version_name, ist_now))
            schedule_id = cur.lastrowid
            _insert_assignments(cur, schedule_id, schedule_results, placeholder='?')
            conn.commit()
            logger.info(f"✓ [SQLite] Schedule saved with id={schedule_id}")
            return schedule_id
        except Exception as e:
            logger.error(f"Error saving schedule (SQLite): {e}")
            raise
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn:
            err = get_last_db_error() or 'Unknown database connection error'
            raise ConnectionError(f"Database unavailable: {err}")
        try:
            with conn.cursor() as cursor:
                from datetime import timedelta
                # Increment time by 5.5 hours to match IST
                ist_now = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("INSERT INTO schedules (version_name, created_at) VALUES (%s, %s) RETURNING id", (version_name, ist_now))
                result = cursor.fetchone()
                if not result:
                    raise Exception("Failed to insert schedule and retrieve ID")
                schedule_id = result['id']
                _insert_assignments(cursor, schedule_id, schedule_results, placeholder='%s')
            conn.commit()
            logger.info(f"✓ [PostgreSQL] Schedule saved with id={schedule_id}")
            return schedule_id
        except Exception as e:
            logger.error(f"Error saving schedule (PostgreSQL): {e}")
            raise
        finally:
            conn.close()


def _rows_to_dicts(rows):
    """Convert sqlite3.Row or psycopg2 DictRow objects to plain dicts."""
    return [dict(row) for row in rows]


def get_latest_schedule_assignments():
    """Gets the assignments of the most recent schedule ID."""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM schedules ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if not row:
                return []
            cur.execute("SELECT * FROM assignments WHERE schedule_id = ?", (row['id'],))
            return _rows_to_dicts(cur.fetchall())
        except Exception as e:
            logger.error(f"Error loading latest assignments (SQLite): {e}")
            return []
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn:
            return []
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM schedules ORDER BY id DESC LIMIT 1")
                latest = cursor.fetchone()
                if not latest:
                    return []
                cursor.execute("SELECT * FROM assignments WHERE schedule_id = %s", (latest['id'],))
                return _rows_to_dicts(cursor.fetchall())
        except Exception as e:
            logger.error(f"Error loading latest assignments (PostgreSQL): {e}")
            return []
        finally:
            conn.close()


def get_all_schedules():
    """Gets all schedules from the database."""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, version_name, created_at FROM schedules ORDER BY created_at DESC")
            return _rows_to_dicts(cur.fetchall())
        except Exception as e:
            logger.error(f"Error loading schedules (SQLite): {e}")
            return []
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn:
            return []
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, version_name, created_at FROM schedules ORDER BY created_at DESC")
                return _rows_to_dicts(cursor.fetchall())
        except Exception as e:
            logger.error(f"Error loading schedules (PostgreSQL): {e}")
            return []
        finally:
            conn.close()


def get_schedule_assignments(schedule_id):
    """Gets the assignments of a specific schedule ID."""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM assignments WHERE schedule_id = ?", (schedule_id,))
            return _rows_to_dicts(cur.fetchall())
        except Exception as e:
            logger.error(f"Error loading assignments for id {schedule_id} (SQLite): {e}")
            return []
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn:
            return []
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM assignments WHERE schedule_id = %s", (schedule_id,))
                return _rows_to_dicts(cursor.fetchall())
        except Exception as e:
            logger.error(f"Error loading assignments for id {schedule_id} (PostgreSQL): {e}")
            return []
        finally:
            conn.close()


def delete_schedule(schedule_id):
    """Deletes a schedule and its assignments (cascaded)."""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM assignments WHERE schedule_id = ?", (schedule_id,))
            cur.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting schedule {schedule_id} (SQLite): {e}")
            return False
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn:
            return False
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM schedules WHERE id = %s", (schedule_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting schedule {schedule_id} (PostgreSQL): {e}")
            return False
        finally:
            conn.close()


def rename_schedule(schedule_id, new_name):
    """Renames a saved schedule."""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE schedules SET version_name = ? WHERE id = ?", (new_name, schedule_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error renaming schedule {schedule_id} (SQLite): {e}")
            return False
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn:
            return False
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE schedules SET version_name = %s WHERE id = %s", (new_name, schedule_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error renaming schedule {schedule_id} (PostgreSQL): {e}")
            return False
        finally:
            conn.close()