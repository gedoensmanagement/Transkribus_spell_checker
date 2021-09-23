#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A rudimentary user management: Users can register with their Transkribus credentials.
Having registered they can log in and log out using the flask_login module. 

Created on Tue May 12 16:33:20 2020

@author: muellerM@ieg-mainz.de
"""

from flask import (Blueprint, render_template, url_for, flash, 
                   redirect, request, session, json)
from flask_login import login_user, current_user, logout_user, login_required
from .. import db
from ..models import User, Locker
from ..auth.forms import RegistrationForm, LoginForm
from ..io.web import Transkribus_Web
from werkzeug.security import check_password_hash, generate_password_hash

users = Blueprint('auth', __name__)

@users.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        
        TR = Transkribus_Web()
        if not TR.verify(form.username.data, form.password.data):
            flash("You cannot register with these credentials.", 'error')
            return redirect(url_for('auth.register'))

        hashed_password = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully.", 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html', title='Register', form=form)

@users.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            TR = Transkribus_Web()
            JSESSIONID = TR.login(form.username.data, form.password.data)
            session['JSESSIONID'] = JSESSIONID
            
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('browser.browser'))
        else:
            flash('Wrong credentials.', 'error')
    return render_template('login.html', title='Login', form=form)

@users.route("/logout")
@login_required
def logout():
    # logout from Transkribus server
    TR = Transkribus_Web(session_id=session['JSESSIONID'])
    if not TR.logout():
        flash("Could not log out from Transkribus.")
    session.pop('JSESSIONID')

    # clear cache
    current_user.colcache = str(json.dumps({}))
    # clear locked pages
    userId = current_user.id
    Locker.query.filter_by(userid=userId).delete()
    db.session.commit()

    # logout from website
    logout_user() 
   
    return redirect(url_for('auth.login'))