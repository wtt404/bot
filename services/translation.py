import asyncio

import argostranslate.package
import argostranslate.translate

from config import settings

LANGUAGE_NAME_TO_CODE = {
    "english": "en",
    "arabic": "ar",
    "japanese": "ja",
    "korean": "ko",
    "chinese": "zh",
    "russian": "ru",
    "french": "fr",
    "german": "de",
    "ukrainian": "uk",
    "spanish": "es",
    "hebrew": "he",
    "italian": "it",
    "portuguese": "pt",
    "persian": "fa",
}

_index_updated = False
_ensure_lock = asyncio.Lock()


def _installed_pair(from_code: str, to_code: str) -> bool:
    installed = argostranslate.package.get_installed_packages()
    return any(p.from_code == from_code and p.to_code == to_code for p in installed)


def _install_pair_sync(from_code: str, to_code: str):
    global _index_updated

    if not _index_updated:
        print("Updating Argos package index...", flush=True)
        argostranslate.package.update_package_index()
        _index_updated = True

    available = argostranslate.package.get_available_packages()

    match = next(
        (p for p in available if p.from_code == from_code and p.to_code == to_code),
        None
    )

    if match is None:
        raise RuntimeError(f"No Argos model available for {from_code} -> {to_code}")

    print(f"Downloading Argos model {from_code} -> {to_code} (one-time)...", flush=True)
    download_path = match.download()
    argostranslate.package.install_from_path(download_path)
    print(f"Installed Argos model {from_code} -> {to_code}", flush=True)


async def _ensure_pair(from_code: str, to_code: str):
    if _installed_pair(from_code, to_code):
        return

    async with _ensure_lock:
        if _installed_pair(from_code, to_code):
            return

        await asyncio.to_thread(_install_pair_sync, from_code, to_code)


def _translate_sync(text: str, from_code: str, to_code: str) -> str:
    return argostranslate.translate.translate(text, from_code, to_code)


async def translate(text: str, source_language: str = None) -> str:
    if not source_language:
        print("Argos translate: no detected source language, can't translate", flush=True)
        return None

    target_code = LANGUAGE_NAME_TO_CODE.get(settings.TARGET_LANGUAGE.lower(), "en")

    if source_language == target_code:
        return text

    try:
        await _ensure_pair(source_language, target_code)
    except Exception as e:
        print(f"Argos model setup failed for {source_language} -> {target_code}: {e}", flush=True)
        return None

    try:
        return await asyncio.to_thread(_translate_sync, text, source_language, target_code)
    except Exception as e:
        print(f"Argos translation failed: {e}", flush=True)
        return None
