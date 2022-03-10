#!/usr/bin/env python
import html

import flask
import markdown
from sqlitedict import SqliteDict

import index
import lexicon


application = flask.Flask(__name__)

@application.route('/search/oe/')
@application.route('/search/oe/<search_terms>')
def search_oe(search_terms="nawiht"):
    search_terms = search_terms.split()
    text = ""
    with open('lexicon.txt', 'r', encoding='utf-8') as lexfile:
        with SqliteDict('index.sqlite') as db:
            for term in search_terms:
                entries = index.lookup(term, lexfile, db)
                if len(entries) == 0:
                    text += f"<h2>Not found: {html.escape(term)}</h2>\n"
                else:
                    text += format_entries(entries)
            return text


@application.route('/search/reverse/')
@application.route('/search/reverse/<search_string>')
def search_reverse(search_string="nothing"):
    lex = lexicon.Lexicon('lexicon.txt')
    entries = lex.reverse_lookup(search_string)
    text = ""
    if len(entries) == 0:
        text += f"<h2>Not found: {html.escape(search_string)}</h2>\n"
    else:
        text += format_entries(entries)
    return text


def format_entries(entries):
    text = ""
    for entry in entries:
        types = "; ".join(lexicon.expand_word_type(word_type) for word_type in entry.word_types)
        text += f"<h2 lang=\"ang\">{html.escape(entry.lemma)}</h2>\n"
        text += f"<p><i>{html.escape(types)}</i></p>\n"
        text += markdown.markdown(entry.text)
    return text

