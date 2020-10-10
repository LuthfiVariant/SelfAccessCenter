import mytoken
import socketserver
import base64
from flask_mail import Message, Mail
from flask import Flask, render_template, url_for, redirect, session, logging, request, flash
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, FileField, IntegerField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from io import BytesIO
from werkzeug.utils import secure_filename



app = Flask(__name__)



app.config['SECRET_KEY'] = 'tenshichanmajitenshi'
app.config['SECURITY_PASSWORD_SALT'] = 'lifestream'

#config email

app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'lutfhivarianthanif@gmail.com'
app.config['MAIL_PASSWORD'] = 'tenshichanmajitenshi'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

app.config['MAIL_DEFAULT_SENDER'] = 'noreply@selfaccesscenter'

#init mail

mail = Mail(app)
mail.init_app(app)

def kirim_email(to, subject, template):
    message = Message(
        subject,
        recipients=[to],
        html=template,
        sender=app.config['MAIL_DEFAULT_SENDER']
    )
    mail.send(message)

#config MySQL

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'kanaderu'
app.config['MYSQL_DB'] = 'sac'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

#init MySQL

mysql = MySQL(app)

#formulir

class FormulirPendaftaran(Form):
    nama = StringField('Nama', [
        validators.Length(min=1, max=50),
        validators.DataRequired()
        ])
    nim = IntegerField(u'NIM', [validators.DataRequired()])
    email = StringField('Email', [
        validators.Regexp('.@student.upi.edu', message='Harap gunakan email @student.upi.edu'),
        validators.DataRequired()
        ])
    password = PasswordField('Password', [
        validators.Length(min=5, max=50, message="kata sandi harus memiliki minimal 5 karakter dan maksimal 50 karakter"),
        validators.EqualTo('confirm', message="kata sandi dan konfirmasi harus sama"),
        validators.DataRequired()])
    confirm = PasswordField('Confirm Password', [validators.DataRequired()])

class FormulirSkripsi(Form):
    judul = StringField('Judul', [
        validators.Length(min=20, max=255, message='Panjang judul hanya bisa 20-255 karakter'),
        validators.DataRequired()
    ])
    tahun = IntegerField('Tahun', [
        validators.DataRequired()
    ])
    abstrak = TextAreaField('Abstrak', [
    validators.length(min=100, message="Abstrak hanya bisa 100-300 kata"),
    validators.DataRequired()
    ])
    berkas = FileField('Dokumen Skripsi', [
        validators.DataRequired()
    ])

#ubah file menjadi data binary

def encode(data: bytes):
    return base64.b64encode(data)

def ubahKeDataBinary(berkas):
    with open(berkas, 'rb') as file:
        encode(file)
    

