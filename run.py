#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import the app from the package and run it.

Created on Mon May 11 15:23:44 2020

@author: muellerM@ieg-mainz.de
"""

import os

if __name__ == '__main__':
    # Make sure that debugging is on when we are in development mode:
    if os.environ.get("FLASK_ENV") == "development":
        print("FLASK: Entering development mode...")
        app.run(port=5000, debug=True, use_reloader=False, threaded=True, processes=2)
    else:
        app.run(port=5000)
