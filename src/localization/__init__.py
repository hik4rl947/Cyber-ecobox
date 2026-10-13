from localization.en import ENGLISH_TEXT
from localization.zh_cn import CHINESE_TEXT


LANGUAGE = "zh_CN"
TRANSLATIONS = {
    "en": ENGLISH_TEXT,
    "zh_CN": CHINESE_TEXT,
}
TEXT = TRANSLATIONS[LANGUAGE]


def set_language(language):
    global LANGUAGE, TEXT
    if language not in TRANSLATIONS:
        raise ValueError(f"Unsupported language: {language}")
    LANGUAGE = language
    TEXT = TRANSLATIONS[language]
