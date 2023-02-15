from anki.notes import Note
from anki.models import NoteType
from aqt import mw, gui_hooks
from aqt.utils import showInfo

from .jotoba import *
from .utils import format_furigana, log

# Field constants
EXPRESSION_FIELD_NAME = "Expression"
EXPRESSION_FIELD_POS = 0

READING_FIELD_NAME = "Reading"
READING_FIELD_POS = 1

PITCH_FIELD_NAME = "Pitch"
PITCH_FIELD_POS = 2

MEANING_FIELD_NAME = "Meaning"
MEANING_FIELD_POS = 3

POS_FIELD_NAME = "POS"
POS_FIELD_POS = 4

IMAGE_FIELD_NAME = "Image"
Image_FIELD_POS = 5

AUDIO_FIELD_NAME = "Audio"
AUDIO_FIELD_POS = 6

NOTES_FIELD_NAME = "Notes"
NOTES_FIELD_POS = 7

EXAMPLE_FIELD_PREFIX = "Example "
Example_Field_Offset = 8

ALL_FIELDS = {EXPRESSION_FIELD_NAME: EXPRESSION_FIELD_POS,
              READING_FIELD_NAME: READING_FIELD_POS,
              PITCH_FIELD_NAME: PITCH_FIELD_POS,
              MEANING_FIELD_NAME: MEANING_FIELD_POS,
              POS_FIELD_NAME: POS_FIELD_POS,
              IMAGE_FIELD_NAME: Image_FIELD_POS,
              AUDIO_FIELD_NAME: AUDIO_FIELD_POS,
              NOTES_FIELD_NAME: NOTES_FIELD_POS,
              EXAMPLE_FIELD_PREFIX + "1": Example_Field_Offset,
              EXAMPLE_FIELD_PREFIX + "1 Audio": Example_Field_Offset + 1,
              EXAMPLE_FIELD_PREFIX + "2": Example_Field_Offset + 2,
              EXAMPLE_FIELD_PREFIX + "2 Audio": Example_Field_Offset + 3,
              EXAMPLE_FIELD_PREFIX + "3": Example_Field_Offset + 4,
              EXAMPLE_FIELD_PREFIX + "3 Audio": Example_Field_Offset + 5,}


def fill_data(note: Note, expr: str, flag: bool, reading: str = "", overwrite: bool = True):

    try:
        word = request_word(expr, reading)
    except Exception as e:  # error while fetching word
        log(e)
        return flag

    if word is None:  # word not found or ambiguity (no kana reading) -> user will call again after providing reading
        return flag

    if overwrite or note[EXPRESSION_FIELD_NAME] == "":
        note[EXPRESSION_FIELD_NAME] = word.expression

    if overwrite or note[READING_FIELD_NAME] == "":
        note[READING_FIELD_NAME] = word.reading

    if overwrite or note[PITCH_FIELD_NAME] == "":
        note[PITCH_FIELD_NAME] = word.pitch

    if overwrite or note[MEANING_FIELD_NAME] == "":
        note[MEANING_FIELD_NAME] = "; ".join(word.glosses[:3])

    if overwrite or note[POS_FIELD_NAME] == "":
        note[POS_FIELD_NAME] = "; ".join(word.part_of_speech)

    try:
        sentences = request_sentence(expr)
        for i, sentence in enumerate(sentences):
            if i > 2:
                break

            field_name = EXAMPLE_FIELD_PREFIX + str(i + 1)
            if overwrite or note[field_name] == "":
                note[field_name] = format_furigana(sentence["furigana"])
    except Exception as e:
        log(e)
        pass

    return True


# Check whether all fields are available in given notetype
def has_fields(notetype: NoteType) -> bool:
    if notetype is None:
        return False
    
    for f in ALL_FIELDS:
        exists = False
        for pos, name in enumerate(mw.col.models.field_names(notetype)):
            if name == f and pos == ALL_FIELDS[f]:
                exists = True
        if not exists:
            return False
    return True

def fields_empty(note: Note) -> bool:
    for f in set(ALL_FIELDS.keys()) - {EXPRESSION_FIELD_NAME, READING_FIELD_NAME}:
        if note[f] != "":
            return False
    return True


def fill_on_focus_lost(flag: bool, note: Note, fidx: int):
    if fidx not in [EXPRESSION_FIELD_POS, READING_FIELD_POS]:
        return flag

    if not has_fields(note.note_type()):
        log("Note does not have the required fields")
        return flag

    expr_text = note[EXPRESSION_FIELD_NAME]

    if expr_text == "":
        log("Expression field is empty")
        return flag

    if not fields_empty(note):
        log("Not all data fields are empty")
        return flag

    if fidx == EXPRESSION_FIELD_POS:
        return fill_data(note, expr_text, flag)

    reading_text = note[READING_FIELD_NAME]

    if reading_text == "":
        return flag

    return fill_data(note, expr_text, flag, reading_text)

def init():
    gui_hooks.editor_did_unfocus_field.append(fill_on_focus_lost)
