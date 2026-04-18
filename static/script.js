let currentScheduleResults = [];
let selectedPreferences = [];
let twoShiftPreferences = [];  // NEW: Store 2-shift preferences
let teacherList = [];
let staffList = [];

// Calendar variables
let selectedDates = [];
const today = new Date();
let currentMonth = today.getMonth();
let currentYear = today.getFullYear();
const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// Initialize calendar when page loads
document.addEventListener('DOMContentLoaded', function() {
    renderCalendar();
    populateYearSelect();
});

async function loadTeacherData() {
    if (teacherList.length > 0 && staffList.length > 0) {
        return;
    }

    try {
        const response = await fetch('/api/data');
        const data = await response.json();
        if (data.success) {
            teacherList = data.data.teachers || [];
            staffList = data.data.staff || [];
        }
    } catch (error) {
        console.error('Failed to load teacher data:', error);
    }
}

function updatePreferenceSelects() {
    const teacherSelect = document.getElementById('preferenceTeacherSelect');
    const dateSelect = document.getElementById('preferenceDateSelect');
    const twoShiftsSelect = document.getElementById('twoShiftsTeacherSelect');
    
    const staffSelect = document.getElementById('preferenceStaffSelect');
    const staffDateSelect = document.getElementById('preferenceStaffDateSelect');

    teacherSelect.innerHTML = '<option value="">Select teacher</option>';
    teacherList.forEach(teacher => {
        teacherSelect.innerHTML += `<option value="${teacher}">${teacher}</option>`;
    });

    staffSelect.innerHTML = '<option value="">Select staff</option>';
    staffList.forEach(staff => {
        staffSelect.innerHTML += `<option value="${staff}">${staff}</option>`;
    });
    
    // NEW: Also populate the two-shifts teacher select (Faculty Only)
    twoShiftsSelect.innerHTML = '<option value="">Select faculty member</option>';
    teacherList.forEach(teacher => {
        twoShiftsSelect.innerHTML += `<option value="${teacher}">${teacher}</option>`;
    });

    dateSelect.innerHTML = '<option value="">Select date</option>';
    selectedDates.slice().sort().forEach(date => {
        dateSelect.innerHTML += `<option value="${date}">${date}</option>`;
    });

    staffDateSelect.innerHTML = '<option value="">Select date</option>';
    selectedDates.slice().sort().forEach(date => {
        staffDateSelect.innerHTML += `<option value="${date}">${date}</option>`;
    });
}

function showPreferencePanel() {
    if (selectedDates.length === 0) {
        alert('Select exam dates first before adding preferences.');
        return;
    }
    document.getElementById('uploadSection').style.display = 'none';
    document.getElementById('preferenceSection').style.display = 'block';
    loadTeacherData().then(updatePreferenceSelects);
    updatePreferenceRulesList();
    updateTwoShiftsList();  // NEW: Update the two-shifts list
}

function hidePreferencePanel() {
    document.getElementById('preferenceSection').style.display = 'none';
    document.getElementById('uploadSection').style.display = 'block';
}

function addPreferenceRule(type = 'teacher') {
    let person, date, status, shift;

    if (type === 'teacher') {
        person = document.getElementById('preferenceTeacherSelect').value;
        date = document.getElementById('preferenceDateSelect').value;
        status = document.getElementById('preferenceStatusSelect').value;
        shift = document.getElementById('preferenceShiftSelect').value;
    } else {
        person = document.getElementById('preferenceStaffSelect').value;
        date = document.getElementById('preferenceStaffDateSelect').value;
        status = document.getElementById('preferenceStaffStatusSelect').value;
        shift = document.getElementById('preferenceStaffShiftSelect').value;
    }

    if (!person || !date) {
        alert('Please choose both person and date.');
        return;
    }

    const existingIndex = selectedPreferences.findIndex(rule => (rule.person === person || rule.teacher === person) && rule.date === date && rule.shift === shift);
    if (existingIndex !== -1) {
        selectedPreferences[existingIndex].status = status;
    } else {
        selectedPreferences.push({ person, date, shift, status });
    }

    updatePreferenceRulesList();
}

function updatePreferenceRulesList() {
    const list = document.getElementById('preferenceRulesList');
    if (selectedPreferences.length === 0) {
        list.innerHTML = '<p class="no-dates">No preference rules added yet.</p>';
        return;
    }
    let html = '';
    selectedPreferences.forEach((rule, index) => {
        // Create compact identifier format: person_date_shift
        const dateOnly = rule.date ? rule.date.split('-').slice(2).join('-') : 'unknown'; // Extract day from date
        const shiftLower = (rule.shift || 'morning').toLowerCase();
        const personName = rule.person || rule.teacher || 'unknown';
        const identifier = `${personName}_${dateOnly}_${shiftLower}`;
        
        html += `
            <div class="preference-item">
                <div>
                    <strong>${identifier}</strong> — <span style="color: #666;">${rule.status === 'emergency' ? '🚨 Emergency' : '⭐ Preferred'}</span>
                </div>
                <button onclick="removePreferenceRule(${index})">Remove</button>
            </div>
        `;
    });
    list.innerHTML = html;
}

