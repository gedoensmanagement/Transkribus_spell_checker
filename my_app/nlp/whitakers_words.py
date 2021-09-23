#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May  4 11:53:56 2020

@author: muellerM@ieg-mainz.de
"""

import os
import sys
import subprocess
from pathlib import Path
import re

class Whitakers_Words():
    """ Ask the Latin dictionary 'words' by William A. Whitaker by using 
        the check(word) function provided in this class. """

    def __init__(self, dictionary_path):
        if sys.platform == "win32": # other path and executable on my office PC (for local testing)
            self.wordspath = "u:\Dokumente\Synchronisation\Sprachen\Latein\words-windows"
            self.wordsexe = "words.exe"
        else:
            self.wordspath = os.path.join(dictionary_path, "words-linux")
            self.wordsexe = "words"

        if not Path(self.wordspath, self.wordsexe).exists():
            print("ERROR: Whitaker's Words not found in", str(Path(self.wordspath, self.wordsexe)))
        
        self.letters_only = re.compile("^[a-zA-Z]+$")
        
    def request(self, word):
        """ Requests Whitaker's Words for a word and 
            returns the raw command line response. """

        """ We have to cd into the directory of the 'words' executable in 
            to make this working… """

        if self.letters_only.match(word):
            current_directory = os.getcwd()
            #print("changing directory from", current_directory, "to", self.wordspath)
            os.chdir(str(self.wordspath))
            exe = "./" + self.wordsexe
            #print("executing", exe, "now")
            response = subprocess.run([exe, word], capture_output=True, encoding="utf-8", check=True).stdout
            #response = subprocess.Popen([exe, word], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            #print(response)
            #print("changing back to", current_directory)
    
            os.chdir(current_directory)
        else: 
            response = False
            
        return response

    def check(self, word):
        """ Checks if a word is found in Whitaker's 'Words' dictionary. """
        
        word = word.lower()
        #print("This is Whitaker's Words looking for", word)
        
        # Cache not yet implemented here because we check only a few words per page
        #if word in self.cache:  # Word already cached
        #    response = self.cache[word]['response']
        #else:
        #    response = self.request(word).stdout
        #    self.cache[word] = {'response': response}
        
        response = self.request(word)
        #print("Whitaker says", response)
        if not response:
            return False
        elif "UNKNOWN" in response or "Two words" in response or "Word mod" in response or "est                  TACKON" in response: #   or "TACKON" in response or "probably incorrect" in response
            #print("Whitaker doesn't know", word)
            return False
        else:
            return True

def main():
    dictionary = Whitakers_Words()
    print(dictionary.check("amare"))
    print(dictionary.check("profundissimo"))
    pass

if __name__ == "__main__":
    main()