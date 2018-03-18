from flask import render_template, session, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from . import user
from .forms import LoginForm
from ..models import User


# 保护路由，未经授权的用户访问该路由会转到登陆页面
@user.route('/secret')
@login_required
def secret():
    return 'Only authenticated users are allowed!'


@user.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user_login = User.query.filter_by(name=form.name.data).first()
        if user_login is not None and user_login.verify_password(form.password.data):
            login_user(user_login, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('main.index'))
    if request.method == 'POST':
        flash('Invalid username or password.')
    return render_template('user/login.html', form=form)


@user.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))
