from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os

app = Flask(__name__)

# Konfigurasi Database dan Keamanan
app.config['SECRET_KEY'] = 'kunci_rahasia_ekg_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- MODEL DATABASE ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    # Relasi ke tabel history
    history = db.relationship('EKGData', backref='owner', lazy=True)

class EKGData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nilai = db.Column(db.Integer) # Nilai dari sensor EKG
    timestamp = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES HALAMAN ---

@app.route('/')
def home():
    return render_template('base.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Username sudah ada!')
            return redirect(url_for('register'))
            
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Berhasil daftar! Silakan login.')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('account'))
        
        flash('Login gagal! Periksa username dan password.')
    return render_template('login.html')

@app.route('/account')
@login_required
def account():
    # Ambil riwayat pengecekan khusus user yang sedang login
    user_history = EKGData.query.filter_by(user_id=current_user.id).order_by(EKGData.timestamp.desc()).all()
    return render_template('account.html', history=user_history)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# --- API UNTUK ESP32 ---

@app.route('/update', methods=['POST'])
def update():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No JSON"}), 400
        
    user_id = data.get('user_id')
    nilai = data.get('nilai')
    
    if user_id and nilai:
        new_data = EKGData(nilai=nilai, user_id=user_id)
        db.session.add(new_data)
        db.session.commit()
        return jsonify({"status": "success"}), 200
        
    return jsonify({"status": "failed"}), 400

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ini yang membuat tabel secara otomatis
    app.run(host='0.0.0.0', port=5000, debug=True)