from email import kirim_email
from token import generate_confirmation_token, confirm_token
from flask import Flask, render_template, url_for, redirect, session, logging, request, flash
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, FileField, IntegerField, validators
from passlib.hash import sha256_crypt



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

#config MySQL

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'kanaderu'
app.config['MYSQL_DB'] = 'sac'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

#init MySQL

mysql = MySQL(app)

class FormulirPendaftaran(Form):
    nama = StringField('Nama', [
        validators.Length(min=1, max=50),
        validators.DataRequired()
        ])
    nim = IntegerField(u'NIM', [validators.DataRequired()])
    email = StringField('Email', [
        validators.Regexp('.*@student.upi.edu', message="Hanya bisa menggunakan email @student.upi.edu"), 
        validators.DataRequired()
        ])
    password = PasswordField('Password', [
        validators.Length(min=5, max=50, message="kata sandi harus memiliki minimal 5 karakter dan maksimal 50 karakter"),
        validators.EqualTo('confirm', message="kata sandi dan konfirmasi harus sama"),
        validators.DataRequired()])
    confirm = PasswordField('Confirm Password', [validators.DataRequired()])


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

        #create cursor

        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO akun(nama,nim, email, password, verifikasi) VALUES(%s, %s, %s, %s, %s)", (nama, nim, email, password, verifikasi))

        #comit to DB

        mysql.connection.commit()

        #create token

        token = generate_confirmation_token(email)
        confirm_url = url_for('konfirmasi', token=token, _external=True)
        html = render_template('activate.html', confirm_url=confirm_url)
        subject = "Konfirmasi akun Layanan Unggah Mandiri Self Access Center Bahasa dan Sastra Inggris UPI"
        kirim_email(email, subject, html)

        #close connection

        cur.close()

        flash('Email konfirmasi telah dikirim ke email anda. Konfirmasi akun anda untuk bisa menggunakannya', 'success')
        
        return redirect(url_for('index'))
    return render_template('daftar.html', form=form)

@app.route('/konfirmasi/<token>')
def konfirmasi(token):
    try:
        email = confirm_token(token)
    except:
        flash('Link sudah kadaluarsa', 'danger')
        redirect(url_for('index'))
    
    #query akun untuk mencari user
    cur = mysql.connection.cursor()

    cur.execute('SELECT verifikasi FROM akun WHERE email like %s', (email))

    verifikasi = cur.fetchone()

    #cek apakah akun sudah terverifikasi atau belum. Jika sudah, maka arahkan ke login jika belum maka ubah verifikasi menjadi true
    if verifikasi == True:
        flash('Akun ini sudah terkonfirmasi. Silahkan Masuk.', 'success')
        redirect(url_for('index'))
    else:
        cur.execute('UPDATE akun SET verifikasi = true WHERE email=%s', (email))

        mysql.connection.commit()

        cur.close()
        flash('Akun anda berhasil dikonfirmasi. Silahkan Login', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)