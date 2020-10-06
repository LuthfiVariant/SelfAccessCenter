from flask import Flask, render_template, url_for, redirect, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, FileField, IntegerField, validators
from passlib.hash import sha256_crypt


app = Flask(__name__)

class FormulirPendaftaran(Form):
    nama = StringField('Nama', [
        validators.Length(min=1, max=50),
        validators.DataRequired()
        ])
    nim = IntegerField(u'NIM', [validators.DataRequired()])
    email = StringField('Email', [
        validators.Regexp('@student.upi.edu', message="Hanya bisa menggunakan email @student.upi.edu"), 
        validators.DataRequired()
        ])
    password = PasswordField('Password', [
        validators.Length(min=5, max=50, message="kata sandi harus memiliki minimal 5 karakter dan maksimal 50 karakter"),
        validators.EqualTo('confirm', message="kata sandi dan konfirmasi harus sama"),
        validators.DataRequired()])
    confirm = PasswordField('Confirm Password', [validators.DataRequired()])


@app.route('/')
def home():
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
        return render_template('daftar.html', form=form)
    return render_template('daftar.html', form=form)


if __name__ == '__main__':
    app.run(debug=True)