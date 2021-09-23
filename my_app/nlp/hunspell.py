#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 15 12:05 2021

@author: muellerM@ieg-mainz.de
"""

from flask import current_app
from hunspell import Hunspell
import os

class Hunspell_Dictionary:
    """ Latin dictionary built with cyhunspell: https://pypi.org/project/cyhunspell/.
        Dictionary.check_word(word) checks a single word (string) and returns True or False.
        Needs the Latin Hunspell dictionary by Karl Zeiler and Jean-Pierre Sutto 
        from https://latin-dict.github.io/docs/hunspell-la.zip  ↓↓↓↓  """
    def __init__(self, locale_code='la_LA', dictionary_path='hunspell-la'):
        """ Initialize the Hunspell object. 
            dictionary_path = folder that contains the hunspell-la folder which 
                              contains la_LA.aff and la_LA.dic. """
        data_dir = os.path.join(dictionary_path, "hunspell-la")
        self.hunspell = Hunspell(locale_code, hunspell_data_dir=data_dir)
        current_app.logger.info("HUNSPELL: Sucessfully initialized Hunspell dictionary.")

    def check(self, word):
        """ Eats a word (string), checks whether it is in the dictionary, and 
            returns True/False. """
        if self.hunspell.spell(word):
            return word
        else:
            return False



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