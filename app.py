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
from service.db import read_teachers, read_staff, read_rooms, add_teacher, add_staff, add_room, delete_teacher, delete_staff, delete_room, get_all_data
from service.createTable import create_table_pdf

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
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'}), 400
            
        if role not in ['teacher', 'staff']:
            return jsonify({'success': False, 'error': 'Invalid role specified'}), 400

        if file and file.filename.lower().endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
                
            lines = text.split('\n')
            added_count = 0
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # Clean up leading numbers like "1. ", "2) ", "10."
                cleaned_name = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
                
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
        
        if preferences:
            logger.info(f'✓ Applied {len(preferences)} preference rules')
        if two_shift_preferences:
            logger.info(f'✓ Applied {len(two_shift_preferences)} two-shift preferences')
        
        # Call the scheduling function with the new API and preferences
        results, status = formal_scheduler_api(teachers, staff, rooms, exam_dates, preferences, two_shift_preferences)
        
        # Convert results to more readable format with actual names
        formatted_results = []
        for result in results:
            date_idx = result.get('date', 0)
            shift_idx = result.get('shift', 0)
            room_idx = result.get('room', 0)
            
            formatted_results.append({
                'date': exam_dates[date_idx] if date_idx < len(exam_dates) else f'Date {date_idx + 1}',
                'shift': shifts[shift_idx] if shift_idx < len(shifts) else f'Shift {shift_idx + 1}',
                'room': rooms[room_idx] if room_idx < len(rooms) else f'Room {room_idx + 1}',
                'faculty1': teachers[result.get('faculty1', 0)] if result.get('faculty1', 0) < len(teachers) else 'N/A',
                'faculty2': teachers[result.get('faculty2', 0)] if result.get('faculty2', 0) < len(teachers) else 'N/A',
                'staff': staff[result.get('staff', 0)] if result.get('staff', 0) < len(staff) else 'N/A'
            })
        
        logger.info(f'✓ Schedule generated successfully with {len(formatted_results)} assignments')
        logger.info(f'📂 Status: {status["message"]}')
        
        # Generate CSV and display schedule with comprehensive logs
        from service.schedule import display_schedule
        try:
            csv_path = display_schedule(results, teachers, staff, rooms, exam_dates)
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

