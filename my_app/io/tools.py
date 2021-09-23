#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provides the "IO_Tools" object, i.e. a 
set of tools …
a) to process raw Transkribus page XML data 
(either coming from the cloud or from a local folder)
(TODO: loading from local folder yet to be implemented!)
b) to read a table from Google sheets
c) to write PageXML to a file

Created on Fri Apr 17 15:31:47 2020
@author: muellerm@ieg-mainz.de
"""

from flask import current_app
import re
import sys
import csv
from lxml import etree as ET
from lxml import objectify
import requests
from collections import OrderedDict

class IO_Tools:
    @staticmethod
    def _customAttributes(customAttribute):
        """ Eats a 'custom' attribute of a Transkribus METS file and
            returns its keys and values as a nested dict. """
        output = {}
        parts = customAttribute[:-2].split(";} ")
        for part in parts:
            elements = part.split(" {")
            subelements = elements[1].split(":")
            output[elements[0]] = {subelements[0]: subelements[1]}
        return output
    
    def get_element(self, colId, docId=None, pageNr=None):
        """ Returns a collection, document or page object depending on the 
            number or 'depth' of arguments given. """
        if colId and docId and pageNr:
            return self.cols[colId].get_child("docId", docId).get_child("pageNr", pageNr)
        elif colId and docId and not pageNr:
            return self.cols[colId].get_child("docId", docId)
        elif colId and not docId and not pageNr:
            return self.cols[colId]
        else:
            sys.exit("ERROR: You must at least provide a colId!")
    
    def unpack_page(self, colId, docId, pageNr, regionType="paragraph"):
        """ Extracts the transcript plus metadata from the raw XML data 
            of a specific page and stores it in the Transkribus Object. 
            You can filter a specific RegionType by providing a RegEx. 
            For all regions, say 'regionType=".*"' 
            Returns the XML and the Page Object."""
        current_app.logger.debug(f"IO_TOOLS: Received unpack_page command for {self.cols[colId]['docs'][docId]['pages'][pageNr]['xml']}.")
        current_app.logger.info(f"IO_TOOLS: Unpacking page {colId}/{docId}/{pageNr}.")
        xml = objectify.fromstring(bytes(self.cols[colId]['docs'][docId]['pages'][pageNr]['xml'], 'utf-8'))
        # Build regions (if they exist in the page XML)
        if hasattr(xml.Page, "TextRegion"):
            thispage = self.cols[colId]['docs'][docId]['pages'][pageNr]
            thispage['imageWidth'] = int(xml.Page.attrib['imageWidth'])
            thispage['imageHeight'] = int(xml.Page.attrib['imageHeight'])
            thispage['regions'] = []

            for region in xml.Page.TextRegion:
                regionAttributes = self._customAttributes(region.attrib['custom'])
                if 'structure' in regionAttributes:
                    if bool(re.match(regionType, regionAttributes['structure']['type'])):
                        lines = []
                        if hasattr(region, "TextLine"):
                            for line in region.TextLine:
                                if hasattr(line, "TextEquiv"):
                                    lineAttributes = self._customAttributes(line.attrib['custom'])
                                    lines.append({
                                        'readingOrderIndex': lineAttributes['readingOrder']['index'],
                                        'raw_data': str(line.TextEquiv.Unicode),
                                        'baseline': str(line.Baseline.attrib['points']),
                                        })
                                else:
                                    current_app.logger.error("IO_TOOLS: ERROR no 'TextEquiv' in this line")
                                    return False
                        else:
                            current_app.logger.error("IO_TOOLS: ERROR unpacking TextLines")
                            return False
                        thispage['regions'].append({
                            'readingOrderIndex': regionAttributes['readingOrder']['index'],
                            'structureType': regionAttributes['structure']['type'],
                            'lines': lines
                            })
                else:
                    current_app.logger.error("IO_TOOLS: Error unpacking TextRegions")
                    return False
            return True
        else:
            current_app.logger.error("IO_TOOLS: Error unpacking pageXML")
            return False

    @staticmethod
    def load_google_sheet(url):
        """ Loads a spreadsheet from Google Docs and returns it as an OrderedDict. 
            (The spreadsheet must be accessible as csv for 'anyone with the link'!)
            sheet_id is a unique ID in the URL: …/d/XXXXXX…/.
            gid identifies a tab within the sheet. The first tab always has
            gid = 0, the others have unique IDs. The gid is the last query
            parameter in the URL. 
            Example:                                  sheet_id            gid
                                                         ↓                ↓
            https://docs.google.com/spreadsheets/d/XXXXXXXXXXXXX/edit#gid=0
            
            A direct link to the table in csv format looks like this:
            https://docs.google.com/spreadsheets/d/XXXXXXXXXXXXX/pub?gid=0&single=true&output=csv
            
            THIS direct csv link is what this function eats!
            """
        try:
            r = requests.get(url)
        except:
            sys.exit(f"ERROR: Google Sheet not found!")
        
        lines = r.content.decode().splitlines()
        #print(lines) #DEBUG
        csv_reader = csv.reader(lines)
        
        output = OrderedDict()
        for idx, row in enumerate(csv_reader):
            
            if idx == 0:
                fieldnames = row # Split only the first line#
            else:
                if not row[0].startswith("#"):   # skips comments and empty lines
                    output[row[0]] = {}
                    for idx, element in enumerate(row[1:], 1): # starting with the second element
                        try:
                            output[row[0]][fieldnames[idx]] = element
                        except:
                            current_app.logger.error("IO_TOOLS: Cannot load Google Sheet. Check if config.py has the correct link and if it is accessible for 'anyone with the link'.")
        current_app.logger.info("IO_TOOLS: Loaded Google spreadsheet.")
        return output

    @staticmethod
    def dict_reader(file, separator=","):
        """ Reads a csv file and transforms it to an OrderedDict:
            - the rows of the first column become the keys of the first level
            - the fieldnames in the first row become keys of the second level
            - skips lines starting with "#" as comments. 
            That means…:
                a1, b1, c1
                # a comment
                a3, b3, c3
            …is transformed to:
                {'a3': {'b1': 'b3', 'c1': 'c3'},
                 'a4': {'b1': 'b4', 'c1': 'c4'}} """
        try:
            with open(file, "r", encoding="utf-8") as f:
                exceptions_file = f.read()
        except:
            sys.exit("ERROR: "+str(file)+" not found!")
        
        output = OrderedDict()
        lines = exceptions_file.split("\n")
        fieldnames = lines[0].split(separator) # Split only the first line
    
        for line in lines[1:]: # all lines minus the first
            if not line.startswith("#") and not line == "":   # skips comments and empty lines
                elements = line.split(separator)
                output[elements[0]] = {}
                for idx, element in enumerate(elements[1:], 1): # starting with the second element
                    output[elements[0]][fieldnames[idx]] = element
        current_app.logger.info(f"IO_TOOLS: Loaded {str(file)}.")
        return output

    
    def write_to_file(self, pageXML, outfile):
        """ Writes PageXML data to a file. """
        
        xml = ET.tostring(pageXML, pretty_print=True, xml_declaration=True, encoding="UTF-8")
        try:
            with open(outfile, "wb") as xml_writer:
                xml_writer.write(xml)
            current_app.logger.info(f"IO_TOOLS: {outfile} written successfully.")
        except IOError as e:
            current_app.logger.error(f"IO_TOOLS: ERROR writing {outfile}, {str(e)}")
    