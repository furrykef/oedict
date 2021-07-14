#!/usr/bin/env python
import html
from flask import Flask

import lexicon


application = Flask(__name__)

@application.route('/search/oe/')
@application.route('/search/oe/<search_terms>')
def dict(search_terms="nawiht"):
    lex = lexicon.Lexicon('dict.txt')
    search_terms = search_terms.split()
    text = ""
    for term in search_terms:
        entries = lex.lookup(term)
        if len(entries) == 0:
            text += "<h2>Not found: " + term + "</h2>\n"
        else:
            for entry in entries:
                text += f"<h2 lang=\"ang\">{entry.lemma}</h2>\n<p>{html.escape(entry.definition.strip())}</p>\n"
    return text

