#!/usr/bin/env python
import argparse
import re
import unicodedata
import unidecode
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
    p = argparse.ArgumentParser(description="Kef's Old English dictionary")
    p.add_argument('-d', '--dict', default='dict.txt', help="filename of dictionary")
    p.add_argument('-i', '--interactive', action='store_true', help="interactive mode")
    p.add_argument('--dump', action='store_true', help="dump debug stuff")
    p.add_argument('word', nargs='*')
    args = p.parse_args(argv)
    index = read_lexicon(args.dict)
    if args.dump:
        dump(index)
    for word in args.word:
        lookup(index, word)
    if args.interactive:
        interactive_mode(index)


def read_lexicon(filename):
    words = {}
    entry = None
    line_num = 0
    with open(filename, 'r') as infile:
        try:
            for line in infile:
                line_num += 1
                if line.startswith(" "):
                    # Add to most recent entry's definition
                    entry.definition += line
                else:
                    # Create a new entry if there's anything on this line
                    line = line.strip()
                    if len(line) == 0 or line[0] == '#':
                        continue
                    if ':' not in line:
                        raise LexiconError("missing colon")
                    split_line = line.split(':')
                    if len(split_line) > 2:
                        raise LexiconError("too many colons")
                    lemma = [x.strip() for x in split_line[0].split(",")]
                    headword = lemma[0]
                    word_types = lemma[1:]
                    special = parse_special(split_line[1])
                    entry = Entry(headword)
                    for word_type in word_types:
                        for forms in gen_forms(headword, word_type, special):
                            for form in forms:
                                if form != '-':
                                    form = normalize(form)
                                    if form not in words:
                                        words[form] = set()
                                    words[form].add(entry)
        except LexiconError as err:
            print("Line", line_num, ":", err, file=sys.stderr)
            sys.exit(1)
    return words


# Parses a list of special forms
# Input: "2sg eart; 3sg sind|sindon"
# Output: {'2sg': ['eart'], '3sg': ['sind', 'sindon']}
def parse_special(special):
    if len(special) == 0:
        return {}
    special = [x.strip() for x in special.split(';')]
    result = {}
    for item in special:
        form, args = item.split(maxsplit=1)
        result[form] = args.split('|')
    return result


def gen_forms(headword, word_type, special):
    if word_type[0] == 'n':
        return gen_noun(headword, word_type, special)
    elif word_type[0] == 'v':
        return gen_verb(headword, word_type, special)
    else:
        return [[headword]]


def gen_noun(headword, word_type, special):
    if word_type[1:] == 'm':
        # Strong masculine noun
        return [
            special.get('nom.sg') or [headword],
            special.get('acc.sg') or special.get('nom.sg') or [headword],
            special.get('gen.sg') or [headword + 'es'],
            special.get('dat.sg') or [headword + 'e'],
            special.get('nom.pl') or [headword + 'as'],
            special.get('acc.pl') or special.get('nom.pl') or [headword + 'as'],
            special.get('gen.pl') or [headword + 'a'],
            special.get('dat.pl') or [headword + 'um'],
        ]
    elif word_type[1:] == 'f':
        # Strong feminine noun
        if headword[-1] == 'u':
            stem = headword[:-1]
        else:
            stem = headword
        return [
            special.get('nom.sg') or [headword],
            special.get('acc.sg') or [stem + 'e'],
            special.get('gen.sg') or [stem + 'e'],
            special.get('dat.sg') or [stem + 'e'],
            special.get('nom.pl') or [stem + 'a', stem + 'e'],
            special.get('acc.pl') or special.get('nom.pl') or [stem + 'a', stem + 'e'],
            special.get('gen.pl') or [stem + 'a'],
            special.get('dat.pl') or [stem + 'um'],
        ]
    elif word_type[1:] == 'n':
        # Strong neuter noun
        return [
            special.get('nom.sg') or [headword],
            special.get('acc.sg') or special.get('nom.sg') or [headword],
            special.get('gen.sg') or [headword + 'es'],
            special.get('dat.sg') or [headword + 'e'],
            special.get('nom.pl') or [headword],
            special.get('acc.pl') or special.get('nom.pl') or [headword],
            special.get('gen.pl') or [headword + 'a'],
            special.get('dat.pl') or [headword + 'um'],
        ]
    elif word_type[1:] in ('mw', 'fw', 'nw'):
        # Weak noun
        stem = headword[:-1]
        oblique = stem + 'an'
        if word_type[1:] == 'nw':
            accusative = special.get('nom.sg') or headword
        else:
            accusative = oblique
        return [
            special.get('nom.sg') or [headword],
            special.get('acc.sg') or [accusative],
            special.get('gen.sg') or [oblique],
            special.get('dat.sg') or [oblique],
            special.get('nom.pl') or [oblique],
            special.get('acc.pl') or special.get('nom.pl') or [oblique],
            special.get('gen.pl') or [stem + 'ena'],
            special.get('dat.pl') or [stem + 'um'],
        ]
    elif word_type[1:] in ('mv', 'fv'):
        # Vocalic noun
        mutated = i_mutate(headword)
        if word_type[1] == 'm':
            genitives = [headword + 'es']
        else:
            genitives = [headword + 'e', mutated]
        return [
            special.get('nom.sg') or [headword],
            special.get('acc.sg') or special.get('nom.sg') or [headword],
            special.get('gen.sg') or genitives,     # no brackets!
            special.get('dat.sg') or [mutated],
            special.get('nom.pl') or [mutated],
            special.get('acc.pl') or special.get('nom.pl') or [mutated],
            special.get('gen.pl') or [headword + 'a'],
            special.get('dat.pl') or [headword + 'um'],
        ]
    else:
        # Other
        return [headword]


