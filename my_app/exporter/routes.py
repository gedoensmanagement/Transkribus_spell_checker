# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 10:10:11 2020

@author: muellerm@ieg-mainz.de
"""
from flask import Blueprint, session, render_template, url_for, flash, redirect, request, jsonify, json, current_app, send_from_directory
from flask_login import login_required, current_user
from .. import db
from ..io.web import Transkribus_Web
from pathlib import Path
from lxml import etree as ET
from lxml import objectify
from datetime import datetime
import re

def getDownloadableFiles():
    """ Build a list of already exported xml files in the cache on disk: """
    dumping_path = Path(current_app.config["CACHE_PATH"])   # \Dokumente\Synchronisation\Programmieren\Python\tutorial_flask_wsgi\my_app\static\cache
    response = {}
    filelist = []
    for suffix in ["*.csv", "*.html", "*.tsv", "*.xml", "*.tracker", "*.txt"]:
        newlist = dumping_path.glob(suffix)
        if newlist != []:
            filelist.extend(newlist)
    for idx, file in enumerate(filelist):
        last_changed = re.search(r"\d\d\d\d\-\d\d-\d\dT\d\d-\d\d-\d\d", file.name)[0]
        ending = re.search(r"\.(.{1,4})", file.name).group(1)
        docId = re.search(r",(\d{6}),", file.name)
        if docId:
            docId = docId.group(1)
        else:
            docId = "none"
        response[idx] = {'filename': file.name,
                         'ending': ending,
                         'docId': docId,
                         'lastChanged': last_changed,
                         'links': [{'href': f'/download/{file.name}',
                                    'rel': 'download',
                                    'type': 'GET'}],
                         'self': {'href': f'/download/{file.name}'}}
    
    return response

def getExportedFiles():
    """ Builds a dictionary of the available json files in the cache 
        on disk (i.e. pages that have been "dumped" already): 
        data : colId : colName
                       docs : title
                              pages : pageId
                                      pageFile
                                      status """
    dumping_path = Path(current_app.config["CACHE_PATH"])   # \Dokumente\Synchronisation\Programmieren\Python\tutorial_flask_wsgi\my_app\static\cache
    exportedFiles = {}
    for colPath in [d for d in dumping_path.glob('*') if d.is_dir()]:  # iterate over directories only
        for docPath in [x for x in colPath.glob('*') if x.is_dir()]: 
            for pagePath in [y for y in docPath.glob('*') if y.is_dir()]:
                for file in pagePath.glob('*.json'):
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.loads(f.read())
                        if data['colId'] not in exportedFiles:
                            exportedFiles[data['colId']] = {'docs': {}}
                        exportedFiles[data['colId']]['colName'] = data['colName']
                        if data['docId'] not in exportedFiles[data['colId']]['docs']:
                            exportedFiles[data['colId']]['docs'][data['docId']] = {'pages': {}}
                        exportedFiles[data['colId']]['docs'][data['docId']]['title'] = data['title']
                        if data['pageNr'] not in exportedFiles[data['colId']]['docs'][data['docId']]['pages']:
                            exportedFiles[data['colId']]['docs'][data['docId']]['pages'][data['pageNr']] = {}
                        exportedFiles[data['colId']]['docs'][data['docId']]['pages'][data['pageNr']]['pageId'] = data['pageId']
                        exportedFiles[data['colId']]['docs'][data['docId']]['pages'][data['pageNr']]['pageFile'] = str(file)
                        exportedFiles[data['colId']]['docs'][data['docId']]['pages'][data['pageNr']]['status'] = data['status']
        
    return exportedFiles

downloader_bp = Blueprint('downloader', __name__)

@downloader_bp.route("/download", methods = ['GET', 'DELETE'])
@login_required
def get_downloadable_files():
    if request.method == "GET":
        response = getDownloadableFiles()
        return response, 200
    
    elif request.method == 'DELETE':
        filename = request.args.get('file')

        delete_candidate = Path(current_app.config["CACHE_PATH"], filename)
        #print("DEBUG: delete", delete_candidate)
        try:
            delete_candidate.unlink()
            return {'message': 'success'}, 200
        except:
            return {'message': f'Could not delete {delete_candidate}.'}, 404
        
    else:
        return {'message': "Only GET and DELETE are available"}, 400
    
@downloader_bp.route("/download/<string:filename>", methods = ['GET'])
@login_required
def download(filename):
    if request.method == "GET":
        print("DEBUG: requested file for download:", current_app.config["CACHE_PATH"], filename)
        return send_from_directory(current_app.config["CACHE_PATH"], filename, as_attachment=True)
    else:
        return {'message': "Only GET is available"}, 400

# Viewer for html files:
viewer_bp = Blueprint('viewer', __name__)

@viewer_bp.route("/view/<string:filename>", methods = ['GET'])
@login_required
def view(filename):
    if request.method == "GET":
        file = Path(current_app.config["CACHE_PATH"], filename)
        with open(file, "r", encoding="utf-8") as f:
            html = f.read()
        return html
    else:
        flash("ERROR: Wrong request method.")
        redirect(url_for('browser.browser'))
    
# Export workflows and converters:
exporter_bp = Blueprint('exporter', __name__)

@exporter_bp.route("/export", methods = ['GET', 'POST', 'DELETE'])
@login_required
def export():
    dumping_path = Path(current_app.config["CACHE_PATH"])   # \Dokumente\Synchronisation\Programmieren\Python\tutorial_flask_wsgi\instance\cache
    
    if request.method == "GET":
        exportedFiles = getExportedFiles()
        
        return exportedFiles, 200
    
    if request.method == "POST":
        # Read and pre-process query parameters:    
        colId = request.args.get('colId')
        docId = request.args.get('docId')
        pageNr = request.args.get('pageNr')
        export_format = request.args.get('format')
        page_list = request.args.get('pages')
        page_list = sorted(page_list.split(","))
        

        # Export to TEI xml for LERA:
        if export_format == "TEI for LERA":
            exportedFiles = getExportedFiles()
            metadata = exportedFiles[colId]['docs'][docId]
            separators = ".:;?!" # The data will be segmnented after these separators.
            
            # Let another function do the export work:
            tei = convert_to_tei_lera(metadata, page_list, separators)
            
            #date = datetime.date(datetime.now()).isoformat()
            timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
            filename = f"{metadata['title']},{docId},{timestamp},pp{build_ranges(page_list)}.xml"
            savename = Path(dumping_path, filename)
            
            try:
                with open(savename, "w", encoding="utf-8") as f:
                    f.write(tei)
                return jsonify(message = 'success',
                               links = [{'href': f'/download/{filename}',
                                   'rel': 'download',
                                   'type': 'GET'}]), 200
            except:
                return {'message': f'Could not write {savename}.'}, 500
        
        # Export to CSV for comparison with difflib:
        elif export_format == "CSV for comparison":
            exportedFiles = getExportedFiles()
            metadata = exportedFiles[colId]['docs'][docId]
            id_addition = request.args.get('idAddition') 
            
            # Let another function do the export work:
            comparable = convert_to_comparable(colId, docId, page_list)
            
            timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
            filename = f"{metadata['title']},{id_addition},{docId},{timestamp},pp{build_ranges(page_list)}.csv"
            savename = Path(dumping_path, filename)

            try:
                with open(savename, "w", encoding="utf-8") as f:
                    f.write(comparable)
                return jsonify(message = 'success',
                               links = [{'href': f'/download/{filename}',
                                   'rel': 'download',
                                   'type': 'GET'}]), 200
            except:
                return {'message': f'Could not write {savename}.'}, 500
        
        # Export to TSV for comparison with TRACER:
        elif export_format == "TSV for TRACER":
            print("EXPORTER: Exporting to TRACER ...")
            separators = request.args.get('separators') # The data will be segmnented after these separators.
            id_addition = request.args.get('idAddition') # String that will be added to the section ID of the TRACER data.
            exportedFiles = getExportedFiles()
            metadata = exportedFiles[colId]['docs'][docId]
            
            tracer, tracker = convert_to_tsv_tracer(metadata, page_list, separators, id_addition)
            
            timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
            filename = f"{metadata['title']},{id_addition},{docId},pp{build_ranges(page_list)},{timestamp}.tsv"
            filename_tracker = f"{metadata['title']},{id_addition},{docId},pp{build_ranges(page_list)},{timestamp}.tracker"
            savename = Path(dumping_path, filename)
            savename_tracker = Path(dumping_path, filename_tracker)
            
            #print("DEBUG: Tracker data")
            #print(tracker)
            #print(f"DEBUG: Exporter: I'm now trying to write {savename} and {savename_tracker}.")

            try:
                with open(savename, "w", encoding="utf-8") as f:
                    f.writelines(tracer)
                with open(savename_tracker, "w", encoding="utf-8") as ft:
                    ft.write(json.dumps(tracker, indent=4))
                print("EXPORTER: Successfully exported TSV for TRACER.")
                return jsonify(message = 'success',
                                links = [{'href': f'/download/{filename}',
                                    'rel': 'download',
                                    'type': 'GET'},
                                         {'href': f'/download/{filename_tracker}',
                                    'rel': 'download',
                                    'type': 'GET'}]), 200
            except:
                print(f"ERROR: Exporter: Could not write {savename} or/and {savename_tracker}.")
                return {'message': f'Could not write {savename}.'}, 500
              
    # Delete a file from the cache:
    elif request.method == "DELETE":
        filename = request.args.get('file')

        delete_candidate = Path(current_app.config["CACHE_PATH"], filename)
        print("DEBUG: delete", delete_candidate)
        try:
            delete_candidate.unlink()
            return jsonify(success = 'success')
        except:
            return jsonify(success = 'error',
                           response = f'Could not delete {delete_candidate}.')

def convert_to_tsv_tracer(metadata, page_list, separators, id_addition):
    """ Eats a dict with metadata (filename and others) and
        a list of pages, and returns list of lines ready to be used
        as input file for the "text reuse detection machine" TRACER. """

    abbreviations = ["cap", "lib", 
                     "tom",
                     "ibid", "sc", 
                     "item", 
                     "genesis", "genes", "gen", 
                     "exodus", "ex", "exod", "exodus",
                     "leviticus", "leuiticus", "lev", "leu", "leuit", "levit",
                     "numeri", "numer", "num", 
                     "deuteronomium", "deut", "dt", "deuter", "deutero",
                     "iosue", "ios", 
                     "iudicum", "iud", 
                     "ruth", "rut", 
                     "1sam", "2sam", "sam", 
                     "regum", "1reg", "2reg", "reg", 
                     "1par", "2par", "par", 
                     "esdrae", "esd", "esdr", "esdrae",
                     "nehemiae", "neh", 
                     "thobis", "tho", "tob", 
                     "iud", 
                     "esth", "esther", #"est", 
                     "iob", "job", 
                     "ps", "psa", "psalm", "psal",
                     "pro", "prov", "prou",
                     "ec", "ecc", "eccl", "eccle", "eccli",
                     "qo", "qoh", 
                     "can", "cant", 
                     "sap", "sapient",
                     "isa", "esa", "jes"
                     "ier", 
                     "lam", "lament", 
                     "thren",
                     "para", "paralip",
                     "bar", "baruch",
                     "eze", "hezek", "ezech",
                     "dan", "daniel",
                     "os", "hos", "ose",
                     "ioel", "ioel",
                     "amos", 
                     "abd", "obadja", "obd",
                     "iona", "ion",
                     "mic", "mich", 
                     "nah", "nahum",
                     "hab", "habac",
                     "soph", "zef", "zeph", 
                     "ag", "hag", "agg",
                     "amos",
                     "mal", "malach", "malac",
                     "1macc", "2macc", "macc", "mac", "mach", "machab",
                     "matth", "mat",
                     "marc", "mc",
                     "lucae", "luc",
                     "joh", "ioh", "ioan", "joan",
                     "act", "actor",
                     "rom", "roma", "ro", 
                     "1kor", "2kor", "kor", 
                     "cor", "corinth",
                     "galat", "gal", 
                     "eph", "ephes",
                     "phil", "philip", "philipp",
                     "col", "colos", "coloss",
                     "thess", "1thess", "2thess",
                     "tim",
                     "tit",
                     "phil",
                     "hebr", 
                     "iak", "jak", "iac", "jac",
                     "1petr", "2petr", "petr",
                     "1joh", "2joh", "3joh",
                     "jud",
                     "apoc", "apc"]

    abbreviations = set(abbreviations)

    tracker = []
    output = []
    identifier = "XX"  # first two digits of the ID of the TRACER dataset
    i = 1              # the remaining 5 digits of the ID of the TRACER dataset

    # Load data from dumped JSON files
    for pageNr in page_list:
        infile = metadata['pages'][pageNr]['pageFile']
        with open(infile, 'r', encoding='utf-8') as f:
            data = json.loads(f.read())

            # Find bibtex in the document title or use the Transkribus ID:
            bibtex = re.search(r'^[a-zA-Z]*\d{4}[a-z]?', metadata['title'])
            if bibtex:
                docId = bibtex[0]
            else:
                docId = data['docId']

            # segmentation (using the separators), build the columns:
            newline = {'words': []}
            for region in data['regions']:
                for idx, line in enumerate(region['lines']):
                    if i == 1 and idx == 0: # set the very first tracker stamp
                        newtracker = {i: f"{docId}:{pageNr}:{int(region['readingOrderIndex'])+1}:{int(line['readingOrderIndex'])+1}"}
                        tracker.append(newtracker)
                    
                    for idx, word in enumerate(line['words']):
                        newline['words'].append(word)
                        # Look for separators and check if we have to start a new line:
                        if word['data_type'] != 'word' and word['data'] in separators:
                            dummy = {'data': "a", 'data_type': "word"}

                            if idx-1 >= 0:
                                previous_word = line['words'][idx-1]
                            else:
                                previous_word = dummy

                            if idx+1 < len(line['words']):
                                next_word = line['words'][idx+1]
                            else:
                                next_word = dummy

                            # If the line is not too short and the previous word is not a punctuation or an abbreviation:
                            if len(newline['words']) > 3 and next_word['data_type'] == 'word' and previous_word['data'].lower() not in abbreviations:
                                # begin a new line:
                                newline = auto_spacer(newline, "")
                                #newline.replace('§%§%', '') # delete auto_space's markers
                                newline = identifier + f"{i:05}\t" + newline.strip() + f"\tNULL\t{docId}{id_addition}\n"
                                output.append(newline)
                                newline = {'words': []}

                                # set a new tracker stamp:
                                i += 1
                                newtracker = {i: f"{docId}:{pageNr}.r{int(region['readingOrderIndex'])+1}l{int(line['readingOrderIndex'])+1}"}
                                tracker.append(newtracker)

    return output, tracker

def OLD_convert_to_tsv_tracer(metadata, page_list, separators, id_addition):
    """ Version 1.0 --> OUTDATED!
    
        Eats a dict with metadata (filename and others) and
        a list of pages, and returns list of lines ready to be used
        as input file for the "text reuse detection machine" TRACER. """

    tracker = []
    output = []
    identifier = "XX"  # first two digits of the ID of the TRACER dataset
    i = 1              # the remaining 5 digits of the ID of the TRACER dataset
    newline = identifier + f"{i:05}\t" # make a start

    abbreviations = ["cap.", "lib.", 
                     "tom.",
                     "ibid.", "sc.", 
                     "item:", 
                     "genesis", "genes.", "gen.", 
                     "exodus", "ex.", "exod.", "exodus",
                     "leviticus", "leuiticus", "lev.", "leu.", "leuit.", "levit.",
                     "numeri", "numer.", "num.", 
                     "deuteronomium", "deut.", "dt.", "deuter.", "deutero.",
                     "iosue", "ios.", 
                     "iudicum", "iud.", 
                     "ruth", "rut.", 
                     "1sam.", "2sam.", "sam.", 
                     "regum", "1reg.", "2reg.", "reg.", 
                     "1par.", "2par.", "par.", 
                     "esdrae", "esd.", "esdr.", "esdrae",
                     "nehemiae", "neh.", 
                     "thobis", "tho.", "tob.", 
                     "iud.", 
                     "esth.", "esther", #"est.", 
                     "iob.", "job.", 
                     "ps.", "psa.", "psalm.", "psal.",
                     "pro.", "prov.", "prou.",
                     "ec.", "ecc.", "eccl.", "eccle.", "eccli.",
                     "qo.", "qoh.", 
                     "can.", "cant.", 
                     "sap.", "sapient.",
                     "isa.", "esa.", "jes."
                     "ier.", 
                     "lam.", "lament.", 
                     "thren.",
                     "para.", "paralip.",
                     "bar.", "baruch",
                     "eze.", "hezek.", "ezech.",
                     "dan.", "daniel",
                     "os.", "hos.", "ose.",
                     "ioel.", "ioel.",
                     "amos", 
                     "abd.", "obadja", "obd.",
                     "iona", "ion.",
                     "mic.", "mich.", 
                     "nah.", "nahum",
                     "hab.", "habac.",
                     "soph.", "zef.", "zeph.", 
                     "ag.", "hag.", "agg.",
                     "amos",
                     "mal.", "malach.", "malac.",
                     "1macc.", "2macc.", "macc.", "mac.", "mach.", "machab.",
                     "matth.", "mat.",
                     "marc.", "mc.",
                     "lucae", "luc.",
                     "joh.", "ioh.", "ioan.", "joan.",
                     "act.", "actor.",
                     "rom.", "roma.", "ro.", 
                     "1kor.", "2kor.", "kor.", 
                     "cor.", "corinth.",
                     "galat.", "gal.", 
                     "eph.", "ephes.",
                     "phil.", "philip.", "philipp.",
                     "col.", "colos.", "coloss.",
                     "thess.", "1thess.", "2thess.",
                     "tim.",
                     "tit.",
                     "phil.",
                     "hebr.", 
                     "iak.", "jak.", "iac.", "jac.",
                     "1petr.", "2petr.", "petr.",
                     "1joh.", "2joh.", "3joh.",
                     "jud.",
                     "apoc.", "apc."]

    # Load data from dumped JSON files
    for pageNr in page_list:
        infile = metadata['pages'][pageNr]['pageFile']
        with open(infile, 'r', encoding='utf-8') as f:
            data = json.loads(f.read())

            # Find bibtex in the document title or use the Transkribus ID:
            bibtex = re.search(r'^[a-zA-Z]*\d{4}[a-z]?', metadata['title'])
            if bibtex:
                docId = bibtex[0]
            else:
                docId = data['docId']

            # segmentation (using the separators), build the columns:
            for region in data['regions']:
                for idx, line in enumerate(region['lines']):
                    if i == 1 and idx == 0: # set the very first tracker stamp
                        newtracker = {i: f"{docId}:{pageNr}:{int(region['readingOrderIndex'])+1}:{int(line['readingOrderIndex'])+1}"}
                        tracker.append(newtracker)
                    # Segment the line using separators:
                    raw_data = auto_spacer(line, separators)
                    if '§%§%' in raw_data: # if there is one or more segmentation markers
                        parts = raw_data.split('§%§%')
                        # Calculate the length of the newline and begin a new 
                        # token only if the newline is at least 2 words long
                        # and the last word of the junk is longer than 2 characters.
                        # (This avoids pseudo tokens like "Gen.", "Item:" or "3.")
                        # length = len(newline.split(" ") + parts[0].split(" "))
                        # if length > 2:
                        for part in parts[:-1]: # for all parts except the first and the last
                            if len(part.split(" ")[-1]) > 2 and part.split(" ")[-1].lower() not in abbreviations: # the junk is longer than 2: begin a new line
                                # write the rest of the line and close it by appending meta data:
                                newline += " " + part.strip() + f"\tNULL\t{docId}{id_addition}\n"
                                output.append(newline)
                                # begin a new line of data:
                                i += 1
                                newtracker = {i: f"{docId}:{pageNr}.r{int(region['readingOrderIndex'])+1}l{int(line['readingOrderIndex'])+1}"}
                                tracker.append(newtracker)
                                newline = identifier + f"{i:05}\t"
                            else: # the junk is <= 2: add it to the current line
                                newline += " " + part.strip()

                        # append the last part:
                        newline += " " + parts[-1].strip()
                    else:
                        newline += " " + raw_data.strip()
    
    # Close the last line of data:
    newline += f"\tNULL\t{docId}{id_addition}\n"
    output.append(newline)
    #print(output)
    
    return output, tracker
    
    
def convert_to_comparable(colId, docId, page_list):
    """ Eats a colId, docId and a list of pages, 
        fetches the data of these pages, 
        and returns a csv file ready to be used
        in the "compare" module of this application. """

    print("Converting to CSV for comparison with difflib ...")
    
    exportedFiles = getExportedFiles()
    metadata = exportedFiles[colId]['docs'][docId]
    
    output = ""
    
    for pageNr in page_list:
        infile = metadata['pages'][pageNr]['pageFile']
        with open(infile, 'r', encoding='utf-8') as f:
            data = json.loads(f.read())

            # Find bibtex in the document title or use the Transkribus ID
            bibtex = re.search(r'^[a-zA-Z]*\d{4}[a-z]?', metadata['title'])
            if bibtex:
                bibtex = bibtex[0]
            else:
                bibtex = data['docId'] 

            # Add a heading containing the bibtex or the Transkribus ID
            #output += f"<h3 class=\"{ docId }\">{ docId }, p. { data['pageNr'] }</h3>;;;;\n"
            
            # Collect all words and add one per line together with metadata:
            # word; docId; colId/docId; pageNr; r<regionNr>l<lineNr>; wordIdx; type (word|punctuation|unreadable)
            for region in data['regions']:
                for line in region['lines']:
                    for wordIdx, word in enumerate(line['words']):
                        newline = ""
                        newline += '"' + word['data'] + '"' + ";"       # the word itself
                        newline += '"' + bibtex + '"' + ";"             # bibtex (or docId)
                        newline += '"' + f"{colId}.{docId}" + '"' + ';' # coldoc
                        newline += '"' + pageNr + '"' + ";"             # pageNr
                        newline += '"' + f"r{int(region['readingOrderIndex'])+1}l{int(line['readingOrderIndex'])+1}" + '"' + ";" # regionNr and lineNr
                        newline += '"' + str(wordIdx) + '"' + ";"       # wordIdx
                        newline += '"' + word['data_type'] + '"'        # data type
                        output += newline + "\n"
    
    return output

def convert_to_tei_lera(metadata, page_list, separators):
    """ Eats a dict, returns the TEI root and teiHeader in a 
        format processable by LERA. """
    
    print("Converting to TEI XML for LERA...")
    # Build the TEI root and teiHeader:
    tei = objectify.Element("TEI")
    tei.set('xmlns', "http://www.tei-c.org/ns/1.0")
    titleStmt = objectify.Element("titleStmt")
    titleStmt.title = metadata['title']
    titleStmt.author = "Transkribus Spellchecker"

    editionStmt = objectify.Element("editionStmt")
    editionStmt.edition = objectify.Element("date")
    editionStmt.edition.date = datetime.date(datetime.now()).isoformat()
    
    teiHeader = objectify.Element("teiHeader")
    teiHeader.fileDesc = objectify.Element("fileDesc")
    teiHeader.fileDesc.titleStmt = titleStmt
    teiHeader.fileDesc.editionStmt = editionStmt
    tei.teiHeader = teiHeader
    
    # Build the TEI text body:
    text = objectify.Element("text")
    body = objectify.Element("body")
    tei['text'] = text
    tei['text'].body = body

    content = ""        
    for pageNr in page_list:
        filename = metadata['pages'][pageNr]['pageFile']
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.loads(f.read())
            content += f'<pb n="{pageNr}"/>'
            for region in data['regions']:
                content += f"<cb n=\"r{region['readingOrderIndex']}\"/>"
                for line in region['lines']:
                    content += f"<lb n=\"r{region['readingOrderIndex']}l{line['readingOrderIndex']}\"/>"
                    content += auto_spacer(line, separators)

    # Replace the token separators in the content with proper xml tags:
    junks = []
    elements = content.split('§%§%')
    for token_counter, element in enumerate(elements, start=1):
        junks.append(objectify.fromstring(f'<ab xml:id="token{token_counter}">{element}</ab>'))

    tei['text'].body.ab = junks

    # Clean-up the xml code (get rid of "py-type" stuff etc.)
    objectify.deannotate(tei, xsi_nil=True)
    ET.cleanup_namespaces(tei)

    # Dump the lxml object to a string and return it
    output = ET.tostring(tei, pretty_print=True, xml_declaration=True, encoding="utf-8").decode()
    print("Success!")
    #print("DEBUG", output)

    return output

def auto_spacer(line, separators):
    """ Reads a line dict and joins all its words to a string
        while putting spaces at the correct places (e.g. no space
        before punctuation etc.). 
        After a separator '§%§%' will be added. This marker can be used
        later to tokenize the string.
        Returns the line as a string. """
    newline = ""
    no_leading_space = True
    for word in line['words']:
        if word['data_type'] == "word":
            if no_leading_space == True:
                newline += word['data']
                no_leading_space = False
            else:
                newline += " " + word['data']
        else:
            if word['data'] == "(":
                newline += " " + word['data']
                no_leading_space = True
            elif word['data'] in separators:
                newline += word['data']
                newline += '§%§%' # token separator will be replaced later
                #newline += f'<milestone xml:id="token{token_counter}" unit="token"/>'
            else:
                newline += word['data']
    return newline
    
def analyze_range(range_string, colId, docId):
    """ Analyze exportRange and build a list of pages to be processed
        (every sublist represents a page range): """

    if range_string != "":
        # Strip all spaces from exportRange:
        exportRange = range_string.replace(" ", "")
        selected_pages = []
        for parts in exportRange.split(","):
            subparts = parts.split("-")
            if len(subparts) == 1:
                selected_pages.append(f"{str(colId)}-{str(docId)}-{subparts[0]}")
                
            elif len(subparts) == 2:
                # iterate through the page range:
                if int(subparts[0]) < int(subparts[1]):
                    r = int(subparts[1]) - int(subparts[0]) + 1
                    for a in range(r):
                        thisPageNr = int(subparts[0]) + a
                        selected_pages.append(f"{str(colId)}-{str(docId)}-{thisPageNr}")
                else:
                    print(f"ERROR in page range '{parts}': {subparts[0]} is bigger than {subparts[1]}!")
    
        return selected_pages
    else:
        return []

def build_ranges(page_list):
    """ Eats a list of items, groups consecutive items in separate lists and 
        returns a list of lists """
    page_list.append(-1)
    output = []
    last = int(page_list[0])-1
    beginning = int(page_list[0])
    for i in page_list:
        i = int(i)
        if i != last + 1:
            output.append([str(beginning), str(last)])
            beginning = i
        last = i
    page_list.pop()

    return ",".join(["-".join(x) for x in output])
