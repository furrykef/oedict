#!/usr/bin/env python
import html
import sqlite3

import flask
import markdown

import lexdb
import lexicon


DB_URI = 'file:lexicon.out.sqlite3?mode=ro'


application = flask.Flask(__name__)

@application.route('/search/oe/')
@application.route('/search/oe/<search_terms>')
def search_oe(search_terms="nawiht"):
    conn = sqlite3.connect(DB_URI, uri=True)
    try:
        search_terms = search_terms.split()
        text = ""
        for term in search_terms:
            entries = lexdb.lookup(term, conn)
            if len(entries) == 0:
                text += f"<h2>Not found: {html.escape(term)}</h2>\n"
            else:
                text += format_entries(entries)
    finally:
        conn.close()
    return text


@application.route('/search/reverse/')
@application.route('/search/reverse/<search_string>')
def search_reverse(search_string="nothing"):
    conn = sqlite3.connect(DB_URI, uri=True)
    try:
        entries = lexdb.reverse_lookup(search_string, conn)
        if len(entries) == 0:
            text = f"<h2>Not found: {html.escape(search_string)}</h2>\n"
        else:
            text = format_entries(entries)
    finally:
        conn.close()
    return text


def format_entries(entries):
    text = ""
    for entry in entries:
        types = "; ".join(lexicon.expand_word_type(word_type) for word_type in entry.word_types)
        text += f"<h2 lang=\"ang\">{html.escape(entry.lemma)}</h2>\n"
        text += f"<p><i>{html.escape(types)}</i></p>\n"
        text += markdown.markdown(entry.text)
    return text

