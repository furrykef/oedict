import argparse
import sys
import textwrap

from . import lexdb
from . import lexicon


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    p = argparse.ArgumentParser(description="Kef's Old English dictionary")
    p.add_argument('-l', '--lexicon', default='lexicon.txt', help="filename of lexicon")
    p.add_argument('-i', '--interactive', action='store_true', help="interactive mode")
    p.add_argument('-r', '--reverse', action='store_true', help="reverse lookup")
    p.add_argument('-d', '--db', default='lexicon.out.sqlite3', help="filename of sqlite database")
    p.add_argument('--abc', action='store_true', help="check lexicon is in alphabetical order")
    p.add_argument('search_terms', nargs='*')
    args = p.parse_args(argv)
    with lexdb.LexDB(args.lexicon, args.db) as db:
        if args.abc:
            db.check_alphabetization()
        for term in args.search_terms:
            lookup(db, term, args.reverse)
        if args.interactive:
            interactive_mode(db, args.reverse)


def interactive_mode(db, reverse):
    while True:
        try:
            search_str = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        lookup(db, search_str, reverse)


def lookup(db, search_str, reverse):
    if reverse:
        entries = db.reverse_lookup(search_str)
    else:
        entries = db.lookup(search_str)
    if len(entries) == 0:
        print("Not found:", search_str, "\n")
    else:
        for entry in entries:
            types = "; ".join(lexicon.expand_word_type(word_type) for word_type in entry.word_types)
            print(f"{entry.lemma}: {types}")
            print(textwrap.indent(entry.text, " "*4))

