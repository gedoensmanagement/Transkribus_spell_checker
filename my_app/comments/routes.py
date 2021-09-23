#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Endpoint for requesting comments. Still experimental.

Created on Mon Nov 23 11:08:03 2020

@author: muellerM@ieg-mainz.de
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from .. import db
from ..models import Comment, Tag, User

comments_bp = Blueprint('comments', __name__)

@comments_bp.route("/comments", methods = ["GET"])
@login_required
def get_comments():
    """ returns a list of all comments in the database or 
        starts to search them with a given filter """

    cts = request.args.get('search')
    
    if cts: # it's a search request! 
        # TODO: Implement search functionality for comments!!
        pass
    
    # ELSE: it's not a search request: return all comments
    comments = Comment.query.all()
    output = []
    for c in comments:
        comment = {'id': c.id,
                   'timestamp': c.timestamp.strftime('%Y-%m-%dT%H-%M-%S'),
                   'username': User.query.filter_by(id = c.userid).first().username,
                   'comment': c.comment,
                   'cts': c.cts,
                   'flag': c.flag,
                   'tagid': c.tagid}
        output.append(comment)
    
    return jsonify(output), 200