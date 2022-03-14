#!/usr/bin/env python
import html

import flask
import markdown

import lexdb
import lexicon


LEX_FILENAME = 'lexicon.txt'
DB_FILENAME = 'lexicon.out.sqlite3'


application = flask.Flask(__name__)

@application.route('/search/oe/')
@application.route('/search/oe/<search_terms>')
def search_oe(search_terms="nawiht"):
    with lexdb.LexDB(LEX_FILENAME, DB_FILENAME) as db:
        search_terms = search_terms.split()
        text = ""
        for term in search_terms:
            entries = db.lookup(term)
            if len(entries) == 0:
                text += f"<h2>Not found: {html.escape(term)}</h2>\n"
            else:
                text += format_entries(entries)
    return text


@application.route('/search/reverse/')
@application.route('/search/reverse/<search_string>')
def search_reverse(search_string="nothing"):
    with lexdb.LexDB(LEX_FILENAME, DB_FILENAME) as db:
        entries = db.reverse_lookup(search_string)
        if len(entries) == 0:
            text = f"<h2>Not found: {html.escape(search_string)}</h2>\n"
        else:
            text = format_entries(entries)
    return text


def format_entries(entries):
    text = ""
    for entry in entries:
        types = "; ".join(lexicon.expand_word_type(word_type) for word_type in entry.word_types)
        text += f"<h2 lang=\"ang\">{html.escape(entry.lemma)}</h2>\n"
        text += f"<p><i>{html.escape(types)}</i></p>\n"
        text += markdown.markdown(entry.text)
    return text

