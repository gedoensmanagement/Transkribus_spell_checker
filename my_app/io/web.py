#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provides the Transkribus_Web object, i.e. a client to 
communicate with the Transkribus REST API.

Created on Fri Apr 17 16:59:51 2020

@author: muellerM@ieg-mainz.de
"""

from flask import current_app
import requests
import json
from lxml import objectify
from .tools import IO_Tools

from pprint import pprint

class Transkribus_Web(IO_Tools):
    """ The Transkribus_Web object implements the communication with the 
        Transkribus REST API. """
    def __init__(self, session_id=False, api_base_url="https://transkribus.eu/TrpServer/rest/"):
        # TODO: Put the api_base_url variable into a config file:
        self.cols = {}
        self.api_base_url = api_base_url
        self.session_id = session_id

    def _url(self, endpoint):
        """ Returns a full URL for a request to the REST API, 
            i.e. the API base URL + the endpoint. """
        
        return self.api_base_url + endpoint
    
    def verify(self, username, password):
        """ Logs in and logs out to check whether the credentials
            are valid on the Transkribus server."""
        
        session_id = self.login(username, password)
        if session_id:
            self.logout()
            return True
        else: 
            return False
    
    def login(self, username, password):
        """ Performs a login. If successful, the server responds by sending
            a session cookie which the function returns. """
        
        credentials = {'user': username,
                       'pw': password}
        response = requests.post(self._url("auth/login"), data=credentials)
        if response:
            r = objectify.fromstring(response.content)
            self.session_id = str(r.sessionId)
            current_app.logger.info(f"TRANSKRIBUS: User {r.firstname} {r.lastname} ({r.userId}) logged in successfully.")
            return str(r.sessionId)
        else:
            current_app.logger.error(f"TRANSKRIBUS: Login failed. HTTP status {response.status_code}.")
            return False
    
    def logout(self):
        """ Log out. """
        
        cookies = dict(JSESSIONID=self.session_id)
        response = requests.post(self._url("auth/logout"), cookies=cookies)
        if response:
            current_app.logger.info("TRANSKRIBUS: Logged out successfully.")
            return True
        else:
            current_app.logger.error(f"TRANSKRIBUS: Logout failed. HTTP status {response.status_code}: {response.content}")
            return False

    def request_endpoint(self, endpoint):
        """ Sends a GET request to a Transkribus API endpoint, the 
            "endpoint" argument being a relative path to the REST API endpoint

            Cf. the list of available endpoints:
            https://transkribus.eu/TrpServer/Swadl/wadl.html

            Depending on the content type (JSON or XML), 
            the function tries to decode the raw content of the response.
            It returns a json object or an "objectify" object (lxml). If
            the conversion fails the raw content is returned. """

        cookies = dict(JSESSIONID=self.session_id)
        
        response = requests.get(self._url(endpoint), cookies=cookies)

        if response:
            try:
                json = response.json()
                return json
            except:
                try:
                    xml = objectify.fromstring(response.content)
                    return xml
                except:
                    return response.content  # fallback option if the server returns just text
        else:
            current_app.error(f'TRANSKRIBUS: ERROR when requesting "{endpoint}". HTTP status: {response.status_code}')
            return False


    def list_collections(self):
        """ Get the basic metadata of the user's collections. 
            Stores the metadata in the "cols" dictionary. 
            Returns False if not successfull. """
        
        endpoint = "collections/list"
        collections = self.request_endpoint(endpoint)
        for col in collections:
            colId = str(col['colId'])
            if colId not in self.cols:
                self.cols[colId] = {'colName': str(col['colName']),
                                    'nrOfDocuments': col['nrOfDocuments'],
                                    'docs': {}
                                   }

            current_app.logger.info(f"{col['colId']} {col['colName']} {col['nrOfDocuments']} {col['role']}")
        return True
        
    def list_documents_in_collection(self, colId):
        """ Get the basic metadata of the documents in a collection. 
            Stores the metadata in the "cols" dictionary. 
            Returns False if not successfull.
           
            colId -- collection ID in Transkribus (int) 
            docId -- document ID in Transkribus (int)  """

        endpoint = f"collections/{colId}/list"
        documents = self.request_endpoint(endpoint)
        for doc in documents:
            docId = doc['docId']
            if docId not in self.cols[colId]['docs']:
                self.cols[colId]['docs'][docId] = {'title': doc['title'],
                                                   'nrOfPages': doc['nrOfPages'],
                                                   'pages': {}
                                                  }
            current_app.logger.info(f"TRANSKRIBUS: {doc['docId']} {doc['title']} {doc['nrOfPages']}")
        return True

    
    def list_pages_in_document(self, colId, docId):
        """ Get the basic metadata of the pages in a document. 
            Stores the metadata in the "cols" dictionary. 
            Returns False if not successfull.
           
            colId -- collection ID in Transkribus (int) 
            docId -- document ID in Transkribus (int) 
            pageNr -- page ID in Transkribus (int) """

        endpoint = f"collections/{colId}/{docId}/pages"
        pages = self.request_endpoint(endpoint)
        current_app.logger.info(f"TRANSKRIBUS: Loading pages from document {docId} with {len(pages)} pages.")
        previous = 'None'
        for page in pages:
            self.cols[colId]['docs'][docId]['pages'][str(page['pageNr'])] = {'pageId': str(page['pageId']),
                                                                             'status': str(page['tsList']['transcripts'][0]['status']),
                                                                             'imgUrl': page['url'],
                                                                             'previous': str(previous),
                                                                             'next': 'None',
                                                                            }
            # Save the current pageNr as "previous" for the next iteration:
            if previous != 'None':
                self.cols[colId]['docs'][docId]['pages'][previous]['next'] = str(page['pageNr'])
                previous = str(int(previous) + 1)
            else:
                previous = str(page['pageNr'])
                
        current_app.logger.info(f"TRANSKRIBUS: {len(self.cols[colId]['docs'][docId]['pages'])} pages loaded.")
        return True
    
    def get_page_xml(self, colId, docId, pageNr):
        """ Get the XML content of a page. 
            Stores the "objectify" object (lxml) in self.cols or returns False. 
            
            colId -- collection ID in Transkribus (int) 
            docId -- document ID in Transkribus (int) 
            pageNr -- page ID in Transkribus (int) 
            
            The "objectify" object X has two attributes: X.Metadata and X.Page. 
            X.Page is empty if there are no transcripts yet. 
            If there exists a transcription X.Page has further attributes
            (i and j are list indices counting from 0):
            
            X.Page.Metadata
                  .ReadingOrder
                  .values()   -> list containing imgFileName, width (px), height (px)
                  .TextRegion[i].Coords.attrib['points']               -> coordinates of the whole text region (1)
                                .TextEquiv.Unicode                     -> utf-8 string of the transcription of the whole text region
                                .TextLine[j].Coords.attrib['points']   -> coordinates of this line (1) (2)
                                            .BaseLine.attrib['points'] -> coordinates of this baseline (2)
                                            .TextEquiv.Unicode         -> utf-8 string of the transcription
            
            (1) Instead of .attrib['points'] you can say .values()[0].
            (2) The line is a polygon around the line of text, the BaseLine is a line below the text.
            
            You can check for the existence of attributes: if hasattr(X.Page, "TextRegion")…
            Get a list of existing attributes: X.Page.__dict__ """

        current_app.logger.info(f"Downloading pageXML for {colId}-{docId}-{pageNr}")
        cookies = dict(JSESSIONID=self.session_id)
        # Request the page XML data:
        response_XML = requests.get(self._url(f"collections/{colId}/{docId}/{pageNr}/text"), cookies=cookies)
        # Request the metadata of the latest transcript
        response_TS = requests.get(self._url(f"collections/{colId}/{docId}/{pageNr}/curr"), cookies=cookies)
        if response_XML and response_TS:
            self.cols[colId]['docs'][docId]['pages'][pageNr]['xml'] = str(response_XML.content, 'utf-8')
            self.cols[colId]['docs'][docId]['pages'][pageNr]['tsid'] = int(json.loads(response_TS.text)['tsId'])
            self.cols[colId]['docs'][docId]['pages'][pageNr]['lastUser'] = str(json.loads(response_TS.text)['userName'])
            self.cols[colId]['docs'][docId]['pages'][pageNr]['lastTimestamp'] = int(json.loads(response_TS.text)['timestamp'])
            return True
        else:
            current_app.logger.error(f"TRANSKRIBUS Failed to get the contents {colId}/{docId}, page {pageNr}. HTTP status: {response_XML.status_code}")
            return False
    
    def upload_page(self, colId, docId, pageNr, status, xml):
        """ Upload page XML data to the Transkribus server using a POST request. 
            Returns True or False.
        
            colId -- collection ID in Transkribus (int) 
            docId -- document ID in Transkribus (int) 
            pageNr -- page ID in Transkribus (int) 
            status -- the new status of the page. Possible values are NEW, IN_PROGRESS, DONE, FINAL, GT. 
            
            tsId = transcript ID of the last version of this transcription (int).
            After the upload Transkribus will generate a new transcription Id and save 
            the old one as the 'parentTsId' of the new transcription. """

        # Get the transcript ID of the latest transcription:
        current_transcript = self.request_endpoint(f"collections/{colId}/{docId}/{pageNr}/curr")
        if current_transcript:
            tsId = current_transcript['tsId']
        else:
            return False

        headers = {'Content-Type': 'text/xml'} 
        cookies = dict(JSESSIONID=self.session_id)
        params = {'status': status, 
                  'parent': tsId,
                  'overwrite': 'false'}
        data = xml

        response = requests.post(self._url(f"collections/{colId}/{docId}/{pageNr}/text"), 
                                 headers=headers,
                                 params=params,
                                 cookies=cookies, 
                                 data=data)
        
        if response:
            current_app.logger.info(f"TRANSKRIBUS: Uploaded page {colId}/{docId}/{pageNr} successfully: {response.status_code}")
            current_app.logger.debug(response.content)
            return "success", response.content.decode(encoding="utf-8")
        else:
            current_app.logger.error(f"TRANSKRIBUS: ERROR while uploading {colId}/{docId}/{pageNr}: {response.status_code}")
            current_app.logger.debug(response.content)
            return "error", response.content.decode(encoding="utf-8")