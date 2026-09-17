from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a secure random key in production

# MongoDB configuration
client = MongoClient('mongodb://localhost:27017/')
db = client['pcos_prediction']

# Collections
users = db.users
predictions = db.predictions

# Routes
@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = users.find_one({'username': username})
        
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['user_id'] = str(user['_id'])
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
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        
        if users.find_one({'username': username}):
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
        if users.find_one({'email': email}):
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        user_data = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'full_name': request.form.get('full_name'),
            'date_of_birth': request.form.get('dob'),
            'created_at': datetime.utcnow()
        }
        
        users.insert_one(user_data)
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        flash('Please login to access this page', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Update profile information
        update_data = {
            'full_name': request.form.get('full_name'),
            'date_of_birth': request.form.get('dob'),
            'height': float(request.form.get('height', 0)),
            'weight': float(request.form.get('weight', 0)),
            'blood_type': request.form.get('blood_type'),
            'medical_history': request.form.get('medical_history')
        }
        
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        users.update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$set': update_data}
        )
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    user = users.find_one({'_id': ObjectId(session['user_id'])})
    return render_template('profile.html', user=user)

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if 'username' not in session:
        flash('Please login to access this page', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        form_data = request.form
        risk_percentage = calculate_risk(form_data)
        risk_level = 'low' if risk_percentage < 30 else 'moderate' if risk_percentage < 60 else 'high'
        
        prediction_data = {
            'user_id': ObjectId(session['user_id']),
            'prediction_date': datetime.utcnow(),
            'risk_level': risk_level,
            'risk_percentage': risk_percentage,
            'age': int(form_data.get('age')),
            'bmi': form_data.get('bmi'),
            'hirsutism': form_data.get('hirsutism'),
            'acne': form_data.get('acne'),
            'menstrual': form_data.get('menstrual'),
            'family_history': form_data.get('familyHistory'),
            'waist_hip_ratio': float(form_data.get('waistHipRatio', 0)),
            'amh': float(form_data.get('amh', 0)),
            'fasting_glucose': int(form_data.get('fastingGlucose', 0)),
            'fasting_insulin': int(form_data.get('fastingInsulin', 0)),
            'notes': form_data.get('notes')
        }
        
        predictions.insert_one(prediction_data)
        flash('Assessment completed successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('predict.html', username=session['username'])

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        flash('Please login to access this page', 'danger')
        return redirect(url_for('login'))
    
    user_predictions = list(predictions.find(
        {'user_id': ObjectId(session['user_id'])}
    ).sort('prediction_date', -1))
    
    user = users.find_one({'_id': ObjectId(session['user_id'])})
    
    return render_template('dashboard.html',
                         username=session['username'],
                         user=user,
                         predictions=user_predictions)

@app.route('/prediction/<prediction_id>')
def view_prediction(prediction_id):
    if 'username' not in session:
        flash('Please login to access this page', 'danger')
        return redirect(url_for('login'))
    
    prediction = predictions.find_one({
        '_id': ObjectId(prediction_id),
        'user_id': ObjectId(session['user_id'])
    })
    
    if not prediction:
        flash('Prediction not found', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('prediction_detail.html',
                         prediction=prediction,
                         username=session['username'])

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
    
    def format_date(value, format='%Y-%m-%d %H:%M'):
        if value:
            return value.strftime(format)
        return ""
    
    return dict(
        get_recommendations=get_recommendations,
        format_date=format_date
    )

if __name__ == '__main__':
    app.run(debug=True)