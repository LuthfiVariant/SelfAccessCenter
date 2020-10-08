import app
from flask_mail import Message, Mail

mail = Mail(app)
mail.init_app(app)

def kirim_email(to, subject, template):
    message = Message(
        subject=app.FormulirPendaftaran.email,
        recipients=[to],
        html=template,
        sender=app.app.config['MAIL_DEFAULT_SENDER']
    )
    Mail.send_message(message)