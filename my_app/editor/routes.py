#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Endpoints for the communication between the server and the editor.html/editor.js 
which provide a user interface to proof read Transkribus transcriptions. 

Created on Tue May 12 16:53:53 2020

@author: muellerM@ieg-mainz.de
"""

import re
import datetime
from lxml import etree as ET
from lxml import objectify
from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify, json, session, current_app
from flask_login import login_required, current_user
from .. import db
from ..models import User, Locker, Comment
from ..io.web import Transkribus_Web
from ..io.tools import IO_Tools
from pathlib import Path

editor_bp = Blueprint('editor', __name__)

def lock_page(colId, docId, pageNr):
    """ Set a page as 'locked' by a user if the page is not 
        locked by somebody else. """

    # Guests cannot lock pages:
    if current_user.id == 2:
        return True
    
    # Everybody else can lock pages:
    pageId = f"{colId}-{docId}-{pageNr}"

    if not Locker.query.filter_by(pageid = pageId).first():
        timestamp = datetime.datetime.now(datetime.timezone.utc).astimezone() #.astimezone().isoformat(timespec="milliseconds")
        lock = Locker(pageid = pageId, 
                      timestamp = timestamp,
                      userid = current_user.id)
        db.session.add(lock)
        db.session.commit()
        current_app.logger.info(f"LOCKER: Access to page {colId}-{docId}-{pageNr} GRANTED for {current_user} at {timestamp}")
        return True
    elif Locker.query.filter_by(pageid = pageId).first().userid == current_user.id:
        current_app.logger.info(f"LOCKER: Access to page {colId}-{docId}-{pageNr} has already been GRANTED for {current_user}")
        return True
    elif Locker.query.filter_by(pageid = pageId).first().userid == current_user.id:
        difference = datetime.datetime.now() - Locker.query.filter_by(pageid = pageId).first().timestamp
        if difference > datetime.timedelta(minutes=120):
            # If the page is locked for more than 120 minutes: Delete the lock
            # and re-lock the page for the current user:
            deleted = Locker.query.filter_by(pageid = pageId).delete()
            
            timestamp = datetime.datetime.now(datetime.timezone.utc).astimezone() #.astimezone().isoformat(timespec="milliseconds")
            lock = Locker(pageid = pageId, 
                          timestamp = timestamp,
                          userid = current_user.id)
            db.session.add(lock)
            db.session.commit()
            current_app.logger.info(f"LOCKER: Access to page {colId}-{docId}-{pageNr} GRANTED for {current_user} after deleting old locker entry {deleted}.")
            
            return True
    else:
        current_app.logger.info(f"LOCKER: Access to page {colId}-{docId}-{pageNr} DENIED for {current_user}")
        return False

def unlock_page(colId, docId, pageNr):
    """ Remove the lock from a page. """

    # Guests cannot unlock pages:
    if current_user.id == 2:
        return True
    
    # Everybody else can unlock pages:
    pageId = f"{colId}-{docId}-{pageNr}"
    if Locker.query.filter_by(pageid = pageId, 
                              userid = current_user.id).first():
        deleted = Locker.query.filter_by(pageid = pageId, 
                               userid = current_user.id).delete()
        current_app.logger.debug(f"LOCKER: Deleted locker entry: {deleted}")
        db.session.commit()
        current_app.logger.info(f"UNLOCKED page {colId}-{docId}-{pageNr} for {current_user}")
        return True
    else:
        current_app.logger.info(f"COULD NOT UNLOCK page {colId}-{docId}-{pageNr} for {current_user}")
        return False

def clean_check(colId, docId, pageNr):
    """ Cleans and spellchecks a page. """
    TR = Transkribus_Web(session['JSESSIONID'])
    TR.cols = json.loads(current_user.colcache)
    
    cleaner = current_app.cleaner
    
    current_app.logger.info("EDITOR: cleaning...")
    TR = cleaner.clean_page(TR, colId, docId, pageNr)
    
    current_app.logger.info("EDITOR: spellchecking...")
    TR = cleaner.spellcheck_page(TR, colId, docId, pageNr)
    
    current_user.colcache = str(json.dumps(TR.cols))
    db.session.commit()
    
    current_user.colcache = str(json.dumps(TR.cols))
    
    return TR

def build(colId, docId, pageNr):
    """ Reconstructs the TR object from cache and 
        extracts some data (thispage). """
    TR = Transkribus_Web(session['JSESSIONID'])
    TR.cols = json.loads(current_user.colcache)
    
    current_app.logger.info("EDITOR: building page object...")
    page = TR.cols[colId]['docs'][docId]['pages'][pageNr]
    thispage = {'colId': colId, 'colName': TR.cols[colId]['colName'],
                'docId': docId, 'title': TR.cols[colId]['docs'][docId]['title'],
                'pageNr': pageNr, 'status': page['status'],
                'pageId': page['pageId'], 'tsid': page['tsid'],
                'lastUser': page['lastUser'], 
                'lastTimestamp': datetime.datetime.fromtimestamp(page['lastTimestamp']/1000).strftime('%Y-%m-%d %H:%M:%S'),
                'imgUrl': page['imgUrl'],
                'next': page['next'],
                'previous': page['previous'],
                }
    if 'regions' in page:
        thispage['regions'] = page['regions']
        thispage['imageHeight'] = page['imageHeight']
        thispage['imageWidth'] = page['imageWidth']

    return json.dumps(thispage)

def dump(colId, docId, pageNr, status):
    """ Dump a json copy of this page on disk if status is "GT" or "FINAL". """
    BIBTEX_PATTERN = re.compile(r'(\w*\d\d\d\d\w?)-')
    TR = Transkribus_Web(session['JSESSIONID'])
    TR.cols = json.loads(current_user.colcache)
    if status == "GT" or status == "FINAL":
        current_app.logger.info("EDITOR: Storing page data on local disk...")
        # Make a folder path "colId/docId/pageNr/" and create it if it doesn't exist:
        dumping_path = Path(current_app.config["CACHE_PATH"], colId, docId, pageNr)
        dumping_path.mkdir(parents=True, exist_ok=True)
        bibtex = re.findall(BIBTEX_PATTERN, TR.cols[colId]['docs'][docId]['title'])
        if bibtex:
            bibkey = bibtex[0].lower()
            # Make a file name and write json to this file:
            filename = f"{bibkey},trp_{int(pageNr):04}.json"
        else:
            filename = f"{colId},{docId},{int(pageNr):04}.json"
        dumping_file = Path(dumping_path, filename)
        jsondata = json.loads(str(build(colId, docId, pageNr)))
        jsondata['status'] = status
        pagedata = str(json.dumps(jsondata, indent=2))
        try:
            with open(dumping_file, 'w', encoding='utf-8') as outfile:
                outfile.write(pagedata)
            current_app.logger.info(f"EDITOR: {dumping_file} successfully written.")
            return True
        except:
            flash("ERROR writing page data to local disk!")
            current_app.logger.error(f"EDITOR: ERROR writing page data to local disk! ({dumping_file})")
            return False
    else:
        return "wrong_status"

@editor_bp.route("/editor", methods=['GET', 'POST'])
@login_required
def editor():
    """ Main endpoint to communicate with the editor.html/editor.js in the client's browser. 
        The client sends a request containing the following arguments in the URL. 
        The 'action' argument says what the server should do. """
    colId = request.args.get('colId')   # required
    docId = request.args.get('docId')   # required
    pageNr = request.args.get('pageNr') # required
    action = request.args.get('action') # required
    oldPageNr = request.args.get('oldPageNr') # optional
    
    TR = Transkribus_Web(session['JSESSIONID'])
    TR.cols = json.loads(current_user.colcache)
    
    def getComments():
        """ Load and return the comments for a specific page: """
        comments = Comment.query.filter((Comment.cts.startswith(f"tr:{colId}.{docId}:{pageNr}:")) | (Comment.cts.startswith(f"tr:{colId}.{docId}:{pageNr}."))).all()
        commentData = []
        for comment in comments:
            commentData.append({'id': comment.id,
                                'comment': comment.comment,
                                'user': User.query.filter_by(id=comment.userid).first().username,
                                'timestamp': comment.timestamp.astimezone().isoformat(timespec='seconds'),
                                'cts': comment.cts})
        return commentData
    
    """ Handle the 'action' argument of the requests sent by the client: """
    if request.method == 'GET':
        # (RE)LOAD the page from the Transkribus server
        if action == 'open' and lock_page(colId, docId, pageNr):
            if oldPageNr:
                unlock_page(colId, docId, oldPageNr)
            
            if TR.get_page_xml(colId, docId, pageNr):
                current_user.colcache = str(json.dumps(TR.cols))
                db.session.commit()
            else:
                flash(f"Couldn't get XML data for page {pageNr}.")
            if TR.unpack_page(colId, docId, pageNr):
                current_user.colcache = str(json.dumps(TR.cols))
                db.session.commit()
                
                clean_check(colId, docId, pageNr)
            else:
                flash(f'There is one of the following problems on page {pageNr}:<ul></li><li>no TextRegion named "paragraph" → Add one!</li><li>not all TextRegions are assigned a structure type → Add structure types!</li><li>missing Text Regions → Add them!</li><li>no text in lines → Transcribe the page or run OCR!</li></ul>', 'error')
            
            # CLEAN and CHECK the page        
            thispage = build(colId, docId, pageNr)
            
            return render_template('editor.html', thispage=thispage, comments=getComments())

        # CLOSE the page
        elif action == 'close':
            unlock_page(colId, docId, pageNr)
            return redirect(url_for('browser.browser'))
        
    elif request.method == 'POST':
        
        # CLEAN and SPELLCHECK the page
        if action == 'check':
            current_app.logger.info(f"EDITOR: Clean and check page {pageNr}")
            page = request.get_json(force=True)
            TR.cols[colId]['docs'][docId]['pages'][pageNr]['regions'] = page['regions']
            current_user.colcache = str(json.dumps(TR.cols))
            clean_check(colId, docId, pageNr)
            TR.cols = json.loads(current_user.colcache)
            page['regions'] = TR.cols[colId]['docs'][docId]['pages'][pageNr]['regions']

            return jsonify(page)
        
        # SAVE to the Transkribus server
        elif action == 'save':
            current_app.logger.info(f"EDITOR: Saving page {pageNr}...")
            # Get and store the data from the POST request:
            new_page = request.get_json()
            thispage = TR.cols[colId]['docs'][docId]['pages'][pageNr]
            thispage['status'] = new_page['status']
            
            # Iterate through the lines and replace the old raw_text with the new one:
            xml = objectify.fromstring(bytes(thispage['xml'], 'utf-8'))
            regionId = 0
            for region in xml.Page.TextRegion:
                regionAttributes = IO_Tools._customAttributes(region.attrib['custom'])
                if bool(re.match("paragraph", regionAttributes['structure']['type'])):            
                    for lineId, line in enumerate(region.TextLine):
                        line.TextEquiv.Unicode = new_page['regions'][regionId]['lines'][lineId]['raw_data']
                        current_app.logger.debug(f"EDITOR: Wrote line '{line.TextEquiv.Unicode}'")
                    regionId += 1

            # Get metadata for upload:
            status = thispage['status']
            # Convert modified pageXML to string:
            new_xml = ET.tostring(xml, pretty_print=True, xml_declaration=True, encoding="UTF-8")
            
            # ==============================================
            # Upload it to the Transkribus server together with required metadata:
            current_app.logger.info("EDITOR: Page {pageNr} successfully uploaded to Transkribus")
            success, response = TR.upload_page(colId, docId, pageNr, 
                                               status = status, 
                                               xml = new_xml,
                                               session_id = session['JSESSIONID'])
            if not success:
                flash(f"ERROR uploading page {pageNr} to Transkribus!")
                current_app.logger.error(f"EDITOR: ERROR uploading page {pageNr} to Transkribus!")
                
            # Dump a copy of the json on disk if status is "GT" or "FINAL":
            dump(colId, docId, pageNr, status)
            
            return jsonify(success = success, 
                           response = response)
 
        # Dump a copy of the page on disk as a json file:
        elif action == "dump":
            status = request.get_json()
            dumped = dump(colId, docId, pageNr, status['status'])
            if  dumped == True:
                success = "success"
                response = f"Page {pageNr} successfully saved on disk as a JSON file."
            elif dumped == "wrong_status":
                success = "error"
                response = f"ERROR: Export failed: The status of page {pageNr} is neither FINAL nor GROUND TRUTH."
            else:
                success = "error"
                response = f"ERROR: Export failed while saving page {pageNr} as a JSON file."

            return jsonify(success = success, 
                           response = response)
        
        # Add a comment to a specific word (identified by a cts URN)
        elif action == "addComment":
            comment = request.get_json(force=True)['comment']
            cts = request.get_json(force=True)['cts']
            try:
                new_comment = Comment(userid = current_user.id,
                                      comment = comment,
                                      cts = cts)
                db.session.add(new_comment)
                db.session.commit()
                success = 'success'
                response = f'Comment successfully added:\n"{comment}"'
                comments = getComments()
            except:
                success = 'error'
                response = f'ERROR: Could not add the comment!\n(cts: {cts})'
                comments = getComments()
                
            return jsonify(success = success, 
                           response = response,
                           comments = comments)
            
        # Delete a comment to a specific word (identified by a cts URN)
        elif action == "deleteComment":
            commentId = request.get_json(force=True)['commentId']
            delete_candidate = Comment.query.filter_by(id=commentId).first()
            if delete_candidate:
                response = f"Comment deleted successfully.\n({delete_candidate.comment})."
                db.session.delete(delete_candidate)
                db.session.commit()
                success = "success"
                comments = getComments()
            else:
                success = "error"
                response = f"ERROR: Could not delete the comment!"
                comments = getComments()
            
            return jsonify(success = success, 
                           response = response,
                           comments = comments)       