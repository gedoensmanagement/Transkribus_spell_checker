# -*- coding: utf-8 -*-
"""
Created on Thu Nov 19 09:56:38 2020

@author: muellerM@ieg-mainz.de
"""

from flask import Blueprint, session, render_template, url_for, flash, redirect, request, jsonify, json, current_app, send_from_directory
from flask_login import login_required, current_user
from .. import db
from ..models import Censorship, Censoredword, User
import sys

comparer_bp = Blueprint('comparer', __name__)

@comparer_bp.route("/comparer", methods = ["GET"])
@login_required
def comparer():
    file1 = request.args.get('file1')
    file2 = request.args.get('file2')
    return render_template('comparer3.html', files=[file1, file2], user=current_user.id)

censorship_bp = Blueprint('censorship', __name__)

@censorship_bp.route("/censorship", methods = ["GET"])
@login_required
def get_censorships():
    """ returns a list of all censorships in the database or 
        starts to search them with a given filter """
    
    cts = request.args.get('cts')
    source = request.args.get('source')
    print("DEBUG cts =", cts, "source =", source)
    
    if cts: # it's a search request!
        if source:
            matches = Censorship.query.filter(Censorship.cts.startswith(cts), 
                                              Censorship.source == source)
        else:
            matches = Censorship.query.filter_by(cts = cts).all()
        if matches:
            output = []
            for c in matches:
                censorship = {'uuid': c.uuid, 
                              'cts': c.cts,
                              'source': c.source,
                              'target': c.target,
                              'html': c.html,
                              'comment': c.comment,
                              'username': User.query.filter_by(id = c.userid).first().username,}
                output.append(censorship)
            return jsonify(output), 200
        else:
            return f"no matches for {cts}", 404
    
    # ELSE: it's not a search request: return all censorships
    censorships = Censorship.query.all()
    output = []
    for c in censorships:
        censorship = {'uuid': c.uuid, 
                      'cts': c.cts,
                      'source': c.source,
                      'target': c.target,
                      'html': c.html,
                      'comment': c.comment,
                      'username': User.query.filter_by(id = c.userid).first().username,}
        output.append(censorship)
    
    return jsonify(output), 200

@censorship_bp.route("/censorship", methods = ["POST"])
@login_required
def add_censorship():
    """ POST = add new censorship: Eats JSON as payload containing censorship 
        object and a list of censored_words objects. """

    new_censorship = request.get_json()['censorship']
    new_censoredwords = request.get_json()['censoredWords']
    
    try:
        new_censorship = Censorship(userid = current_user.id,
                                    cts = new_censorship['cts'],
                                    source = new_censorship['source'],
                                    target = new_censorship['target'],
                                    html = new_censorship['html'],
                                    comment = new_censorship['comment'],
                                    uuid = new_censorship['uuid'])
        
        db.session.add(new_censorship)

        db.session.commit()

        for word in new_censoredwords:
            new_censoredword = Censoredword(cts = word['cts'],
                                            type = word['type'],
                                            parent = word['parent'],
                                            reference = word['reference'],
                                            )
            db.session.add(new_censoredword)
    
        db.session.commit()

        return jsonify({'message': 'Censorship saved successfully!'}), 200
    
    except:
        print(f'ERROR: Could not write new censorship to database. ({sys.exc_info()[0]})')
        return jsonify({'message': 'ERROR: Could not write to database.'}), 500
    
        
@censorship_bp.route("/censorship/<string:uuid>", methods = ["GET"])
@login_required
def get_censored_words(uuid):
    """ GET: returns all censored words belonging to the censorship with the provided uuid """
    censoredWords = Censoredword.query.filter_by(parent=uuid).all()
    if not censoredWords:
        return "uuid not found", 404
    output = []
    for cw in censoredWords:
        censoredword = {'cts': cw.cts,
                        'type': cw.type,
                        'parent': cw.parent,
                        'reference': cw.reference}
        output.append(censoredword)
    
    return jsonify(output), 200
        
@censorship_bp.route("/censorship/<string:uuid>", methods = ["DELETE"])
@login_required
def delete_censorship(uuid):
    """ DELETE: deletes the censorship with the given uuid from the database """
    delete_candidate = Censorship.query.filter_by(uuid=uuid).first()
    if not delete_candidate:
        return "uuid not found", 404
    censoredWords = Censoredword.query.filter_by(parent=uuid).all()
    if not censoredWords:
        return "no censored words related to this uuid", 500

    for cw in censoredWords:
        db.session.delete(cw)
    db.session.commit()

    db.session.delete(delete_candidate)
    db.session.commit()

    return {'uuid': uuid}, 200
        
