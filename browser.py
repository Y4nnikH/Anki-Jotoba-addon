from anki.notes import NoteId, Note
from anki.collection import Collection
from aqt.browser import Browser
from typing import List, Sequence, Tuple

from .editor import EXPRESSION_FIELD_NAME, READING_FIELD_NAME, PITCH_FIELD_NAME, MEANING_FIELD_NAME, POS_FIELD_NAME, EXAMPLE_FIELD_PREFIX, has_fields
from .jotoba import *
from .utils import format_furigana, log
import aqt
from aqt import progress
from aqt import mw, gui_hooks
from aqt.operations import CollectionOp, OpChanges
from aqt.utils import showInfo
from aqt.qt import *


def setup_browser_menu(browser: Browser):
    """ Add bulk-add menu """
    a = QAction("Joto Bulk-add Data", browser)
    a.triggered.connect(lambda: bulk_update_selected_notes(browser))
    browser.form.menuEdit.addSeparator()
    browser.form.menuEdit.addAction(a)

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


def bulk_options_dialog(browser: Browser) -> dict[str, bool]:
    dialog = QDialog(browser.window())
    dialog.setWindowTitle("Select options")
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    dialog.setLayout(QGridLayout())

    label_1 = QLabel("Select which fields should be filled")

    expression_checkbox = QCheckBox("Expression")
    reading_checkbox = QCheckBox("Reading")
    pitch_checkbox = QCheckBox("Pitch")
    meaning_checkbox = QCheckBox("Meaning")
    pos_checkbox = QCheckBox("POS")
    sentences_checkbox = QCheckBox("Sentences")

    expression_checkbox.setChecked(False)
    reading_checkbox.setChecked(True)
    pitch_checkbox.setChecked(True)
    meaning_checkbox.setChecked(True)
    pos_checkbox.setChecked(True)
    sentences_checkbox.setChecked(True)

    label_2 = QLabel("If an exact match is not found")
    behaviour_radio = QButtonGroup()
    select_result_radio = QRadioButton("Manually select result")
    replace_similar_radio = QRadioButton("Replace with similar")
    skip_unk_radio = QRadioButton("Skip")
    skip_unk_radio.setChecked(True)
    select_result_radio.setDisabled(True)
    behaviour_radio.addButton(replace_similar_radio)
    behaviour_radio.addButton(skip_unk_radio)
    behaviour_radio.addButton(select_result_radio)

    label_3 = QLabel("If a field is already filled")
    overwrite_radio = QButtonGroup()
    overwrite_do_radio = QRadioButton("Overwrite field")
    overwrite_skip_radio = QRadioButton("Skip field")
    overwrite_skip_radio.setChecked(True)
    overwrite_radio.addButton(overwrite_do_radio)
    overwrite_radio.addButton(overwrite_skip_radio)

    dialog.layout().addWidget(label_1, 0, 0, 1, 3)
    dialog.layout().addWidget(expression_checkbox, 1, 0)
    dialog.layout().addWidget(reading_checkbox, 1, 1)
    dialog.layout().addWidget(pitch_checkbox, 1, 2)
    dialog.layout().addWidget(meaning_checkbox, 2, 0)
    dialog.layout().addWidget(pos_checkbox, 2, 1)
    dialog.layout().addWidget(sentences_checkbox, 2, 2)
    dialog.layout().addWidget(label_2, 3, 0, 1, 3)
    dialog.layout().addWidget(select_result_radio, 4, 0)
    dialog.layout().addWidget(replace_similar_radio, 4, 1)
    dialog.layout().addWidget(skip_unk_radio, 4, 2)
    dialog.layout().addWidget(label_3, 5, 0, 1, 3)
    dialog.layout().addWidget(overwrite_do_radio, 6, 0)
    dialog.layout().addWidget(overwrite_skip_radio, 6, 1)

    ok_button = QPushButton("OK")
    ok_button.clicked.connect(dialog.accept)

    cancel_button = QPushButton("Cancel")
    cancel_button.clicked.connect(dialog.reject)

    dialog.layout().addWidget(ok_button, 7, 0)
    dialog.layout().addWidget(cancel_button, 7, 1)

    dialog.exec()

    if dialog.result() == QDialog.DialogCode.Accepted:
        return {
            "expression": expression_checkbox.isChecked(),
            "reading": reading_checkbox.isChecked(),
            "pitch": pitch_checkbox.isChecked(),
            "meaning": meaning_checkbox.isChecked(),
            "pos": pos_checkbox.isChecked(),
            "sentences": sentences_checkbox.isChecked(),
            "replace_similar": replace_similar_radio.isChecked(),
            "skip_unk": skip_unk_radio.isChecked(),
            "overwrite": overwrite_do_radio.isChecked()
        }
    else:
        return None

