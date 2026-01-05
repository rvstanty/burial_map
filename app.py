from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Grave, DaftarKematian
import os
from sqlalchemy import or_

app = Flask(__name__)

# Konfigurasi Database
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'database.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Fungsi untuk mencipta table jika belum wujud
def create_tables():
    with app.app_context():
        db.create_all()

create_tables()

# --- ROUTES ---

@app.route('/')
def home():
    query = request.args.get('query', '').strip()
    graves = []
    daftar_kematian_records = []
    
    if query:
        like_pattern = f"%{query}%"
        # Carian pada table Grave
        graves = Grave.query.filter(or_(Grave.name.ilike(like_pattern), Grave.section.ilike(like_pattern))).all()
        # Carian pada table DaftarKematian (yang mengandungi data koordinat)
        daftar_kematian_records = DaftarKematian.query.filter(
            or_(
                DaftarKematian.deceased_name.ilike(like_pattern),
                DaftarKematian.stone_number.ilike(like_pattern),
                DaftarKematian.heir_name.ilike(like_pattern)
            )
        ).all()
    
    return render_template('home.html', graves=graves, daftar_kematian_records=daftar_kematian_records, query=query)

@app.route('/daftar_kematian', methods=['GET', 'POST'])
def daftar_kematian():
    user_id = session.get('user_id')
    if not user_id:
        flash('Sila log masuk untuk mengakses halaman ini.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Ambil Data dari Form
        deceased_name = request.form.get('deceased_name')
        stone_number = request.form.get('stone_number')
        date_of_birth = request.form.get('date_of_birth')
        age_at_death = request.form.get('age_at_death')
        heir_name = request.form.get('heir_name')
        heir_contact = request.form.get('heir_contact')
        
        # Data Lokasi (Pin)
        selected_plot = request.form.get('selected_plot')
        coord_x = request.form.get('coord_x')
        coord_y = request.form.get('coord_y')

        # Validasi
        if not all([deceased_name, stone_number, coord_x, coord_y]):
            flash('Sila isi maklumat dan tetapkan lokasi pada peta.', 'error')
            return redirect(url_for('daftar_kematian'))

        try:
            age_val = int(age_at_death)
            cx = float(coord_x)
            cy = float(coord_y)
        except ValueError:
            flash('Data teknikal koordinat tidak sah.', 'error')
            return redirect(url_for('daftar_kematian'))

        # 1. Simpan/Update data dalam table Grave (Maklumat Induk)
        grave = Grave.query.filter_by(lot_number=stone_number).first()
        if not grave:
            grave = Grave(
                name=deceased_name,
                date_of_birth=date_of_birth,
                lot_number=stone_number,
                section=selected_plot.upper(),
                family_details=heir_name,
                notes=heir_contact
            )
            db.session.add(grave)
            db.session.flush() # Ambil ID untuk kegunaan record bawah

        # 2. Simpan dalam table DaftarKematian (Rekod Pendaftaran & Koordinat)
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
        return redirect(url_for('daftar_kematian'))

    records = DaftarKematian.query.all()
    return render_template('daftar_kematian.html', records=records)

# --- ROUTE BARU UNTUK BUTIRAN KUBUR ---
@app.route('/grave/<int:grave_id>')
def grave_detail(grave_id):
    # Kita ambil data dari DaftarKematian kerana table ini ada simpan koordinat pin
    # Jika anda guna query.get(), ia cari berdasarkan Primary Key (id)
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
    app.run(debug=True, host='0.0.0.0', port=5000)