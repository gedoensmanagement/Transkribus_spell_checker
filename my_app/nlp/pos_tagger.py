# -*- coding: utf-8 -*-
"""
Provides the PosTagger class that uses the new LamonPy package (Sept 2020) 
to PoS tag Latin words. PoS = part of speech.

Created on Fri Oct  2 16:38:51 2020

@author: muell018
"""
from lamonpy import Lamon

class PosTagger:
    """ Uses the new LamonPy package (Sept 2020) to PoS tag Latin words. """
    def __init__(self):
        self.lamon = Lamon()
    
    def tag(self, word):
        score, tagged = self.lamon.tag(word)[0]
        return {word: {'lemma': tagged[0][2], 
                       'wordclass': tagged[0][3][0]}}
    
def main():
    p = PosTagger("")
    print(p.tag("porro"))

if __name__ == "__main__":
    main()