#decorator
def telah_masuk(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'masuk' in session:
            return f(*args, **kwargs)
        else:
            flash('Harap masuk terlebih dahulu', 'danger')
            return redirect(url_for('masuk'))
    return wrap



#app route

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/dataskripsi')
def dataSkripsi():
    return render_template('dataskripsi.html', dataSkripsi = skripsi)

@app.route('/skripsi/<string:id>')
def skripsi(id):
    return render_template('skripsi.html', id = id)

@app.route('/daftar', methods=['POST', 'GET'])
def daftar():
    form = FormulirPendaftaran(request.form)

    if request.method == 'POST' and form.validate():
        nama = form.nama.data
        nim = form.nim.data
        email = form.email.data
        password = sha256_crypt.encrypt(str(form.password.data))
        verifikasi = False

        #create token

        token = mytoken.generate_confirmation_token(email)
        confirm_url = url_for('konfirmasi', token=token, _external=True)

        html = render_template('aktivasi.html', confirm_url=confirm_url)
        subject = "Konfirmasi akun Layanan Unggah Mandiri Self Access Center Bahasa dan Sastra Inggris UPI"
        kirim_email(email, subject, html)

        #create cursor

        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO akun(nama,nim, email, password, verifikasi) VALUES(%s, %s, %s, %s, %s)", (nama, nim, email, password, verifikasi))

        #comit to DB

        mysql.connection.commit()

        #close connection

        cur.close()

        flash('Email konfirmasi telah dikirim ke email anda. Konfirmasi akun anda untuk bisa menggunakannya', 'success')
        
        return redirect(url_for('index'))
    return render_template('daftar.html', form=form)

@app.route('/konfirmasi/<token>')
def konfirmasi(token):
    try:
        email = mytoken.confirm_token(token)
    except:
        flash('Link sudah kadaluarsa', 'danger')
        redirect(url_for('index'))
    
    #query akun untuk mencari user
    cur = mysql.connection.cursor()

    cur.execute('SELECT verifikasi FROM akun WHERE email like %s', (email,))

    verifikasi = cur.fetchone()

    #cek apakah akun sudah terverifikasi atau belum. Jika sudah, maka arahkan ke login jika belum maka ubah verifikasi menjadi true
    if verifikasi == True:
        flash('Akun ini sudah terkonfirmasi. Silahkan Masuk.', 'success')
        redirect(url_for('index'))
    else:
        cur.execute('UPDATE akun SET verifikasi = true WHERE email=%s', (email,))

        mysql.connection.commit()

        cur.close()
        flash('Akun anda berhasil dikonfirmasi. Silahkan Login', 'success')
    return redirect(url_for('index'))

@app.route('/masuk', methods=['POST', 'GET'])
def masuk():
    if request.method == 'POST':
        #ambil form field
        nim = request.form['nim']
        password_candidate = request.form['password']

        #buat cursor

        cur = mysql.connection.cursor()

        #cari berdasarkan nim

        hasil = cur.execute('SELECT * FROM akun WHERE nim = %s', [nim])

        if hasil > 0:
            #ambil hash
            data = cur.fetchone()
            password = data['password']
            verifikasi = data['verifikasi']
            nama = data['nama']

            #bandingkan password dan verifikasi

            if sha256_crypt.verify(password_candidate, password) and verifikasi == False:
                error = 'Verifikasi terlebih dahulu akun anda.'
                return render_template('masuk.html', error=error)

            if sha256_crypt.verify(password_candidate, password) and verifikasi == True:
                #sukses login
                session['masuk'] = True
                session['nama'] = nama

                flash('Anda sudah masuk.', 'success')
                return redirect(url_for('dasbor'))

            else:
                error = 'Password atau NIM anda salah'
                return render_template('masuk.html', error=error)

            #tutup query SQL
            cur.close()

        else:
            error = 'Data anda tidak ditemukan'
            return render_template('masuk.html', error=error)
    return render_template('masuk.html')

@app.route('/keluar')
@telah_masuk
def keluar():
    session.clear()
    flash('Anda telah keluar.', 'success')
    return redirect(url_for('masuk'))

@app.route('/dasbor')
@telah_masuk
def dasbor():
    return render_template('dasbor.html')

@app.route('/tambah_skripsi', methods=['GET', 'POST'])
@telah_masuk
def tambah_skripsi():
    form = FormulirSkripsi(request.form)
    if request.method == 'POST' and form.validate():
        judul = form.judul.data
        tahun = form.tahun.data
        abstrak = form.abstrak.data
        berkas = form.berkas.data

        #ubah data berkas menjadi blob
        bytes
        file_pdf = ubahKeDataBinary(berkas)

        #buat cursor

        cur = mysql.connection.cursor()

        #masukkan ke dalam database
        cur.execute('INSERT INTO skripsi(judul, penulis, tahun, abstrak, berkas) VALUES(%s, %s, %s, %s, %s)', [judul, session['nama'], tahun, abstrak, file_pdf])

        mysql.connection.commit()

        cur.close()

        flash('Skripsi anda telah berhasil ditambahkan ke dalam database', 'success')

        redirect(url_for('dasbor'))
    return render_template('tambahskripsi.html', form=form)

if __name__ == '__main__':
    app.run(debug=True)