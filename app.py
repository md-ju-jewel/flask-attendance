from flask import Flask, request, render_template, redirect, url_for, session, send_file
import sqlite3
from datetime import date
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = 'secret123'  # Change this in production

DB_NAME = 'attendance.db'

# Load valid student IDs from file
with open('students.txt') as f:
    VALID_IDS = set(line.strip() for line in f)

# Admin credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password'

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id TEXT,
                date TEXT
            )
        ''')

@app.route('/', methods=['GET', 'POST'])
def index():
    message = ''
    if request.method == 'POST':
        student_id = request.form.get('student_id').strip()
        today = date.today().isoformat()
        if student_id in VALID_IDS:
            with sqlite3.connect(DB_NAME) as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM attendance WHERE id = ? AND date = ?", (student_id, today))
                if cur.fetchone():
                    message = 'Already marked as present.'
                else:
                    conn.execute("INSERT INTO attendance (id, date) VALUES (?, ?)", (student_id, today))
                    message = 'Attendance marked!'
        else:
            message = 'Invalid ID.'
    
    return render_template('index.html', message=message, valid_ids=sorted(VALID_IDS))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    message = ''
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_present'))
        else:
            message = 'Invalid credentials'
    return render_template('admin_login.html', message=message)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/present', methods=['GET', 'POST'])
def admin_present():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    today = date.today().isoformat()
    
    if request.method == 'POST':
        student_id = request.form.get('delete_id')
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("DELETE FROM attendance WHERE id = ? AND date = ?", (student_id, today))
    
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM attendance WHERE date = ?", (today,))
        present_ids = [row[0] for row in cur.fetchall()]
    
    return render_template('present.html', present_ids=present_ids, admin=True)


@app.route('/admin/history', methods=['GET', 'POST'])
def admin_history():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    records = []
    selected_date = ''
    filter_id = ''
    
    if request.method == 'POST':
        selected_date = request.form['date']
        filter_id = request.form.get('filter_id', '')
        
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            if filter_id:
                cur.execute("SELECT id FROM attendance WHERE date = ? AND id = ?", (selected_date, filter_id))
            else:
                cur.execute("SELECT id FROM attendance WHERE date = ?", (selected_date,))
            records = [row[0] for row in cur.fetchall()]
    
    return render_template('history.html', records=records, selected_date=selected_date, filter_id=filter_id)


@app.route('/export')
def export_attendance():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    today = date.today().isoformat()
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query("SELECT * FROM attendance WHERE date = ?", conn, params=(today,))
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return send_file(output, download_name=f"attendance_{today}.xlsx", as_attachment=True)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
