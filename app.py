import mytoken
import socketserver
import base64
import os
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from flask_mail import Message, Mail
from flask import Flask, render_template, url_for, redirect, session, logging, request, flash
from flask_uploads import DOCUMENTS, UploadSet, uploaded_file
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, FileField, IntegerField, SubmitField, MultipleFileField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from io import BytesIO
from werkzeug.utils import secure_filename

app = Flask(__name__)



app.config['SECRET_KEY'] = 'tenshichanmajitenshi'
app.config['SECURITY_PASSWORD_SALT'] = 'lifestream'

#flask Upload
ALLOWED_EXTENSIONS = set(['pdf', 'docx'])
app.config['UPLOAD_FOLDER'] = "E:\\Programming\\SelfAccessCenter\\skripsi"

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

#ubah file menjadi data binary

def convertToBinaryData(dokumen):
    with open(dokumen, 'rb') as file:
        dataBinary = file.read()
    return dataBinary


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

class FormulirSkripsi(FlaskForm):
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
    berkas = FileField('Dokumen Skripsi')
    simpan = SubmitField('Simpan')


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
        cur = mysql.connection.cursor()

        hasil = cur.execute('SELECT * FROM skripsi WHERE penulis LIKE %s', [session['nama']])

        data = cur.fetchall()

        if hasil > 0:
            return render_template('dasbor.html', data=data)
        else:
            flash('Anda belum mengupload apapun', 'danger')
        return render_template('dasbor.html')
        cur.close()
    

@app.route('/tambah_skripsi', methods=['GET', 'POST'])
@telah_masuk
def tambah_skripsi():
    form = FormulirSkripsi()

    cur = mysql.connection.cursor()

    if request.method == 'POST' and form.validate():
        try:
            judul   = form.judul.data
            tahun   = form.tahun.data
            abstrak = form.abstrak.data
            berkas  = form.berkas.data

            #upload file ke folder skripsi
            filename = secure_filename(judul + '.pdf')
            berkas.save(os.path.join('skripsi/' + filename))

            dokumen = convertToBinaryData('skripsi/' + filename)

            os.remove('skripsi/' + filename)

            #upload ke database
            cur.execute('INSERT INTO skripsi (judul, penulis, tahun, abstrak, berkas) VALUES(%s, %s, %s, %s, %s)', [judul, session['nama'], tahun, abstrak, dokumen])

            mysql.connection.commit()

            cur.close()

            flash('Skripsi anda telah berhasil ditambahkan ke dalam database', 'success')

            return redirect(url_for('dasbor'))
        except:
            flash('Terjadi error saat memasukkan data ke database.', 'danger')
    return render_template('tambahskripsi.html', form=form)

@app.route('/edit_skripsi/<string:id>/', methods=['GET', 'POST'])
@telah_masuk
def edit_skripsi(id):

    cur = mysql.connection.cursor()

    cur.execute('SELECT * FROM skripsi WHERE id = %s', [id])

    skripsi = cur.fetchone()
        
    cur.close()

    form = FormulirSkripsi()

    form.judul.data = skripsi['judul']
    form.tahun.data = skripsi['tahun']
    form.abstrak.data = skripsi['abstrak']
    form.berkas.data = skripsi['berkas']

    if skripsi['penulis'] != session['nama']:
        flash('Anda bukan pemilik dokumen ini.', 'danger')
        return render_template('dasbor.html')
    else:
        if request.method == 'POST' and form.validate():
            
            judul   = request.form['judul']
            tahun   = request.form['tahun']
            abstrak = request.form['abstrak']
                
            cur = mysql.connection.cursor()
                
            #upload ke database
            cur.execute('UPDATE skripsi SET judul=%s, tahun=%s, abstrak=%s WHERE id = %s', [judul, tahun, abstrak, id])

            mysql.connection.commit()

            cur.close()

            flash('Anda telah berhasil mengedit skripsi anda.', 'success')

            return redirect(url_for('dasbor'))
    return render_template('editskripsi.html', form=form)

@app.route('/cari_skripsi', methods=['GET', 'POST'])
@telah_masuk
def cari_skripsi():

    cur = mysql.connection.cursor()

    if request.method == 'POST':

        skripsi = request.form['skripsi']

        hasil = cur.execute('SELECT * FROM skripsi where judul like %s or penulis like %s', ['%' + skripsi + '%', '%' + skripsi + '%'])

        data = cur.fetchall()

        if hasil > 0:
            return render_template('cariskripsi.html', data=data)
        else:
            flash('Pencarian tidak menghasilkan apapun. Periksa lagi judul atau penulis yang dicari', 'danger')
    return render_template('cariskripsi.html')

@app.route('/skripsi/<string:id>/')
@telah_masuk
def skripsi(id):

    cur = mysql.connection.cursor()

    hasil = cur.execute('SELECT * FROM skripsi WHERE id = %s', [id])

    skripsi = cur.fetchone()

    return render_template('skripsi.html', skripsi=skripsi )

@app.route('/hapus_skripsi/<string:id>', methods=['POST'])
@telah_masuk
def hapus_skripsi(id):
    cur = mysql.connection.cursor()

    cur.execute('DELETE FROM skripsi WHERE id = %s', [id])

    mysql.connection.commit()

    cur.close()

    flash('Skripsi berhasil dihapus', 'success')
    return redirect(url_for('dasbor'))

if __name__ == '__main__':
    app.run(debug=True)