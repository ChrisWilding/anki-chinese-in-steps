#!/usr/bin/env python3

import base64
import hashlib
import itertools
import json
import os
import sqlite3
import time
import uuid
import zipfile

DECK_ID = 1578170359311
MODEL_ID = 1578170379751

SEPERATOR = "\u001F"

CARD_SQL = "INSERT INTO cards VALUES(?,?,?,0,?,-1,0,0,?,0,0,0,0,0,0,0,0,'');"
NOTE_SQL = "INSERT INTO notes VALUES(?,?,?,?,-1,?,?,?,?,0,'');"

card_counter = itertools.count(start=1)
note_counter = itertools.count(start=1)

def get_anki_guid():
    u = uuid.uuid4()
    encoded = base64.encodebytes(u.bytes)
    return encoded[:10].decode("utf-8")

def get_epoch_s():
    return int(time.time())

def get_epoch_ms():
    return int(time.time() * 1000)

epoch_counter = itertools.count(get_epoch_ms())

def annotate(entry):
    if not 'guid' in entry:
        entry['guid'] = get_anki_guid()
    if not 'cid' in entry:
        entry['cid'] = next(epoch_counter)
    if not 'nid' in entry:
        entry['nid'] = next(epoch_counter)

def build_checksum(id):
    encoded = str(id).encode('utf-8')
    hexdigest = hashlib.sha1(encoded).hexdigest()
    return int(hexdigest[:8], 16)

def build_fields(id, entry):
    return SEPERATOR.join((
        str(id),
        entry['chinese'],
        entry['pinyin'],
        entry['meaning'],
        entry.get('part-of-speech', ''),
        entry.get('sentence', ''),
        entry.get('sentence-pinyin', ''),
        entry.get('sentence-meaning', '')
    ))

def build_cards(data):
    cards = []
    for entry in data:
        id = next(card_counter)
        cards.append((
            entry['cid'],
            entry['nid'],
            DECK_ID,
            get_epoch_s(),
            id
        ))
    return cards

def build_notes(data):
    notes = []
    for entry in data:
        id = next(note_counter)
        notes.append((
            entry['nid'],
            entry['guid'],
            MODEL_ID,
            get_epoch_s(),
            ' chinese-in-steps-1 lesson-1 ',
            build_fields(id, entry),
            id,
            build_checksum(id)
        ))
    return notes

def build_database():
    with open('./anki.sql', 'r') as f:
        script = f.read()

    con = sqlite3.connect('collection.anki2')
    cur = con.cursor()

    cur.executescript(script)

    cur.close()
    con.commit()
    con.close()

def output(data):
    cards = build_cards(data)
    notes = build_notes(data)

    con = sqlite3.connect('collection.anki2')
    cur = con.cursor()

    cur.executemany(NOTE_SQL, notes)
    cur.executemany(CARD_SQL, cards)

    cur.close()
    con.commit()
    con.close()

def get_lesson_dirs():
    entries = os.listdir(os.path.join(os.getcwd(), 'lessons'))
    dirs = [os.path.join(os.getcwd(), 'lessons', entry) for entry in entries]
    return [d for d in dirs if os.path.isdir(d)]

dirs = get_lesson_dirs()

build_database()

for d in dirs:
    path = os.path.join(d, 'vocabulary.json')

    with open(path) as f:
        data = json.load(f)
        for entry in data:
            annotate(entry)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4, sort_keys=True)

    output(data)

zf = zipfile.ZipFile('Chinese in Steps.apkg', 'w', zipfile.ZIP_DEFLATED)
zf.write(os.path.join(os.getcwd(), 'collection.anki2'), 'collection.anki2')
zf.writestr('media', '{}')
zf.close()
