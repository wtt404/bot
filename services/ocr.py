import aiohttp
import time

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
    # Engine 3 supports 200+ languages (incl. Hebrew, Persian, and other
    # RTL scripts) via auto-detection - Engine 2 only ever added a handful
    # of extra languages (Korean/Japanese/Russian/Ukrainian/Thai/Vietnamese)
    # and doesn't reliably handle Hebrew/Persian. Engine 3 has its own
    # separate free quota (2,500/mo) so this doesn't eat into Engine 1/2's.
    data.add_field("language", "auto")
    data.add_field("OCREngine", "3")
    data.add_field("isOverlayRequired", "false")
    data.add_field(
        "file",
        image_bytes,
        filename=filename,
        content_type="application/octet-stream",
    )

    try:
        ocr_start = time.monotonic()
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OCR_URL,
                data=data,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                result = await resp.json()
        print(f"[TIMING] OCR.space request: {time.monotonic() - ocr_start:.2f}s", flush=True)

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
