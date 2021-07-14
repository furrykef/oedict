#!/usr/bin/env python
import argparse
import sys

import lexicon


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    p = argparse.ArgumentParser(description="Kef's Old English dictionary")
    p.add_argument('-d', '--dict', default='dict.txt', help="filename of dictionary")
    p.add_argument('-i', '--interactive', action='store_true', help="interactive mode")
    p.add_argument('--dump', action='store_true', help="dump debug stuff")
    p.add_argument('word', nargs='*')
    args = p.parse_args(argv)
    lex = lexicon.Lexicon(args.dict)
    if args.dump:
        lex.dump()
    for word in args.word:
        lookup(lex, word)
    if args.interactive:
        interactive_mode(lex)


def interactive_mode(lex):
    while True:
        try:
            word = input("Input a word: ").strip()
        except KeyboardInterrupt:
            print()
            break
        lookup(lex, word)


def lookup(lex, word):
    entries = lex.lookup(word)
    if len(entries) == 0:
        print("Not found:", word)
    else:
        for entry in entries:
            print(entry.lemma, ':')
            print(entry.definition.rstrip())


if __name__ == '__main__':
    main()