@app.route('/api/download-csv', methods=['POST'])
def download_csv():
    """Generate and download grouped CSV files (main, teachers, staffs, rooms) with constant filenames"""
    try:
        data = request.json
        results = data['results']
        csv_type = data.get('type', 'main')  # 'main', 'teacher', 'staff', or 'room'
        
        logger.info(f'📊 CSV generation started with {len(results)} schedule entries - Type: {csv_type}')
        
        # Create main DataFrame
        df = pd.DataFrame(results)
        
        # Determine which file to download
        if csv_type == 'teacher':
            logger.info('📋 Generating teacher-grouped schedule')
            # Group by faculty (faculty1 or faculty2)
            teacher_records = []
            for _, row in df.iterrows():
                if row['faculty1'] != 'N/A':
                    teacher_records.append({
                        'Teacher': row['faculty1'],
                        'Date': row['date'],
                        'Shift': row['shift'],
                        'Room': row['room'],
                        'Role': 'Faculty 1'
                    })
                if row['faculty2'] != 'N/A':
                    teacher_records.append({
                        'Teacher': row['faculty2'],
                        'Date': row['date'],
                        'Shift': row['shift'],
                        'Room': row['room'],
                        'Role': 'Faculty 2'
                    })
            teacher_df = pd.DataFrame(teacher_records)
            teacher_df = teacher_df.sort_values(['Teacher', 'Date', 'Shift']).reset_index(drop=True)
            output_df = teacher_df
            filename = TEACHER_SCHEDULE_CSV
            
        elif csv_type == 'staff':
            logger.info('📋 Generating staff-grouped schedule')
            # Group by staff
            staff_records = []
            for _, row in df.iterrows():
                if row['staff'] != 'N/A':
                    staff_records.append({
                        'Staff': row['staff'],
                        'Date': row['date'],
                        'Shift': row['shift'],
                        'Room': row['room'],
                        'Faculty1': row['faculty1'],
                        'Faculty2': row['faculty2']
                    })
            staff_df = pd.DataFrame(staff_records)
            staff_df = staff_df.sort_values(['Staff', 'Date', 'Shift']).reset_index(drop=True)
            output_df = staff_df
            filename = STAFF_SCHEDULE_CSV
            
        elif csv_type == 'room':
            logger.info('📋 Generating room-grouped schedule')
            # Group by room
            room_df = df.sort_values(['room', 'date', 'shift']).reset_index(drop=True)
            output_df = room_df
            filename = ROOM_SCHEDULE_CSV
            
        else:  # main
            logger.info('📋 Generating main schedule')
            output_df = df
            filename = MAIN_SCHEDULE_CSV
        
        # Generate CSV string
        csv_string = output_df.to_csv(index=False)
        
        # Save to permanent storage with constant filename (will overwrite)
        filepath = os.path.join(SCHEDULE_STORAGE_DIR, filename)
        output_df.to_csv(filepath, index=False)
        logger.info(f'✓ CSV file saved to permanent storage: {filepath}')
        logger.info(f'📂 CSV contains {len(output_df)} rows with columns: {list(output_df.columns)}')
        
        # Create CSV file in memory for download
        output = BytesIO()
        output.write(csv_string.encode('utf-8'))
        output.seek(0)
        
        print(f'\n✓ CSV FILE GENERATED OK - {filename}\n')
        logger.info(f'✓ CSV file generated and ready for download: {filename}')
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        logger.error(f'❌ CSV generation failed: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/download-all-csv', methods=['POST'])
def download_all_csv():
    """Download all grouped CSVs as a ZIP file"""
    try:
        import zipfile
        
        data = request.json
        results = data['results']
        
        logger.info(f'📦 Creating ZIP with all grouped schedules')
        
        # Create main DataFrame
        df = pd.DataFrame(results)
        
        # Create ZIP in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add main schedule
            csv_string = df.to_csv(index=False)
            zip_file.writestr(MAIN_SCHEDULE_CSV, csv_string)
            logger.info(f'✓ Added {MAIN_SCHEDULE_CSV} to ZIP')
            
            # Add teacher schedule
            teacher_records = []
            for _, row in df.iterrows():
                if row['faculty1'] != 'N/A':
                    teacher_records.append({
                        'Teacher': row['faculty1'],
                        'Date': row['date'],
                        'Shift': row['shift'],
                        'Room': row['room'],
                        'Role': 'Faculty 1'
                    })
                if row['faculty2'] != 'N/A':
                    teacher_records.append({
                        'Teacher': row['faculty2'],
                        'Date': row['date'],
                        'Shift': row['shift'],
                        'Room': row['room'],
                        'Role': 'Faculty 2'
                    })
            teacher_df = pd.DataFrame(teacher_records)
            teacher_df = teacher_df.sort_values(['Teacher', 'Date', 'Shift']).reset_index(drop=True)
            csv_string = teacher_df.to_csv(index=False)
            zip_file.writestr(TEACHER_SCHEDULE_CSV, csv_string)
            logger.info(f'✓ Added {TEACHER_SCHEDULE_CSV} to ZIP')
            
            # Add staff schedule
            staff_records = []
            for _, row in df.iterrows():
                if row['staff'] != 'N/A':
                    staff_records.append({
                        'Staff': row['staff'],
                        'Date': row['date'],
                        'Shift': row['shift'],
                        'Room': row['room'],
                        'Faculty1': row['faculty1'],
                        'Faculty2': row['faculty2']
                    })
            staff_df = pd.DataFrame(staff_records)
            staff_df = staff_df.sort_values(['Staff', 'Date', 'Shift']).reset_index(drop=True)
            csv_string = staff_df.to_csv(index=False)
            zip_file.writestr(STAFF_SCHEDULE_CSV, csv_string)
            logger.info(f'✓ Added {STAFF_SCHEDULE_CSV} to ZIP')
            
            # Add room schedule
            room_df = df.sort_values(['room', 'date', 'shift']).reset_index(drop=True)
            csv_string = room_df.to_csv(index=False)
            zip_file.writestr(ROOM_SCHEDULE_CSV, csv_string)
            logger.info(f'✓ Added {ROOM_SCHEDULE_CSV} to ZIP')
        
        zip_buffer.seek(0)
        
        print(f'\n✓ ZIP FILE GENERATED OK - All schedules included\n')
        logger.info(f'✓ ZIP file generated with all schedules')
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name='exam_schedules.zip'
        )
    
    except Exception as e:
        logger.error(f'❌ ZIP generation failed: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

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
        if pdf_type in ['teacher', 'staff']:
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
