#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Defines the structure of our database with SQLAlchemy.
Be aware that you have to provide the length of a string when
using SQLAlchemy with a MySQL database like MariaDB. 
JSON datatype is an alias for LONGTEXT in MariaDB (since version
10.2.7).

Created on Mon May 11 15:08:46 2020

@author: muellerM@ieg-mainz.de
"""

from my_app import db, login_manager
from flask_login import UserMixin
from datetime import datetime

@login_manager.user_loader
def load_user(userid):
    return User.query.get(int(userid))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    colcache = db.Column(db.JSON)
    locks = db.relationship('Locker', backref='user', lazy=True)
    #abbreviations = db.relationship('Abbreviation', backref='user', lazy=True)
    #printerserrors = db.relationship('PrintersError', backref='user', lazy=True)
    
    def __repr__(self):
        return f"User('{self.id}', '{self.username}')"

class Locker(db.Model):
    pageid = db.Column(db.String(30), primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, 
                          default=datetime.utcnow)
    userid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Locker('{self.pageid}', '{self.userid}', '{self.timestamp}')"

class Dictionary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(40), nullable=False)
    count = db.Column(db.Integer, nullable=False, default=10)
    timestamp = db.Column(db.DateTime, nullable=False, 
                          default=datetime.utcnow)
    userid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cts = db.Column(db.String(30)) # Canonical Text Service address, CTSNAMESPACE = tr (= transkribus)
    action = db.Column(db.String(15)) # "add", "delete" or "modify"
    flag = db.Column(db.String(15)) # status etc.
    comment = db.Column(db.String(160))

    def __repr__(self):
        return f"Dictionary('{self.id}', '{self.word}', count='{self.count}', cts='{self.cts}', '{self.comment}')"

class PrintersError(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, 
                          default=datetime.utcnow)
    userid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cts = db.Column(db.String(30)) # Canonical Text Service address, CTSNAMESPACE = tr (= transkribus)
    pattern = db.Column(db.String(30), nullable=False)
    replacement = db.Column(db.String(40), nullable=False)

    comment = db.Column(db.String(160))

    def __repr__(self):
        return f"PrintersError('{self.id}', '{self.pattern}' → '{self.replacement}', cts='{self.cts}', '{self.comment}')"

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, 
                          default=datetime.utcnow)
    userid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    comment = db.Column(db.Text(2048), nullable=False)
    cts = db.Column(db.String(30)) # Canonical Text Service address, CTSNAMESPACE = tr (= transkribus)
    flag = db.Column(db.String(15)) # status etc.

    tagid = db.Column(db.Integer, db.ForeignKey('tag.id'))

    def __repr__(self):
        return f"Comment('{self.id}', '{self.comment}', '{self.cts}')"

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, 
                          default=datetime.utcnow)
    userid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    tag = db.Column(db.String(144), nullable=False)

    def __repr__(self):
        return f"Tag('{self.id}', '{self.tag}')"

class Censorship(db.Model):
    """ complete data of a registered censorship (source, target, html, comment, userid, uuid) """
    uuid = db.Column(db.String(32), primary_key=True)
    cts = db.Column(db.String(128), nullable=False)
    source = db.Column(db.String(56))
    target = db.Column(db.String(56))
    html = db.Column(db.Text(65000)) # a whole page needs ca. 37,000 characters, max length of this field type in MariaDB is 65,535 ( 2^16 - 1 )
    comment = db.Column(db.Text(2048))
    userid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    #censored_words = db.relationship('Censoredword', backref='censorship', lazy=True)

class Censoredword(db.Model):
    """ A single word that is part of a censorship """
    id = db.Column(db.Integer, primary_key=True)
    cts = db.Column(db.String(128), nullable=False)
    type = db.Column(db.String(6))
    parent = db.Column(db.String(32), db.ForeignKey('censorship.uuid'), nullable=False)
    reference = db.Column(db.String(128))