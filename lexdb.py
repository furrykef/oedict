import os
import re
import tempfile

import sqlite3

import lexicon


SCHEMA = """
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
"""


class LexDB(object):
    def __init__(self, lex_filename, db_filename):
        self.conn = None
        self.gen_db_if_outdated(lex_filename, db_filename)
        self.conn = sqlite3.connect(f'file:{db_filename}?mode=ro', uri=True)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def gen_db(self, lex_filename, db_filename):
        lex = lexicon.Lexicon(lex_filename)
        # Write the new database to a temporary file, then move it to the
        # desired location. This way it should be friendly to concurrent
        # processes, and should still do the Right Thing when two processes
        # run this function at the same time. The temporary file is created
        # in the same directory as its final location in case /tmp is on
        # another filesystem; this way the move should be atomic.
        dirname, basename = os.path.split(db_filename)
        tmpfile, tmp_filename = tempfile.mkstemp(".tmp", f"{basename}-", dirname)
        os.close(tmpfile)       # sqlite3 will reopen it
        os.chmod(tmp_filename, 0o664)
        try:
            self.gen_db_impl(lex, tmp_filename)
            os.rename(tmp_filename, db_filename)
        except:
            # Something went wrong; delete our temporary file
            try:
                os.remove(tmp_filename)
            except:
                pass
            raise

    def gen_db_if_outdated(self, lex_filename, db_filename):
        # Generate new database file if it's out of date
        # If it's up-to-date, just use that instead
        lex_time = os.stat(lex_filename).st_mtime
        try:
            db_time = os.stat(db_filename).st_mtime
        except FileNotFoundError:
            db_time = 0
        if lex_time > db_time:
            self.gen_db(lex_filename, db_filename)

    def gen_db_impl(self, lex, filename):
        conn = sqlite3.connect(filename)
        try:
            cur = conn.cursor()
            cur.executescript(SCHEMA)
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
            conn.commit()
        finally:
            conn.close()

    def lookup(self, word):
        results = []
        self._lookup_impl(word, results)
        return results

    def _lookup_impl(self, word, results):
        cursor = self.conn.cursor()
        word = lexicon.normalize(word)
        cursor.execute("SELECT entry_id FROM lex_index WHERE word = ?", (word,))
        entry_ids = [x[0] for x in cursor.fetchall()]
        entries = [self.fetch_entry(id) for id in entry_ids]
        for entry in entries:
            if entry not in results:
                results.append(entry)
                matches = re.match(r"^SEE(?:\s+?)(.+)", entry.text)
                if matches:
                    # Follow redirect
                    self._lookup_impl(matches.group(1), results)

    # TODO: use FTS? This is what it's made for, but it's quite limited...
    def reverse_lookup(self, search_string):
        cursor = self.conn.cursor()
        search_string = search_string.lower()
        results = []
        for row in cursor.execute("SELECT id, definition FROM entries"):
            id, definition = row
            if not definition.startswith("SEE"):
                if search_string in definition.lower():
                    results.append(self.fetch_entry(id))
        return results

    def random_lookup(self):
        result = self.conn.execute("SELECT id FROM entries WHERE definition NOT GLOB 'SEE *' ORDER BY RANDOM() LIMIT 1")
        return self.fetch_entry(result.fetchone()[0])

    def check_alphabetization(self):
        alphabet = "aæbcdefghijklmnopqrstþuvwxyz"
        xlate = str.maketrans("āǣēīōūȳċġ", "aæeiouycg")
        lemmas = self.conn.execute("SELECT lemma FROM entries").fetchall()
        lemmas = [x[0].replace("-", "").lower().translate(xlate) for x in lemmas]
        sorted_lemmas = sorted(lemmas, key=lambda s: [alphabet.index(ch) for ch in s])
        for item1, item2 in zip(lemmas, sorted_lemmas):
            if item1 != item2:
                print(f"Out of order: {item1} (expected {item2})")
                return
        print("All in order")

    def fetch_entry(self, id):
        cursor = self.conn.cursor()
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