function removePreferenceRule(index) {
    selectedPreferences.splice(index, 1);
    updatePreferenceRulesList();
}

// NEW: Functions for managing 2-shift preferences
function addTwoShiftPreference() {
    const teacher = document.getElementById('twoShiftsTeacherSelect').value;
    const permission = document.getElementById('twoShiftsPermissionSelect').value;

    if (!teacher) {
        alert('Please select a faculty member.');
        return;
    }

    // Check if preference already exists and update it
    const existingIndex = twoShiftPreferences.findIndex(p => p.person === teacher);
    if (existingIndex !== -1) {
        twoShiftPreferences[existingIndex].allowTwoShifts = (permission === 'yes');
    } else {
        twoShiftPreferences.push({
            person: teacher,
            allowTwoShifts: (permission === 'yes')
        });
    }

    updateTwoShiftsList();
}

function updateTwoShiftsList() {
    const list = document.getElementById('twoShiftsList');
    if (twoShiftPreferences.length === 0) {
        list.innerHTML = '<p class="no-dates">No 2-shift preferences set yet.</p>';
        return;
    }
    let html = '';
    twoShiftPreferences.forEach((pref, index) => {
        const status = pref.allowTwoShifts ? '✅ Allow' : '❌ Restrict';
        const statusColor = pref.allowTwoShifts ? 'green' : 'red';
        
        html += `
            <div class="preference-item">
                <div>
                    <strong>${pref.person}</strong> — <span style="color: ${statusColor};">${status}</span>
                </div>
                <button onclick="removeTwoShiftPreference(${index})">Remove</button>
            </div>
        `;
    });
    list.innerHTML = html;
}

function removeTwoShiftPreference(index) {
    twoShiftPreferences.splice(index, 1);
    updateTwoShiftsList();
}

async function applyPreferences() {
    if (selectedPreferences.length === 0 && twoShiftPreferences.length === 0) {
        alert('No preference rules added yet.');
        return;
    }
    await processSchedule(true);
}


// Calendar functions
function populateYearSelect() {
    const yearSelect = document.getElementById("yearSelect");
    for (let y = 2024; y <= 2030; y++) {
        let option = document.createElement("option");
        option.value = y;
        option.text = y;
        if (y === currentYear) option.selected = true;
        yearSelect.appendChild(option);
    }
}

function renderCalendar() {
    const daysContainer = document.getElementById("days");
    const monthYear = document.getElementById("monthYear");
    
    daysContainer.innerHTML = "";
    monthYear.innerText = `${monthNames[currentMonth]} ${currentYear}`;

    const firstDay = new Date(currentYear, currentMonth, 1).getDay();
    const totalDays = new Date(currentYear, currentMonth + 1, 0).getDate();

    // Empty spaces for days before the first day of the month
    for (let i = 0; i < firstDay; i++) {
        daysContainer.innerHTML += "<div></div>";
    }

    for (let day = 1; day <= totalDays; day++) {
        const paddedDay = String(day).padStart(2, '0');
        const paddedMonth = String(currentMonth + 1).padStart(2, '0');
        const dateStr = `${currentYear}-${paddedMonth}-${paddedDay}`;

        const div = document.createElement("div");
        div.classList.add("day");
        div.innerText = day;

        // Highlight today
        if (
            day === today.getDate() &&
            currentMonth === today.getMonth() &&
            currentYear === today.getFullYear()
        ) {
            div.classList.add("today");
        }

        if (selectedDates.includes(dateStr)) {
            div.classList.add("selected");
        }

        div.onclick = () => toggleDate(dateStr, div);
        daysContainer.appendChild(div);
    }
}

function toggleDate(dateStr, element) {
    if (selectedDates.includes(dateStr)) {
        selectedDates = selectedDates.filter(d => d !== dateStr);
        element.classList.remove("selected");
    } else {
        selectedDates.push(dateStr);
        element.classList.add("selected");
    }
    updateSelectedDatesDisplay();
}

