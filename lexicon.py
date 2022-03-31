import re
import sys
import unicodedata
import unidecode


SPECIAL_TYPES = set((
    '1sg', '2sg', '3sg', 'pl', 'subj',
    'past', 'past.1sg', 'past.pl',
    'long.inf', 'pres.p', 'pp', 'imp',
    'acc', 'gen', 'dat', 'inst',
    'stem', 'stem.pl',
    'acc.sg', 'gen.sg', 'dat.sg',
    'nom.pl', 'acc.pl', 'gen.pl', 'dat.pl',
    'masc.acc.sg', 'fem.nom.sg', 'fem.nom.pl', 'neut.nom.pl',
    'comp', 'sup', 'adv'
))


# NB: num_lines is only a crude hack to aid tracking the line number when parsing the file
class Entry(object):
    def __init__(self, lemma, word_types, special, text, num_lines=0):
        self.lemma = lemma
        self.word_types = word_types
        self.special = special
        self.text = text
        self.num_lines = num_lines


class LexiconError(Exception):
    pass


class Lexicon(object):
    def __init__(self, filename):
        self.entries = []
        self.index = {}
        entry = None
        line_num = 1
        with open(filename, 'r', encoding='utf-8') as infile:
            try:
                while entry := read_next_entry(infile):
                    line_num += entry.num_lines
                    self.entries.append(entry)
                    for word_type in entry.word_types:
                        forms = gen_forms(entry.lemma, word_type, entry.special)
                        for key, value in forms.items():
                            assert isinstance(value, list)
                            for form in value:
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


def read_next_entry(infile):
    num_lines = 0
    # Skip comments and blank lines
    while True:
        line = infile.readline()
        if not line:
            # Hit end of file without finding an entry
            return None
        num_lines += 1
        line = line.strip()
        if len(line) != 0 and not line.startswith("#"):
            break
    if ':' not in line:
        raise LexiconError("missing colon")
    split_line = line.split(':')
    if len(split_line) > 2:
        raise LexiconError("too many colons")
    lemma_section = [x.strip() for x in split_line[0].split(",")]
    lemma = lemma_section[0]
    word_types = lemma_section[1:]
    special = parse_special(split_line[1])
    text = ""
    backup = infile.tell()
    while line := infile.readline():
        if line.startswith(" "):
            num_lines += 1
            text += line.strip() + "\n"
            backup = infile.tell()
        else:
            # Whoops, this line isn't part of this entry
            # We've finished reading the entry
            infile.seek(backup)
            break
    return Entry(lemma, word_types, special, text, num_lines)


# Parses a list of special forms
# Input: "2sg eart; 3sg sind|sindon"
# Output: {'2sg': ['eart'], '3sg': ['sind', 'sindon']}
def parse_special(special):
    result = {}
    if len(special) == 0:
        return result
    special = [x.strip() for x in special.split(';')]
    for item in special:
        form, args = item.split(maxsplit=1)
        if not form in SPECIAL_TYPES:
            raise LexiconError(f"Unknown special: {form}")
        result[form] = args.split('|')
    return result


def gen_forms(lemma, word_type, special):
    if word_type in ('adji', 'nmi', 'nfi', 'nni', 'adv', 'prep', 'conj', 'int', 'particle'):
        return {'invariable': [lemma]}
    elif word_type[0] == 'n':
        return gen_noun(lemma, word_type, special)
    elif word_type.startswith('adj'):
        return gen_adjective(lemma, word_type, special)
    elif word_type == 'pron':
        return gen_pronoun(lemma, word_type, special)
    elif word_type[0] == 'v':
        return gen_verb(lemma, word_type, special)
    else:
        raise LexiconError(f"Invalid word type: {word_type}")


