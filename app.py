from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
from io import BytesIO
import math
import networkx as nx
from datetime import datetime
import os
import logging
import sys
import re
import PyPDF2
import fitz  # PyMuPDF
import pytesseract
from PIL import Image

# Explicitly set Tesseract path for Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# Setup logging with both file and console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create schedule storage folder
SCHEDULE_STORAGE_DIR = os.path.join(os.path.dirname(__file__), 'schedule_storage')
if not os.path.exists(SCHEDULE_STORAGE_DIR):
    os.makedirs(SCHEDULE_STORAGE_DIR)
    logger.info(f'✓ Created schedule storage directory: {SCHEDULE_STORAGE_DIR}')

logger.info('🚀 Starting Exam Scheduling System')
logger.info(f'📁 Schedule storage directory: {SCHEDULE_STORAGE_DIR}')

# Create Flask app with correct paths
app = Flask(__name__, template_folder='templates', static_folder='static')

# Import the scheduling logic and constants
from service.schedule import formal_scheduler_api, MAIN_SCHEDULE_CSV, TEACHER_SCHEDULE_CSV, STAFF_SCHEDULE_CSV, ROOM_SCHEDULE_CSV
from service.db import read_teachers, read_staff, read_rooms, add_teacher, add_staff, add_room, delete_teacher, delete_staff, delete_room, get_all_data, delete_all_teachers, delete_all_staff
from service.createTable import create_table_pdf, create_room_tables_pdf

@app.route('/')
def index():
    logger.info('📄 Loading main scheduling interface')
    return render_template('index.html')

@app.route("/register")
def register():
    """Registration page for teachers, staff, and rooms"""
    data = get_all_data()
    return render_template('register.html', **data)

@app.route('/api/data', methods=['GET'])
def api_data():
    """Return teachers, staff, and rooms for client-side preference setup"""
    data = get_all_data()
    return jsonify({'success': True, 'data': data})