function updateSelectedDatesDisplay() {
    const selectedDatesDiv = document.getElementById("selectedDatesList");
    
    if (selectedDates.length === 0) {
        selectedDatesDiv.innerHTML = '<p class="no-dates">No dates selected yet</p>';
        return;
    }
    
    // Sort dates for better display
    const sortedDates = [...selectedDates].sort();
    
    let html = '';
    sortedDates.forEach(dateStr => {
        const date = new Date(dateStr);
        const formattedDate = date.toLocaleDateString('en-US', { 
            weekday: 'short', 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
        
        html += `
            <div class="selected-date-item">
                <span class="selected-date-text">${formattedDate}</span>
                <button class="remove-date-btn" onclick="removeDate('${dateStr}')">×</button>
            </div>
        `;
    });
    
    selectedDatesDiv.innerHTML = html;
}

function removeDate(dateStr) {
    selectedDates = selectedDates.filter(d => d !== dateStr);
    updateSelectedDatesDisplay();
    renderCalendar(); // Update calendar display
}

function clearAllDates() {
    if (selectedDates.length === 0) return;
    
    if (confirm(`Are you sure you want to clear all ${selectedDates.length} selected dates?`)) {
        selectedDates = [];
        updateSelectedDatesDisplay();
        renderCalendar(); // Update calendar display
    }
}

function changeMonth(direction) {
    currentMonth += direction;

    if (currentMonth < 0) {
        currentMonth = 11;
        currentYear--;
    } else if (currentMonth > 11) {
        currentMonth = 0;
        currentYear++;
    }

    document.getElementById("yearSelect").value = currentYear;
    renderCalendar();
}

function changeYear() {
    currentYear = parseInt(document.getElementById("yearSelect").value);
    renderCalendar();
}

// Process schedule with selected dates
async function processSchedule() {
    if (selectedDates.length === 0) {
        alert('Please select at least one exam date');
        return;
    }

    // Show loading spinner
    document.getElementById('loadingSpinner').style.display = 'flex';
    document.getElementById('processBtn').disabled = true;
    document.getElementById('processBtn').innerText = 'Processing...';

    try {
        const response = await fetch('/api/schedule', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                exam_dates: selectedDates,
                preferences: selectedPreferences,
                two_shift_preferences: twoShiftPreferences  // NEW: Include 2-shift preferences
            })
        });

        const data = await response.json();

        if (data.success) {
            currentScheduleResults = data.results;
            displayResults(data.results, data.status);
        } else {
            showError(data.error);
        }
    } catch (error) {
        showError('Failed to generate schedule: ' + error.message);
    } finally {
        document.getElementById('loadingSpinner').style.display = 'none';
        document.getElementById('processBtn').disabled = false;
        document.getElementById('processBtn').innerText = 'Generate Schedule';
    }
}

