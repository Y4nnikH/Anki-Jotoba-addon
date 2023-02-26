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
        word, top_hits = request_word(src_text)
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
    buttons += [editor.addButton("", "add_audio", get_audio, "Adds Audio from Jotoba", "Add Audio", "add_audio_btn")]


# Clear contents
def clear_contents(editor: Editor):
    all_fields = editor.note.fields
    for i in range(len(all_fields)):
        all_fields[i] = f''
    editor.loadNote()
    editor.web.eval(f'focusField(0);')


def add_clear_content(buttons: List[str], editor: Editor):
    buttons += [editor.addButton("", "clear_contents", clear_contents, "Clears all fields", "Clear all", "clear_contents_btn")]


# Update fields
def update_fields(editor: Editor):
    all_fields = editor.note.fields

    if not has_fields(editor.note.note_type()):
        log("Note does not have the required fields")
        return
    
    if all_fields[EXPRESSION_FIELD_POS] == "":
        showInfo("Please enter a word in the Expression field")
        return
    
    try:
        word, top_hits = request_word(all_fields[EXPRESSION_FIELD_POS], all_fields[READING_FIELD_POS])
    except Exception as e:  # error while fetching word
        showInfo("An error occurred while fetching the word from Jotoba")
        log(e)
        return
    
    if not word:
        if top_hits == []:
            showInfo("Word not found")
        else:
            open_select_dialog(editor, top_hits)
        return

    fill_data(editor.note, word, False)

    editor.loadNote()


def add_update_field_btn(buttons: List[str], editor: Editor):
    buttons += [editor.addButton("", "update_fields", update_fields, "Overwrites all fields with data from Jotoba", "Update data", "update_fields_btn")]
    #s = QShortcut(QKeySequence("Ctrl+Shift+U"), editor.parentWindow, activated=)

def complement_data(editor: Editor):
    all_fields = editor.note.fields

    if not has_fields(editor.note.note_type()):
        log("Note does not have the required fields")
        return
    
    if all_fields[EXPRESSION_FIELD_POS] == "":
        showInfo("Please enter a word in the Expression field")
        return
    
    try:
        word, top_hits = request_word(all_fields[EXPRESSION_FIELD_POS], all_fields[READING_FIELD_POS])
    except Exception as e:  # error while fetching word
        showInfo("An error occurred while fetching the word from Jotoba")
        log(e)
        return
    
    if not word:
        if top_hits == []:
            showInfo("Word not found")
        else:
            open_select_dialog(editor, top_hits, overwrite=False)
        return

    fill_data(editor.note, word, False, overwrite=False)

    editor.loadNote()

def add_complement_data_btn(buttons: List[str], editor: Editor):
    buttons += [editor.addButton("", "complement_data", complement_data, "Only fills empty fields with data from Jotoba", "Complement data", "complement_data_btn")]




def open_select_dialog(editor: Editor, top_hits: List[Word], overwrite: bool = True):

    dialog = QDialog(editor.parentWindow)
    dialog.setWindowTitle("Select word")
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    dialog.setMinimumWidth(400)
    dialog.setMinimumHeight(250)
    dialog.height = 250
    layout = QVBoxLayout()
    dialog.setLayout(layout)

    text = QLabel("No exact match found. Please select a word from the list.")
    layout.addWidget(text)

    list_widget = QListWidget()
    for hit in top_hits:
        list_widget.addItem(hit.expression)
    list_widget.currentRowChanged.connect(lambda: show_word_info(list_widget, expression, meaning, top_hits))
    layout.addWidget(list_widget)

    # Expression, reading, meaning of currently selected word
    selected_word = top_hits[list_widget.currentRow()]
    expression = QLabel(f"Expression: {selected_word.expression} ({selected_word.reading})")
    meaning = QLabel(f"Meaning: {'; '.join(selected_word.glosses)}")
    layout.addWidget(expression)
    layout.addWidget(meaning)
    

    accept_btn = QPushButton("Select")
    accept_btn.clicked.connect(lambda: select_word(list_widget, editor, dialog, top_hits, overwrite))

    cancel_btn = QPushButton("Cancel")
    cancel_btn.clicked.connect(dialog.reject)

    btn_layout = QHBoxLayout()
    btn_layout.addWidget(accept_btn)
    btn_layout.addWidget(cancel_btn)

    layout.addLayout(btn_layout)

    dialog.exec()

def show_word_info(list_widget: QListWidget, expression: QLabel, meaning: QLabel, top_hits: List[Word]):
    selected_word = top_hits[list_widget.currentRow()]
    expression.setText(f"Expression: {selected_word.expression} ({selected_word.reading})")
    meaning.setText(f"Meaning: {', '.join(selected_word.glosses)}")

def select_word(list_widget: QListWidget, editor: Editor, dialog: QDialog, top_hits: List[Word], overwrite: bool = True):
    word = top_hits[list_widget.currentRow()]
    fill_data(editor.note, word, False, overwrite)
    editor.loadNote()
    dialog.accept()



def hide_buttons(editor: Editor):
    if not has_fields(editor.note.note_type()):
        show = 'none'
    else:
        show = 'inline-block'

    try:
        editor.web.eval(f"document.getElementById('add_audio_btn').style.display = '{show}';")
        editor.web.eval(f"document.getElementById('clear_contents_btn').style.display = '{show}';")
        editor.web.eval(f"document.getElementById('update_fields_btn').style.display = '{show}';")
        editor.web.eval(f"document.getElementById('complement_data_btn').style.display = '{show}';")
    except Exception as e:
        log(e)

def init():
    gui_hooks.editor_did_init_buttons.append(add_clear_content)
    gui_hooks.editor_did_init_buttons.append(add_update_field_btn)
    gui_hooks.editor_did_init_buttons.append(add_complement_data_btn)
    gui_hooks.editor_did_init_buttons.append(add_audio_btn)
    # hide buttons
    gui_hooks.editor_did_load_note.append(hide_buttons)
