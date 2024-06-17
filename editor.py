from anki.notes import Note
from anki.models import NoteType
from aqt import mw, gui_hooks
from aqt.utils import showInfo

from .jotoba import *
from .utils import format_furigana, log

# Field constants
EXPRESSION_FIELD_NAME = "Expression"
READING_FIELD_NAME = "Reading"
PITCH_FIELD_NAME = "Pitch"
MEANING_FIELD_NAME = "Meaning"
POS_FIELD_NAME = "POS"
IMAGE_FIELD_NAME = "Image"
AUDIO_FIELD_NAME = "Audio"
NOTES_FIELD_NAME = "Notes"
EXAMPLE_FIELD_PREFIX = "Example "

ALL_FIELDS = [EXPRESSION_FIELD_NAME, READING_FIELD_NAME, PITCH_FIELD_NAME, MEANING_FIELD_NAME, POS_FIELD_NAME,
             IMAGE_FIELD_NAME, AUDIO_FIELD_NAME, NOTES_FIELD_NAME, EXAMPLE_FIELD_PREFIX + "1",
             EXAMPLE_FIELD_PREFIX + "1 Audio", EXAMPLE_FIELD_PREFIX + "2", EXAMPLE_FIELD_PREFIX + "2 Audio",
             EXAMPLE_FIELD_PREFIX + "3", EXAMPLE_FIELD_PREFIX + "3 Audio"]


def fill_data(note: Note, word: Word, flag: bool, overwrite: bool = True):

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
        sentences = request_sentence(word.expression)
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


# Check whether all fields are available in given notetype and return their positions
def get_joto_fields(notetype: NoteType) -> Optional[dict]:
    fields = {}
    for f in ALL_FIELDS:
        for pos, name in enumerate(mw.col.models.field_names(notetype)):
            if name == f:
                fields[f] = pos
        if f not in fields:
            return None
    return fields

def fields_empty(note: Note) -> bool:
    for f in set(ALL_FIELDS) - {EXPRESSION_FIELD_NAME, READING_FIELD_NAME}:
        if note[f] != "":
            return False
    return True


def fill_on_focus_lost(flag: bool, note: Note, fidx: int):
    joto_fields = get_joto_fields(note.note_type())
    if joto_fields is None:
        log("Note does not have the required fields")
        return flag
    
    EXPRESSION_FIELD_POS = joto_fields[EXPRESSION_FIELD_NAME]
    READING_FIELD_POS = joto_fields[READING_FIELD_NAME]

    if fidx not in [EXPRESSION_FIELD_POS, READING_FIELD_POS]:
        return flag

    expr_text = note[EXPRESSION_FIELD_NAME]

    if expr_text == "":
        log("Expression field is empty")
        return flag

    if not fields_empty(note):
        log("Not all data fields are empty")
        return flag

    reading_text = note[READING_FIELD_NAME]

    if fidx == EXPRESSION_FIELD_POS and reading_text != "": # expression field was focused and reading field is not empty
        return flag
    if fidx == READING_FIELD_POS and reading_text == "":    # reading field was focused and reading field is empty
        return flag
    
    try:
        word, top_hits = request_word(expr_text, reading_text)
    except Exception as e:  # error while fetching word
        log("Error while fetching word")
        log(e)
        return
    
    if not word:
        log("Word not found")
        return

    return fill_data(note, word, flag)

def init():
    gui_hooks.editor_did_unfocus_field.append(fill_on_focus_lost)
