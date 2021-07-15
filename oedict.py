#!/usr/bin/env python
import argparse
import sys

import lexicon


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    p = argparse.ArgumentParser(description="Kef's Old English dictionary")
    p.add_argument('-l', '--lexicon', default='lexicon.txt', help="filename of lexicon")
    p.add_argument('-i', '--interactive', action='store_true', help="interactive mode")
    p.add_argument('-r', '--reverse', action='store_true', help="reverse lookup")
    p.add_argument('--dump', action='store_true', help="dump debug stuff")
    p.add_argument('search_terms', nargs='*')
    args = p.parse_args(argv)
    lex = lexicon.Lexicon(args.lexicon)
    if args.dump:
        lex.dump()
    for term in args.search_terms:
        lookup(lex, term, args.reverse)
    if args.interactive:
        interactive_mode(lex, args.reverse)


def interactive_mode(lex, reverse):
    while True:
        try:
            search_str = input("> ").strip()
        except KeyboardInterrupt:
            print()
            break
        lookup(lex, search_str, reverse)


def lookup(lex, search_str, reverse):
    if reverse:
        entries = lex.reverse_lookup(search_str)
    else:
        entries = lex.lookup(search_str)
    if len(entries) == 0:
        print("Not found:", search_str)
    else:
        for entry in entries:
            print(entry.lemma, ':')
            print(entry.definition.rstrip())


if __name__ == '__main__':
    main()

