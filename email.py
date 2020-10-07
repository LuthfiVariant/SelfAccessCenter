from flask_mail import Message, Mail
import app

def kirim_email(to, subject, template):
    msg = Message(
        subject,
        recipients=[to],
        html=template,
        sender=app.config['MAIL_DEFAULT_SENDER']
    )

    Mail.send(msg)