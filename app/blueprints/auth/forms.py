from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo


class LoginForm(FlaskForm):
    username = StringField("用户名", validators=[DataRequired(), Length(min=2, max=50)])
    password = PasswordField("密码", validators=[DataRequired()])
    submit = SubmitField("登录")


class RegisterForm(FlaskForm):
    username = StringField("用户名", validators=[DataRequired(), Length(min=2, max=50)])
    password = PasswordField("密码", validators=[DataRequired(), Length(min=6, max=64)])
    confirm = PasswordField("确认密码", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("注册")
