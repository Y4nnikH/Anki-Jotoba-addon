from typing import Optional, List

import requests
import json
from aqt import mw

from .utils import log

config = mw.addonManager.getConfig(__name__)
log(config)

LANGUAGE = config["Language"]
JOTOBA_URL = config["Jotoba_URL"]
WORDS_API_URL = JOTOBA_URL + config["API_Words_Suffix"]
SENTENCE_API_URL = JOTOBA_URL + config["API_Sentence_Suffix"]


class Word:
    expression: str
    reading: str
    glosses: List[str]
    pitch: str
    part_of_speech: List[str]
    audio_url: str

    def __init__(self, word):
        if not word:
            return
        if "kanji" in word["reading"]:
            self.expression = word["reading"]["kanji"]
            self.reading = word["reading"]["kana"]
        else:
            self.expression = word["reading"]["kana"]
            self.reading = ""
        self.pitch = get_pitch_html(word)
        self.glosses = get_glosses(word)
        self.part_of_speech = get_pos(word)
        if "audio" in word:
            self.audio_url = JOTOBA_URL + word["audio"]

    def __repr__(self):
        return f"{self.expression} ({self.reading})"


def request_sentence(text) -> List[str]:
    return json.loads(request(SENTENCE_API_URL, text).text)["sentences"]


def request_word(text, kana="", must_match=True) -> tuple[Optional[Word], List[Word]]:
    log("Looking up '" + text + "' ...")
    return find_word(json.loads(request(WORDS_API_URL, text).text), text, kana)


def request(URL, text) -> requests.Response:
    data = '{"query":"' + text + '","language":"' + LANGUAGE + '","no_english":true}'
    headers = {"Content-Type": "application/json; charset=utf-8", "Accept": "application/json"}
    return requests.post(URL, data=data.encode('utf-8'), headers=headers)


def find_word(res, expr:str, kana="") -> tuple[Optional[Word], List[Word]]:
    words = res["words"]
    potential_words = []
    kana_words = []
    for word in words:
        reading = word["reading"]

        if "kanji" in reading:
            if reading["kanji"] == expr and (reading["kana"] == kana or kana == ""):
                potential_words.append(word)
            elif reading["kana"] == expr or reading["kana"] == kana:    # kana word has kanji writing or kanji writing is different from expr
                kana_words.append(word)
        else:
            if reading["kana"] == expr:
                potential_words.append(word)

    if len(potential_words) == 0:
        potential_words = kana_words

    if len(potential_words) != 1:  # esp. multiple hits for word written in kana possible, but also for kanji words with different readings
        if len(potential_words) > 1:
            log("Multiple hits for '" + expr + "'")
        else:
            log("No exact hit for '" + expr + "'")
        top_hits = []
        for word in words:
            top_hits.append(Word(word))
        return None, top_hits

    word = Word(potential_words[0])

    return word, None


def get_pos(word) -> List[str]:
    pos = []
    if word is not None and "senses" in word:
        for sense in word["senses"]:
            for key in sense["pos"]:
                pos.append(parse_pos(word, key))
            if "misc" in sense:
                pos.append(parse_misc(sense["misc"]))
        pos = list(dict.fromkeys(pos)) # remove duplicates
    return pos

def parse_pos(word, pos) -> str:
    if isinstance(pos, str):
        if pos == "Adverb":
            return "fukushi"
        if pos == "AdverbTo":
            return "taking to"
        if pos == "Expr":
            return "expression"
        if pos == "Conjunction":
            return "conjunction"
        if pos == "Interjection":
            return "interjection"
        if pos == "Prefix":
            return "prefix"
        if pos == "Suffix":
            return "suffix"
        if pos == "Particle":
            return "particle"
        if pos == "Counter":
            return "counter"
    else:
        if "Noun" in pos:
            if pos.get("Noun") == "Normal":
                return "futsuumeishi"
            if pos.get("Noun") == "Suffix":
                return "suffix"
        if "Verb" in pos:
            if pos.get("Verb") == "Ichidan":
                return "verb ichidan"
            if isinstance(pos.get("Verb"), dict) and "Godan" in pos.get("Verb"):
                return "verb godan"
            if pos.get("Verb") == "Transitive":
                return "transitive"
            if pos.get("Verb") == "Intransitive":
                return "intransitive"
            if word.get("reading").get("kana") in ["する", "くる"]:
                return "verb irregular"
            if isinstance(pos.get("Verb"), dict) and pos.get("Verb").get("Irregular") == "NounOrAuxSuru":
                return "suru"
        if "Adjective" in pos:
            if pos.get("Adjective") == "Keiyoushi":
                return "keiyoushi"
            if pos.get("Adjective") == "I":
                return "keiyoushi"
            if pos.get("Adjective") == "Na":
                return "keiyoudoushi"
            if pos.get("Adjective") == "No":
                return "taking no"
    return "?"

def parse_misc(misc) -> str:
    if misc == "UsuallyWrittenInKana":
        return "kana"
    if misc == "OnomatopoeicOrMimeticWord":
        return "onomatopoeia"
    if misc == "Abbreviation":
        return "abbreviation"
    if misc == "Rare":
        return "rare"
    if misc == "InternetSlang":
        return "internet slang"
    if misc == "Derogatory":
        return "derogatory"
    if misc == "HonorificLanguage":
        return "honorific"
    if misc == "Colloquialism":
        return "colloquialism"
    return "?"


def get_katakana(word) -> str:
    return word["reading"]["kana"]


def gloss_count(word) -> int:
    senses = word["senses"]
    count = 0
    for sense in senses:
        count += len(sense["glosses"])

    return count


def get_glosses(word) -> List[str]:
    senses = word["senses"]
    glosses = []
    for sense in senses:
        for gloss in sense["glosses"]:
            glosses.append(gloss)
    return glosses


def get_pitch(word) -> str:
    if not "pitch" in word:
        return ""

    pitch_str = ""
    pitch = word["pitch"]

    for i in pitch:
        part = i["part"]
        high = i["high"]
        if high:
            pitch_str += "↑"
        else:
            pitch_str += "↓"
        pitch_str += part

    if pitch_str == "":
        return ""

    return pitch_str


def get_pitch_html(word) -> str:
    if word is None or "pitch" not in word:
        return ""

    pitch_str = ""
    pitch = word["pitch"]

    p_count = len(pitch)

    for i, p in enumerate(pitch):
        part = p["part"]
        high = p["high"]

        classes = ""

        if high:
            classes += "t"
        else:
            classes += "b"

        if i != p_count - 1:
            classes += " r"

        pitch_str += f'<span class="pitch {classes}">{part}</span>'

    if pitch_str == "":
        return ""

    return pitch_str
