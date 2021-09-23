# -*- coding: utf-8 -*-
"""
Created on Thu Sep 17 17:30:07 2020

@author: muell018

run the test
a) from the console:
    python -m unittest test_cts.py
b) from the IDE:
    this works because we say "unittest.main()" at the end.
"""

import unittest
import cts

test_cases = [{'cts': "zt:soto1554:no.40",
               'namespace': "zt",
               'work': "soto1554",
               'passage': "no.40",
               'subreference': ""},
              {'cts': "zt:wild1550b:fol.10r",
               'namespace': "zt",
               'work': "wild1550b",
               'passage': "fol.10r",
               'subreference': ""},
              {'cts': "tr:37299.291391:165:r2l15@8",
               'namespace': "tr",
               'work': "37299.291391",
               'passage': "165.r2l15",
               'subreference': "8"},
              {'cts': "tr:37299.291391:165:r2l15",
               'namespace': "tr",
               'work': "37299.291391",
               'passage': "165.r2l15",
               'subreference': ""},
              {'cts': "zs:ProtF.Apg:05",
               'namespace': "zs",
               'work': "ProtF.Apg",
               'passage': "05",
               'subreference': ""}]

def check_cts_object(test_case, cts_object):
    namespace = True if test_case['namespace'] == cts_object.namespace else False
    work = True if test_case['work'] == cts_object.work else False
    passage = True if test_case['passage'] == cts_object.passage else False
    subreference = True if test_case['subreference'] == cts_object.subreference else False
    
    return namespace and work and passage and subreference
    

class TestCalc(unittest.TestCase):
    def test_from_string(self):
        for idx, test_case in enumerate(test_cases):
            print(f"\nTest case no. {idx+1}:")
            x = cts.Cts().from_string(test_case['cts'])
            result = check_cts_object(test_case, x)
            self.assertTrue(result, f"\nERROR: cts decoding failed in test_case no. {idx+1}:\n\"{test_case['cts']}\"")

if __name__ == "__main__":
    unittest.main()