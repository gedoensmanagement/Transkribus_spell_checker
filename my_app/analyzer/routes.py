# -*- coding: utf-8 -*-
"""
Created on Fri Sep 25 16:29:19 2020

@author: muell018
"""
from flask import Blueprint, session, render_template, url_for, flash, redirect, request, jsonify, json, current_app, send_from_directory
from flask_login import login_required, current_user

from ..io.cts import Cts

import difflib
from jinja2 import Template
from pathlib import Path
from datetime import datetime
from collections import OrderedDict
import csv

from pprint import pprint

compare_bp = Blueprint('compare', __name__)

@compare_bp.route("/compare", methods = ['GET', 'POST'])
@login_required
def compare():
    """ Eats two file names, returns a comparison of the two files. 
        Both files must be csv files containing
            <a word>;<doc ID>;<pageNr>;<line ID>;<index of the word> 
        They may also contain lines with additional HTML code (if the
        output format is html): 
            <h3>Document 1</h3> 
    """
    
    if request.method == 'GET':
        return "html"
    
    elif request.method == 'POST':
        # Get the JSON payload of the request containing the two file names
        payload = request.get_json()
        
        if payload['format'] == "html":
            # Read input data, i.e. both input files (CSV) from disk:
            dumping_path = Path(current_app.config["CACHE_PATH"])   # \Dokumente\Synchronisation\Programmieren\Python\tutorial_flask_wsgi\instance\cache
            filename1 = Path(dumping_path, payload['files'][0])
            filename2 = Path(dumping_path, payload['files'][1])
            o = openfile(filename1)
            e = openfile(filename2)
            
            balance_tokens(o, e)
        
            data1 = prepare_for_diff(o)
            data2 = prepare_for_diff(e)
            
            # Use difflib to find the differences:
            print("ANALYZER: searching for differences (with difflib) ...")
            d = difflib.Differ()
            delta = d.compare(data1, data2)
            delta = [*delta] # convert generator to list
        
            pairs = prepare_output(delta, o,e)
            
            filtered = filter_false_positives(pairs)
            
            html = export_to_html(filtered, 
                                  original_document=o[0]['document'],
                                  censored_document=e[0]['document'])
    
            dumping_path = Path(current_app.config["CACHE_PATH"])
            timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
            filename = f"differences,{o[0]['document']}_vs_{e[0]['document']},{timestamp}.html"
            savename = Path(dumping_path, filename)
            try:
                with open(savename, "w", encoding="utf-8") as f:
                    f.write(html)
            except:
                pass
            
            return html
        
        elif payload['format'] == "raw_diff":
            # Read input data, i.e. both input files (CSV) from disk:
            dumping_path = Path(current_app.config["CACHE_PATH"])
            filename1 = Path(dumping_path, payload['files'][0])
            filename2 = Path(dumping_path, payload['files'][1])
            o = openfile(filename1)
            e = openfile(filename2)
            
            balance_tokens(o, e)
        
            data1 = prepare_for_diff(o)
            data2 = prepare_for_diff(e)
            
            # Use difflib to find the differences:
            print("ANALYZER: searching for differences (with difflib) ...")
            d = difflib.Differ()
            delta = d.compare(data1, data2)
            delta = [*delta] # convert generator to list
        
            pairs = prepare_output(delta, o,e)
            
            filtered = filter_false_positives(pairs)
            
            output = serialize_diff_pairs(filtered)
            
            output["original"]["docTitle"] = o[0]['document']
            output["censored"]["docTitle"] = e[0]['document']
            
            output["message"] = "Success! Use the censorship inspector to process the output."
            
            print("ANALYZER: Done! Sending JSON to client.")
            
            return jsonify(output)
        
        elif payload['format'] == "TRACER":
            """ The TRACER data is already formatted correctly in the TSV files. 
                The only thing we have to do here is to replace the "XX" place holders
                at the beginning of every line with a two digit number representing 
                the no. of the document. """
            dumping_path = Path(current_app.config["CACHE_PATH"])
            output = []
            docs = []
            docnr = 10
            for file in payload['files']:
                infile = Path(dumping_path, file)
                with open(infile, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for idx, line in enumerate(lines):
                        output.append(f"{docnr}{line[2:]}")
                        if idx == 0: # get the document identifier of the first line
                            docs.append(line.split("\t")[-1].strip())
                docnr += 1
            
            timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
            filename = f"tracer_{','.join([str(x) for x in docs])}_{timestamp}.txt"
            savename = Path(dumping_path, filename)
            print(f"ANALYZER: Trying to write {savename}")
            try:
                print("ANALYZER: Sucess!")
                with open(savename, "w", encoding="utf-8") as f:
                    f.writelines(output)

                return jsonify(message = f'Success! You can download the exported file under /download/{savename}',
                               links = [{'href': f'/download/{savename}',
                                         'rel': 'download',
                                         'type': 'GET'}]), 200
            except:
                print(f"ERROR: Analyzer: Could not write file {savename}")

                return jsonify(message = f"ERROR: Analyzer: Could not write file {savename}",
                               links = [{'href': "error",
                                         'rel': 'download',
                                         'type': 'GET'}]), 500

def openfile(filename,separator=";"):
    """ Opens a csv file and returns a dict. """
    
    output = []
    fieldnames = ["word","document","coldoc","page","line","wordnr", "type"]
    with open(filename, newline='', encoding="utf-8") as csvfile:
        data = csv.DictReader(csvfile, fieldnames=fieldnames, delimiter=";", quotechar='"')
        for item in data:
            output.append(item)

    return output

def balance_tokens(t1, t2):
    """ When the texts to be compared have different lengths, the rendering of 
        the differences found in these texts will be difficult. Therefore, we 
        add dummy lines to the shorter file. Returns two equally long lists of dicts. """
    difference = len(t1) - len(t2)
    print("ANALYZER: Balancing different lengths:", len(t1), len(t2), len(t1) - len(t2))
    
    if difference < 0:
        line = t1[-1]['line']
        for element in range(1, (difference * -1) + 1):
            t1.append({'word': '',
                       'document': 'Dummy1977',
                       'coldoc': '0.0',
                       'page': '0',
                       'line': line, 
                       'wordnr': '', # str(offset + element)
                       'type': 'dummy'})
    elif difference > 0:
        line = t2[-1]['line']
        for element in range(1, difference + 1):
            t2.append({'word': '',
                       'document': 'Dummy1977',
                       'coldoc': '0.0',
                       'page': '0',
                       'line': line, 
                       'wordnr': '', # str(offset + element)
                       'type': 'dummy'})

    print("ANALYZER: Balanced:                   ", len(t1), len(t2), len(t1) - len(t2))

def prepare_for_diff(data):
    """ Eats a list of dicts, extracts the words in lower case and
        returns them as a list. (We don't want capital letters to 
        disturb our comparison.) """
    prepared = []
    for item in data:
        prepared.append(item['word'].lower())
    return prepared

def prepare_output(delta, o, e):
    """ Eats the delta produced by difflib and converted to a list, 
        the original (o) and expurgated (e) data, and returns 
        a list of lists containing the code (" "/"+"/"-"), the word
        in the original version, the word in the expurgated version, the type
        (word or punctuation) and the precise cts addresses in both versions. """
    print("ANALYZER: preparing data for export ...")
    newline = []
    pairs = []
    position_d1 = 0
    position_d2 = 0
    for d in delta:
        if position_d1 + 1 > len(o) or position_d2 + 1 > len(e):
            break
        
        code = d[:1]
        data = d[2:]
        
        org = o[position_d1]
        exp = e[position_d2]
        
        if code == "?" or code == "":
            pass
        else:
            orgcts = Cts().from_string(f"tr:{org['coldoc']}:{org['page']}.{org['line']}@{org['wordnr']}")
            expcts = Cts().from_string(f"tr:{exp['coldoc']}:{exp['page']}.{exp['line']}@{exp['wordnr']}")
            if code == " ":
                pairs.append([" ", 
                              org['word'], 
                              orgcts,
                              exp['word'], 
                              expcts, 
                              org['type']])
                position_d1 += 1
                position_d2 += 1
            elif code == "+":
                pairs.append(["+", 
                              "", 
                              orgcts,
                              exp['word'], 
                              expcts, 
                              exp['type']])
                position_d2 += 1
            elif code == "-":
                pairs.append(["-", 
                              org['word'], 
                              orgcts,
                              "", 
                              expcts, 
                              org['type']])
                position_d1 += 1
        

    # with open("debug_prepare_output.txt", "w", encoding="utf-8") as f:
    #     for pair in pairs:
    #         f.write(str(pair)+"\n")
    #     print("DEBUG: ANALYZER: debug file written.")

    return pairs

def serialize_diff_pairs(pairs):
    """ Makes the list of pairs JSON serializable by converting the Cts objects
        and adding some metadata. """

    output = {"original": {"colId": pairs[0][2].col,
                           "docId": pairs[0][2].doc},
              "censored": {"colId": pairs[0][4].col,
                           "docId": pairs[0][4].doc}}
    pages = {}
    words = []
    last_page = pairs[0][2].page
    last_line = pairs[0][2].rl
    for pair in pairs:
        this_page = pair[2].page
        this_line = pair[2].rl
        if this_page != last_page:
            pages[last_page] = {'words': words}
            words = []
            last_page = this_page
        words.append([pair[0],
                      pair[1],
                      f"{pair[2].rl}@{pair[2].subreference}",
                      pair[3],
                      f"{pair[4].page}.{pair[4].rl}@{pair[4].subreference}",
                      pair[5]])
    
    pages[last_page] = {'words': words}
    
    output['pages'] = pages
    
    return output

def filter_false_positives(pairs):
    ''' Use a sliding window (three items long) to search for patterns like:
        
        - ne
        - dum
        +         nedum  <<
        
        +         nobisipsis <<
        - nobis
        - ipsis
        
        - it
        +         ita    <<
        - a
        
        - etiamsi        <<
        +         etiam  
        +         si
        
        If there is a match, keep the long word and drop the two shorter ones.'''

    print("ANALYZER: filtering false positives ...")
    output = []
    countdown = 0
    for i in range(len(pairs)-2):
        if countdown >  0:
            countdown -= 1
        if countdown == 0:
            if pairs[i][0] == "+" or pairs[i][0] == "-":
                first = pairs[i][1] + pairs[i][3]
                second = pairs[i+1][1] + pairs[i+1][3]
                third = pairs[i+2][1] + pairs[i+2][3]
                if first.lower() + second.lower() == third.lower():
                    output.append([' ', 
                                   third, pairs[i+2][2],
                                   third, pairs[i+2][4],
                                   pairs[i+2][5]])
                    countdown = 3
                elif first.lower() + third.lower() == second.lower():
                    output.append([' ', 
                                   second, pairs[i+1][2],
                                   second, pairs[i+1][4],
                                   pairs[i+1][5]])
                    countdown = 3
                elif second.lower() + third.lower() == first.lower():
                    output.append([' ', 
                                   first, pairs[i][2],
                                   first, pairs[i][4],
                                   pairs[i][5]])
                    countdown = 3
                else:
                    output.append(pairs[i])
                    countdown = 0
            else:
                output.append(pairs[i])
        
    return output

def add_text(original, censored):
    """ This function preserves prossible lower/upper case 
        differences between the two versions: """
    html = ""
    template = Template('<span class="{{ classname }}">{{ text }}</span> ')
    if original != censored:
        if original == "":
            html += censored + " "
        elif censored == "":
            html += original + " "
        else:
            html += template.render(classname="original", text=original)
            html += template.render(classname="censored", text=censored)
    else:
        html += original + " "
    return html

def export_to_html(pairs, original_document, censored_document):
    """ Eats a list of differences (pairs) produced by difflib and 
        pre-processed by the "prepare_output()" function. 
        Uses this data to build an HTML page (using jinja2 templates). 
        Returns an HTML string ready to be sent to a browser. """
    
    print("ANALYZER: exporting to HTML ...")
    wrapper = Template(
    '''<!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="utf-8">
        <link rel="stylesheet" href="https://cdn.materialdesignicons.com/5.4.55/css/materialdesignicons.min.css">
        <style>
            .{{ censored }} {
                display: none;
                }
            span.linenr {
                color: gray;
                text-decoration: none;
                font-style: italic;
                }
            u.det {
                text-decoration: line-through dotted;
                color: red;
                }
            u.add {
                text-decoration: underline green;
                color: green;
                }
        </style>
        <title>{{ original_document }} vs. {{ censored_document }}</title>
    </head>
    <body>
        <h1>Differences {{ original_document }} vs. {{ censored_document }}</h1>
        {{ body }}
    </body>
    </html>
    ''')
    new_line = Template('\n<span class="{{ classname }}"><br /><a href="/cts/resolver?urn={{ cts }}" title="{{ cts }}" target="{{ cts }}">{{ identifier }}</a>  </span>')
    new_page = Template('\n<h3 class="{{ classname }}">{{ document }}, p. {{ identifier }}</h3>')
    new_page_censored = Template('\n<a title="open {{ document }}, p. {{ identifier }}" href="/cts/resolver?urn={{ cts }}" target="{{ cts }}"><i class="mdi mdi-book-open-page-variant"></i></a>')
    markup = Template('<u class="{{ classname }}" title="{{ tooltip }}">{{ text }}')

    output = ""
    
    # add markup before the first line starts:
    firstline = ""
    firstline += new_page.render(classname="pagenr original", document=original_document, identifier=pairs[0][2].page)
    firstline += new_page_censored.render(classname="pagenr", document=censored_document, identifier=pairs[0][4].page, 
                                          cts=pairs[0][4].to_string())
    firstline += new_line.render(classname="linenr original", identifier=pairs[0][2].rl, cts=pairs[0][2].to_string())
    firstline += new_line.render(classname="linenr censored", identifier=pairs[0][4].rl, cts=pairs[0][4].to_string())
    if pairs[0][0] == " ":
        last_tag = ""
        pass
    elif pairs[0][0] == "-":
        firstline += markup.render(classname="det", text="")
        last_tag = markup.render(classname="det", text="")
    elif pairs[0][0] == "+":
        firstline += markup.render(classname="add", text="")
        last_tag = markup.render(classname="det", text="")

    # cycle through the pairs and build the html markup:
        
    # TODO: This algorithm is quite inefficient! How could it be improved?!
    
    max = len(pairs)
    for idx, pair in enumerate(pairs):
        html = ""
        if idx+1 < max:
            this_code = pair[0]
            next_code = pairs[idx+1][0]
            codes = this_code + next_code
            
            #####################################################
            # Check for changes in page number or line number:
            enclosing = Template("</u>{{ between }}{{ last_tag }}")
            between = ""
            # Page numbers:
            this_page_original = pair[2].page
            next_page_original = pairs[idx+1][2].page
            this_page_censored = pair[4].page
            next_page_censored = pairs[idx+1][4].page

            if this_page_original != next_page_original:
                print(f"ANALYZER: rendering {original_document}, p. {next_page_original}")
                between += new_page.render(classname="pagenr original", 
                                           document=original_document,
                                           identifier=next_page_original)
            elif this_page_censored != next_page_censored:
                between += new_page_censored.render(classname="pagenr", 
                                           document=censored_document,
                                           identifier=next_page_censored,
                                           cts=pairs[idx+1][4].to_string())

            # Line numbers:
            this_line_original = pair[2].rl
            next_line_original = pairs[idx+1][2].rl
            this_line_censored = pair[4].rl
            next_line_censored = pairs[idx+1][4].rl

            if this_line_original != next_line_original:
                between += new_line.render(classname="linenr original", 
                                           identifier=next_line_original, 
                                           cts=pairs[idx+1][2].to_string())
            elif this_line_censored != next_line_censored:
                between += new_line.render(classname="linenr censored", 
                                           identifier=next_line_censored, 
                                           cts=pairs[idx+1][4].to_string())    

            # Add enclosing around 'between' if necessary:
            if between != "" and last_tag != "" and this_code == next_code:
                between = enclosing.render(between=between, last_tag=last_tag)
        
            #####################################################
            # Add markup to highlight the differences:
            # add = addition, det = detraction
            tooltip_add = f"{censored_document}, {pair[4].to_string()}"
            tooltip_det = f"{original_document}, {pair[2].to_string()}"
            if this_code == next_code:
                # no changes, just add text:
                html += add_text(pair[1], pair[3])
                html += between
            elif codes == " -":
                #"begin det"
                html += add_text(pair[1], pair[3])
                html += between
                addition = markup.render(classname="det", tooltip=tooltip_det, text="")
                html += addition
                last_tag = addition
            elif codes == "- ":
                #"end det"
                html += pair[1] + "</u> "
                last_tag = ""
                html += between
            elif codes == "-+":
                #"end det, begin add"
                html += pair[1] + "</u> "
                last_tag = ""
                html += between
                addition = markup.render(classname="add", tooltip=tooltip_add, text="")
                html += addition
                last_tag = addition
            elif codes == " +":
                #"begin add"
                html += add_text(pair[1], pair[3])
                html += between
                addition = markup.render(classname="add", tooltip=tooltip_add, text="")
                html += addition
                last_tag = addition
            elif codes == "+ ":
                #"end add"
                html += pair[3] + "</u> "
                last_tag = ""
                html += between
            elif codes == "+-":
                #"end add, begin det"
                html += pair[3] + "</u> "
                last_tag = ""
                html += between
                addition = markup.render(classname="det", tooltip=tooltip_det, text="")
                html += addition
                last_tag = addition
        
        output += html
    
    output = firstline + output
    output = wrapper.render(body=output, 
                            censored="censored",
                            original_document=original_document,
                            censored_document=censored_document)

    return output