def gen_noun(lemma, word_type, special):
    if 'stem' in special:
        if len(special['stem']) > 1:
            raise LexiconError(f"{lemma}: multiple stems not supported")
        stem = special['stem'][0]
    elif lemma[-1] in ('a', 'e', 'u'):
        stem = lemma[:-1]
    else:
        stem = lemma
    if 'stem.pl' in special:
        if len(special['stem.pl']) > 1:
            raise LexiconError(f"{lemma}: multiple plural stems not supported")
        stem_pl = special['stem.pl'][0]
    else:
        stem_pl = lower_ae(stem)
    if word_type[1:] == 'm':
        # Strong masculine noun
        forms = {
            'nom.sg': [lemma],
            'acc.sg': special.get('nom.sg') or [lemma],
            'gen.sg': [stem + ('es' if not is_vowel(stem[-1]) else 's')],
            'dat.sg': [stem + ('e' if not is_vowel(stem[-1]) else "")],
            'nom.pl': [stem_pl + ('as' if not is_vowel(stem[-1]) else 's')],
            'acc.pl': special.get('nom.pl') or [stem_pl + ('as' if not is_vowel(stem_pl[-1]) else 's')],
            'gen.pl': [stem_pl + ('a' if not is_vowel(stem_pl[-1]) else 'na')],
            'dat.pl': [stem_pl + ('um' if not is_vowel(stem_pl[-1]) else 'm')],
        }
    elif word_type[1:] == 'f':
        forms = {
            'nom.sg': [lemma],
            'acc.sg': [stem + ('e' if not is_vowel(stem[-1]) else "")],
            'gen.sg': [stem + ('e' if not is_vowel(stem[-1]) else "")],
            'dat.sg': [stem + ('e' if not is_vowel(stem[-1]) else "")],
            'nom.pl': [stem_pl + 'a', stem_pl + 'e'] if not is_vowel(stem_pl[-1]) else [stem_pl],
            'acc.pl': special.get('nom.pl') or [stem_pl + 'a', stem_pl + 'e'] if not is_vowel(stem_pl[-1]) else [stem_pl],
            'gen.pl': [stem_pl + ('a' if not is_vowel(stem_pl[-1]) else 'na')],
            'dat.pl': [stem_pl + ('um' if not is_vowel(stem_pl[-1]) else 'm')],
        }
    elif word_type[1:] == 'n':
        # Strong neuter noun
        nom_pl = add_u(lemma, stem_pl)
        forms = {
            'nom.sg': [lemma],
            'acc.sg': special.get('nom.sg') or [lemma],
            'gen.sg': [stem + ('es' if not is_vowel(stem[-1]) else 's')],
            'dat.sg': [stem + ('e' if not is_vowel(stem[-1]) else "")],
            'nom.pl': [nom_pl],
            'acc.pl': special.get('nom.pl') or [nom_pl],
            'gen.pl': [stem_pl + ('a' if not is_vowel(stem_pl[-1]) else 'na')],
            'dat.pl': [stem_pl + ('um' if not is_vowel(stem_pl[-1]) else 'm')],
        }
    elif word_type[1:] in ('mw', 'fw', 'nw'):
        # Weak noun
        forms = gen_weak_nominal(stem, word_type[1])
    elif word_type[1:] in ('mv', 'fv'):
        # Vocalic noun
        mutated = i_mutate(lemma)
        if word_type[1] == 'm':
            genitives = [stem + 'es']
        else:
            genitives = [stem + 'e', mutated]
        forms = {
            'nom.sg': [lemma],
            'acc.sg': special.get('nom.sg') or [lemma],
            'gen.sg': genitives,     # no brackets!
            'dat.sg': [mutated],
            'nom.pl': [mutated],
            'acc.pl': special.get('nom.pl') or [mutated],
            'gen.pl': [stem_pl + ('a' if not is_vowel(stem_pl[-1]) else 'na')],
            'dat.pl': [stem_pl + ('um' if not is_vowel(stem_pl[-1]) else 'm')],
        }
    else:
        # Other (TODO: implement all types and throw an error here instead)
        forms = {'nom.sg': [lemma]}
    special_forms = { key: value for (key, value) in special.items() if key in [
        'nom.sg', 'acc.sg', 'gen.sg', 'dat.sg',
        'nom.pl', 'acc.pl', 'gen.pl', 'dat.pl',
    ] }
    forms.update(special_forms)
    return forms