// Display results in table
function displayResults(results, status) {
    const resultsBody = document.getElementById('resultsBody');
    resultsBody.innerHTML = '';

    results.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${row.date}</td>
            <td>${row.shift}</td>
            <td>${row.room}</td>
            <td>${row.faculty1}</td>
            <td>${row.faculty2}</td>
            <td>${row.staff}</td>
        `;
        resultsBody.appendChild(tr);
    });

    // Display status message
    const statusDiv = document.getElementById('statusMessage');
    statusDiv.innerHTML = status.message || 'Schedule generated successfully';
    statusDiv.className = 'status-message';
    
    if (status.empty_positions > 0) {
        statusDiv.classList.add('warning');
    } else {
        statusDiv.classList.add('success');
    }

    // Show results section
    document.getElementById('resultsSection').style.display = 'block';
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}

// Export to CSV (main, teacher, staff, or room grouped)
async function exportToCSV(csvType = 'main') {
    if (currentScheduleResults.length === 0) {
        alert('No results to export');
        return;
    }

    document.getElementById('loadingSpinner').style.display = 'flex';

    try {
        const response = await fetch('/api/download-csv', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                results: currentScheduleResults,
                type: csvType
            })
        });

        if (response.ok) {
            // Get filename from Content-Disposition header
            const contentDisposition = response.headers.get('content-disposition');
            let filename = `schedule_${csvType}.csv`;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
                if (filenameMatch) {
                    filename = filenameMatch[1];
                }
            }

            // Download the file synchronously
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            
            console.log(`✓ Downloaded: ${filename}`);
        } else {
            const errorData = await response.json();
            showError(errorData.error);
        }
    } catch (error) {
        showError('Failed to export CSV: ' + error.message);
    } finally {
        document.getElementById('loadingSpinner').style.display = 'none';
    }
}

// Export all CSVs as ZIP
async function exportAllAsZip() {
    if (currentScheduleResults.length === 0) {
        alert('No results to export');
        return;
    }

    document.getElementById('loadingSpinner').style.display = 'flex';

    try {
        const response = await fetch('/api/download-all-csv', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                results: currentScheduleResults
            })
        });

        if (response.ok) {
            // Download the ZIP file synchronously
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'exam_schedules.zip';
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            
            console.log('✓ Downloaded: exam_schedules.zip');
        } else {
            const errorData = await response.json();
            showError(errorData.error);
        }
    } catch (error) {
        showError('Failed to export ZIP: ' + error.message);
    } finally {
        document.getElementById('loadingSpinner').style.display = 'none';
    }
}

// Download PDF for schedule
async function downloadPDF(pdfType = 'main') {
    document.getElementById('loadingSpinner').style.display = 'flex';

    try {
        const response = await fetch('/api/download-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                type: pdfType
            })
        });

        if (response.ok) {
            // Get filename from Content-Disposition header
            const contentDisposition = response.headers.get('content-disposition');
            let filename = `schedule_${pdfType}.pdf`;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
                if (filenameMatch) {
                    filename = filenameMatch[1];
                }
            }

            // Download the PDF synchronously
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            
            console.log(`✓ Downloaded: ${filename}`);
        } else {
            const errorData = await response.json();
            showError(errorData.error);
        }
    } catch (error) {
        showError('Failed to download PDF: ' + error.message);
    } finally {
        document.getElementById('loadingSpinner').style.display = 'none';
    }
}

// View Grouped Schedules (display in main results table)
function viewAndDownloadSchedule(scheduleType) {
    if (currentScheduleResults.length === 0) {
        alert('No results to display');
        return;
    }

    const resultsTable = document.getElementById('resultsTable');
    const tableHead = resultsTable.querySelector('thead');
    const tableBody = document.getElementById('resultsBody');

    let headers = [];
    let rows = [];

    if (scheduleType === 'room') {
        headers = ['Date', 'Room', 'Shift', 'Faculty 1', 'Faculty 2', 'Staff'];
        rows = currentScheduleResults.map(row => [
            row.date, row.room, row.shift, row.faculty1, row.faculty2, row.staff
        ]);
        rows.sort((a, b) => a[1].localeCompare(b[1]) || a[0].localeCompare(b[0]));
    } 
    else if (scheduleType === 'teacher') {
        headers = ['Teacher', 'Date', 'Shift', 'Room', 'Role'];
        const teacherMap = {};
        
        currentScheduleResults.forEach(row => {
            if (row.faculty1 !== 'N/A') {
                if (!teacherMap[row.faculty1]) teacherMap[row.faculty1] = [];
                teacherMap[row.faculty1].push([row.faculty1, row.date, row.shift, row.room, 'Faculty 1']);
            }
            if (row.faculty2 !== 'N/A') {
                if (!teacherMap[row.faculty2]) teacherMap[row.faculty2] = [];
                teacherMap[row.faculty2].push([row.faculty2, row.date, row.shift, row.room, 'Faculty 2']);
            }
        });
        
        rows = Object.values(teacherMap).flat();
        rows.sort((a, b) => a[0].localeCompare(b[0]) || a[1].localeCompare(b[1]));
    } 
    else if (scheduleType === 'staff') {
        headers = ['Staff', 'Date', 'Shift', 'Room', 'Faculty 1', 'Faculty 2'];
        const staffMap = {};
        
        currentScheduleResults.forEach(row => {
            if (row.staff !== 'N/A') {
                if (!staffMap[row.staff]) staffMap[row.staff] = [];
                staffMap[row.staff].push([row.staff, row.date, row.shift, row.room, row.faculty1, row.faculty2]);
            }
        });
        
        rows = Object.values(staffMap).flat();
        rows.sort((a, b) => a[0].localeCompare(b[0]) || a[1].localeCompare(b[1]));
    } 
    else { // main
        headers = ['Date', 'Shift', 'Room', 'Faculty 1', 'Faculty 2', 'Staff'];
        rows = currentScheduleResults.map(row => [
            row.date, row.shift, row.room, row.faculty1, row.faculty2, row.staff
        ]);
    }

    // Update table headers
    tableHead.innerHTML = '';
    const headerRow = document.createElement('tr');
    headers.forEach(header => {
        const th = document.createElement('th');
        th.textContent = header;
        headerRow.appendChild(th);
    });
    tableHead.appendChild(headerRow);
    
    // Update table body
    tableBody.innerHTML = '';
    rows.forEach(rowData => {
        const tr = document.createElement('tr');
        rowData.forEach(cell => {
            const td = document.createElement('td');
            td.textContent = cell;
            tr.appendChild(td);
        });
        tableBody.appendChild(tr);
    });
    
    // Scroll to table
    resultsTable.scrollIntoView({ behavior: 'smooth' });
}



// Show error message
function showError(message) {
    const statusDiv = document.getElementById('statusMessage');
    statusDiv.innerHTML = '❌ Error: ' + message;
    statusDiv.className = 'status-message error';
    document.getElementById('resultsSection').style.display = 'block';
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}

// Reset form
function resetForm() {
    document.getElementById('examDatesFile').value = '';
    document.getElementById('resultsSection').style.display = 'none';
    currentScheduleResults = [];
    document.getElementById('uploadSection').scrollIntoView({ behavior: 'smooth' });
}
