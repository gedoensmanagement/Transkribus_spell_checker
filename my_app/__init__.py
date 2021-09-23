#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" This code is called by run.py after you say 'flask run'.
    Here, we create Flask's 'app' object which contains the core functionality of
    the whole app. """
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
#from flask_script import Manager
from flask_migrate import Migrate#, MigrateCommand
from flask_login import LoginManager

# Pymysql is a fix to avoid the "No module named 'MySQLdb'" error when 
# SQLAlchemy tries to connect to a MySQL database (this happens in production
# when we don't use sqlite3 anymore)
import pymysql
pymysql.install_as_MySQLdb()

# Create the database engine with SQLAlchemy and migrate
db = SQLAlchemy()
migrate = Migrate(compare_type=True)

# Initialize the Flask's login manager:
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'error'

""" WITHOUT FLASK-MIGRATE you can create the database by starting a 
    Python cli within the my_app directory and enter:
        from my_app import db
        from my_app.models import User, Locker
        db.create_all() 
    There should be a 'site.db' in the 'instance' folder now. 
    
    USING FLASK-MIGRATE you export all necessary environment variables
    (FLASK_ENV and FLASK_APP) and then –not having a database or a "migrations" folder yet–
    you say:
        db init    → creates a 'migrations' folder (Flask migrate will store its database here).
        db migrate → detects changes relative to the existing database (at first run there is no database yet).
        db upgrade → applies all the changes detected in the previous step. """


def create_app(test_config=None):
    """ This is the factory that produces the Flask 'app' and 'db'
        object which are the core of the whole app. """

    # Create a Flask 'app' object:
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        # Define the default configuration (can be overwritten by config.py file in production mode)
        SQLALCHEMY_DATABASE_URI='sqlite:///'+os.path.join(app.instance_path, 'site.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS = False,
        DICTIONARY_PATH=os.path.join(app.root_path, "dictionaries"),
        CACHE_PATH=os.path.join(app.static_folder, "cache"),
        )
    if os.environ.get("FLASK_ENV") == "development":
        # Load the test/development configuration
        app.config.from_pyfile('test-config.py')
    else:
        # We are in production mode! Load ./instance/config.py and overwrite the default configuration:
        app.config.from_pyfile('config.py')
        
    # ensure the instance folder exists otherwise create it:
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Run the initialization commands:
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Import the blueprints from their modules and register them in the app:
    from .auth.routes import users
    from .browser.routes import browser_bp, cts_bp
    from .editor.routes import editor_bp
    from .dictionary.routes import dictionary_bp
    from .exporter.routes import exporter_bp, downloader_bp, viewer_bp
    from .analyzer.routes import compare_bp
    from .comparer.routes import comparer_bp, censorship_bp
    from .comments.routes import comments_bp
    app.register_blueprint(users)
    app.register_blueprint(browser_bp)
    app.register_blueprint(cts_bp)
    app.register_blueprint(editor_bp)
    app.register_blueprint(dictionary_bp)
    app.register_blueprint(exporter_bp)
    app.register_blueprint(downloader_bp)
    app.register_blueprint(viewer_bp)
    app.register_blueprint(compare_bp)
    app.register_blueprint(censorship_bp)
    app.register_blueprint(comparer_bp)
    app.register_blueprint(comments_bp)
    
    with app.app_context():
        # Initialize the building blocks for the cleaner
        # (i.e. SymSpell dictionary, Whitaker's Words dictionary, printer's errors)
        
        app.logger.info("FLASK: Initialize SymSpell")
        from .nlp.latin_dictionary import Dictionary
        from .dictionary.routes import load_printers_errors, load_user_dictionary
        app.dictionary = Dictionary(app.config['DICTIONARY_PATH'])
        # Read the user's additions and deletions from the database and apply them to the dictionary:
        load_user_dictionary()

        app.logger.info("FLASK: Initialize Cleaner and the secondary dictionary")
        from .nlp.cleaner import Cleaner
        #from .nlp.whitakers_words import Whitakers_Words
        from .nlp.hunspell import Hunspell_Dictionary
        app.whitaker = Hunspell_Dictionary(dictionary_path=app.config['DICTIONARY_PATH'])
        #app.whitaker = Whitakers_Words(app.config['DICTIONARY_PATH'])
        app.cleaner = Cleaner(replacement_table_url = app.config['ABBREVIATIONS'],
                              printers_errors_url = app.config['PRINTERS_ERRORS'],
                              printers_errors = load_printers_errors())

    
    return app

app = create_app()