def gen_adjective(lemma, word_type, special):
    has_strong = word_type != 'adjw'
    has_weak = word_type != 'adjs'
    stem = lemma[:-1] if lemma[-1] in ('a', 'e', 'h') else lemma
    lowered_stem = lower_ae(stem)
    forms = {}
    if has_strong:
        forms.update({
            'masc.nom.sg': [lemma],
            'masc.acc.sg': [stem + 'ne'],
            'masc.gen.sg': [lowered_stem + ('es' if not is_vowel(stem[-1]) else 's')],
            'masc.dat.sg': [lowered_stem + 'um'],
            'masc.nom.pl': [lowered_stem + ('e' if not is_vowel(stem[-1]) else "")],
            'masc.acc.pl': [lowered_stem + ('e' if not is_vowel(stem[-1]) else "")],
            'masc.gen.pl': [stem + 'ra'],
            'masc.dat.pl': [lowered_stem + 'um'],
            'fem.nom.sg': [add_u(lemma, lowered_stem)],
            'fem.acc.sg': [lowered_stem + ('e' if not is_vowel(stem[-1]) else "")],
            'fem.gen.sg': [stem + 're'],
            'fem.dat.sg': [stem + 're'],
            'fem.nom.pl': [lowered_stem + 'a', lowered_stem + 'e'] if not is_vowel(lowered_stem[-1]) else [lowered_stem],
            'fem.acc.pl': [lowered_stem + 'a', lowered_stem + 'e'] if not is_vowel(lowered_stem[-1]) else [lowered_stem],
            'fem.gen.pl': [stem + 'ra'],
            'fem.dat.pl': [lowered_stem + 'um'],
            'neut.nom.sg': [add_u(lemma, lowered_stem)],
            'neut.acc.sg': [add_u(lemma, lowered_stem)],
            'neut.gen.sg': [lowered_stem + ('es' if not is_vowel(stem[-1]) else 's')],
            'neut.dat.sg': [lowered_stem + 'um'],
            'neut.nom.pl': [lowered_stem + ('e' if not is_vowel(stem[-1]) else "")],
            'neut.acc.pl': [lowered_stem + ('e' if not is_vowel(stem[-1]) else "")],
            'neut.gen.pl': [stem + 'ra'],
            'neut.dat.pl': [lowered_stem + 'um'],
        })
    if has_weak:
        forms.update(gen_weak_nominal(stem, 'm', True, 'w.masc.'))
        forms.update(gen_weak_nominal(stem, 'f', True, 'w.fem.'))
        forms.update(gen_weak_nominal(stem, 'm', True, 'w.neut.'))
    special_forms = { key: value for (key, value) in special.items() if key in [
        'masc.nom.sg', 'masc.acc.sg', 'masc.gen.sg', 'masc.dat.sg',
        'masc.nom.pl', 'masc.acc.pl', 'masc.gen.pl', 'masc.dat.pl',
        'fem.nom.sg', 'fem.acc.sg', 'fem.gen.sg', 'fem.dat.sg',
        'fem.nom.pl', 'fem.acc.pl', 'fem.gen.pl', 'fem.dat.pl',
        'neut.nom.sg', 'neut.acc.sg', 'neut.gen.sg', 'neut.dat.sg',
        'neut.nom.pl', 'neut.acc.pl', 'neut.gen.pl', 'neut.dat.pl',
        'w.masc.nom.sg', 'w.masc.acc.sg', 'w.masc.gen.sg', 'w.masc.dat.sg',
        'w.masc.nom.pl', 'w.masc.acc.pl', 'w.masc.gen.pl', 'w.masc.dat.pl',
        'w.fem.nom.sg', 'w.fem.acc.sg', 'w.fem.gen.sg', 'w.fem.dat.sg',
        'w.fem.nom.pl', 'w.fem.acc.pl', 'w.fem.gen.pl', 'w.fem.dat.pl',
        'w.neut.nom.sg', 'w.neut.acc.sg', 'w.neut.gen.sg', 'w.neut.dat.sg',
        'w.neut.nom.pl', 'w.neut.acc.pl', 'w.neut.gen.pl', 'w.neut.dat.pl',
    ] }
    forms.update(special_forms)
    return forms


def gen_weak_nominal(stem, gender, adjective=False, prefix=""):
    if is_vowel(stem[-1]):
        nominative = stem
        oblique = stem + 'n'
        gen_pls = [stem + 'ra', stem + 'rra']
        dat_pls = [stem + 'm', stem + 'um']
    else:
        lowered_stem = lower_ae(stem)
        nominative = lowered_stem + 'a' if gender == 'm' else lowered_stem + 'e'
        oblique = lowered_stem + 'an'
        gen_pls = [lowered_stem + 'ena']
        if adjective:
            gen_pls.append(stem + 'ra')
        dat_pls = [lowered_stem + 'um']
    if gender == 'n':
        accusative = nominative
    else:
        accusative = oblique
    return {
        f'{prefix}nom.sg': [nominative],
        f'{prefix}acc.sg': [accusative],
        f'{prefix}gen.sg': [oblique],
        f'{prefix}dat.sg': [oblique],
        f'{prefix}nom.pl': [oblique],
        f'{prefix}acc.pl': [oblique],
        f'{prefix}gen.pl': gen_pls,
        f'{prefix}dat.pl': dat_pls,
    }


