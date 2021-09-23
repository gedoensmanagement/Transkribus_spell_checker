#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Functions to clean the raw transcript from Transkribus:
    - resolve abbreviations
    - tokenize a line into Word objects
    - resolve makrons
    - resolve hyphenation and line breaks
    - resolve the last line on a page / page breaks.

Created on Fri Apr 17 16:59:51 2020

@author: muellerm@ieg-mainz.de
"""

import re
from itertools import product
from ..io.tools import IO_Tools
from flask import current_app

class Cleaner:
    """ Provides functions for cleaning a text using a replacement table
        and a dictionary. 
        The replacement table contains two columns:
            1. REGEX patterns for searching abbreviations and 
            2. their replacements as strings. 
        Lines beginning with "#" are treated as comments.
        The dictionary checks if a word or bigram exists, knows its frequency 
        in a text corpus, and can provide suggestions for correct spelling 
        based on (Bayesian) statistics (via the symspellpy package).
        "whitaker" is another dictionary that will be checked in case 
        symspell does not know the word.
        """

    def __init__(self, replacement_table_url, printers_errors_url,
                 printers_errors={},
                 punctuation_to_clean=".,;:?-=()]", 
                 remove_blanks_iterations=5):
        self.punctuation_to_clean = punctuation_to_clean
        self.remove_blanks_iterations = remove_blanks_iterations
        self.dictionary = current_app.dictionary
        self.whitaker = current_app.whitaker
        self.replacement_table_url = replacement_table_url
        self.printers_errors_url = printers_errors_url
        self.printers_errors = printers_errors
        
        current_app.logger.info("CLEANER: Loading abbreviations and printer's errors...")
        self.replacement_table = IO_Tools.load_google_sheet(self.replacement_table_url)

    def reload_tables(self):
        current_app.logger.info("CLEANER: Reloading abbreviations ...")
        self.replacement_table = IO_Tools.load_google_sheet(self.replacement_table_url)
        return True
        

    def clean_page(self, TR, colId, docId, pageNr):
        thisPage = TR.cols[colId]['docs'][docId]['pages'][pageNr]
        for region in thisPage['regions']:
            for lineIdx, line in enumerate(region['lines']):
                text = self.replace_abbreviations(line['raw_data'])
                text = self.replace_printers_errors(text)
                words = self.tokenize(text)
                words = self.resolve_makrons(words)
                line['words'] = words

        self.resolve_linebreaks(thisPage)
        return TR

    def spellcheck_word(self, word, tricks=True):
        """ Checks the word (dict) for spelling errors, returns the result 
            in the 'spellcheck' attribute of the word. 
            Spellchecking has three steps:
                1) Ask symspell,
                2) if symspell doesn't know the word: ask Whitaker's Words. 
                3) if still unknown: generate suggestions with symspell. """

        #print("spellchecking word:", word)    
        if word['data_type'] == 'word': # ask symspell
            #print("It's an actual word!")
            W, wc = self.dictionary.check_word(word['data'])
            if tricks and word['data'].endswith("que"):
                wordmod = word['data'][:-3]
                W2, wc2 = self.dictionary.check_word(wordmod)
            else: 
                tricks = False
            #print("Symspell says", W, wc)
            if W:
                word['spellcheck'] = {'spelling': 'ok'}
                #print("symspell knows it")
            elif self.whitaker.check(word['data']): # ask Whitaker's Words if symspell does not know
                word['spellcheck'] = {'spelling': 'ok whitaker'}
                #print("whitaker knows it")
            elif tricks:
                if W2:
                    word['spellcheck'] = {'spelling': 'ok'}
                elif self.whitaker.check(wordmod):
                    word['spellcheck'] = {'spelling': 'ok whitaker'}
                else: # generate suggestions with symspell if Whitaker can't help
                    #print("nobody knows it: generating suggestions...")
                    word['spellcheck'] = {'spelling': 'check manually',
                                          'suggestions': self.dictionary.suggestions_word(word['data'])}
            else: # generate suggestions with symspell if Whitaker can't help
                #print("nobody knows it: generating suggestions...")
                word['spellcheck'] = {'spelling': 'check manually',
                                      'suggestions': self.dictionary.suggestions_word(word['data'])}
        else:
            word['spellcheck'] = {'spelling': 'ok'}
            
        return word

    def spellcheck_page(self, TR, colId, docId, pageNr):
        thisPage = TR.cols[colId]['docs'][docId]['pages'][pageNr]
        for region in thisPage['regions']:
            #print("spellchecking region", region['readingOrderIndex'], region['structureType'])
            for line in region['lines']:
                #print("spellchecking line", line['readingOrderIndex'])
                for word in line['words']:
                    word = self.spellcheck_word(word)
        return TR
    
    def spellcheck_line(self, line):
        for word in line['words']:
            word = self.spellcheck_word(word)
            
        return line

    def replace_printers_errors(self, text):
        """ Simple search-replace-procedure to get rid of known spelling 
            errors of the 16th-century printers. """
        for error, correction in self.printers_errors.items():
            repl = correction['correction']
            
            def func(match):
                """ Preserves the case of the original text during 
                    regex subtitiution. """
                g = match.group()
                if g.islower(): return repl.lower()
                if g.istitle(): return repl.title()
                if g.isupper(): return repl.upper()
                return repl

            # search whole words only (to avoid things like aput→apud vs. caput→capud)
            error = re.compile(r'\b' + error + r'\b', flags=re.IGNORECASE)  

            text = re.sub(error, func, text)
            
        return text

    # DONE
    def replace_abbreviations(self, text):
        """ Resolves all abbreviations except the n/m-makrons.
            Uses the replacement table (self.table) to search for 
            abbreviations etc. and replacements. 
            returns the cleaned text. """
        
        for pattern, replacement in self.replacement_table.items():
            repl = replacement['replacement']

            pattern = r"{}".format(pattern) # convert pattern to raw string
                                            # (otherwise \B doesn't work as expected!!)

            # "func" preserves the case of the original text:
            def func(match):
                g = match.group()
                if g.islower(): return repl.lower()
                if g.istitle(): return repl.title()
                if g.isupper(): return repl.upper()
                return repl
            
            text = re.sub(pattern, func, text, flags=re.IGNORECASE)

        return text

    # DONE
    def tokenize(self, text):
        """ Eats a string containing the normalized text.
            Tokenizes the string by separating letters and punctuation.
            Returns a list of word objects, i.e. dictionaries.
            To distinguish correctly between words and punctuation, 
            the abbreviations in the text have to be resolved 
            /before/ the tokenization. """

        words = []
        for input_word in re.split("([\s.,;:?\-=()\]])", text):
            # This pattern generates some empty elements that have
            # to be filtered out. 
            if input_word != " " and input_word != '': 
                if input_word in ".,;:?-=()]":
                    data_type = "punctuation"
                elif "#" in input_word:  
                    # TODO könnte man verbessern: wenn das Wort außer
                    # "#" noch lesbare Buchstaben enthält, ist es nicht
                    # gänzlich "unreadable".
                    data_type = "unreadable"
                else:
                    data_type = "word"

                if data_type != "word":
                    words.append({'data_type': data_type,
                                 'data': input_word,
                                 'spellcheck': {'spelling': 'ok'},
                                 'hasComment': False})
                else:
                    words.append({'data_type': data_type,
                                 'data': input_word,
                                 'hasComment': False})

        return words

    def resolve_makrons(self, words):
        """ Resolve the makrons for a list of words (which are dicts), 
            except the first and last word. Those will be 
            checked later while resolving the line breaks. """
            
        # Search for the last word in the line (avoiding punctuation, unreadable, etc.)
        if words[-1]['data_type'] == "word":
            offset = -1
        elif len(words) > 1:
            if words[-1]['data_type'] != "word" and words[-2]['data_type'] != "word":
                offset = -3
            elif words[-1]['data_type'] != "word":
                offset = -2            
        else:
            return words

        # Resolve makrons now:
        for word in words[1:offset]:
            if word['data_type'] == "word":
                word['data'] = self.replace_makrons(word['data'])
        return words

    def replace_makrons(self, unresolved):
        """ Replaces makrons with 'n' or 'm' after checking the self.dictionary
            for the correct replacement. Returns resolved word. """
        
        thisword = unresolved.lower()
        replacements = {'ā': 'a',
                        'ē': 'e',
                        'ō': 'o',
                        'ū': 'u',
                        'ī': 'i'}
        mns = ['m', 'n']
        candidates = []
        # Get a list of all vocals with makrons in this word:
        makrons = re.findall(r'[āēīōū]', thisword)
        if len(makrons) != 0:
            # Generate lists with all possible replacement comibinations:
            # (https://www.geeksforgeeks.org/python-extract-combination-mapping-in-two-lists/)
            combinations = list(list(zip(makrons, e)) for e in product(mns, repeat=len(makrons)))
            # For every combination, ask the dictionary if the word exists:
            for c in combinations:
                new = thisword
                # perform all the replacements suggested in this combination:
                for pair in c:
                    new = re.sub(pair[0], replacements[pair[0]]+pair[1], new, count=1)
                # if the new word exists, add it to the list of candidates
                exists, count = self.dictionary.check_word(new)
                if exists: 
                    candidates.append((count, new))
            # If there are candidates: return the most frequent candidate 
            # (i.e. with the highest count)
            if len(candidates) != 0:
                #print("DEBUG candidates for", thisword, candidates)
                candidates = max(sorted(candidates, reverse=True))[1]
                return candidates
            else:
                # if there are no candidates: replace the makron with "●"
                for k,v in replacements.items():
                    unresolvable = re.sub(k, v+'●', unresolved)
                return unresolvable
        else:
            return unresolved
    
    def clean_word(self, text):
        """ Wrapper function that replaces abbreviations, printer's errors and
            makrons in a word (i.e. a string). Words that are joined during 
            the resolution of line breaks still need this treatment. """
        cleaned = self.replace_abbreviations(text)
        cleaned = self.replace_printers_errors(cleaned)
        cleaned = self.replace_makrons(cleaned)
        return cleaned
    
    def resolve_linebreaks(self, page):
        """ Eats a page. Scrutinizes the first and the last word of every
            line on the page and decides whether the last word of a line 
            and the first word of the following line belong together. If 
            so, the parts are joined and the remaining empty position is
            deleted or (if the whole line would become empty) marked as 
            "empty". 
            
            NB: The first and the last word on the page are NOT
            processed by this function! You have to treat them separately 
            when you join pages. """
        
        nextLine = None
        
        for regionId, region in enumerate(page['regions']):
            for lineId, line in enumerate(region['lines']):
                
                # ====================================
                # Check if this line is not empty or already done
                if len(line['words']) == 1 and line['words'][0]['data_type'] == "empty":
                    #print("CLEANER: Line", lineId, "is empty.")
                    continue # This line is empty!

                """
                if line['hyphenation_resolved'] == True:
                    print("Line", lineId, "has already been processed.")
                    continue # This line has already been processed.
                """
                
                # ====================================
                # Check if there exists a next line
                if line == region['lines'][-1] and region == page['regions'][-1]:
                    continue # This is the last line on the page. No more regions to come.
                elif line == region['lines'][-1]:
                    # If the next region is not empty, take its first line as next line
                    if len(page['regions'][regionId + 1]['lines']) != 0:
                        nextLine = page['regions'][regionId + 1]['lines'][0]
                    else:
                        print("Next region is empty", lineId)
                        continue
                else: # There is a next line in this region. Take it!
                    nextLine = page['regions'][regionId]['lines'][lineId + 1]

                # ====================================
                # Now that we are sure that there is a nextLine,
                # check if the nextLine is not empty and get the 
                # first word of the nextLine:
                if len(nextLine['words']) == 0:
                    #print("Next line is empty: nothing to join in line", lineId)
                    continue # nextLine is empty
                elif nextLine['words'][0]['data_type'] == "empty":
                    #print("First word of next line is empty: nothing to join in line", lineId)
                    continue # first word of nextLine is empty
                else:
                    nextWord = nextLine['words'][0]

                # ====================================
                # Now that we are sure that there is a nextword
                # scrutinize the last word of this line:

                thisWord = line['words'][-1]

                # -----------------------------------
                # Last word is PUNCTUATION
                if thisWord['data_type'] == "punctuation":
                    # take the penultimate word
                    # If it's a hyphenated word: join it with the next word!
                    if line['words'][-1]['data'] == "-" or line['words'][-1]['data'] == "=":
                        # cut off the "-" or "=", i.e. the last word of this line
                        line['words'].pop()
                        # join the two words
                        line = self.join_words(True, 
                                               line, -1,
                                               nextLine,
                                               "hyphenated")
                        continue
                    # If it's a punctuation but not "-/=" --> ends of a part of speech
                    else: 
                        # do NOT join the two words
                        line = self.join_words(False,
                                               line, -2,
                                               nextLine,
                                               "ends a part of speech")
                        continue
                # -----------------------------------
                # Last word is a NORMAL WORD!
                elif thisWord['data_type'] == "word":
                    # If the first letter of the nextword is uppercase:
                    if nextWord['data'][0].isupper(): # nextword is a proper name
                        line = self.join_words(False,
                                               line, -1,
                                               nextLine,
                                               "capitalized")
                        continue
                    else:
                        line = self.join_words(True,
                                               line, -1,
                                               nextLine,
                                               "try joining")

                else: # It's something else, e.g. "unreadable".
                    print(f"Leaving out line {regionId}-{lineId}: unknown data_type = {thisWord['data_type']}.")
                    continue                
                
    def join_words(self, yes_no, thisLine, thisWordIndex, nextLine, message):
        """ Eats 1) a boolean whether the words should be joined or not, 
            2) thisLine object and the index of the last word (-1 or -2),
            3) nextLine object, and a message for logging. 
    
            The function a) cleans the words, b) tries to join them (if 
            yes_no is True), and c) takes care of the nextLine if it is
            empty because of the whole process."""
        if yes_no == False: # do NOT join
            # Clean the words
            thisLine['words'][thisWordIndex]['data'] = self.clean_word(thisLine['words'][thisWordIndex]['data'])
            nextLine['words'][0]['data'] = self.clean_word(nextLine['words'][0]['data'])
            #print(thisLine['words'][thisWordIndex]['data'], nextLine['words'][0]['data'], "|",message)
            return thisLine
        else:               # DO join
            clean_up = True
            if message == "hyphenated": # if hyphenated, JOIN them in any case
                combi = self.clean_word(thisLine['words'][thisWordIndex]['data'] + nextLine['words'][0]['data'])
                thisLine['words'][thisWordIndex]['data'] = combi
                # spellcheck the combi:
                thisLine['words'][thisWordIndex] = self.spellcheck_word(thisLine['words'][thisWordIndex])
                del nextLine['words'][0]
                #print(thisLine['words'][thisWordIndex]['data'], "|", message)
            else: # ask the dictionary if thisword and nextword fit together:
                first = self.clean_word(thisLine['words'][thisWordIndex]['data'])
                second = self.clean_word(nextLine['words'][0]['data'])
                bigram = first + " " + second
                combi = self.clean_word(thisLine['words'][thisWordIndex]['data'] + nextLine['words'][0]['data'])
                
                B, bc = self.dictionary.check_bigram(bigram)   # bigram      "a Deo"
                F, fc = self.dictionary.check_word(first)      # first       "a"
                S, sc = self.dictionary.check_word(second)     # second        "Deo"
                C, cc = self.dictionary.check_word(combi)      # combination "adeo"
                #W = self.whitaker.check(combi) # ask Whitaker for combination "adeo"

                # The bigram is correct: do not join.
                if B and bc*4 > cc:
                    thisLine['words'][thisWordIndex]['data'] = first
                    nextLine['words'][0]['data'] = second
                    thisLine['words'][thisWordIndex]['spellcheck'] = {'spelling': 'ok'}
                    nextLine['words'][0]['spellcheck'] = {'spelling': 'ok'}
                    #print("BIGRAM", thisLine['words'][thisWordIndex]['data'], nextLine['words'][0]['data'], "|", "bigram in dictionary")
                    clean_up = False
  
                # First, second and combination all have a count > 0.
                # We have to decide which is the most likely solution:
                elif (F and S) or C: # compare the counts of the first word, 
                                     # the second word and the combination 
                                     # of both words:
                    if cc > 0: # JOIN because the combination is correct
                        thisLine['words'][thisWordIndex]['data'] = combi
                        del nextLine['words'][0]
                        thisLine['words'][thisWordIndex]['spellcheck'] = {'spelling': 'ok'}
                        #print(thisLine['words'][thisWordIndex]['data'], "|", "combination in dictionary (A)")
                        
                    # do not join because both words are correct individually
                    elif (fc > cc) and (sc > cc) and (fc > 0) and (sc > 0):  
                        thisLine['words'][thisWordIndex]['data'] = first
                        nextLine['words'][0]['data'] = second
                        thisLine['words'][thisWordIndex]['spellcheck'] = {'spelling': 'ok'}
                        nextLine['words'][0]['spellcheck'] = {'spelling': 'ok'}
                        #print("BIGRAM", thisLine['words'][thisWordIndex]['data'], nextLine['words'][0]['data'], "|",
                        #      f"add bigram ({fc}/{sc}/{cc})")
                        clean_up = False
                        
                    # do not join and check manually because they do not fit together and they both have a count <= 1
                    elif (fc == 0) or (sc == 0): # 
                        thisLine['words'][thisWordIndex]['data'] = first
                        nextLine['words'][0]['data'] = second
                        thisLine['words'][thisWordIndex]['spellcheck'] = {'spelling': 'check manually',
                                                                 'suggestions': self.dictionary.suggestions_word(first)}
                        nextLine['words'][0]['spellcheck'] = {'spelling': 'check manually',
                                                     'suggestions': self.dictionary.suggestions_word(second)}
                        #print(thisLine['words'][thisWordIndex]['data'], nextLine['words'][0]['data'], "|", "check manually")
                        clean_up = False
                     
                    # JOIN in case none of the conditions applied.
                    else: 
                        thisLine['words'][thisWordIndex]['data'] = combi
                        del nextLine['words'][0]
                        thisLine['words'][thisWordIndex]['spellcheck'] = {'spelling': 'ok'}
                        #print(thisLine['words'][thisWordIndex]['data'], "|", "combination in dictionary (B)")
                
                # Neither the individual words nor the combination is correct.
                # We will generate suggestions for correct spelling:
                else: 
                    # generate three lists of possible spellings
                    possible_combis = self.dictionary.suggestions_word(bigram)
                    possible_first = self.dictionary.suggestions_word(first)
                    possible_second = self.dictionary.suggestions_word(second)
                    
                    suggestions = []
                    for s in possible_combis + possible_first + possible_second + possible_second:
                        #print(s, s['distance'])
                        if s['term'] not in [sub['term'] for sub in suggestions]:
                            suggestions.append(s)
                    thisLine['words'][thisWordIndex]['data'] = first
                    nextLine['words'][0]['data'] = second
                    thisLine['words'][thisWordIndex]['spellcheck'] = {'spelling': 'check manually',
                                                                      'suggestions': suggestions}
                    nextLine['words'][0]['spellcheck'] = {'spelling': 'check manually',
                                                          'suggestions': suggestions}
                    #print(thisLine['words'][thisWordIndex]['data'], nextLine['words'][0]['data'], "|","check manually")
                    clean_up = False
                
            if clean_up:
                # Clean up the nextLine
                # If nextLine looses all its words due to the joining
                # process, it cannot remain completely empty because
                # this would break the rest of the code as well as the 
                # correct order of the line_numbers! Therefore, we
                # insert one empty word as a dummy:
                if len(nextLine['words']) == 0:
                    print("CLEANER: !! Line", nextLine['readingOrderIndex'], "is EMPTY after resolving hyphenation.")
                    nextLine['words'].insert(0, {'data_type': 'empty',
                                                 'data': ''})                # If the new composite word was followed by a punctuation:
                # move this punctuation to the end of thisLine.
                if nextLine['words'][0]['data_type'] == "punctuation":
                    thisLine['words'].append(nextLine['words'][0])
                    del nextLine['words'][0]
                # And again: make sure the next line has at least one empty word.
                if len(nextLine['words']) == 0:
                    print("CLEANER: !! Line", nextLine['readingOrderIndex'], "is EMPTY after resolving hyphenation.")
                    nextLine['words'].insert(0, {'data_type': 'empty',
                                                 'data': ''})

        return thisLine

    def remove_punctuation(self, mytext):
        """ Removes punctuation. """
        for char in self.punctuation_to_clean:
            mytext = mytext.replace(char, "")
        return mytext

    def remove_multiple_blanks(self, mytext):
        """ Removes multiple blanks and blanks at the beginning
            or the end of the line. """
        for i in range(self.remove_blanks_iterations):
            mytext = mytext.replace("  ", " ")
        return mytext.strip()

    def auto_spacer(self, line):
        """ Reads a Line object and joins all its words to a string
            while putting spaces at the correct places (e.g. no space
            before punctuation, special treatment for parenthesis etc.). 
            Returns the line as a string. """
        newline = ""
        no_leading_space = True
        for word in line.children:
            if word.data_type == "word":
                if no_leading_space == True:
                    newline += word.data
                    no_leading_space = False
                else:
                    newline += " " + word.data
            else:
                if word.data == "(":
                    newline += " " + word.data
                    no_leading_space = True
                else:
                    newline += word.data
        
        return newline
