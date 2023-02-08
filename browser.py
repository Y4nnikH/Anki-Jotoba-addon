from anki.notes import NoteId
from aqt.browser import Browser
from typing import List, Sequence

from .editor import EXPRESSION_FIELD_NAME, PITCH_FIELD_NAME, has_fields, READING_FIELD_NAME, POS_FIELD_NAME, EXAMPLE_FIELD_PREFIX
from .jotoba import *
from .utils import format_furigana, log
from aqt.utils import showInfo
from aqt.qt import *
from aqt import mw, gui_hooks


def setup_browser_menu(browser: Browser):
    """ Add pitch menu """
    a = QAction("Bulk-add Pitch", browser)
    a.triggered.connect(lambda: on_regenerate(browser, pitch=True))
    browser.form.menuEdit.addSeparator()
    browser.form.menuEdit.addAction(a)

    """ Add POS menu """
    a = QAction("Bulk-add POS", browser)
    a.triggered.connect(lambda: on_regenerate(browser, pos=True))
    browser.form.menuEdit.addAction(a)

    """ Add Sentence menu """
    a = QAction("Bulk-add Sentences", browser)
    a.triggered.connect(lambda: on_regenerate(browser, sentences=True))
    browser.form.menuEdit.addAction(a)

    """ Add All menu """
    a = QAction("Bulk-add All", browser)
    a.triggered.connect(lambda: on_regenerate(
        browser, pitch=True, pos=True, sentences=True))
    browser.form.menuEdit.addAction(a)

    """ Overwrite POS menu """
    a = QAction("Bulk-overwrite POS", browser)
    a.triggered.connect(lambda: on_regenerate(browser, overwrite_pos=True))
    browser.form.menuEdit.addAction(a)


def on_regenerate(browser: Browser, pitch=False, pos=False, sentences=False, overwrite_pos=False):
    if overwrite_pos:
        bulk_overwrite_pos(browser.selectedNotes())
    else:
        bulk_add(browser.selectedNotes(), pitch, pos, sentences)


def sanitize(word: str) -> str:
    if word.find("（") != -1:
        word = word[:word.find("（")] # Remove parenthesis and everything after
    if word.find("」") != -1:
        word = word[word.find("」") + 1:]
    if word.find("] ") != -1:
        word = word[word.find("] ") + 2:]
    if word.find("］") != -1:
        word = word[word.find("］") + 1:]
    word = word.replace("～", "")
    
    return word


def bulk_add(nids: Sequence[NoteId], pitch=False, pos=False, sentences=False):
    mw.checkpoint("Bulk-add data")
    mw.progress.start()
    for nid in nids:
        note = mw.col.get_note(nid)

        if not has_fields(note.note_type()):
            log("Skipping: wrong note type")
            continue

        need_change = False
        need_sentence = False

        if note[PITCH_FIELD_NAME] == "" and pitch:
            need_change = True

        if note[POS_FIELD_NAME] == "" and pos:
            need_change = True

        if sentences:
            for i in range(3):
                if note[EXAMPLE_FIELD_PREFIX + str(i + 1)] == "":
                    need_change = True
                    need_sentence = True
                    break

        if not need_change:
            continue

        try:
            kana = note[READING_FIELD_NAME]
            word = request_word(note[EXPRESSION_FIELD_NAME], kana)
        except:
            log("Could not fetch '" + note[EXPRESSION_FIELD_NAME] + "'")
            continue

        if not word:
            continue

        pitch_d = word.pitch
        if note[PITCH_FIELD_NAME] == "" and pitch and pitch_d != "":
            note[PITCH_FIELD_NAME] = pitch_d

        pos_d = word.part_of_speech
        if note[POS_FIELD_NAME] == "" and pos and pos_d != "":
            note[POS_FIELD_NAME] = "; ".join(pos_d)

        if sentences and need_sentence:
            try:
                sentences = request_sentence(note[EXPRESSION_FIELD_NAME])
                for i, sentence in enumerate(sentences):
                    if i > 2:
                        break

                    field_name = EXAMPLE_FIELD_PREFIX + str(i + 1)
                    if note[field_name] != "":
                        continue

                    note[field_name] = format_furigana(sentence["furigana"])
            except:
                log("Didn't find sentences")
                pass

        note.flush()
    mw.progress.finish()
    mw.reset()


def bulk_overwrite_pos(nids: Sequence[NoteId]):
    mw.checkpoint("Bulk-overwrite pos")
    mw.progress.start()
    for nid in nids:
        note = mw.col.get_note(nid)

        if not has_fields(note.note_type()):
            log("Skipping: wrong note type")
            continue

        expr = sanitize(note[EXPRESSION_FIELD_NAME])
        kana = sanitize(note[READING_FIELD_NAME])

        try:
           word = request_word(expr, kana)
        except:
           log("Could not fetch '" + str(expr) + "'")
           continue

        if not word:
            note[POS_FIELD_NAME] = ""
            note.add_tag("no_pos")
        else:
            note[POS_FIELD_NAME] = "; ".join(word.part_of_speech)
            note.remove_tag("no_pos")

        note.flush()
    mw.progress.finish()
    mw.reset()



def init():
    gui_hooks.browser_menus_did_init.append(setup_browser_menu)  # Bulk add
