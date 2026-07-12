import aiohttp

from config import OCR_SPACE_API_KEY

OCR_URL = "https://api.ocr.space/parse/image"


async def ocr_image(image_bytes: bytes, filename: str = "image.png") -> str:
    """Extract text from an image via OCR.space. Returns None on failure or
    if no text was found."""

    if not OCR_SPACE_API_KEY:
        print("OCR_SPACE_API_KEY is not set", flush=True)
        return None

    data = aiohttp.FormData()
    data.add_field("apikey", OCR_SPACE_API_KEY)
    # language=auto + OCREngine=2 together enable OCR.space's language
    # auto-detection across 200+ languages, since we don't know ahead of
    # time what language text in a given post's image will be in.
    data.add_field("language", "auto")
    data.add_field("OCREngine", "2")
    data.add_field("isOverlayRequired", "false")
    data.add_field(
        "file",
        image_bytes,
        filename=filename,
        content_type="application/octet-stream",
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OCR_URL,
                data=data,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                result = await resp.json()

    except Exception as e:
        print("OCR.space request failed:", e, flush=True)
        return None

    if result.get("IsErroredOnProcessing"):
        print("OCR.space error:", result.get("ErrorMessage"), flush=True)
        return None

    parsed_results = result.get("ParsedResults") or []

    if not parsed_results:
        return None

    text = (parsed_results[0].get("ParsedText") or "").strip()

    return text or None