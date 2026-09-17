from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'pcos_secret_key_2024'
DATABASE = 'database.db'

# Run DB init on startup (needed for gunicorn)
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        risk_level TEXT NOT NULL,
        risk_percentage REAL NOT NULL,
        age INTEGER, bmi TEXT, hirsutism TEXT, acne TEXT,
        menstrual TEXT, family_history TEXT,
        waist_hip_ratio REAL, amh REAL,
        fasting_glucose INTEGER, fasting_insulin INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )""")
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize DB on every startup
init_db()

def calculate_risk(form_data):
    risk = 20
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
    return min(max(risk, 0), 100)

def get_recommendations(risk_level):
    if risk_level == 'low':
        return [
            "Maintain healthy lifestyle habits",
            "Monitor menstrual cycle patterns regularly",
            "Annual check-up with your doctor"
        ]
    elif risk_level == 'moderate':
        return [
            "Consult with a healthcare provider soon",
            "Get hormonal blood tests (LH, FSH, testosterone)",
            "Reduce sugar and processed food intake",
            "Exercise at least 30 minutes daily",
            "Monitor your symptoms regularly"
        ]
    else:
        return [
            "Schedule appointment with endocrinologist or gynecologist ASAP",
            "Get comprehensive metabolic and hormonal testing",
            "Consider pelvic ultrasound",
            "Develop a treatment plan with your doctor",
            "Follow a low-GI diet and exercise regularly",
            "Ask your doctor about inositol or metformin"
        ]

def get_message(risk_level):
    if risk_level == 'low':
        return "Good news — your responses suggest a LOW risk of PCOS. Keep maintaining a healthy lifestyle."
    elif risk_level == 'moderate':
        return "You show some indicators associated with PCOS. We recommend consulting a healthcare provider for further evaluation."
    else:
        return "Your responses suggest several strong indicators of PCOS. Please schedule an appointment with a healthcare provider as soon as possible."

# ── Routes ────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('test'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            flash('Please fill in all fields.', 'danger')
            return render_template('login.html')
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Welcome back, ' + username + '!', 'success')
            return redirect(url_for('test'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('test'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm  = request.form.get('confirm_password', '').strip()
        if not username or not password or not confirm:
            flash('Please fill in all fields.', 'danger')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')
        conn = get_db()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                         (username, generate_password_hash(password)))
            conn.commit()
            flash('Account created! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already taken. Try another.', 'danger')
            return render_template('register.html')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/test')
def test():
    if 'user_id' not in session:
        flash('Please login first to take the assessment.', 'warning')
        return redirect(url_for('login'))
    return render_template('test.html', result=None, username=session.get('username'))

@app.route('/predict', methods=['POST'])
def predict():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    form_data = request.form
    risk_pct  = calculate_risk(form_data)
    risk_lvl  = 'low' if risk_pct < 30 else ('moderate' if risk_pct < 60 else 'high')

    conn = get_db()
    conn.execute("""INSERT INTO predictions
        (user_id, risk_level, risk_percentage, age, bmi, hirsutism, acne,
         menstrual, family_history, waist_hip_ratio, amh, fasting_glucose, fasting_insulin)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (session['user_id'], risk_lvl, risk_pct,
         form_data.get('age'),    form_data.get('bmi'),
         form_data.get('hirsutism'), form_data.get('acne'),
         form_data.get('menstrual'), form_data.get('familyHistory'),
         form_data.get('waistHipRatio'), form_data.get('amh'),
         form_data.get('fastingGlucose'), form_data.get('fastingInsulin')))
    conn.commit()
    conn.close()

    result = {
        'risk_level':      risk_lvl,
        'risk_percentage': risk_pct,
        'message':         get_message(risk_lvl),
        'recommendations': get_recommendations(risk_lvl)
    }
    return render_template('test.html', result=result, username=session.get('username'))

@app.route('/symptoms')
def symptoms():
    return render_template('symptoms.html')

@app.route('/recommend')
def recommend():
    return render_template('recommend.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/learn_more')
def learn_more():
    return render_template('learn_more.html')

@app.route('/user-history')
def user_history():
    return render_template('user-history.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
