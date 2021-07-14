#!/usr/bin/env python
import html
from flask import Flask

import oedict


application = Flask(__name__)

@application.route('/search/oe/')
@application.route('/search/oe/<search_terms>')
def dict(search_terms="nawiht"):
    index = oedict.read_lexicon('dict.txt')
    search_terms = search_terms.split()
    text = ""
    for term in search_terms:
        try:
            entries = index[oedict.normalize(term)]
        except KeyError:
            text += "<h2>Not found: " + term + "</h2>\n"
        else:
            for entry in entries:
                text += f"<h2 lang=\"ang\">{entry.lemma}</h2>\n<p>{html.escape(entry.definition.strip())}</p>\n"
    return f"""
<!doctype html>
<html>
  <head>
    <title>oedict: {search_terms}</title>
  </head>
  <body>
    {text}
  </body>
"""