def update_selected_notes_action(col: Collection, nids: Sequence[NoteId], options: dict[str, bool]):
    custom_undo_pos = col.add_custom_undo_entry("Joto bulk-update data")
    
    expression = options["expression"]
    reading = options["reading"]
    pitch = options["pitch"]
    meaning = options["meaning"]
    pos = options["pos"]
    sentences = options["sentences"]
    replace_similar = options["replace_similar"]
    skip_unk = options["skip_unk"]
    overwrite = options["overwrite"]
    
    replaced_with = []
    
    def update_single_note(col: Collection, note: Note, undo_pos: int) -> OpChanges:
        col.update_note(note)
        return col.merge_undo_entries(undo_pos)

    for i, nid in enumerate(nids):

        log(f"Processing note {i + 1} of {len(nids)}")
        # Progress Bar
        aqt.mw.taskman.run_on_main(lambda: aqt.mw.progress.update("Processing note {}/{}".format(i + 1, len(nids)), value=i, max=len(nids)))

        note = col.get_note(nid)

        if not has_fields(note.note_type()):
            log("Skipping: wrong note type")
            continue

        if not options["overwrite"]:
            need_change = expression and note[EXPRESSION_FIELD_NAME] == "" or reading and note[READING_FIELD_NAME] == "" or pitch and note[PITCH_FIELD_NAME] == "" or meaning and note[MEANING_FIELD_NAME] == "" or pos and note[POS_FIELD_NAME] == ""

            if sentences:
                for i in range(3):
                    if note[EXAMPLE_FIELD_PREFIX + str(i + 1)] == "":
                        need_change = True
                        break

            if not need_change:
                continue

        try:
            kana = note[READING_FIELD_NAME]
            word, top_hits = request_word(sanitize(note[EXPRESSION_FIELD_NAME]), kana)
        except Exception as e:
            log("Could not fetch '" + note[EXPRESSION_FIELD_NAME] + "'")
            log(e)
            note.add_tag("joto_error")
            update_single_note(col, note, custom_undo_pos)
            continue

        if not word:
            if top_hits == []:
                note.add_tag("joto_skip")
                update_single_note(col, note, custom_undo_pos)
                continue
            elif top_hits[0].expression == note[EXPRESSION_FIELD_NAME]:
                word = top_hits[0]
            elif replace_similar:
                word = top_hits[0]
                replaced_with.append([note[EXPRESSION_FIELD_NAME], word.expression])
            elif skip_unk:
                note.add_tag("joto_skip")
                update_single_note(col, note, custom_undo_pos)
                continue
            else:
                note.add_tag("joto_skip")
                update_single_note(col, note, custom_undo_pos)
                continue
                #TODO: mw.progress...? is causing the dialog to be unreachable (processing.. window shows up and blocks the dialog)
                dialog = QDialog(browser.window())
                dialog.setWindowTitle("Select word")
                dialog.setWindowModality(Qt.WindowModality.WindowModal)
                dialog.setLayout(QVBoxLayout())

                word = top_hits[0]

                def set_word(value):
                    global word
                    word = value

                for i, word in enumerate(top_hits):
                    button = QPushButton(word.expression)
                    button.clicked.connect(lambda i=i: set_word(top_hits[i]))
                    dialog.layout().addWidget(button)

                dialog.exec() # Wait for dialog to close

                if word is None:
                    note.add_tag("joto_skip")
                    update_single_note(col, note, custom_undo_pos)
                    continue

        if expression and (note[EXPRESSION_FIELD_NAME] == "" or overwrite):
            note[EXPRESSION_FIELD_NAME] = word.expression
        
        if reading and (note[READING_FIELD_NAME] == "" or overwrite):
            note[READING_FIELD_NAME] = word.reading
            
        if pitch and (note[PITCH_FIELD_NAME] == "" or overwrite) and word.pitch != "":
            note[PITCH_FIELD_NAME] = word.pitch
            
        if meaning and (note[MEANING_FIELD_NAME] == "" or overwrite):
            note[MEANING_FIELD_NAME] = "; ".join(word.glosses[:3])
            
        if pos and (note[POS_FIELD_NAME] == "" or overwrite):
            note[POS_FIELD_NAME] = "; ".join(word.part_of_speech)

        if sentences:
            try:
                sentences = request_sentence(note[EXPRESSION_FIELD_NAME])
                
                if overwrite:
                    for i, sentence in enumerate(sentences):
                        if i > 2:
                            break
                        field_name = EXAMPLE_FIELD_PREFIX + str(i + 1)
                        note[field_name] = format_furigana(sentence["furigana"])
                else:
                    need_sentence = []
                    for i in range(3):
                        if note[EXAMPLE_FIELD_PREFIX + str(i + 1)] == "":
                            need_sentence.append(i)
                    
                    for i,j in zip(need_sentence, range(len(sentences))):
                        field_name = EXAMPLE_FIELD_PREFIX + str(i + 1)
                        note[field_name] = format_furigana(sentences[j]["furigana"])
            except:
                log("Did not find any sentences")
                note.add_tag("joto_no_sentences")
                pass
        
        update_single_note(col, note, custom_undo_pos)
    
    return col.merge_undo_entries(custom_undo_pos)
    

def update_selected_notes_op(*, nids: Sequence[NoteId], options: dict[str, bool], parent: QWidget) -> CollectionOp[OpChanges]:
    return CollectionOp(parent, lambda col: update_selected_notes_action(col, nids, options))

def bulk_update_selected_notes(browser: Browser):
    options = bulk_options_dialog(browser)
    if options is None:
        return
    
    selected_nodes = browser.selectedNotes()
    
    # todo: make progress bar work -> use aqt.mw.taskman.run_on_main without running op in background ?

    update_selected_notes_op(parent=browser.window(), nids=selected_nodes, options=options).run_in_background()


def init():
    gui_hooks.browser_menus_did_init.append(setup_browser_menu)  # Bulk add
