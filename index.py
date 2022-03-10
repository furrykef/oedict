import os
import re

from sqlitedict import SqliteDict

import lexicon


def gen_index_db(lex, filename):
    try:
        os.unlink(filename)
    except FileNotFoundError:
        pass
    with SqliteDict(filename) as db:
        for key, value in lex.index.items():
            db[key] = [entry.file_pos for entry in value]
        db.commit()


def lookup(word, lexfile, db):
    results = []
    _lookup_impl(word, lexfile, db, results)
    return results

# TODO: code duplication with Lexicon._lookup_impl
def _lookup_impl(word, lexfile, db, results):
    word = lexicon.normalize(word)
    try:
        entries = db[word]
    except KeyError:
        return []
    for entry_pos in entries:
        lexfile.seek(entry_pos)
        entry = lexicon.read_next_entry(lexfile)
        if entry not in results:
            results.append(entry)
            matches = re.match(r"^SEE(?:\s+?)(.+)", entry.text)
            if matches:
                # Follow redirect
                _lookup_impl(matches.group(1), lexfile, db, results)

