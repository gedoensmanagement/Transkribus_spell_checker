#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Endpoints for the communication of the server with the client's dictionary.html/dictionary.js.
Provides database operations to manage the user dictionary and the list of printer's errors.

Created on Wed May 20 17:19:00 2020

@author: muellerM@ieg-mainz.de
"""

from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify, json, session, current_app
from flask_login import login_required, current_user
from .. import db
from ..models import User, Dictionary, PrintersError
import csv
import requests

# Functions for loading data from the database and Google Spreadsheets:
#######################################################################
def load_printers_errors():
    """ Load the printer's errors from the database. """
    try:
        all_printerserrors = PrintersError.query.all()
        printerserrors = {}
        for error in all_printerserrors:
            printerserrors[error.pattern] = {'correction': error.replacement}
        return printerserrors
    except:
        return False

def load_user_dictionary():
    """ Update SymSpell with the entries from the user dictionary. """
    user_dictionary = Dictionary.query.all()
    additions = 0
    deletions = 0
    errors = 0
    for entry in user_dictionary:
        if entry.action == "add":
            # Add to SymSpell:
            if current_app.dictionary.sym_spell.create_dictionary_entry(entry.word, entry.count):
                #print(f'USER-DICTIONARY: added "{entry.word}" as a new word to SymSpell.')
                pass
            else:
                #print(f'USER-DICTIONARY: added (below threshold) or updated "{entry.word}" in SymSpell.')
                pass
            additions += 1
        elif entry.action == "del":
            # Delete from SymSpell:
            if current_app.dictionary.sym_spell.delete_dictionary_entry(entry.word):
                #print(f'USER-DICTIONARY: "{entry.action}" "{entry.word}" from SymSpell.')
                deletions += 1
            else:
                current_app.logger.info(f'USER-DICTIONARY: ERROR: could not delete "{entry.word}": not found.')
                errors += 1
    current_app.logger.info(f'USER-DICTIONARY: Added/updated {additions}, deleted {deletions} words to/from SymSpell.')
    if errors > 0:
        current_app.logger.info(f'USER-DICTIONARY: There were {errors} errors.')

    return True

def import_from_google(source):
    """ To import data from Google Sheets, provide a source:
            'Dictionary' or 'PrintersErrors'
        
        The URLs for Google Sheets are stored in config.py:
            url = current_app.config['DICTIONARY']
        and
            url = urrent_app.config['PRINTERS_ERRORS'] """

    if source == 'Dictionary':
        url = current_app.config['DICTIONARY']
    elif source == 'PrintersErrors':
        url = current_app.config['PRINTERS_ERRORS']

    current_app.logger.debug(f"DICTIONARY: url\n{url}")

    try: 
        r = requests.get(url)
        
        lines = r.content.decode().splitlines()
        
        current_app.logger.debug(f"DICTIONARY: csv\n{lines}")
        csv_reader = csv.reader(lines)
        
        additions = 0
        skipped = 0
        
        for idx, row in enumerate(csv_reader):
            if idx == 0:
                fieldnames = row # Split only the first line#
            else:
                if not row[0].startswith("#"):   # skips comments
                    key = row[0]
                    value = row[1]
    
                    # Treat every target table differently:        
                        
                    # Add to user dictionary in our database:
                    if source == "Dictionary":
                        if Dictionary.query.filter_by(word=key).first():
                            skipped += 1
                            current_app.logger.info(f"DICTIONARY: Skipping '{key}': already in dictionary")
                        else:
                            new_word = Dictionary(word=key, 
                                                  count=10, 
                                                  action="add",
                                                  userid=current_user.id,
                                                  cts="tr:GoogleSheets:Dictionary")
                            db.session.add(new_word)
                            db.session.commit()
            
                            # Add to symspell:
                            current_app.dictionary.sym_spell.create_dictionary_entry(new_word.word, new_word.count)
                            
                            additions += 1
                            current_app.logger.info(f"DICTIONARY: added {key}")
    
                    elif source == "PrintersErrors":
                        if PrintersError.query.filter_by(pattern=key).first():
                            skipped += 1
                            current_app.logger.info(f"PRINTERS_ERROR: Skipping '{key}': already in the list of printer's errors")
                        else:
                            new_pattern = PrintersError(pattern=key, 
                                                        replacement=value, 
                                                        userid=current_user.id,
                                                        cts="tr:GoogleSheets:PrintersErrors")
                            db.session.add(new_pattern)
                            db.session.commit()
                            
                            additions += 1
                            current_app.logger.info(f"PRINTERS_ERROR: added {key} → {value}")
                
            if source == "PrintersErrors":
                cleaner = current_app.cleaner
                cleaner.printers_errors = load_printers_errors()

    except: 
        current_app.logger.error(f"DICTIONARY: Could not load Google Sheet from {url}.")

    message = f"IMPORT: Finished import from Google Sheets to {source}:\n{additions} additions, {skipped} skipped."
    current_app.logger.info(message)
    return message


    
