#!/usr/bin/env python
"""Setup file and install script SciLife python scripts.
"""
from setuptools import setup, find_packages
import sys
import os
import glob

setup(name = "LIMS2DB",
    version = "1.0",
    author = "Maya Brandi",
    author_email = "maya.brandi@scilifelab.se",
    description = "Pacage make and load statusDB objects out of Lims data",
    scripts = ['flowcell_summary_uppload_LIMS.py','project_summary_upload_LIMS.py'],
    py_modules = ['objectsDB','statusDB_utils','lims_utils','helpers'])