def gen_pronoun(lemma, word_type, special):
    # Pronouns in the lexicon file define all their forms explicitly
    forms = {'nom': [lemma]}
    forms.update({key: value for (key, value) in special.items() if key in [
        'acc', 'dat', 'gen'
    ]})
    return forms


def gen_verb(lemma, word_type, special):
    long_infinitives = [lemma + 'ne']
    if lemma.endswith(('ēan', 'ēon', 'īon', 'ān', 'ōn', 'ȳn')):
        # Irregular infinitive
        inf_stem = lemma[:-1]
        pres_1sg = inf_stem
        subjs = special.get('subj') or [inf_stem]
        pres_participles = special.get('pres.p') or [lemma + 'de']
        irregular_infinitive = True
    elif lemma.endswith('an'):
        # Regular infinitive
        inf_stem = lemma[:-2]
        pres_1sg = inf_stem + 'e'
        long_infinitives.append(inf_stem + 'enne')
        subjs = special.get('subj') or [inf_stem + 'e']
        pres_participles = special.get('pres.p') or [lemma[:-2] + 'ende']
        irregular_infinitive = False
    else:
        raise LexiconError(f"invalid infinitive: {lemma}")
    result = {
        'inf': [lemma],
        'long.inf': long_infinitives,
        'pres.p': pres_participles,
        '1sg': [pres_1sg],
        'subj.sg': subjs,
        'subj.pl': [subj + 'n' for subj in subjs],
        'imp.pl': [lemma[:-1] + 'þ'],
    }
    if word_type[1] == 'w':
        # Weak verb
        long_stem = lemma[:-2]
        if word_type[2] == '1':
            # Weak class I
            if irregular_infinitive:
                short_stem = inf_stem
            elif lemma.endswith('bban'):
                short_stem = lemma[:-4] + 'f'
            elif lemma.endswith('ċġan'):
                short_stem = lemma[:-4] + 'ġ'
            else:
                if lemma.endswith(('ċċan', 'llan', 'mman', 'nnan', 'ppan', 'rian', 'rran', 'ssan')):
                    short_stem = lemma[:-3] + 'e'
                else:
                    short_stem = long_stem
            if lemma.endswith('eċċan'):
                past_stem = lemma[:-5] + 'eaht'
            elif lemma.endswith('ellan'):
                past_stem = lemma[:-5] + 'eald'
            elif short_stem.endswith(('t', 'd')):
                past_stem = short_stem
            else:
                past_stem = short_stem + 'd'
        elif word_type[2] == '2':
            # Weak class II
            if not lemma.endswith('ian'):
                raise LexiconError("weak class II verbs must end in -ian")
            short_stem = lemma[:-3] + 'a'
            past_stem = lemma[:-3] + 'od'
        elif word_type[2] == '3':
            # Weak class III
            # These are so irregular that the lexicon file contains most of the forms
            short_stem = ""     # TODO: hacky. Result gets overwritten
        else:
            raise LexiconError("invalid weak verb class")
        past_stems = special.get('past') or [past_stem]
        if len(past_stems) == 1 and re.match(r"^.*[^ol]d$", past_stems[0]):
            # Transform e.g. hīerd into hīered
            # (but not seald into sealed or lufod into lufed)
            pps = [past_stems[0][:-1] + 'ed']
        else:
            pps = past_stems
        result.update({
            '2sg': [assimilate(short_stem, 'st')],
            '3sg': [assimilate(short_stem, 'þ')],
            'pl': [inf_stem + 'aþ'],
            'past.1sg': [x + 'e' for x in past_stems],
            'past.2sg': [x + 'est' for x in past_stems],
            'past.3sg': [x + 'e' for x in past_stems],
            'past.pl': [x + 'on' for x in past_stems],
            'past.subj.sg': [x + 'e' for x in past_stems],
            'past.subj.pl': [x + 'en' for x in past_stems],
            'imp': [short_stem],
            'pp': pps,
        })
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
        past_participles = [mutate(inf_stem, pp_repl) + 'en']
        result.update({
            '2sg': [assimilate(i_mutate(inf_stem), 'st')],
            '3sg': [assimilate(i_mutate(inf_stem), 'þ')],
            'pl': [inf_stem + 'aþ'],
            'past.1sg': [mutate(inf_stem, past_1sg_repl)],
            'past.2sg': [x + 'e' for x in past_pl_stems],
            'past.3sg': [mutate(inf_stem, past_1sg_repl)],
            'past.pl': past_pls,
            'past.subj.sg': [x + 'e' for x in past_pl_stems],
            'past.subj.pl': [x + 'en' for x in past_pl_stems],
            'imp': [inf_stem],
            'pp': past_participles,
        })
    elif word_type in ('vpp', 'vi'):
        # Preterite-present or irregular verb
        # These define most of their forms explicitly
        # Past participle is *not* inferred from "past" special
        if 'past' in special:
            # Past conjugates like weak verb (e.g. ēodon)
            result.update({
                'past.1sg': [x + 'e' for x in special['past']],
                'past.2sg': [x + 'est' for x in special['past']],
                'past.3sg': [x + 'e' for x in special['past']],
                'past.pl': [x + 'on' for x in special['past']],
                'past.subj.sg': [x + 'e' for x in special['past']],
                'past.subj.pl': [x + 'en' for x in special['past']],
            })
        elif 'past.pl' in special:
            # Past conjugates like strong verb (e.g. wǣron)
            stems = [x[:-2] for x in special['past.pl']]
            result.update({
                'past.2sg': [x + 'e' for x in stems],
                'past.subj.sg': [x + 'e' for x in stems],
                'past.subj.pl': [x + 'en' for x in stems],
            })
        if word_type == 'vpp':
            result['pres.pl'] = [inf_stem + 'on']
    else:
        raise LexiconError(f"Unrecognized verb type: {word_type}")
    special_forms = { key: value for (key, value) in special.items() if key in [
        'inf', 'long.inf',
        '1sg', '2sg', '3sg', 'pl',
        'subj.sg', 'subj.pl',
        'past.1sg', 'past.2sg', 'past.3sg', 'past.pl',
        'past.subj.sg', 'past.subj.pl',
        'imp', 'imp.pl', 'pres.p', 'pp'
    ] }
    result.update(special_forms)
    if 'pp' in result and result['pp'] != ['-']:
        result['pp'] = result['pp'] + [
            'ġe-' + x for x in result['pp'] if not x.startswith('ġe-')
        ]
    return result


