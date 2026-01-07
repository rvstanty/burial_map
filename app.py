from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Grave, DaftarKematian
import os
from sqlalchemy import or_
from datetime import datetime, timedelta
from functools import wraps 

app = Flask(__name__)

# Konfigurasi Database
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'database.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# --- SECURITY CHECK DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Sila log masuk untuk mengakses halaman ini.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTES ---

@app.route('/')
def home():
    query = request.args.get('query', '').strip()
    graves_records = []
    daftar_kematian_records = []
    
    if query:
        like_pattern = f"%{query}%"
        graves_records = Grave.query.filter(or_(Grave.name.ilike(like_pattern), Grave.section.ilike(like_pattern))).all()
        daftar_kematian_records = DaftarKematian.query.filter(
            or_(
                DaftarKematian.deceased_name.ilike(like_pattern),
                DaftarKematian.stone_number.ilike(like_pattern),
                DaftarKematian.heir_name.ilike(like_pattern)
            )
        ).all()
    
    return render_template('home.html', graves=graves_records, daftar_kematian_records=daftar_kematian_records, query=query)

# --- SENARAI SEMUA REKOD ---
@app.route('/graves')
@login_required 
def graves():
    all_records = DaftarKematian.query.order_by(DaftarKematian.id.desc()).all()
    current_time = datetime.utcnow()
    
    graves_list = []
    for record in all_records:
        is_new = False
        if hasattr(record, 'created_at') and record.created_at:
            if current_time - record.created_at < timedelta(days=7):
                is_new = True
        
        graves_list.append({
            'id': record.id,
            'nama_simati': record.deceased_name,
            'ic_simati': record.stone_number,
            'tarikh_meninggal': record.date_of_birth,
            'koordinat': f"{record.coord_x}, {record.coord_y}",
            'nama_waris': record.heir_name,
            'is_new': is_new
        })
        
    return render_template('graves.html', graves=graves_list)

# --- DAFTAR KEMATIAN ---
@app.route('/daftar_kematian', methods=['GET', 'POST'])
@login_required 
def daftar_kematian():
    if request.method == 'POST':
        deceased_name = request.form.get('deceased_name')
        stone_number = request.form.get('stone_number')
        date_of_birth = request.form.get('date_of_birth')
        age_at_death = request.form.get('age_at_death')
        heir_name = request.form.get('heir_name')
        heir_contact = request.form.get('heir_contact')
        selected_plot = request.form.get('selected_plot')
        coord_x = request.form.get('coord_x')
        coord_y = request.form.get('coord_y')

        if not all([deceased_name, stone_number, coord_x, coord_y]):
            flash('Sila isi maklumat dan tetapkan lokasi pada peta.', 'error')
            return redirect(url_for('daftar_kematian'))

        try:
            age_val = int(age_at_death)
            cx = float(coord_x)
            cy = float(coord_y)
        except (ValueError, TypeError):
            flash('Data teknikal tidak sah.', 'error')
            return redirect(url_for('daftar_kematian'))

        grave = Grave.query.filter_by(lot_number=stone_number).first()
        if not grave:
            grave = Grave(
                name=deceased_name,
                date_of_birth=date_of_birth,
                lot_number=stone_number,
                section=selected_plot.upper() if selected_plot else "UNKNOWN",
                family_details=heir_name,
                notes=heir_contact
            )
            db.session.add(grave)
            db.session.flush()

        new_record = DaftarKematian(
            grave_id=grave.id,
            deceased_name=deceased_name,
            stone_number=stone_number,
            date_of_birth=date_of_birth,
            age_at_death=age_val,
            heir_name=heir_name,
            heir_contact=heir_contact,
            selected_plot=selected_plot,
            coord_x=cx,
            coord_y=cy
        )
        
        db.session.add(new_record)
        db.session.commit()
        flash('Pendaftaran berjaya disimpan!', 'success')
        return redirect(url_for('graves'))

    records = DaftarKematian.query.all()
    return render_template('daftar_kematian.html', records=records)

# --- DETAIL KUBUR (Dibaiki untuk ralat BuildError) ---
@app.route('/grave/<int:grave_id>')
@login_required
def grave_detail(grave_id):
    # Mengambil data berdasarkan ID unik pendaftaran
    grave = DaftarKematian.query.get_or_404(grave_id)
    return render_template('grave_detail.html', grave=grave)

# --- AUTH ROUTES ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Email telah didaftarkan.', 'error')
            return redirect(url_for('register'))
        new_user = User(email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Pendaftaran berjaya! Sila log masuk.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_email'] = user.email
            return redirect(url_for('home'))
        flash('Log masuk gagal. Sila periksa email/password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah log keluar.', 'info')
    return redirect(url_for('home'))

# --- STATIK ROUTES ---
@app.route('/organisasi')
def organisasi(): return render_template('organisasi.html')

@app.route('/adab')
def adab(): return render_template('adab.html')

@app.route('/privasi')
def privasi(): return render_template('privasi.html')

@app.route('/terma')
def terma(): return render_template('terma.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)