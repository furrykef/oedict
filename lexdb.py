import os
import re

import sqlite3

import lexicon


def gen_db(lex, filename):
    try:
        os.unlink(filename)
    except FileNotFoundError:
        pass
    with sqlite3.connect(filename) as con:
        cur = con.cursor()
        cur.executescript("""
CREATE TABLE entries (
    id INT PRIMARY KEY,
    lemma TEXT NOT NULL,
    definition TEXT NOT NULL
);

CREATE TABLE word_types (
    id INT NOT NULL,
    word_type TEXT NOT NULL,
    UNIQUE(id, word_type)
);

CREATE TABLE specials (
    id INT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    UNIQUE(id, key, value)
);

CREATE TABLE lex_index (
    word TEXT NOT NULL,
    entry_id INT REFERENCES entries(id) NOT NULL,
    UNIQUE(word, entry_id)
);
""")
        ids = {}
        for num, entry in enumerate(lex.entries):
            id = num + 1
            ids[entry] = id
            cur.execute(
                "INSERT INTO entries VALUES (?, ?, ?)",
                (id, entry.lemma, entry.text)
            )
            cur.executemany(
                "INSERT INTO word_types VALUES (?, ?)",
                ((id, word_type) for word_type in entry.word_types)
            )
            for key, values in entry.special.items():
                cur.executemany(
                    "INSERT INTO specials VALUES (?, ?, ?)",
                    ((id, key, value) for value in values)
                )
        for word, entries in lex.index.items():
            cur.executemany(
                "INSERT INTO lex_index VALUES (?, ?)",
                ((word, ids[entry]) for entry in entries)
            )


def lookup(word, cursor):
    results = []
    _lookup_impl(word, cursor, results)
    return results

# TODO: code duplication with Lexicon._lookup_impl
# (We should probably get rid of that one anyway)
def _lookup_impl(word, cursor, results):
    word = lexicon.normalize(word)
    cursor.execute("SELECT entry_id FROM lex_index WHERE word = ?", (word,))
    entry_ids = [x[0] for x in cursor.fetchall()]
    entries = [fetch_entry(id, cursor) for id in entry_ids]
    for entry in entries:
        if entry not in results:
            results.append(entry)
            matches = re.match(r"^SEE(?:\s+?)(.+)", entry.text)
            if matches:
                # Follow redirect
                _lookup_impl(matches.group(1), cursor, results)


def fetch_entry(id, cursor):
    cursor.execute("SELECT lemma, definition FROM entries WHERE id = ?", (id,))
    entry = cursor.fetchone()
    cursor.execute("SELECT word_type FROM word_types WHERE id = ?", (id,))
    word_types = cursor.fetchall()
    cursor.execute("SELECT key, value FROM specials WHERE id = ?", (id,))
    special = cursor.fetchall()
    return lexicon.Entry(
        entry[0],
        [x[0] for x in word_types],
        {x[0]: x[1] for x in special},
        entry[1]
    )

