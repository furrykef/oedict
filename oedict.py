#!/usr/bin/env python
import sys


class Entry(object):
    def __init__(self, lemma):
        self.lemma = lemma
        self.definition = ""


class LexiconError(Exception):
    pass


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    words = read_lexicon("dict.txt")
    interactive_mode(words)


def read_lexicon(filename):
    words = {}
    entry = None
    line_num = 0
    with open(filename, "r") as infile:
        try:
            for line in infile:
                line_num += 1
                if line.startswith(" "):
                    # Add to most recent entry's definition
                    entry.definition += line
                else:
                    # Create a new entry if there's anything on this line
                    line = line.strip()
                    if len(line) == 0:
                        continue
                    if ':' not in line:
                        raise LexiconError("Where's the colon?")
                    split_line = line.split(':')
                    if len(split_line) > 2:
                        raise LexiconError("Too many colons!")
                    lemma = [x.strip() for x in split_line[0].split(",")]
                    headword = lemma[0]
                    types = lemma[1:]
                    special = parse_special(split_line[0]) if len(split_line) > 0 else []
                    entry = Entry(headword)
                    for form in gen_forms(headword, types[0], special):
                        if form not in words:
                            words[form] = set()
                        words[form].add(entry)
        except LexiconError as err:
            print("Line", line_num, ":", err, file=sys.stderr)
            sys.exit(1)
    return words


def parse_special(special):
    return []


def gen_forms(headword, word_type, special):
    if word_type[0] == 'n':
        return gen_noun(headword, word_type, special)
    elif word_type[0] == 'v':
        return gen_verb(headword, word_type, special)
    else:
        return [headword]


def gen_noun(headword, word_type, special):
    if word_type[1:] == 'm':
        # Strong masculine noun
        return [
            headword,           # nom/acc.sg
            headword + 'es',    # gen.sg
            headword + 'e',     # dat.sg
            headword + 'as',    # nom/acc.pl
            headword + 'a',     # gen.pl
            headword + 'um',    # dat.pl
        ]
    elif word_type[1:] == 'f':
        # Strong feminine noun
        if headword[-1] == 'u':
            stem = headword[:-1]
        else:
            stem = headword
        return [
            headword,           # nom.sg
            stem + 'e',         # acc/gen/dat.sg; alt. nom/acc plural
            stem + 'a',         # nom/acc/gen.pl
            stem + 'um',        # dat.pl
        ]
    elif word_type[1:] == 'n':
        # Strong neuter noun
        return [
            headword,           # nom/acc.sg; nom/acc.pl
            headword + 'es',    # gen.sg
            headword + 'e',     # dat.sg
            headword + 'a',     # gen.pl
            headword + 'um',    # dat.pl
        ]
    elif word_type[1:] in ('mw', 'fw', 'nw'):
        # Weak noun
        stem = headword[:-1]
        oblique = stem + 'an'
        return [
            headword,           # nom.sg, sometimes acc.sg
            oblique,            # dat/gen.sg; nom/acc.pl; usu. acc.sg
            stem + 'ena',       # gen.pl
            stem + 'um',        # dat.pl
        ]
    elif word_type[1:] in ('mv', 'fv'):
        # Vocalic noun
        return [headword]
    else:
        # Other
        return [headword]


def gen_verb(headword, word_type, special):
    if word_type[1] == 'w':
        # Weak verb
        long_stem = headword[:-2]
        if word_type[2] == '1':
            # Weak class I
            if headword.endswith('bban'):
                short_stem = headword[:-4] + 'f'
            elif headword.endswith('ċġan'):
                short_stem = headword[:-4] + 'ġ'
            else:
                if headword[-4:] in ('ċċan', 'ddan', 'llan', 'mman', 'nnan', 'ppan', 'rian', 'rran', 'ssan', 'ttan'):
                    short_stem = headword[:-3] + 'e'
                else:
                    short_stem = long_stem
            if headword.endswith('eċċan'):
                past_stem = headword[:-5] + 'eaht'
            elif headword.endswith('ellan'):
                past_stem = headword[:-5] + 'eald'
            else:
                past_stem = short_stem + 'd'
        elif word_type[2] == '2':
            # Weak class II
            if not headword.endswith("ian"):
                raise LexiconError("Weak class II verbs must end in -ian")
            short_stem = headword[:-3] + 'a'
            past_stem = headword[:-3] + 'od'
        else:
            # Weak class III, we hope
            return [headword]
        return [
            headword,               # infinitive
            long_stem + 'enne',     # long infinitive
            long_stem + 'anne',     # variant long infinitive
            long_stem + 'e',        # pres.ind.1sg & pres.subj.sg
            short_stem + 'st',      # pres.ind.2sg
            short_stem + 'þ',       # pres.ind.3sg
            long_stem + 'aþ',       # pres.ind.pl
            long_stem + 'en',       # pres.subj.pl
            past_stem + 'e',        # past.ind.1sg/3sg & past.subj.sg
            past_stem + 'est',      # past.ind.2sg
            past_stem + 'on',       # past.ind.pl
            past_stem + 'en',       # past.subj.pl
            short_stem,             # imperative
            long_stem + 'ende',     # pres. participle
            past_stem,              # bare past participle
            'ġe' + past_stem,       # past participle with ġe-
        ]
    else:
        # Non-weak verb
        return [headword]


def interactive_mode(words):
    while True:
        try:
            inp = input("Input a word: ").strip()
        except KeyboardInterrupt:
            print()
            break
        try:
            entries = words[inp]
        except KeyError:
            print("That's not in the dictionary")
            continue
        for entry in entries:
            print(entry.lemma, ':')
            print(entry.definition.rstrip())


if __name__ == '__main__':
    main()

