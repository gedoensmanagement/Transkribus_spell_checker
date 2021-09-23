#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 13 14:49:41 2020

@author: muellerM@ieg-mainz.de
"""

from flask import Blueprint, session, render_template, url_for, flash, redirect, request, jsonify, json, current_app
from flask_login import login_required, current_user
from pathlib import Path
from .. import db
from ..exporter.routes import getExportedFiles, getDownloadableFiles
from ..io.web import Transkribus_Web
from ..models import Comment
import sys
import re


cts_bp = Blueprint('cts', __name__)

@cts_bp.route("/cts", methods = ['GET'])
@login_required
def cts():
    return "Please specify a protocol: /cts/<protocol> (tr = Transkribus)."

@cts_bp.route("/cts/tr")
def tr():
    TR = Transkribus_Web(session_id=session['JSESSIONID'])
    TR.list_collections()
    current_user.colcache = str(json.dumps(TR.cols))
    db.session.commit()
    return {'tr': {'cols': TR.cols}}, 200

@cts_bp.route("/cts/tr/<string:colId>")
def col(colId):
    TR = Transkribus_Web(session_id=session['JSESSIONID'])
    TR.cols = json.loads(current_user.colcache)
    if TR.list_documents_in_collection(colId):
        current_user.colcache = str(json.dumps(TR.cols))
        db.session.commit()
        return TR.cols[colId], 200
    else:
        return f"Collection {colId} not found.", 404

@cts_bp.route("/cts/tr/<string:colId>/<string:docId>")
def doc(colId, docId):
    TR = Transkribus_Web(session_id=session['JSESSIONID'])
    TR.cols = json.loads(current_user.colcache)
    if TR.list_pages_in_document(colId, docId):
        current_user.colcache = str(json.dumps(TR.cols))
        db.session.commit()
        
        getComments(TR, colId, docId)
        
        return TR.cols[colId]['docs'][docId], 200
    else:
        return f"Document {docId} not found in collection {colId}", 404

@cts_bp.route("/cts/tr/<string:colId>/<string:docId>/<string:pageNr>/edit")
def edit(colId, docId, pageNr):
    """ Redirect to the 'editor' module to open pageNr. """

    # First, check if colId, docId and pageNr are already cached.
    # Load them, if necessary.
    TR = Transkribus_Web(session_id=session['JSESSIONID'])
    TR.cols = json.loads(current_user.colcache)
    if docId not in TR.cols[colId]['docs']:
        TR.list_documents_in_collection(colId)
        current_user.colcache = str(json.dumps(TR.cols))
        db.session.commit()
    if pageNr not in TR.cols[colId]['docs'][docId]['pages']:
        TR.list_pages_in_document(colId, docId)
        current_user.colcache = str(json.dumps(TR.cols))
        db.session.commit()
    
    return redirect(url_for('editor.editor', action="open", colId=colId, docId=docId, pageNr=pageNr))

@cts_bp.route("/cts/resolver", methods=['GET'])
def resolve():
    """ Resolve strings containing a cts URN and (optionally).
        TODO: Let the user define an action that should be executed with the requested text. """
    cts = request.args.get('urn') # required
    #action = request.args.get('action') # optional
    
    cts = re.sub("@.*", "", cts)                     # cut off subreference (wordIdx)
    cts = re.sub("(.*:.*:.*)[\.|:].*", "\g<1>", cts) # cut off region and line reference (old regex: (.*:.*:.*)\..* )
    cts = re.sub("[\.:]", "/", cts)                  # convert to URL path
    
    print("CTS-RESOLVER: Opening", f"/cts/{cts}/edit")
    
    return redirect(cts+"/edit")

    

browser_bp = Blueprint('browser', __name__)

@browser_bp.route("/browser", methods = ['GET'])
@login_required
def browser():
    """ This is the landing page after login. At first visit, it 
        downloads the list of collections from Transkribus. If the 
        user opens a collection or document, the browser will fetch 
        more data using the /cts/tr endpoint. """
    
    TR = Transkribus_Web(session_id=session['JSESSIONID'])
    TR.list_collections()
    current_user.colcache = str(json.dumps(TR.cols))
    db.session.commit()
    
    current_app.logger.info("collections loaded, building list of exported files")
    # Build a dictionary of the available json files in the cache on disk (i.e. pages that have been "dumped" already):
    exportedFiles = getExportedFiles()
    
    current_app.logger.info("building list of downloadable files")
    # Build a list of already exported xml files in the cache on disk:
    downloadableFiles = getDownloadableFiles()

    current_app.logger.info("ready. rendering template")

    return render_template('browser.html', 
                           cols=TR.cols, 
                           exportedFiles=exportedFiles, 
                           downloadableFiles=downloadableFiles, 
                           comparableFiles=[],
                           formats=["TEI for LERA", "TSV for TRACER","CSV for comparison"],
                           pythonversion=sys.version.replace("\n", " "),
                           )


def getComments(TR, colId, docId):
    comments = Comment.query.all()
    for comment in comments:
        cts = explode_cts(comment.cts)
        #print("DEBUG Comments on page", cts['colId'], f"({type(cts['colId'])})", 
        #      cts['docId'], f"({type(cts['docId'])})", 
        #      cts['pageNr'], f"({type(cts['pageNr'])})")
        if cts['colId'] == colId and cts['docId'] == docId:
            TR.cols[cts['colId']]['docs'][cts['docId']]['pages'][cts['pageNr']]['comment'] = 'true'

    return TR

def explode_cts(cts):
    """ Split a cts URI into its parts and return them as a dict. """
    #f"tr:{colId}.{docId}:{pageNr}:{region and line}@wordIdx"
    elements = cts.split(":")    
    protocol = elements[0]
    document = elements[1]
    
    if len(elements) == 4:
        pageNr = elements[2]
        regionLine = elements[3]
    elif len(elements) == 3:
        pageNr, regionLine = elements[2].split(".")
        
    if "@" in regionLine:
        regionLine, wordIdx = regionLine.split("@")
    else:
        wordIdx = ""
    colId, docId = document.split(".")
    return {'protocol': protocol,
            'colId': colId,
            'docId': docId,
            'pageNr': pageNr,
            'regionLine': regionLine,
            'wordIdx': wordIdx}