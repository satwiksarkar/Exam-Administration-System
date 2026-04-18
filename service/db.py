import os

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