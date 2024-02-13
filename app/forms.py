from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, EmailField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, EqualTo, Email, ValidationError, Length
from app import db
from sqlalchemy import select
from .models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField("Remember Me", default=True)
    submit = SubmitField("Login")

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = db.session.scalar(
            select(User).where(User.username == username.data)
        )
        if user is not None:
            raise ValidationError('This username is already taken please choose another username.')
        
    def validate_email(self, email):
        user = db.session.scalar(
            select(User).where(User.email == email.data)
        )
        if user is not None:
            raise ValidationError('Account with this email already exist, try resetting password')
        
    def __dict__(self):
        return {
            'username' : self.username.data,
            'email' : self.email.data,
            'password' : self.password.data,
            'confirm_password': self.confirm_password.data
        }
        
class EditProfileForm(FlaskForm):
    about_me = TextAreaField('About Me:', validators=[Length(min=0, max=120)])
    submit = SubmitField('Save Changes')

class FollowUnfollowForm(FlaskForm):
    submit = SubmitField('Submit')

class PostForm(FlaskForm):
    body = TextAreaField('Write something here', validators=[DataRequired(), Length(min=1, max=140)])
    submit = SubmitField('Post')

class ResetPasswordRequestForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Submit')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Submit')

class EmailVerification(FlaskForm):
    otp = IntegerField('OTP', validators=[DataRequired()])
    submit = SubmitField('Verify')