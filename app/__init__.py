from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import os
from flask_mail import Mail

app = Flask(__name__)
app.config.from_object(Config)
mail = Mail(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'

if not app.debug:
    
    #this auth is used to store credentials of the account from which we are going to send email
    auth = None
    if app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']:
        #this means we have credentials now make tuple of (username, password)
        auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])

    #We set the secure parameter to an empty tuple to use the default secure connection
    secure = None
    if app.config['MAIL_USE_TLS']:
        secure = ()

    mail_handler = SMTPHandler(
        mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
        subject='v3_blogs Failure',
        fromaddr=app.config['ADMINS'][0],
        toaddrs=[app.config['ADMINS'][1]],
        credentials=auth,
        secure=secure
    )

    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)

    if not os.path.exists('logs'):
        os.mkdir('logs')
        
    file_handler = RotatingFileHandler(
        filename='logs/v3_blogs_logs.log',
        mode='a',
        maxBytes=10240,
        backupCount=10
    )

    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s : %(lineno)d]')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    

from app import routes, models, errors