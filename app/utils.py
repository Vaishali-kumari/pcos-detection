from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a secure random key in production

# Database initialization
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        risk_level TEXT NOT NULL,
        risk_percentage REAL NOT NULL,
        age INTEGER,
        bmi TEXT,
        hirsutism TEXT,
        acne TEXT,
        menstrual TEXT,
        family_history TEXT,
        waist_hip_ratio REAL,
        amh REAL,
        fasting_glucose INTEGER,
        fasting_insulin INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Routes
@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/landing')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['user_id'] = user['id']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        
        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, generate_password_hash(password))
            )
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if 'username' not in session:
        flash('Please login to access this page', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        form_data = request.form
        risk_percentage = calculate_risk(form_data)
        risk_level = 'low' if risk_percentage < 30 else 'moderate' if risk_percentage < 60 else 'high'
        
        conn = get_db_connection()
        conn.execute(
            '''INSERT INTO predictions 
            (user_id, risk_level, risk_percentage, age, bmi, hirsutism, acne, menstrual, 
             family_history, waist_hip_ratio, amh, fasting_glucose, fasting_insulin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (session['user_id'], risk_level, risk_percentage, 
             form_data.get('age'), form_data.get('bmi'), form_data.get('hirsutism'), 
             form_data.get('acne'), form_data.get('menstrual'), form_data.get('familyHistory'),
             form_data.get('waistHipRatio'), form_data.get('amh'), 
             form_data.get('fastingGlucose'), form_data.get('fastingInsulin'))
        )
        conn.commit()
        conn.close()
        
        flash('Assessment completed successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('predict.html', username=session['username'])

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        flash('Please login to access this page', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    predictions = conn.execute(
        'SELECT * FROM predictions WHERE user_id = ? ORDER BY prediction_date DESC',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    return render_template('dashboard.html', 
                         username=session['username'],
                         predictions=predictions)

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('landing'))

# Helper functions
def calculate_risk(form_data):
    risk = 20  # Base risk
    
    if form_data.get('bmi') in ['Overweight', 'Obese']:
        risk += 15
    if form_data.get('menstrual') == 'No':
        risk += 25
    if form_data.get('familyHistory') == 'Yes':
        risk += 10
    if form_data.get('hirsutism') == 'Yes':
        risk += 10
    if form_data.get('acne') == 'Yes':
        risk += 5
    
    risk = max(0, min(100, risk))
    return round(risk)

@app.context_processor
def utility_processor():
    def get_recommendations(risk_level):
        if risk_level == 'low':
            return [
                "Maintain healthy lifestyle habits",
                "Monitor menstrual cycle patterns",
                "Annual check-up with your doctor"
            ]
        elif risk_level == 'moderate':
            return [
                "Consult with a healthcare provider",
                "Consider hormonal blood tests",
                "Improve diet and exercise routine",
                "Monitor symptoms regularly"
            ]
        else:
            return [
                "Schedule appointment with endocrinologist",
                "Comprehensive metabolic and hormonal testing",
                "Consider pelvic ultrasound",
                "Develop treatment plan with your doctor",
                "Lifestyle modifications for symptom management"
            ]
    return dict(get_recommendations=get_recommendations)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)