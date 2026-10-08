import json
import re
import time
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from models.post import Post, Media
from services.browser import new_page, page_semaphore
from services.fetchers.base import Fetcher
from services.fetchers.timeutil import from_unix

SHORTCODE_PATTERN = re.compile(r"/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
MAX_ITEMS = 10


def _find_key(obj, key):
    if isinstance(obj, dict):
        if obj.get(key):
            yield obj[key]
        for value in obj.values():
            yield from _find_key(value, key)
    elif isinstance(obj, list):
        for value in obj:
            yield from _find_key(value, key)


def _extract_payload(html):
    scripts = re.findall(r"<script[^>]*data-sjs[^>]*>(.*?)</script>", html, re.DOTALL)

    for script in scripts:
        if "xig_polaris_media" not in script:
            continue

        try:
            data = json.loads(script)
        except json.JSONDecodeError:
            continue

        for media in _find_key(data, "xig_polaris_media"):
            if isinstance(media, dict):
                return media.get("if_not_gated_logged_out") or media

    return None


def _pick_video(item):
    versions = [v for v in (item.get("video_versions") or []) if v.get("url")]

    if versions:
        best = max(versions, key=lambda v: (v.get("width") or 0) * (v.get("height") or 0))
        return best["url"]

    return item.get("video_url")


def _pick_image(item):
    candidates = (item.get("image_versions2") or {}).get("candidates") or []
    candidates = [c for c in candidates if c.get("url")]

    if candidates:
        best = max(candidates, key=lambda c: (c.get("width") or 0) * (c.get("height") or 0))
        return best["url"]

    return item.get("display_url") or item.get("thumbnail_src")


def _children(media):
    if media.get("carousel_media"):
        return media["carousel_media"]

    edges = (media.get("edge_sidecar_to_children") or {}).get("edges") or []

    if edges:
        return [edge.get("node") or {} for edge in edges]

    return [media]


def _caption(media):
    caption = media.get("caption")

    if isinstance(caption, dict):
        return caption.get("text") or ""

    if isinstance(caption, str):
        return caption

    edges = (media.get("edge_media_to_caption") or {}).get("edges") or []

    if edges:
        return (edges[0].get("node") or {}).get("text") or ""

    return ""


def _post_from_payload(media, code):
    owner = media.get("user") or media.get("owner") or {}
    username = owner.get("username")

    items = []
    seen = set()

    for child in _children(media):
        video = _pick_video(child)
        url = video or _pick_image(child)

        if not url or url in seen:
            continue

        seen.add(url)
        items.append(Media(url=url, type="video" if video else "image"))

    return Post(
        platform="instagram",
        text=_caption(media).strip(),
        media=items[:MAX_ITEMS],
        author_name=owner.get("full_name") or username,
        author_handle=username,
        author_avatar=owner.get("profile_pic_url") or owner.get("profile_pic_url_hd"),
        url=f"https://www.instagram.com/p/{code}/" if code else None,
        posted_at=from_unix(media.get("taken_at") or media.get("taken_at_timestamp"))
    )


def _post_from_meta(html, code):
    soup = BeautifulSoup(html, "html.parser")

    def meta(prop):
        tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
        return tag.get("content") if tag else None

    title = meta("og:title") or ""
    description = meta("og:description") or ""
    image = meta("og:image")
    video = meta("og:video") or meta("og:video:secure_url")

    name = None
    handle = None
    caption = ""

    match = re.match(r"^(.*?) on Instagram", title)
    if match:
        name = match.group(1).strip()

    match = re.search(r"-\s*([A-Za-z0-9_.]+)\s+on\s", description)
    if match:
        handle = match.group(1)

    match = re.search(r':\s*["“](.*)["”]\.?\s*$', description, re.DOTALL)
    if match:
        caption = match.group(1).strip()

    posted_at = None
    match = re.search(r"\bon ([A-Z][a-z]+ \d{1,2}, \d{4})", description)
    if match:
        try:
            posted_at = datetime.strptime(match.group(1), "%B %d, %Y").replace(tzinfo=timezone.utc)
        except ValueError:
            posted_at = None

    items = []

    if video:
        items.append(Media(url=video, type="video"))
    elif image:
        items.append(Media(url=image, type="image"))

    if not items and not caption:
        return None

    return Post(
        platform="instagram",
        text=caption,
        media=items,
        author_name=name or handle,
        author_handle=handle,
        author_avatar=None,
        url=f"https://www.instagram.com/p/{code}/" if code else None,
        posted_at=posted_at
    )


class InstagramFetcher(Fetcher):
    async def fetch(self, url: str) -> Post:
        start = time.monotonic()

        match = SHORTCODE_PATTERN.search(url)
        target = url if "/share/" in url or not match else f"https://www.instagram.com/p/{match.group(1)}/"

        async with page_semaphore():
            page = await new_page()

            try:
                await page.set_extra_http_headers({
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "en-US,en;q=0.9",
                })

                await page.goto(target, wait_until="domcontentloaded", timeout=30000)

                try:
                    await page.wait_for_selector(
                        'script[type="application/json"][data-sjs]',
                        state="attached",
                        timeout=8000
                    )
                except Exception:
                    pass

                await page.wait_for_timeout(500)

                final_url = page.url
                html = await page.content()

            finally:
                await page.close()

        if "/accounts/login" in final_url:
            raise RuntimeError(
                "Instagram showed a login wall (private post, or this connection is flagged by Instagram)"
            )

        code_match = SHORTCODE_PATTERN.search(final_url) or match
        code = code_match.group(1) if code_match else ""

        payload = _extract_payload(html)
        post = _post_from_payload(payload, code) if payload else None
        method = "payload"

        if post is None or (not post.media and not post.text):
            post = _post_from_meta(html, code)
            method = "meta"

        if post is None:
            raise RuntimeError("Couldn't read this Instagram post (blocked, private, or removed)")

        print(f"[TIMING] InstagramFetcher.fetch ({method}): {time.monotonic() - start:.2f}s", flush=True)
        print(f"Instagram media: {post.media}", flush=True)

        return post
