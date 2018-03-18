from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField
from wtforms.validators import Required


class LoginForm(FlaskForm):
    name = StringField('username', validators=[Required()])
    password = PasswordField('password', validators=[Required()])
    remember_me = BooleanField('remember me')
    submit = SubmitField('login')


