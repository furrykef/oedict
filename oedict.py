#!/usr/bin/env python
import argparse
import sys
import textwrap

import lexicon


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    p = argparse.ArgumentParser(description="Kef's Old English dictionary")
    p.add_argument('-l', '--lexicon', default='lexicon.txt', help="filename of lexicon")
    p.add_argument('-i', '--interactive', action='store_true', help="interactive mode")
    p.add_argument('-r', '--reverse', action='store_true', help="reverse lookup")
    p.add_argument('--dump-index', action='store_true', help="dump debug stuff")
    p.add_argument('--dump-lemmas', action='store_true', help="dump debug stuff")
    p.add_argument('--type', default="", help="word type for --dump-lemmas (regex)")
    p.add_argument('--abc', action='store_true', help="check lexicon is in alphabetical order")
    p.add_argument('search_terms', nargs='*')
    args = p.parse_args(argv)
    lex = lexicon.Lexicon(args.lexicon)
    if args.dump_index:
        lex.dump_index()
    if args.dump_lemmas:
        lex.dump_lemmas(args.type)
    if args.abc:
        check_alphabetization(lex)
    for term in args.search_terms:
        lookup(lex, term, args.reverse)
    if args.interactive:
        interactive_mode(lex, args.reverse)


def interactive_mode(lex, reverse):
    while True:
        try:
            search_str = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        lookup(lex, search_str, reverse)


def lookup(lex, search_str, reverse):
    if reverse:
        entries = lex.reverse_lookup(search_str)
    else:
        entries = lex.lookup(search_str)
    if len(entries) == 0:
        print("Not found:", search_str, "\n")
    else:
        for entry in entries:
            print(entry.lemma + ':')
            print(textwrap.indent(entry.text, " "*4))


def check_alphabetization(lex):
    alphabet = "aæbcdefghijklmnopqrstþuvwxyz"
    xlate = str.maketrans("āǣēīōūȳċġ", "aæeiouycg")
    entries = [x.lemma.replace("-", "").lower().translate(xlate) for x in lex.entries]
    sorted_entries = sorted(entries, key=lambda s: [alphabet.index(ch) for ch in s])
    for item1, item2 in zip(entries, sorted_entries):
        if item1 != item2:
            print(f"Out of order: {item1} (expected {item2})")
            return
    print("All in order")


if __name__ == '__main__':
    main()