def is_vowel(ch):
    assert len(ch) == 1
    return ch in 'AÆEIOUYĀǢĒĪŌŪȲaæeiouyāǣēīōūȳ'


# I-mutates the nucleus of the last syllable of its argument
# TODO: only works when the nucleus and everything after it is lowercase.
#   Is that OK?
def i_mutate(word):
    initial, nucleus, final = split_word(word)
    if nucleus in ('ēa', 'ēo', 'īo', 'īe'):
        nucleus = 'īe'
    elif nucleus in ('ea', 'eo', 'io', 'ie'):
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
    match = re.match(r"(.*?)(ēa|ea|ēo|eo|īo|io|īe|ie|[āaǣæēeīiōoūuȳy])([b-df-hj-np-tvwxzþðċġ]*)$", word, re.IGNORECASE)
    return match.groups()

def get_nucleus(word):
    return split_word(word)[1]


# Add -u to form neuter plurals and feminine singulars
# according to syllable structure of the lemma
# The stem argument allows things such as hēafod → hēafdu
# TODO: support uppercase??
def add_u(lemma, stem):
    if lemma[-1] == 'e':
        # -e always becomes -u
        return stem + 'u'
    _, vowel, end = split_word(lemma)
    if vowel in ('ā', 'ǣ', 'ē', 'ī', 'ō', 'ū', 'ēa', 'ēo', 'īo', 'īe') or len(end) > 1 or end == 'x':
        # Lemma ends in heavy syllable; no -u
        return lemma
    return stem + 'u'


