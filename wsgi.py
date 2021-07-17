#!/usr/bin/env python
import html
from flask import Flask

import lexicon


application = Flask(__name__)

@application.route('/search/oe/')
@application.route('/search/oe/<search_terms>')
def search_oe(search_terms="nawiht"):
    lex = lexicon.Lexicon('lexicon.txt')
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


@application.route('/search/reverse/')
@application.route('/search/reverse/<search_string>')
def search_reverse(search_string="nothing"):
    lex = lexicon.Lexicon('lexicon.txt')
    entries = lex.reverse_lookup(search_string)
    text = ""
    if len(entries) == 0:
        text += "<h2>Not found: " + search_string + "</h2>\n"
    else:
        for entry in entries:
            text += f"<h2 lang=\"ang\">{entry.lemma}</h2>\n<p>{html.escape(entry.definition.strip())}</p>\n"
    return text