# The actual dictionary functionality:   
######################################

dictionary_bp = Blueprint('dictionary', __name__)

@dictionary_bp.route("/dictionary", methods=['GET', 'POST'])
@login_required
def dictionary():
    action = request.args.get('action') # required
    word = request.args.get('word') # optional
    cts = request.args.get('cts')   # optional

    if request.method == "GET":
        
        # Return an EDITABLE VIEW of the user dictionary
        if action == 'edit':
            all_words = Dictionary.query.all()
            words = []
            for word in all_words:
                words.append({'id': word.id,
                              'word': word.word,
                              'count': word.count,
                              'timestamp': word.timestamp.astimezone().isoformat(timespec='seconds'), #strftime("%Y-%m-%d, %H:%M:%S", gmtime()),
                              'user': User.query.filter_by(id=word.userid).first().username,
                              'cts': word.cts,
                              'action': word.action,                    
                              'comment': word.comment})

            all_printerserrors = PrintersError.query.all()
            printerserrors = []
            for error in all_printerserrors:
                printerserrors.append({'id': error.id,
                                       'pattern': error.pattern,
                                       'replacement': error.replacement,
                                       'timestamp': error.timestamp.astimezone().isoformat(timespec='seconds'), #strftime("%Y-%m-%d, %H:%M:%S", gmtime()),
                                       'user': User.query.filter_by(id=error.userid).first().username,
                                       'cts': error.cts,                
                                       'comment': error.comment})


            return render_template('dictionary.html', data=json.dumps({'words': words,
                                                                       'printerserrors': printerserrors}))

        
        # CHECK a word in the dictionary
        elif action == 'check':
            cleaner = current_app.cleaner
            W, wc = cleaner.dictionary.check_word(word)
            symspell = Dictionary.query.filter_by(word=word).first()
            current_app.logger.debug(f"DICTIONARY: Checked for {word}: {W}, {wc}.")
            if word == "":
                return jsonify(success = 'neutral',
                               response = '')                
            elif symspell:
                if symspell.action != "del":
                    return jsonify(success = 'success',
                                   response = '(user dictionary)')
                else:
                    return jsonify(success = 'error',
                                   response = 'not found (deleted by user)')
            elif W:
                return jsonify(success = 'success',
                               response = f'(word count = {wc})')
            elif cleaner.whitaker.check(word):
                return jsonify(success = 'success',
                               response = "(Whitaker's Words)")               
            else:
                return jsonify(success = 'error',
                               response = 'not found')

            
            #return render_template('dictionary.html', word=word, colId=colId, docId=docId, pageNr=pageNr)
        
        # RELOAD replacement TABLES
        elif action == 'reloadtables':
            cleaner = current_app.cleaner
            if cleaner.reload_tables():
                return jsonify(success = 'success',
                               response = 'Reloaded successufully from Google Docs.')
            else:
                return jsonify(success = 'error',
                               response = 'ERROR loading a table from Google Docs.')
            
        elif action == 'importfromgoogle':
            source = request.args.get('source')
            current_app.logger.debug("DICTIONARY: importing from source {source}")
            message = import_from_google(source)
            return jsonify(success = 'success',
                           response = message)        
        
    if request.method == "POST":
        if action == "add":
            word = request.get_json(force=True)['word']
            if Dictionary.query.filter_by(word=word).first():
                current_app.logger.error(f"DICTIONARY: Could not add {word}")
                return jsonify(success = 'error',
                               response = f'"{word}" already in dictionary')
            else:
                # Add to user dictionary in our database:
                new_word = Dictionary(word=word, 
                                      count=10, 
                                      action="add",
                                      userid=current_user.id,
                                      cts=cts)
                db.session.add(new_word)
                db.session.commit()

                # Add to symspell:
                current_app.dictionary.sym_spell.create_dictionary_entry(new_word.word, new_word.count)
                
                current_app.logger.info(f"DICTIONARY: added {new_word}")
                return jsonify(success = 'success',
                               response = f'"{word}" added')
            
        elif action == "delete":
            wordId = request.get_json(force=True)['id']
            delete_candidate = Dictionary.query.filter_by(id=wordId).first()
            if delete_candidate:
                # Delete from user dictionary in our database:
                word = delete_candidate.word
                db.session.delete(delete_candidate)
                db.session.commit()
                # Delete from symspell:
                current_app.dictionary.sym_spell.delete_dictionary_entry(word)
                return jsonify(success="success",
                               response=f"Deleted {word} from user dictionary successfully.")
            else:
                return jsonify(success="error",
                               response="ERROR: Could not delete this word.")

        elif action == "deleteFromSymSpell":
            # Delete from symspell:
            cleaner = current_app.cleaner
            delete_candidate = request.get_json(force=True)['word']
            W, wc = cleaner.dictionary.check_word(delete_candidate)
            if W:
                # Add to user dictionary in our database:
                new_word = Dictionary(word=delete_candidate, 
                                      count=0, 
                                      action="del",
                                      userid=current_user.id,
                                      cts="tr:user:deletion")
                db.session.add(new_word)
                db.session.commit()

                current_app.dictionary.sym_spell.delete_dictionary_entry(delete_candidate)
                return jsonify(success="success",
                               response=f"Deleted {delete_candidate} from SymSpell successfully.")
            else:
                return jsonify(success="error",
                               response=f"ERROR: Could not delete {delete_candidate}.")

        elif action == "addPrintersError":
            pattern = request.get_json(force=True)['pattern']
            replacement = request.get_json(force=True)['replacement']
            if PrintersError.query.filter_by(pattern=pattern).first():
                current_app.logger.error(f"DICTIONARY: Could not add {pattern}")
                return jsonify(success = 'error',
                               response = f'{pattern} already in the list of printers errors.')
            else:
                # Add to printer's errors in our database:
                new_word = PrintersError(pattern=pattern, 
                                         replacement=replacement, 
                                         userid=current_user.id,
                                         cts=cts)
                db.session.add(new_word)
                db.session.commit()
                current_app.logger.info(f"PRINTER's ERRORS: added {new_word}")
                
                cleaner = current_app.cleaner
                cleaner.printers_errors = load_printers_errors()
                
                return jsonify(success = 'success',
                               response = f'{pattern} → {replacement} added successfully.')
            
        elif action == "deletePrintersError":
            patternId = request.get_json(force=True)['id']
            delete_candidate = PrintersError.query.filter_by(id=patternId).first()
            if delete_candidate:
                # Delete from user dictionary in our database:
                pattern = delete_candidate.pattern
                db.session.delete(delete_candidate)
                db.session.commit()

                cleaner = current_app.cleaner
                cleaner.printers_errors = load_printers_errors()

                return jsonify(success="success",
                               response=f"Deleted {pattern} from the list of printer's errors successfully.")
            else:
                return jsonify(success="error",
                               response="ERROR: Could not delete this pattern.")  
            
        # TODO: Write a function to back up the printer's errors and the user's dictionary, e.g. by exporting to a file or Google spreadsheet!
        elif action == "backupPrintersErrors":
            pass

    #return render_template('dictionary.html', data=data)