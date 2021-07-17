import re
import sys
import unicodedata
import unidecode


SPECIAL_TYPES = set((
    '1sg', '2sg', '3sg', 'pl', 'subj',
    'past', 'past.1sg', 'past.pl',
    'long.inf', 'pres.p', 'pp', 'imp',
    'acc', 'gen', 'dat', 'inst',
    'acc.sg', 'gen.sg', 'dat.sg',
    'nom.pl', 'acc.pl', 'gen.pl', 'dat.pl',
    'masc.acc.sg',
    'comp', 'sup', 'adv'
))


class Entry(object):
    def __init__(self, lemma):
        self.lemma = lemma
        self.definition = ""


class LexiconError(Exception):
    pass


class Lexicon(object):
    def __init__(self, filename):
        self.entries = []
        self.index = {}
        entry = None
        line_num = 0
        with open(filename, 'r', encoding='utf-8') as infile:
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
                        self.entries.append(entry)
                        for word_type in word_types:
                            for forms in gen_forms(headword, word_type, special):
                                assert isinstance(forms, list)  # we've had trouble with strings creeping in
                                for form in forms:
                                    if form != '-':
                                        for variant in gen_variants(form):
                                            variant = normalize(variant)
                                            if variant not in self.index:
                                                self.index[variant] = set()
                                            self.index[variant].add(entry)
            except LexiconError as err:
                # TODO: do something else here??
                print("Line", line_num, ":", err, file=sys.stderr)
                sys.exit(1)

    def lookup(self, word):
        word = normalize(word)
        return self.index[word] if word in self.index else []

    def reverse_lookup(self, search_string):
        search_string = search_string.lower()
        results = []
        for entry in self.entries:
            definition = entry.definition.strip()
            if not definition.startswith("SEE"):
                if search_string in definition.lower():
                    results.append(entry)
        return results

    def dump_index(self):
        for word, entries in self.index.items():
            print(word, ":", [entry.lemma for entry in entries])

    def dump_lemmas(self):
        for entry in self.entries:
            print(entry.lemma)


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
        if not form in SPECIAL_TYPES:
            raise LexiconError("Unknown special: " + form)
        result[form] = args.split('|')
    return result


def gen_forms(headword, word_type, special):
    if word_type[0] == 'n':
        return gen_noun(headword, word_type, special)
    elif word_type in ('adj', 'adjs'):
        return gen_adjective(headword, word_type, special)
    elif word_type == 'pron':
        return gen_pronoun(headword, word_type, special)
    elif word_type[0] == 'v':
        return gen_verb(headword, word_type, special)
    elif word_type in ('adji', 'adv', 'prep', 'conj', 'int', 'particle'):
        return [[headword]]
    else:
        raise LexiconError("Invalid word type: " + word_type)


def gen_noun(headword, word_type, special):
    if headword[-1] in ('a', 'e', 'u', 'h'):
        stem = headword[:-1]
    else:
        stem = headword
    if word_type[1:] == 'm':
        # Strong masculine noun
        return [
            special.get('nom.sg') or [headword],
            special.get('acc.sg') or special.get('nom.sg') or [headword],
            special.get('gen.sg') or [stem + 'es'],
            special.get('dat.sg') or [stem + 'e'],
            special.get('nom.pl') or [stem + 'as'],
            special.get('acc.pl') or special.get('nom.pl') or [stem + 'as'],
            special.get('gen.pl') or [stem + 'a'],
            special.get('dat.pl') or [stem + 'um'],
        ]
    elif word_type[1:] == 'f':
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
            special.get('gen.sg') or [stem + 'es'],
            special.get('dat.sg') or [stem + 'e'],
            special.get('nom.pl') or [headword],
            special.get('acc.pl') or special.get('nom.pl') or [headword],
            special.get('gen.pl') or [stem + 'a'],
            special.get('dat.pl') or [stem + 'um'],
        ]
    elif word_type[1:] in ('mw', 'fw', 'nw'):
        # Weak noun
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
        # Other (TODO: implement all types and throw an error here instead)
        return [[headword]]


def gen_adjective(headword, word_type, special):
    has_strong = True               # TODO: not always!
    has_weak = word_type != 'adjs'
    stem = headword[:-1] if headword[-1] in ('a', 'e') else headword
    if has_strong:
        strong_forms = [
            [headword],             # masc/neut/fem.nom.sg; masc/acc.sg
            [stem + 'es'],          # masc/neut.gen.sg
            [stem + 'e'],           # masc/neut.dat.sg; fem.acc.sg; nom/acc.pl
            [stem + 're'],          # fem.gen/dat.sg
            [stem + 'a'],           # gen.pl
            [stem + 'um'],          # dat.pl
        ]
    else:
        strong_forms = []
    if has_weak:
        weak_forms = [
            [stem + 'a'],           # masc.nom.sg
            [stem + 'e'],           # neut/fem.nom.sg; neut.acc.sg
            [stem + 'an'],          # oblique
            [stem + 'a'],           # gen.pl
            [stem + 'um'],          # dat.pl
        ]
    else:
        weak_forms = []
    return strong_forms + weak_forms