@app.route("/api/register-teacher", methods=['POST'])
def register_teacher():
    """API to register a teacher"""
    try:
        data = request.json
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        if add_teacher(name):
            return jsonify({'success': True, 'message': f'Teacher {name} added successfully'})
        else:
            return jsonify({'success': False, 'error': 'Teacher already exists'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/api/register-staff", methods=['POST'])
def register_staff():
    """API to register a staff member"""
    try:
        data = request.json
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        if add_staff(name):
            return jsonify({'success': True, 'message': f'Staff {name} added successfully'})
        else:
            return jsonify({'success': False, 'error': 'Staff already exists'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/api/delete-teacher", methods=['POST'])
def api_delete_teacher():
    """API to delete a teacher"""
    try:
        data = request.json
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        if delete_teacher(name):
            return jsonify({'success': True, 'message': f'Teacher {name} deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Teacher not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/api/delete-staff", methods=['POST'])
def api_delete_staff():
    """API to delete a staff member"""
    try:
        data = request.json
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        if delete_staff(name):
            return jsonify({'success': True, 'message': f'Staff {name} deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Staff not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/api/delete-all-teachers", methods=['POST'])
def api_delete_all_teachers():
    """API to delete all teachers"""
    try:
        if delete_all_teachers():
            logger.info('🗑️ All teachers deleted')
            return jsonify({'success': True, 'message': 'All teachers deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete teachers'}), 400
    except Exception as e:
        logger.error(f'❌ Error deleting all teachers: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/api/delete-all-staff", methods=['POST'])
def api_delete_all_staff():
    """API to delete all staff"""
    try:
        if delete_all_staff():
            logger.info('🗑️ All staff deleted')
            return jsonify({'success': True, 'message': 'All staff deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete staff'}), 400
    except Exception as e:
        logger.error(f'❌ Error deleting all staff: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/api/register-room", methods=['POST'])
def register_room():
    """API to register a room"""
    try:
        data = request.json
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        if add_room(name):
            return jsonify({'success': True, 'message': f'Room {name} added successfully'})
        else:
            return jsonify({'success': False, 'error': 'Room already exists'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/api/delete-room", methods=['POST'])
def api_delete_room():
    """API to delete a room"""
    try:
        data = request.json
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        if delete_room(name):
            return jsonify({'success': True, 'message': f'Room {name} deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Room not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/api/upload-pdf-list", methods=['POST'])
def upload_pdf_list():
    """API to parse a PDF and bulk add teachers or staff"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        role = request.form.get('role', '').strip()  # 'teacher' or 'staff'
        use_ocr = request.form.get('use_ocr', 'false').lower() == 'true'
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'}), 400
            
        if role not in ['teacher', 'staff']:
            return jsonify({'success': False, 'error': 'Invalid role specified'}), 400

        if file and file.filename.lower().endswith('.pdf'):
            text = ""
            
            # Read file bytes to process
            file_bytes = file.read()
            
            if use_ocr:
                try:
                    logger.info("Using OCR for PDF parsing...")
                    pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
                    for page_num in range(pdf_document.page_count):
                        page = pdf_document.load_page(page_num)
                        # Render page to an image (higher resolution for better OCR)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        
                        # Use tesseract to extract text from image
                        extracted = pytesseract.image_to_string(img)
                        if extracted:
                            text += extracted + "\n"
                    logger.info(f"OCR Extracted {len(text)} characters.")
                except pytesseract.TesseractNotFoundError:
                    return jsonify({
                        'success': False, 
                        'error': 'Tesseract OCR is not installed or not found in PATH on this server. Please install Tesseract-OCR and try again.'
                    }), 500
                except Exception as eval_e:
                    logger.error(f'OCR Failed: {str(eval_e)}')
                    return jsonify({'success': False, 'error': f'OCR Processing failed: {str(eval_e)}'}), 500
            else:
                # Normal text-based PDF parsing
                reader = PyPDF2.PdfReader(BytesIO(file_bytes))
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
                
                # Check if it was empty, suggesting user should use OCR
                if len(text.strip()) < 5:
                    return jsonify({
                        'success': False, 
                        'error': 'No text could be extracted. The PDF might be a scanned image or handwritten. Please check "Enable OCR" and try again.'
                    }), 400
                
            lines = text.split('\n')
            added_count = 0
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # Clean up leading numbers like "1. ", "2) ", "10."
                cleaned_name = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
                
                # Further cleanup for OCR typical artifacts: Remove extra weird characters
                cleaned_name = re.sub(r'[^\w\s\.-]', '', cleaned_name).strip()
                
                # Minimum length to be considered a name
                if len(cleaned_name) > 2:
                    if role == 'teacher':
                        if add_teacher(cleaned_name):
                            added_count += 1
                    elif role == 'staff':
                        if add_staff(cleaned_name):
                            added_count += 1
                            
            return jsonify({
                'success': True, 
                'message': f'Successfully parsed PDF and added {added_count} new {role}(s)!'
            })
        else:
            return jsonify({'success': False, 'error': 'Selected file is not a PDF'}), 400
            
    except Exception as e:
        logger.error(f'❌ PDF Upload failed: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/schedule', methods=['POST'])
def generate_schedule():
    """Generate the invigilation schedule based on selected exam dates"""
    try:
        # Get exam dates from JSON data
        data = request.json
        exam_dates = data.get('exam_dates', [])
        
        if not exam_dates or not isinstance(exam_dates, list):
            logger.warning('⚠️ No exam dates provided')
            return jsonify({'success': False, 'error': 'No valid exam dates provided'}), 400
        
        # Filter out empty strings
        exam_dates = [date.strip() for date in exam_dates if date.strip()]
        
        if not exam_dates:
            logger.warning('⚠️ No valid exam dates after filtering')
            return jsonify({'success': False, 'error': 'No valid exam dates found'}), 400
        
        logger.info(f'📋 Schedule generation started with {len(exam_dates)} dates: {exam_dates}')
        
        # Define shifts
        shifts = ["Morning", "Afternoon"]
        
        # Read data from database
        teachers = read_teachers()
        staff = read_staff()
        rooms = read_rooms()
        
        logger.info(f'✓ Loaded {len(teachers)} teachers, {len(staff)} staff, {len(rooms)} rooms')
        
        if not teachers:
            logger.error('❌ No teachers registered')
            return jsonify({'success': False, 'error': 'No teachers registered'}), 400
        if not staff:
            logger.error('❌ No staff registered')
            return jsonify({'success': False, 'error': 'No staff registered'}), 400
        if not rooms:
            logger.error('❌ No rooms registered')
            return jsonify({'success': False, 'error': 'No rooms registered'}), 400
        
        preferences = data.get('preferences', [])
        if not isinstance(preferences, list):
            preferences = []
        
        # NEW: Extract two-shift preferences
        two_shift_preferences = data.get('two_shift_preferences', [])
        if not isinstance(two_shift_preferences, list):
            two_shift_preferences = []
        
        # Extract per-room requirements
        req_fac = int(data.get('req_fac', 2))
        req_stf = int(data.get('req_stf', 1))
        
        if preferences:
            logger.info(f'✓ Applied {len(preferences)} preference rules')
        if two_shift_preferences:
            logger.info(f'✓ Applied {len(two_shift_preferences)} two-shift preferences')
        logger.info(f'✓ Room config: {req_fac} faculty, {req_stf} staff per room')
        
        # Call the scheduling function with the new API and preferences
        results, status = formal_scheduler_api(teachers, staff, rooms, exam_dates, preferences, two_shift_preferences, req_fac=req_fac, req_stf=req_stf)
        
        # Convert results to more readable format with actual names
        formatted_results = []
        for result in results:
            date_idx = result.get('date', 0)
            shift_idx = result.get('shift', 0)
            room_idx = result.get('room', 0)
            
            fac_names = [teachers[i] if 0 <= i < len(teachers) else 'N/A' for i in result.get('faculties', [])]
            stf_names = [staff[i] if 0 <= i < len(staff) else 'N/A' for i in result.get('staffs', [])]
            
            formatted_results.append({
                'date': exam_dates[date_idx] if date_idx < len(exam_dates) else f'Date {date_idx + 1}',
                'shift': shifts[shift_idx] if shift_idx < len(shifts) else f'Shift {shift_idx + 1}',
                'room': rooms[room_idx] if room_idx < len(rooms) else f'Room {room_idx + 1}',
                'faculties': fac_names,
                'staffs': stf_names
            })
        
        logger.info(f'✓ Schedule generated successfully with {len(formatted_results)} assignments')
        logger.info(f'📂 Status: {status["message"]}')
        
        version_name = data.get('version_name')
        
        # Generate CSV and display schedule with comprehensive logs
        from service.schedule import display_schedule
        try:
            csv_path = display_schedule(results, teachers, staff, rooms, exam_dates, version_name=version_name)
            logger.info(f'✅ CSV successfully saved to: {csv_path}')
        except Exception as e:
            logger.error(f'❌ Error generating CSV: {str(e)}')
        
        return jsonify({
            'success': True,
            'results': formatted_results,
            'status': status
        })
    
    except Exception as e:
        logger.error(f'❌ Schedule generation failed: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/emergency_reschedule', methods=['POST'])
def emergency_reschedule():
    """Takes an absentee and date, loads DB, and regenerates balanced schedule."""
    try:
        from service.db import get_schedule_assignments, read_teachers, read_staff, read_rooms
        data = request.json
        person = data.get('person')
        em_date = data.get('emergency_date')
        schedule_id = data.get('schedule_id')
        
        if not person or not em_date or not schedule_id:
            return jsonify({'success': False, 'error': 'Person, emergency date, and schedule ID required.'}), 400
            
        locked_assignments = get_schedule_assignments(schedule_id)
        if not locked_assignments:
            return jsonify({'success': False, 'error': 'No prior schedule found in database for that ID.'}), 400
            
        # Normalise exam_date: MySQL returns datetime.date objects; convert to plain "YYYY-MM-DD" strings
        for row in locked_assignments:
            if hasattr(row['exam_date'], 'strftime'):
                row['exam_date'] = row['exam_date'].strftime('%Y-%m-%d')

        # Determine the exam dates from the prior assignments
        dates_ordered = []
        for row in locked_assignments:
            if row['exam_date'] not in dates_ordered:
                dates_ordered.append(row['exam_date'])
        
        teachers = read_teachers()
        staff = read_staff()
        rooms = read_rooms()
        shifts = ["Morning", "Afternoon"]

        
        results, status = formal_scheduler_api(
            teachers, staff, rooms, dates_ordered, 
            preferences=None, two_shift_preferences=None,
            locked_assignments=locked_assignments,
            emergency_absence=person,
            emergency_date=em_date
        )
        
        formatted_results = []
        for result in results:
            date_idx = result.get('date', 0)
            shift_idx = result.get('shift', 0)
            room_idx = result.get('room', 0)
            
            fac_names = [teachers[i] if 0 <= i < len(teachers) else 'N/A' for i in result.get('faculties', [])]
            stf_names = [staff[i] if 0 <= i < len(staff) else 'N/A' for i in result.get('staffs', [])]
            
            formatted_results.append({
                'date': dates_ordered[date_idx],
                'shift': shifts[shift_idx],
                'room': rooms[room_idx],
                'faculties': fac_names,
                'staffs': stf_names
            })
            
        from service.schedule import display_schedule
        display_schedule(results, teachers, staff, rooms, dates_ordered, version_name=f"EmResched_{person}")
        
        return jsonify({'success': True, 'results': formatted_results, 'status': status})
    except Exception as e:
        logger.error(f'❌ Emergency reschedule failed: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/routines', methods=['GET'])
def get_routines():
    try:
        from service.db import get_all_schedules
        routines = get_all_schedules()
        for r in routines:
            if 'created_at' in r and r['created_at']:
                r['created_at'] = r['created_at'].strftime('%Y-%m-%dT%H:%M:%S')
        return jsonify({'success': True, 'routines': routines})
    except Exception as e:
        logger.error(f'❌ Failed to get routines: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/routine/<int:schedule_id>', methods=['GET'])
def get_routine(schedule_id):
    try:
        from service.db import get_schedule_assignments, read_teachers, read_staff, read_rooms
        assignments = get_schedule_assignments(schedule_id)
        if not assignments:
            return jsonify({'success': False, 'error': 'Routine not found'}), 404
        
        teachers = read_teachers()
        staff = read_staff()
        rooms = read_rooms()
        
        # Normalise exam_date: MySQL returns datetime.date objects; convert to plain "YYYY-MM-DD" strings
        for a in assignments:
            if hasattr(a['exam_date'], 'strftime'):
                a['exam_date'] = a['exam_date'].strftime('%Y-%m-%d')

        # Determine the unique exam dates and sort them or keep original order.
        unique_dates = sorted(list(set([row['exam_date'] for row in assignments])))
        
        formatted_results = []
        shifts = ["Morning", "Afternoon"]
        
        # Group by date, shift, room — dynamically collect all Faculty_N and Staff_N roles
        grouped = {}
        for a in assignments:
            key = (a['exam_date'], a['shift_name'], a['room_name'])
            if key not in grouped:
                grouped[key] = {'faculties': {}, 'staffs': {}}
            
            role = a['role']
            if role.startswith('Faculty_'):
                try:
                    idx = int(role.split('_')[1]) - 1  # Faculty_1 -> index 0
                    grouped[key]['faculties'][idx] = a['person_name']
                except (ValueError, IndexError):
                    pass
            elif role.startswith('Staff_') or role == 'Staff':
                try:
                    idx = int(role.split('_')[1]) - 1 if '_' in role and role != 'Staff' else 0
                    grouped[key]['staffs'][idx] = a['person_name']
                except (ValueError, IndexError):
                    grouped[key]['staffs'][0] = a['person_name']
                
        for (date_str, shift_name, room_name), roles in grouped.items():
            # Convert dicts to sorted lists
            fac_list = [roles['faculties'].get(i, '---') for i in range(max(roles['faculties'].keys(), default=-1) + 1)]
            stf_list = [roles['staffs'].get(i, '---') for i in range(max(roles['staffs'].keys(), default=-1) + 1)]
            formatted_results.append({
                'date': date_str,
                'shift': shift_name,
                'room': room_name,
                'faculties': fac_list,
                'staffs': stf_list
            })
            
        return jsonify({'success': True, 'results': formatted_results, 'dates': unique_dates})


        
    except Exception as e:
        logger.error(f'❌ Failed to get routine: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/save_routine', methods=['POST'])
def save_routine_api():
    try:
        data = request.json
        results = data.get('results')
        version_name = data.get('version_name')
        
        if not results:
            return jsonify({'success': False, 'error': 'No schedule results to save'}), 400
        if not version_name:
            return jsonify({'success': False, 'error': 'Routine name is required'}), 400
            
        # Re-format results back to what save_schedule_to_db expects (it expects the raw dict)
        # But wait, save_schedule_to_db expects "Faculty1", "Faculty2", "Staff", "Room", "Shift", "Date".
        # The frontend currentScheduleResults already has "date", "shift", "room", "faculty1", "faculty2", "staff".
        # Let's map it:
        db_results = []
        for r in results:
            db_results.append({
                "Date": r.get('date'),
                "Shift": r.get('shift'),
                "Room": r.get('room'),
                "faculties": r.get('faculties', []),
                "staffs": r.get('staffs', [])
            })
            
        from service.db import save_schedule_to_db
        schedule_id = save_schedule_to_db(version_name, db_results)
        if schedule_id:
            return jsonify({'success': True, 'message': 'Routine saved successfully', 'id': schedule_id})
        else:
            return jsonify({'success': False, 'error': 'Failed to save routine'}), 500
            
    except Exception as e:
        logger.error(f'❌ Failed to save routine: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/routine/<int:schedule_id>', methods=['DELETE'])
def delete_routine_api(schedule_id):
    try:
        from service.db import delete_schedule
        if delete_schedule(schedule_id):
            return jsonify({'success': True, 'message': 'Routine deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete routine'}), 400
    except Exception as e:
        logger.error(f'❌ Failed to delete routine: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/routine/<int:schedule_id>', methods=['PUT'])
def rename_routine_api(schedule_id):
    try:
        data = request.json
        new_name = data.get('name')
        if not new_name:
            return jsonify({'success': False, 'error': 'New name is required'}), 400
            
        from service.db import rename_schedule
        if rename_schedule(schedule_id, new_name):
            return jsonify({'success': True, 'message': 'Routine renamed successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to rename routine'}), 400
    except Exception as e:
        logger.error(f'❌ Failed to rename routine: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download-csv', methods=['POST'])
def download_csv():
    """Generate and download grouped CSV files (main, teachers, staffs, rooms) with constant filenames"""
    try:
        data = request.json
        results = data['results']
        csv_type = data.get('type', 'main')  # 'main', 'teacher', 'staff', or 'room'
        
        logger.info(f'📊 CSV generation started with {len(results)} schedule entries - Type: {csv_type}')
        
        # Determine max faculty/staff counts (dynamic)
        max_fac = max((len(r.get('faculties', r.get('faculty1') and [r['faculty1'], r.get('faculty2', '')] or [])) for r in results), default=2)
        max_stf = max((len(r.get('staffs', r.get('staff') and [r['staff']] or [])) for r in results), default=1)
        if max_fac == 0: max_fac = 2
        if max_stf == 0: max_stf = 1

        def get_fac(row, i):
            facs = row.get('faculties')
            if facs is not None: return facs[i] if i < len(facs) else '---'
            if i == 0: return row.get('faculty1', '---')
            if i == 1: return row.get('faculty2', '---')
            return '---'

        def get_stf(row, i):
            stfs = row.get('staffs')
            if stfs is not None: return stfs[i] if i < len(stfs) else '---'
            if i == 0: return row.get('staff', '---')
            return '---'

        fac_col_names = [f'Faculty {i+1}' for i in range(max_fac)]
        stf_col_names = [f'Staff {i+1}' for i in range(max_stf)]

        if csv_type == 'teacher':
            logger.info('📋 Generating teacher-grouped schedule')
            teacher_records = []
            for row in results:
                facs = row.get('faculties') or [row.get('faculty1'), row.get('faculty2')]
                for i, name in enumerate(facs):
                    if name and name not in ('N/A', '---', None, ''):
                        teacher_records.append({
                            'Teacher': name, 'Date': row['date'],
                            'Shift': row['shift'], 'Room': row['room'],
                            'Role': f'Faculty {i+1}'
                        })
            output_df = pd.DataFrame(teacher_records).sort_values(['Teacher', 'Date', 'Shift']).reset_index(drop=True)
            filename = TEACHER_SCHEDULE_CSV

        elif csv_type == 'staff':
            logger.info('📋 Generating staff-grouped schedule')
            staff_records = []
            for row in results:
                stfs = row.get('staffs') or [row.get('staff')]
                for i, name in enumerate(stfs):
                    if name and name not in ('N/A', '---', None, ''):
                        rec = {'Staff': name, 'Date': row['date'], 'Shift': row['shift'], 'Room': row['room']}
                        for fi in range(max_fac):
                            rec[fac_col_names[fi]] = get_fac(row, fi)
                        staff_records.append(rec)
            output_df = pd.DataFrame(staff_records).sort_values(['Staff', 'Date', 'Shift']).reset_index(drop=True)
            filename = STAFF_SCHEDULE_CSV

        elif csv_type == 'room':
            logger.info('📋 Generating room-grouped schedule')
            room_records = []
            for row in results:
                rec = {'Date': row['date'], 'Room': row['room'], 'Shift': row['shift']}
                for i in range(max_fac): rec[fac_col_names[i]] = get_fac(row, i)
                for i in range(max_stf): rec[stf_col_names[i]] = get_stf(row, i)
                room_records.append(rec)
            output_df = pd.DataFrame(room_records).sort_values(['Room', 'Date', 'Shift']).reset_index(drop=True)
            filename = ROOM_SCHEDULE_CSV

        else:  # main
            logger.info('📋 Generating main schedule')
            main_records = []
            for row in results:
                rec = {'Date': row['date'], 'Shift': row['shift'], 'Room': row['room']}
                for i in range(max_fac): rec[fac_col_names[i]] = get_fac(row, i)
                for i in range(max_stf): rec[stf_col_names[i]] = get_stf(row, i)
                main_records.append(rec)
            output_df = pd.DataFrame(main_records)
            filename = MAIN_SCHEDULE_CSV

        csv_string = output_df.to_csv(index=False)
        filepath = os.path.join(SCHEDULE_STORAGE_DIR, filename)
        output_df.to_csv(filepath, index=False)
        logger.info(f'✓ CSV saved: {filepath} ({len(output_df)} rows)')

        output = BytesIO()
        output.write(csv_string.encode('utf-8'))
        output.seek(0)

        return send_file(output, mimetype='text/csv', as_attachment=True, download_name=filename)

    except Exception as e:
        logger.error(f'❌ CSV generation failed: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 400



@app.route('/api/download-all-csv', methods=['POST'])
def download_all_csv():
    """Download all grouped CSVs as a ZIP file"""
    try:
        import zipfile
        
        data = request.json
        results = data['results']
        
        logger.info(f'📦 Creating ZIP with all grouped schedules')
        
        # Determine max faculty/staff counts (dynamic)
        max_fac = max((len(r.get('faculties') or [r.get('faculty1'), r.get('faculty2')] or []) for r in results), default=2)
        max_stf = max((len(r.get('staffs') or [r.get('staff')] or []) for r in results), default=1)
        if max_fac == 0: max_fac = 2
        if max_stf == 0: max_stf = 1

        def get_fac(row, i):
            facs = row.get('faculties')
            if facs is not None: return facs[i] if i < len(facs) else '---'
            if i == 0: return row.get('faculty1', '---')
            if i == 1: return row.get('faculty2', '---')
            return '---'

        def get_stf(row, i):
            stfs = row.get('staffs')
            if stfs is not None: return stfs[i] if i < len(stfs) else '---'
            if i == 0: return row.get('staff', '---')
            return '---'

        fac_col_names = [f'Faculty {i+1}' for i in range(max_fac)]
        stf_col_names = [f'Staff {i+1}' for i in range(max_stf)]

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Main schedule
            main_records = []
            for row in results:
                rec = {'Date': row['date'], 'Shift': row['shift'], 'Room': row['room']}
                for i in range(max_fac): rec[fac_col_names[i]] = get_fac(row, i)
                for i in range(max_stf): rec[stf_col_names[i]] = get_stf(row, i)
                main_records.append(rec)
            zip_file.writestr(MAIN_SCHEDULE_CSV, pd.DataFrame(main_records).to_csv(index=False))
            logger.info(f'✓ Added {MAIN_SCHEDULE_CSV} to ZIP')

            # Teacher schedule
            teacher_records = []
            for row in results:
                facs = row.get('faculties') or [row.get('faculty1'), row.get('faculty2')]
                for i, name in enumerate(facs):
                    if name and name not in ('N/A', '---', None, ''):
                        teacher_records.append({'Teacher': name, 'Date': row['date'], 'Shift': row['shift'], 'Room': row['room'], 'Role': f'Faculty {i+1}'})
            teacher_df = pd.DataFrame(teacher_records).sort_values(['Teacher', 'Date', 'Shift']).reset_index(drop=True) if teacher_records else pd.DataFrame(columns=['Teacher','Date','Shift','Room','Role'])
            zip_file.writestr(TEACHER_SCHEDULE_CSV, teacher_df.to_csv(index=False))
            logger.info(f'✓ Added {TEACHER_SCHEDULE_CSV} to ZIP')

            # Staff schedule
            staff_records = []
            for row in results:
                stfs = row.get('staffs') or [row.get('staff')]
                for i, name in enumerate(stfs):
                    if name and name not in ('N/A', '---', None, ''):
                        rec = {'Staff': name, 'Date': row['date'], 'Shift': row['shift'], 'Room': row['room']}
                        for fi in range(max_fac): rec[fac_col_names[fi]] = get_fac(row, fi)
                        staff_records.append(rec)
            staff_df = pd.DataFrame(staff_records).sort_values(['Staff', 'Date', 'Shift']).reset_index(drop=True) if staff_records else pd.DataFrame()
            zip_file.writestr(STAFF_SCHEDULE_CSV, staff_df.to_csv(index=False))
            logger.info(f'✓ Added {STAFF_SCHEDULE_CSV} to ZIP')

            # Room schedule
            room_records = []
            for row in results:
                rec = {'Date': row['date'], 'Room': row['room'], 'Shift': row['shift']}
                for i in range(max_fac): rec[fac_col_names[i]] = get_fac(row, i)
                for i in range(max_stf): rec[stf_col_names[i]] = get_stf(row, i)
                room_records.append(rec)
            zip_file.writestr(ROOM_SCHEDULE_CSV, pd.DataFrame(room_records).sort_values(['Room', 'Date', 'Shift']).reset_index(drop=True).to_csv(index=False))
            logger.info(f'✓ Added {ROOM_SCHEDULE_CSV} to ZIP')
        
        zip_buffer.seek(0)
        logger.info(f'✓ ZIP file generated with all schedules')
        
        return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='exam_schedules.zip')
    
    except Exception as e:
        logger.error(f'❌ ZIP generation failed: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/download-pdf', methods=['POST'])
def download_pdf():
    """Generate and download PDF from CSV file with optional grouping column"""
    try:
        data = request.json
        pdf_type = data.get('type', 'main')  # 'main', 'teacher', 'staff', or 'room'
        
        # Map type to CSV filename and grouping column
        csv_config_map = {
            'main': {'csv': MAIN_SCHEDULE_CSV, 'grouping': None},
            'teacher': {'csv': TEACHER_SCHEDULE_CSV, 'grouping': 'Teacher'},
            'staff': {'csv': STAFF_SCHEDULE_CSV, 'grouping': 'Staff'},
            'room': {'csv': ROOM_SCHEDULE_CSV, 'grouping': 'Room'}
        }
        
        config = csv_config_map.get(pdf_type, csv_config_map['main'])
        csv_filename = config['csv']
        grouping_column = config['grouping']
        csv_path = os.path.join(SCHEDULE_STORAGE_DIR, csv_filename)
        
        # Check if CSV file exists
        if not os.path.exists(csv_path):
            return jsonify({
                'success': False,
                'error': f'CSV file not found: {csv_filename}'
            }), 404
        
        logger.info(f'📊 Generating PDF from: {csv_filename} (grouping: {grouping_column})')
        
        # Generate PDF in memory
        pdf_filename = csv_filename.replace('.csv', '.pdf')
        pdf_path = os.path.join(SCHEDULE_STORAGE_DIR, pdf_filename)
        
        # Create PDF from CSV
        if pdf_type == 'room':
            # Use special room-per-table PDF generation
            from service.createTable import create_room_tables_pdf
            result = create_room_tables_pdf(csv_path, pdf_path)
        elif pdf_type in ['teacher', 'staff']:
            from service.createTable import create_personnel_report_pdf
            is_staff = (pdf_type == 'staff')
            result = create_personnel_report_pdf(csv_path, pdf_path, is_staff=is_staff)
        else:
            result = create_table_pdf(csv_path, pdf_path, grouping_column_name=grouping_column)
        
        if result and os.path.exists(pdf_path):
            logger.info(f'✓ PDF generated: {pdf_filename}')
            
            # Send file for download
            return send_file(
                pdf_path,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=pdf_filename
            )
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to generate PDF'
            }), 500
    
    except Exception as e:
        logger.error(f'❌ PDF generation failed: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

if __name__ == '__main__':
    logger.info('🚀 Starting Exam Scheduling System')
    logger.info(f'📁 Schedule storage directory: {SCHEDULE_STORAGE_DIR}')
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, port=port, host='0.0.0.0')