# Lowers æ to a if stem ends with a single consonant (not x)
# e.g. smæl → smal
def lower_ae(stem):
    match = re.match(r"^(.*)æ([b-df-hj-np-tvwzþðċġ])$", stem, re.IGNORECASE)
    if not match:
        return stem
    return match[1] + 'a' + match[2]


def assimilate(root, suffix):
    if suffix == 'þ':
        if root.endswith(('dd', 'tt')):
            return root[:-2] + 'tt'
        elif root.endswith(('d', 't', 's')):
            return root[:-1] + 't'
        elif root.endswith('g') and not root.endswith('ng'):
            return root[:-1] + 'ġþ'
        else:
            return root + suffix
    elif suffix == 'st':
        if root.endswith(('dd', 'tt')):
            return root[:-2] + 'tst'
        elif root.endswith(('d', 't')):
            return root[:-1] + 'tst'
        elif root.endswith(('s', 'þ')):
            return root[:-1] + 'st'
        elif root.endswith('g') and not root.endswith('ng'):
            return root[:-1] + 'ġst'
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
    if next == 'w' and preceding.endswith('ēo'):
        # This is a word like trēow, which can also be spelled trēo
        results += [preceding, preceding + 'w']
        return
    if next == 'g' and preceding[-1] != 'n':
        # This is a word like burg, dēag, etc.
        results += [preceding, preceding + 'h']
    if next.startswith('īo'):
        gen_variants_impl(next[2:], results, preceding + 'ēo')
    elif next.startswith('io'):
        gen_variants_impl(next[2:], results, preceding + 'eo')
    elif next.startswith('īe'):
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
    elif next.startswith(('an', 'am')) and not preceding.endswith(('ē', 'e')):
        gen_variants_impl(next[1:], results, preceding + 'o')
    elif next.startswith(('on', 'om')) and not preceding.endswith(('ē', 'e')):
        gen_variants_impl(next[1:], results, preceding + 'a')
    elif next.startswith('sel'):
        gen_variants_impl(next[3:], results, preceding + 'syl')
    gen_variants_impl(next[1:], results, preceding + next[0])


def normalize(text):
    text = unicodedata.normalize('NFC', text)
    text = (text.lower()
                .replace('ð', 'þ')
                .replace('k', 'c')
                .replace('&', 'and')
                .replace('⁊', 'and')
                .replace('ꝥ', 'thaet')
                .replace('x', 'cs')
                .replace('-', ""))
    text = unidecode.unidecode(text)
    if len(text) >= 2 and text[-2] == text[-1]:
        # Word ends with double letter; reduce
        text = text[:-1]
    elif text.endswith(('ngc', 'ncg')):
        text = text[:-3] + 'ng'
    return text


def expand_word_type(word_type):
    if word_type == 'adv':
        return "adverb"
    elif word_type == 'prep':
        return "preposition"
    elif word_type == 'conj':
        return "conjunction"
    elif word_type == 'int':
        return "interjection"
    elif word_type == 'particle':
        return "particle"
    elif word_type == 'pron':
        return "pronoun"
    elif word_type[0] == 'n':
        match = re.match(r"^n([mfn])([wvi])?(\.(?:sg|pl))?$", word_type)
        gender = {
            'm': "masculine ",
            'f': "feminine ",
            'n': "neuter ",
        }[match.group(1)]
        subtype = {
            None: "strong ",
            'w': "weak ",
            'v': "vocalic ",
            'i': "indeclinable ",
        }[match.group(2)]
        plurality = {
            None: "",
            '.sg': "singular-only ",
            '.pl': "plural-only ",
        }[match.group(3)]
        return f"{gender}{subtype}{plurality}noun"
    elif word_type.startswith('adj'):
        # TODO: subtypes
        return "adjective"
    elif word_type[0] == 'v':
        match = re.match(r"^v([wsi]|pp)([1-7])?$", word_type)
        subtype = {
            'w': "weak ",
            's': "strong ",
            'pp': "preterite-present ",
            'i': "irregular ",
        }[match.group(1)]
        class_ = {
            None: "",
            '1': "class I ",
            '2': "class II ",
            '3': "class III ",
            '4': "class IV ",
            '5': "class V ",
            '6': "class VI ",
            '7': "class VII ",
        }[match.group(2)]
        return f"{subtype}{class_}verb"
    else:
        return "unknown"

