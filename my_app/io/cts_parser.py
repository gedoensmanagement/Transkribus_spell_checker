# -*- coding: utf-8 -*-
"""
A collection of functions that can extract additional data fields from 
the work and passage fields of a Cts object. Which additional fields 
are possible depends on the namespace. The "parse_cts" function recognizes
the namespace and decides which function to use for the extraction. 
At the end of the whole process the Cts object with its additional data fields
will be returned.

Created on Thu Sep 17 17:58:49 2020

@author: muell018
"""

import re

def parse_cts(cts_object):
    namespaces = {'zt': zotero_parser,
                  'tr': transkribus_parser,
                  'zs': censorship_parser}
    
    namespaces[cts_object.namespace](cts_object)    

def zotero_parser(zt):
    """ Treats the Cts object as a Zotero cts object. """
    #print("zotero_parser")
    #print(zt)
    if zt.m.group(4) != '':
        zt.mode = zt.m.group(4)
        zt.number = zt.m.group(6)
    #print(f"Zotero extras: mode = {zt.mode}, number = {zt.number}")
    
    return zt
    
def transkribus_parser(tr):
    """ Treats the Cts object as a Transkribus cts object. """
    #print("transkribus_parser")
    #print(tr)
    tr.col = tr.m.group(2)
    tr.doc = tr.m.group(3)
    tr.page = tr.m.group(5)
    #print(f"Transkribus extras:\ncol = {tr.col}\ndoc = {tr.doc}\npage = {tr.page}")
    if tr.m.group(6) != '':
        tr.rl = ''
        p = re.compile(r'r(\d?)l?(\d?)')
        m = p.match(tr.m.group(6))
        if m.group(1):
            tr.region = m.group(1)
            tr.rl += "r"+tr.region
            #print(f"region = {tr.region}")
        if m.group(2):
            tr.line = m.group(2)
            tr.rl += "l"+tr.line
            #print(f"line = {tr.line}")
    if tr.subreference != '':
        tr.word = tr.subreference
        #print(f"word = {tr.word}")
    
    return tr
    
def censorship_parser(zs):
    """ Treats the Cts object as a censorship cts. """
    #print("censorship_parser: yet to be programmed... ")



def main():
    pass

if __name__ == "__main__":
    main()