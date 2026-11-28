import os
import sys

import django

sys.path.insert(0, os.path.abspath('..'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'cafeteria.settings'
django.setup()

project = 'Campus Cafeteria'
author = 'Group 10'
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon', 'sphinx.ext.viewcode']
html_theme = 'alabaster'
exclude_patterns = ['_build']