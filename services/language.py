from lingua import Language, LanguageDetectorBuilder

LANGUAGES = [
    Language.ENGLISH,
    Language.ARABIC,
    Language.JAPANESE,
    Language.KOREAN,
    Language.CHINESE,
    Language.RUSSIAN,
    Language.FRENCH,
    Language.GERMAN,
    Language.UKRAINIAN,
    Language.SPANISH,
    Language.HEBREW,
    Language.ITALIAN,
    Language.PORTUGUESE,
]

detector = LanguageDetectorBuilder.from_languages(*LANGUAGES).build()


def detect_language(text: str):
    language = detector.detect_language_of(text)

    if language is None:
        return None

    return language.iso_code_639_1.name.lower()