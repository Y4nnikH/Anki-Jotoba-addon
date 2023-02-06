from aqt.editor import Editor
from typing import List

from .editor import EXPRESSION_FIELD_POS, AUDIO_FIELD_POS, READING_FIELD_POS, fill_data, has_fields
from .jotoba import *
from .utils import log
from aqt.utils import showInfo
from aqt.qt import *
from aqt import gui_hooks


# Audio button
def get_audio(editor: Editor):
    all_fields = editor.note.fields
    src_text = all_fields[EXPRESSION_FIELD_POS]
    if src_text == "":
        return
    try:
        word = request_word(src_text)
    except:
        showInfo("Word not found")
        return

    try:
        set_audio_in_editor(word.audio_url, editor)
    except AttributeError:
        showInfo("Word has no audio")


def set_audio_in_editor(audio: str, editor: Editor):
    audio = editor.urlToFile(audio)
    all_fields = editor.note.fields
    all_fields[AUDIO_FIELD_POS] = f'[sound:{audio}]'
    editor.loadNote()
    editor.web.setFocus()
    editor.web.eval(f'focusField({AUDIO_FIELD_POS});')
    editor.web.eval('caretToEnd();')


def add_audio_btn(buttons: List[str], editor: Editor):
    buttons += [editor.addButton("", "add_audio", get_audio, "Adds Audio from Jotoba", "Add Audio")]


# Clear contents
def clear_contents(editor: Editor):
    all_fields = editor.note.fields
    for i in range(len(all_fields)):
        all_fields[i] = f''
    editor.loadNote()
    editor.web.eval(f'focusField(0);')


def add_clear_content(buttons: List[str], editor: Editor):
    buttons += [editor.addButton("", "clear_contents", clear_contents, "Clears all fields", "Clear all")]


# Update fields
def update_fields(editor: Editor):
    all_fields = editor.note.fields

    if not has_fields(editor.note):
        log("Note does not have the required fields")
        return
    
    if all_fields[EXPRESSION_FIELD_POS] == "":
        showInfo("Please enter a word in the Expression field")
        return

    if all_fields[READING_FIELD_POS] == "":
        fill_data(editor.note, all_fields[EXPRESSION_FIELD_POS], False)
    else:
        fill_data(editor.note, all_fields[EXPRESSION_FIELD_POS], False, all_fields[READING_FIELD_POS])

    editor.loadNote()


def add_update_field_btn(buttons: List[str], editor: Editor):
    buttons += [editor.addButton("", "update_fields", update_fields, "Overwrites all fields with data from Jotoba", "Update data")]
    #s = QShortcut(QKeySequence("Ctrl+Shift+U"), editor.parentWindow, activated=)


def init():
    gui_hooks.editor_did_init_buttons.append(add_clear_content)
    gui_hooks.editor_did_init_buttons.append(add_update_field_btn)
    gui_hooks.editor_did_init_buttons.append(add_audio_btn)