def gen_verb(headword, word_type, special):
    long_infinitives = [headword + 'ne']
    if headword.endswith(('ēan', 'ēon', 'ān', 'ōn')):
        # Irregular infinitive
        subjs = special.get('subj') or [headword[:-1]]
        pres_participles = special.get('pres.p') or [headword + 'de']
    elif headword.endswith('an'):
        # Regular infinitive
        long_infinitives.append(headword[:-2] + 'enne')
        subjs = special.get('subj') or [headword[:-2] + 'e']
        pres_participles = special.get('pres.p') or [headword[:-2] + 'ende']
    else:
        raise LexiconError("invalid infinitive")
    result = [
        [headword],
        special.get("long.inf") or long_infinitives,
        pres_participles,
    ]
    if word_type[1] == 'w':
        # Weak verb
        long_stem = headword[:-2]
        if word_type[2] == '1':
            # Weak class I
            if not headword.endswith('an'):
                raise LexiconError("weak class I verbs must end in -an")
            if headword.endswith('bban'):
                short_stem = headword[:-4] + 'f'
            elif headword.endswith('ċġan'):
                short_stem = headword[:-4] + 'ġ'
            else:
                if headword.endswith(('ċċan', 'ddan', 'llan', 'mman', 'nnan', 'ppan', 'rian', 'rran', 'ssan', 'ttan')):
                    short_stem = headword[:-3] + 'e'
                else:
                    short_stem = long_stem
            if 'past' in special:
                if len(special['past']) > 1:
                    raise LexiconError("multiple past stems not supported")
                past_stem = special['past'][0]
            if headword.endswith('eċċan'):
                past_stem = headword[:-5] + 'eaht'
            elif headword.endswith('ellan'):
                past_stem = headword[:-5] + 'eald'
            else:
                past_stem = short_stem + 'd'
        elif word_type[2] == '2':
            # Weak class II
            if not headword.endswith('ian'):
                raise LexiconError("weak class II verbs must end in -ian")
            short_stem = headword[:-3] + 'a'
            past_stem = headword[:-3] + 'od'
        elif word_type[2] == '3':
            # Weak class III
            # These are so irregular that the lexicon file contains most of the forms
            pass
        else:
            raise LexiconError("invalid weak verb class")
        past_stems = special.get('past') or [past_stem]
        past_participles = (special.get('pp') or past_stems)[:]
        past_participles += ['ġe-' + x for x in past_participles if not x.startswith('ġe-')]
        return result + [
            special.get('1sg') or [long_stem + 'e'],
            special.get('2sg') or [short_stem + 'st'],
            special.get('3sg') or [short_stem + 'þ'],
            special.get('pl') or [long_stem + 'aþ'],
            subjs,
            [subj + 'n' for subj in subjs],         # subj.pl
            [x + 'e' for x in past_stems],          # past.1sg/3sg; past.subj.sg
            [x + 'est' for x in past_stems],        # past.2sg
            [x + 'on' for x in past_stems],         # past.pl
            [x + 'en' for x in past_stems],         # past.subj.pl
            special.get('imp') or [short_stem],
            past_participles
        ]
    else:
        # Non-weak verb
        return result


# I-mutates the nucleus of the last syllable of its argument
# TODO: only works when the vowel and everything after it is lowercase.
#   Is that OK?
def i_mutate(word):
    match = re.match(r"(.*?)(īe|ie|ēa|ea|ēo|eo|[āaǣæēeīiōoūuȳy])([b-df-hj-np-tv-zþð]*)$", word)
    initial, nucleus, final = match.groups()
    if nucleus in ('ēa', 'ēo'):
        nucleus = 'īe'
    elif nucleus in ('ea', 'eo'):
        nucleus = 'ie'
    elif nucleus == 'a':
        nucleus = 'e' if final.startswith(('n', 'm')) else 'æ'
    else:
        nucleus = nucleus.translate(str.maketrans('āæeōoūu', 'ǣeiēeȳy'))
    return initial + nucleus + final


def normalize(text):
    text = unicodedata.normalize('NFC', text)
    text = (text.lower()
                .replace('ð', 'þ')
                .replace('&', 'and')
                .replace('⁊', 'and')
                .replace('-', ""))
    text = unidecode.unidecode(text)
    if len(text) >= 2 and text[-2] == text[-1]:
        # Word ends with double letter; reduce
        text = text[:-1]
    return text


def interactive_mode(index):
    while True:
        try:
            word = input("Input a word: ").strip()
        except KeyboardInterrupt:
            print()
            break
        lookup(index, word)


def lookup(index, word):
    try:
        entries = index[normalize(word)]
    except KeyError:
        print("Not found:", word)
    else:
        for entry in entries:
            print(entry.lemma, ':')
            print(entry.definition.rstrip())


def dump(index):
    for word, entries in index.items():
        print(word, ":", [entry.lemma for entry in entries])


if __name__ == '__main__':
    main()

