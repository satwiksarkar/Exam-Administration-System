import os
import pymysql
import logging
import sys

logger = logging.getLogger(__name__)

from service.db_config import DB_CONFIG

# Ensure the DB logic creates database on first import
def get_db_connection():
    try:
        # Connect without DB first to create it if missing
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            port=DB_CONFIG['port']
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        conn.close()

        # Return actual connection
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port'],
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        logger.error(f"MySQL Connection Error: {e}")
        return None

def setup_database():
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    version_name VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS assignments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    schedule_id INT NOT NULL,
                    exam_date VARCHAR(50) NOT NULL,
                    shift_name VARCHAR(50) NOT NULL,
                    room_name VARCHAR(50) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    person_name VARCHAR(255) NOT NULL,
                    FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE
                )
                """)
            conn.commit()
        except Exception as e:
            logger.error(f"Error setting up tables: {e}")
        finally:
            conn.close()

# Initialize tables
setup_database()


# Database file paths
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
# SCHEDULE DB OPERATIONS
# ==========================================

def save_schedule_to_db(version_name, schedule_results):
    """Saves the flat dicts from solve_with_ortools into MySQL"""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        with conn.cursor() as cursor:
            # Create schedule version
            cursor.execute("INSERT INTO schedules (version_name) VALUES (%s)", (version_name,))
            schedule_id = conn.insert_id()
            
            for row in schedule_results:
                exam_date = row.get("Date")
                shift_name = row.get("Shift")
                room_name = row.get("Room")
                
                # Support both new arrays (faculties/staffs) and legacy scalar keys
                faculties = row.get("faculties", [])
                staffs = row.get("staffs", [])
                
                # Legacy fallback
                if not faculties:
                    f1 = row.get("Faculty1", row.get("Faculty_1", ""))
                    f2 = row.get("Faculty2", row.get("Faculty_2", ""))
                    if f1 and f1 != "---": faculties.append(f1)
                    if f2 and f2 != "---": faculties.append(f2)
                if not staffs:
                    s1 = row.get("Staff", row.get("Staff1", ""))
                    if s1 and s1 != "---": staffs.append(s1)
                
                for i, name in enumerate(faculties):
                    if name and name not in ("---", "N/A", ""):
                        cursor.execute(
                            "INSERT INTO assignments (schedule_id, exam_date, shift_name, room_name, role, person_name) VALUES (%s, %s, %s, %s, %s, %s)",
                            (schedule_id, exam_date, shift_name, room_name, f'Faculty_{i+1}', name)
                        )
                for i, name in enumerate(staffs):
                    if name and name not in ("---", "N/A", ""):
                        cursor.execute(
                            "INSERT INTO assignments (schedule_id, exam_date, shift_name, room_name, role, person_name) VALUES (%s, %s, %s, %s, %s, %s)",
                            (schedule_id, exam_date, shift_name, room_name, f'Staff_{i+1}', name)
                        )
        conn.commit()
        return schedule_id
    except Exception as e:
        logger.error(f"Error saving schedule: {e}")
        return False
    finally:
        conn.close()

def get_latest_schedule_assignments():
    """Gets the assignments of the most recent schedule ID."""
    conn = get_db_connection()
    if not conn:
        return []
    
    out = []
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM schedules ORDER BY id DESC LIMIT 1")
            latest_sched = cursor.fetchone()
            if not latest_sched:
                return []
            
            schedule_id = latest_sched['id']
            cursor.execute("SELECT * FROM assignments WHERE schedule_id = %s", (schedule_id,))
            out = cursor.fetchall()
            
    except Exception as e:
        logger.error(f"Error loading schedule assignments: {e}")
    finally:
        conn.close()
    return out

def get_all_schedules():
    """Gets all schedules from the database."""
    conn = get_db_connection()
    if not conn:
        return []
    
    out = []
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, version_name, created_at FROM schedules ORDER BY created_at DESC")
            out = cursor.fetchall()
    except Exception as e:
        logger.error(f"Error loading schedules: {e}")
    finally:
        conn.close()
    return out

def get_schedule_assignments(schedule_id):
    """Gets the assignments of a specific schedule ID."""
    conn = get_db_connection()
    if not conn:
        return []
    
    out = []
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM assignments WHERE schedule_id = %s", (schedule_id,))
            out = cursor.fetchall()
    except Exception as e:
        logger.error(f"Error loading schedule assignments for ID {schedule_id}: {e}")
    finally:
        conn.close()
    return out

def delete_schedule(schedule_id):
    """Deletes a schedule and its assignments (cascaded)."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM schedules WHERE id = %s", (schedule_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error deleting schedule {schedule_id}: {e}")
        return False
    finally:
        conn.close()

def rename_schedule(schedule_id, new_name):
    """Renames a saved schedule."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE schedules SET version_name = %s WHERE id = %s", (new_name, schedule_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error renaming schedule {schedule_id}: {e}")
        return False
    finally:
        conn.close()
 