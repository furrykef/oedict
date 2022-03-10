-- WIP schema for a SQLite database. Not actually used yet.
CREATE TABLE entries (
    id INT PRIMARY KEY,
    lemma TEXT NOT NULL,
    stem TEXT NOT NULL,
    part_of_speech TEXT NOT NULL,
    definition_id INT NOT NULL REFERENCES definitions(id),
    etymology TEXT NOT NULL,
    notes TEXT NOT NULL
);

CREATE TABLE noun_attributes (
    entry_id INT PRIMARY KEY REFERENCES entries(id),
    gender TEXT NOT NULL,
    singular INT NOT NULL,
    plural INT NOT NULL
);

CREATE TABLE paradigm_attributes (
    entry_id INT PRIMARY KEY REFERENCES entries(id),
    paradigm TEXT NOT NULL
);

CREATE TABLE definitions (
    id INT PRIMARY KEY,
    definition TEXT NOT NULL
);

CREATE TABLE inflections (
    paradigm TEXT NOT NULL,
    form_name TEXT NOT NULL,
    form TEXT NOT NULL,
    UNIQUE(paradigm, form_name, form)
);