def gen_pronoun(headword, word_type, special):
    # Pronouns in the lexicon file define all their forms explicitly
    return [[headword]] + list(special.values())


def gen_verb(headword, word_type, special):
    long_infinitives = [headword + 'ne']
    if headword.endswith(('ēan', 'ēon', 'ān', 'ōn')):
        # Irregular infinitive
        inf_stem = headword[:-1]
        pres_1sg = inf_stem
        subjs = special.get('subj') or [inf_stem]
        pres_participles = special.get('pres.p') or [headword + 'de']
        irregular_infinitive = True
    elif headword.endswith('an'):
        # Regular infinitive
        inf_stem = headword[:-2]
        pres_1sg = inf_stem + 'e'
        long_infinitives.append(inf_stem + 'enne')
        subjs = special.get('subj') or [inf_stem + 'e']
        pres_participles = special.get('pres.p') or [headword[:-2] + 'ende']
        irregular_infinitive = False
    else:
        raise LexiconError("invalid infinitive")
    result = [
        [headword],
        special.get("long.inf") or long_infinitives,
        pres_participles,
        special.get('1sg') or [pres_1sg],
        subjs,
        [subj + 'n' for subj in subjs],             # subj.pl
        [headword[:-1] + 'þ'],                      # imp.pl
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
                if headword.endswith(('ċċan', 'llan', 'mman', 'nnan', 'ppan', 'rian', 'rran', 'ssan')):
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
            elif short_stem.endswith(('t', 'd')):
                past_stem = short_stem
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
        result += [
            special.get('2sg') or [assimilate(short_stem, 'st')],
            special.get('3sg') or [assimilate(short_stem, 'þ')],
            special.get('pl') or [inf_stem + 'aþ'],
            [x + 'e' for x in past_stems],          # past.1sg/3sg; past.subj.sg
            [x + 'est' for x in past_stems],        # past.2sg
            [x + 'on' for x in past_stems],         # past.pl
            [x + 'en' for x in past_stems],         # past.subj.pl
            special.get('imp') or [short_stem],
            past_participles,
        ]
    elif word_type[1] == 's':
        # Strong verb
        # Me strong. Smash programmer with club.
        if word_type[2] == '1':
            past_1sg_repl = 'ā'
            past_pl_repl = 'i'
            pp_repl = 'i'
        elif word_type[2] == '2':
            past_1sg_repl = 'ēa'
            past_pl_repl = 'u'
            pp_repl = 'o'
        elif word_type[2] == '3':
            def past_1sg_repl(nucleus):
                if nucleus == 'e':
                    return 'æ'
                elif nucleus == 'i':
                    return 'a'
                else:
                    return 'ea'
            past_pl_repl = 'u'
            pp_repl = lambda nucleus: 'u' if nucleus == 'i' else 'o'
        elif word_type[2] == '4':
            past_1sg_repl = 'æ'
            past_pl_repl = 'ǣ'
            pp_repl = 'o'
        elif word_type[2] == '5':
            past_1sg_repl = 'æ'
            past_pl_repl = 'ǣ'
            pp_repl = 'e'
        elif word_type[2] == '6':
            past_1sg_repl = 'ō'
            past_pl_repl = 'ō'
            pp_repl = 'a'
        elif word_type[2] == '7':
            past_1sg_repl = 'ēo'
            past_pl_repl = 'ēo'
            pp_repl = lambda nucleus: nucleus
        past_pls = special.get('past.pl') or [mutate(inf_stem, past_pl_repl) + 'on']
        past_pl_stems = [x[:-2] for x in past_pls]
        past_participles = (special.get('pp') or [mutate(inf_stem, pp_repl) + 'en'])[:]
        past_participles += ['ġe-' + x for x in past_participles if not x.startswith('ġe-')]
        result += [
            special.get('2sg') or [assimilate(i_mutate(inf_stem), 'st')],
            special.get('3sg') or [assimilate(i_mutate(inf_stem), 'þ')],
            special.get('pl') or [inf_stem + 'aþ'],
            special.get('past.1sg') or [mutate(inf_stem, past_1sg_repl)],
            [x + 'e' for x in past_pl_stems],           # past.2sg
            past_pls,
            [x + 'en' for x in past_pl_stems],          # past.subj.pl
            special.get('imp') or [inf_stem],
            past_participles,
        ]
    elif word_type in ('vpp', 'vi'):
        # Preterite-present or irregular verb
        # These define most of their forms explicitly
        # Past participle is *not* inferred from "past" special
        for key, value in special.items():
            if key == 'past':
                # Past conjugates like weak verb (e.g. ēodon)
                result += [
                    [x + 'e' for x in value],           # past.1sg/3sg
                    [x + 'est' for x in value],         # past.2sg
                    [x + 'on' for x in value],          # past.pl
                    [x + 'en' for x in value],          # past.subj.pl
                ]
            elif key == 'past.pl':
                # Past conjugates like strong verb (e.g. wǣron)
                stems = [x[:-2] for x in value]
                result += [
                    value,
                    [x + 'e' for x in stems],           # past.2sg
                    [x + 'en' for x in stems],          # past.subj.pl
                ]
            elif key == 'pp':
                result.append(value + ['ġe-' + x for x in value if not x.startswith('ġe-')])
            else:
                result.append(value)
        if word_type == 'vpp':
            result.append([inf_stem + 'on'])            # pres.pl
    else:
        raise LexiconError("Unrecognized verb type: " + word_type)
    return result


# I-mutates the nucleus of the last syllable of its argument
# TODO: only works when the nucleus and everything after it is lowercase.
#   Is that OK?
def i_mutate(word):
    initial, nucleus, final = split_word(word)
    if nucleus in ('ēa', 'ēo'):
        nucleus = 'īe'
    elif nucleus in ('ea', 'eo'):
        nucleus = 'ie'
    elif nucleus == 'a':
        # This bit is why we can't just call mutate()
        nucleus = 'e' if final.startswith(('n', 'm')) else 'æ'
    else:
        nucleus = nucleus.translate(str.maketrans('āæeōoūu', 'ǣeiēeȳy'))
    return initial + nucleus + final

# TODO: only works when the nucleus and everything after it is lowercase.
#   Is that OK?
def mutate(word, replacement):
    initial, nucleus, final = split_word(word)
    if callable(replacement):
        nucleus = replacement(nucleus)
    else:
        nucleus = replacement
    return initial + nucleus + final

def split_word(word):
    match = re.match(r"(.*?)(īe|ie|ēa|ea|ēo|eo|[āaǣæēeīiōoūuȳy])([b-df-hj-np-tv-zþð]*)$", word)
    return match.groups()

def get_nucleus(word):
    return split_word(word)[1]


def assimilate(root, suffix):
    if suffix == 'þ':
        if root.endswith(('dd', 'tt')):
            return root[:-2] + 'tt'
        elif root.endswith(('d', 't', 's')):
            return root[:-1] + 't'
        else:
            return root + suffix
    elif suffix == 'st':
        if root.endswith(('dd', 'tt')):
            return root[:-2] + 'tst'
        elif root.endswith(('d', 't')):
            return root[:-1] + 'tst'
        elif root.endswith(('s', 'þ')):
            return root[:-1] + 'st'
        else:
            return root + suffix
    else:
        assert False


def gen_variants(text):
    results = []
    gen_variants_impl(text, results)
    return results

# TODO: OK to ignore capitalization?
def gen_variants_impl(next, results, preceding=""):
    if len(next) == 0:
        # Reached end of word
        results.append(preceding)
        return
    if next.startswith('īe'):
        gen_variants_impl(next[2:], results, preceding + 'ī')
        gen_variants_impl(next[2:], results, preceding + 'ȳ')
    elif next.startswith('ie'):
        gen_variants_impl(next[2:], results, preceding + 'i')
        gen_variants_impl(next[2:], results, preceding + 'y')
    elif next.startswith('ī'):
        gen_variants_impl(next[1:], results, preceding + 'ȳ')
    elif next.startswith('i'):
        gen_variants_impl(next[1:], results, preceding + 'y')
    elif next.startswith('ȳ'):
        gen_variants_impl(next[1:], results, preceding + 'ī')
    elif next.startswith('y'):
        gen_variants_impl(next[1:], results, preceding + 'i')
    elif next.startswith('an') and not preceding.endswith(('ē', 'e')):
        gen_variants_impl(next[2:], results, preceding + 'on')
    elif next.startswith('on') and not preceding.endswith(('ē', 'e')):
        gen_variants_impl(next[2:], results, preceding + 'an')
    gen_variants_impl(next[1:], results, preceding + next[0])


def normalize(text):
    text = unicodedata.normalize('NFC', text)
    text = (text.lower()
                .replace('ð', 'þ')
                .replace('k', 'c')
                .replace('&', 'and')
                .replace('⁊', 'and')
                .replace('ꝥ', 'thaet')
                .replace('-', ""))
    text = unidecode.unidecode(text)
    if len(text) >= 2 and text[-2] == text[-1]:
        # Word ends with double letter; reduce
        text = text[:-1]
    elif text.endswith(('ngc', 'ncg')):
        text = text[:-3] + 'ng'
    return text

