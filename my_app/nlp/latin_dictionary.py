#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
First experiment with Wolf Garbe's SymSpell 
- https://github.com/wolfgarbe/SymSpell
- https://medium.com/@wolfgarbe/1000x-faster-spelling-correction-algorithm-2012-8701fcd87a5f
- https://medium.com/@wolfgarbe/fast-approximate-string-matching-with-large-edit-distances-in-big-data-2015-9174a0968c0b

using the Python port by mammothb 
- https://github.com/mammothb/symspellpy
- https://pypi.org/project/symspellpy/
- https://symspellpy.readthedocs.io/en/latest/index.html


        app.config['DICTIONARY']
        
Created on Fri Apr 24 10:33:46 2020

@author: muellerM@ieg-mainz.de
"""

from flask import current_app
import os
import sys
import pickle
from pathlib import Path
from symspellpy.symspellpy import SymSpell, Verbosity

class Dictionary():
    def __init__(self, 
             dictionary_path,
             pickled_counts="symspell_dictionary_LA.pickle",
             max_edit_distance=2,
             prefix_length=7):
        
        self.pickled_counts = os.path.join(dictionary_path, pickled_counts)
        self.max_edit_distance = max_edit_distance
        self.prefix_length = prefix_length
        
        # Build the sym_spell, load word counts and bigrams:
        current_app.logger.info("DICTIONARY: Loading SymSpell dictionary...")
        self.sym_spell = SymSpell(self.max_edit_distance, self.prefix_length)
        self.my_load_pickle()
        
    def load_users_dictionary(self):
        pass
            
    def my_load_pickle(self):
        """ Custom loader for SymSpellPy dictionaries that were pre-pickled
            with my custom safer. The pickle is not compressed (reduces loading
            time) and the pickle also contains bigrams (not only unique words). """
        with open(self.pickled_counts, "rb") as f:
            pickle_data = pickle.load(f)
            self.sym_spell._deletes = pickle_data["deletes"]
            self.sym_spell._words = pickle_data["words"]
            self.sym_spell._max_length = pickle_data["max_length"]
            self.sym_spell._bigrams = pickle_data["bigrams"]
            current_app.logger.info(f"DICTIONARY: Loaded {len(self.sym_spell._words)} words and {len(self.sym_spell._bigrams)} bigrams from {self.pickled_counts}.")
        
        return True
       
    def suggestions_word(self, input_term):
        """ Looks up one word and returns a """
        suggestions = self.sym_spell.lookup(input_term,
                                           Verbosity.CLOSEST, # options: TOP, CLOSEST, ALL
                                           max_edit_distance=2,
                                           include_unknown=True,
                                           transfer_casing=True)
        output = []
        for s in suggestions:
            output.append({'term': s.term, 
                           'count': int(s.count),
                           'distance': int(s.distance)})

        return output
    
    def check_word(self, word):
        #print("This is symspell checking the word", word)
        try: 
            count = self.sym_spell.words[word.lower()]
            #print("Found", word, "with count", count)
            return True, count
        except:
            #print("Didn't find word", word)
            return False, 0
    
    def check_bigram(self, bigram):
        try:
            count = self.sym_spell.bigrams[bigram.lower()]
            return True, count
        except:
            return False, 0
    
    def check(self, first, second):
        """ Eats two words and checks whether they should be joined.
            Returns three values:
            1. join: words should be joined: True/False
            2. word: dictionary containing the correct term or suggestions
                     This is ALWAYS an iterable!
            3. flag: a flag with further information: "add bigram", "check manually"
    
            The checking process in detail:        
            - If the bigram (ABC DEF) exists: False, "ABC DEF".
              Example: "a Deo"
            - If the combination (ABCDEF) or both individual words (ABC and DEF)
              exist: Compare the frequency of both words with the frequency of 
              the combination. If the frequency of the combination is lower in 
              both cases: False, "ABC DEF", else: True, "ABCDEF".
              Example: "non detrahes", "prin cipio"
            - Else: Generate a dictionary containing possible spellings, their
              frequency and their edit distance.
              Example: "pin cipio"
            """
        B, bc = self.check_bigram(first+" "+second) # bigram "a Deo"
        F, fc = self.check_word(first)              # first  "a"
        S, sc = self.check_word(second)             # second   "Deo"
        C, cc = self.check_word(first+second)       # combi. "adeo"
        if B and bc*4 > cc: # the bigram is correct:
            return False, {first+" "+second: {'count': bc, 'distance': 0}}, "correct A"
        elif (F and S) or C: # compare the counts of the first word, the second 
                             # word and the combination of both words:
            if cc > 1:
                return True, {first+second: {'count': cc, 'distance': 0}}, "correct B"
            elif (fc > cc) and (sc > cc) and (fc > 0) and (sc > 0):
                return False, {first+" "+second: {'count': sc+fc/2, 'distance': 0}}, "add bigram "+f"{fc}/{sc}/{cc}"
            elif (fc == 0) or (sc == 0):
                return False, {first+" "+second: {'count': sc+fc/2, 'distance': 0}}, "check manually A"
            else:
                return True, {first+second: {'count': cc, 'distance': 0}}, "correct C"
        else: # generate a list of possible spellings
            possible_combis = self.suggestions_word(first+second)
            possible_first = self.suggestions_word(first)
            possible_second = self.suggestions_word(second)
            
            suggestions = {}
            for s in possible_combis + possible_first+possible_second + possible_second:
                if s.term not in suggestions:
                    suggestions[s.term] = {'count': s.count,
                                           'distance': s.distance}
            
            return False, suggestions, "check manually B"

def main():
    sym_spell = Dictionary()
    
    print(sym_spell.check("a", "deo"))
    print(sym_spell.check("non", "detrahes"))
    print(sym_spell.check("princi", "pio"))
    print(sym_spell.check("pinci", "pio"))
    print(sym_spell.check("co?", "tritio"))

if __name__ == "__main__":
    main()
    pass
