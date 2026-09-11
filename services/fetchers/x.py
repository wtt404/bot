import json
import math
import re
import time

import aiohttp

from models.post import Post, Media
from services.browser import new_page, page_semaphore
from services.fetchers.base import Fetcher

SYNDICATION_URL = "https://cdn.syndication.twimg.com/tweet-result"


def _upgrade_photo_quality(url: str) -> str:
    
    base = url.split("?")[0]
    base = re.sub(r":[a-zA-Z]+$", "", base)

    filename = base.rsplit("/", 1)[-1]
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"

    if ext not in ("jpg", "jpeg", "png"):
        ext = "jpg"

    return f"{base}?format={ext}&name=orig"


def _get_token(tweet_id: str) -> str:
    value = (int(tweet_id) / 1e15) * math.pi
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"

    n = int(value)
    frac = value - n

    int_str = "" if n else "0"
    while n > 0:
        int_str = digits[n % 36] + int_str
        n //= 36

    frac_str = ""
    for _ in range(12):
        frac *= 36
        d = int(frac)
        frac_str += digits[d]
        frac -= d
        if frac <= 1e-9:
            break

    token = int_str + frac_str
    return re.sub(r"(0+|\.)", "", token)


class XFetcher(Fetcher):
    async def fetch(self, url: str) -> Post:
        status_match = re.search(r"/status/(\d+)", url)
        status_id = status_match.group(1) if status_match else None

        if status_id:
            syndication_start = time.monotonic()
            try:
                post = await self._fetch_via_syndication(status_id)
                print(f"[TIMING] Syndication fetch succeeded in {time.monotonic() - syndication_start:.2f}s", flush=True)
                return post
            except Exception as e:
                print(f"Syndication fetch failed ({e}), falling back to browser scraping", flush=True)

        return await self._fetch_via_browser(url)

    async def _fetch_via_syndication(self, status_id: str) -> Post:
        token = _get_token(status_id)

        async with aiohttp.ClientSession() as session:
            async with session.get(
                SYNDICATION_URL,
                params={"id": status_id, "token": token, "lang": "en"},
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Syndication endpoint returned status {resp.status}")

                data = await resp.json()

        raw_text = data.get("text") or ""

        seen = set()
        media = []
        media_tco_urls = set()

        media_details = data.get("mediaDetails", []) or data.get("photos", []) or []

        for photo in media_details:
            photo_url = photo.get("media_url_https")

            tco = photo.get("url") if photo.get("url", "").startswith("https://t.co/") else None
            if tco:
                media_tco_urls.add(tco)

            if not photo_url or photo_url in seen:
                continue

            if photo.get("type") not in (None, "photo"):
                continue

            seen.add(photo_url)
             media.append(Media(url=_upgrade_photo_quality(photo_url), type="image"))

        for m in (data.get("entities", {}) or {}).get("media", []) or []:
            tco = m.get("url")
            if tco and tco.startswith("https://t.co/"):
                media_tco_urls.add(tco)

        video = data.get("video")

        if video:
            variants = video.get("variants", []) or []

            hls_variant = next(
                (v for v in variants if v.get("type") == "application/x-mpegURL" and v.get("src")),
                None
            )

            if hls_variant and hls_variant["src"] not in seen:
                seen.add(hls_variant["src"])
                media.append(Media(url=hls_variant["src"], type="video"))
                print("Using HLS playlist for best video quality", flush=True)
            else:
                mp4_variants = [
                    v for v in variants
                    if v.get("type") == "video/mp4" and v.get("src")
                ]

                if mp4_variants:
                    best = max(mp4_variants, key=lambda v: v.get("bitrate", 0))

                    if best["src"] not in seen:
                        seen.add(best["src"])
                        media.append(Media(url=best["src"], type="video"))
                        print(f"No HLS playlist available, using capped direct mp4 (bitrate={best.get('bitrate')})", flush=True)

        text = raw_text
        for tco in media_tco_urls:
            text = text.replace(tco, "")
        text = text.strip()

        if media and text == raw_text.strip():
            text = re.sub(r"\s*https://t\.co/\w+\s*$", "", text).strip()

        if not text and not media:
            raise RuntimeError("Syndication response has no text and no media")

        print(f"Syndication media: {media}", flush=True)
        print(f"Syndication text after t.co stripping: {text!r}", flush=True)

        return Post(platform="x", text=text, media=media)

    async def _fetch_via_browser(self, url: str) -> Post:
        fetch_start = time.monotonic()

        async with page_semaphore():
            queue_wait = time.monotonic() - fetch_start
            if queue_wait > 0.5:
                print(f"[TIMING] XFetcher: waited {queue_wait:.2f}s for a free browser slot", flush=True)

            page = await new_page()
            captured_video_urls = set()

            def _capture_video(response):
                resp_url = response.url
                if "video.twimg.com" in resp_url and (".m3u8" in resp_url or ".mp4" in resp_url):
                    captured_video_urls.add(resp_url)

            page.on("response", _capture_video)

            try:
                print("FETCH START", flush=True)
                nav_start = time.monotonic()

                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=30000
                )
                print(f"[TIMING] Navigation: {time.monotonic() - nav_start:.2f}s", flush=True)

                print(f"Status: {response.status if response else 'None'}", flush=True)

                print("Current URL:", page.url, flush=True)

                print("Title:", await page.title(), flush=True)

                render_wait_start = time.monotonic()
                try:
                    await page.wait_for_selector(
                        '[data-testid="tweetPhoto"], video',
                        timeout=8000
                    )
                    await page.wait_for_timeout(750)
                except Exception:
                    pass  # text-only tweet, nothing to wait for
                print(f"[TIMING] Render wait: {time.monotonic() - render_wait_start:.2f}s", flush=True)

                status_match = re.search(r"/status/(\d+)", url)
                status_id = status_match.group(1) if status_match else None

                article = None
                if status_id:
                    try:
                        status_link = page.locator(f'a[href*="/status/{status_id}"]').first
                        await status_link.wait_for(state="attached", timeout=5000)
                        candidate = page.locator(
                            f'article[data-testid="tweet"]:has(a[href*="/status/{status_id}"])'
                        ).first
                        if await candidate.count() > 0:
                            article = candidate
                            print(f"Scoped to article matching status ID {status_id}", flush=True)
                    except Exception as e:
                        print(f"Status ID match wait failed: {e}", flush=True)

                if article is None:
                    print("Falling back to first article (couldn't match status ID in DOM)", flush=True)
                    article = page.locator('article[data-testid="tweet"]').first

                has_target_video = False
                try:
                    has_target_video = await article.locator("video").count() > 0
                except Exception:
                    pass

                captured_video_urls.clear()

                if has_target_video:
                    try:
                        await page.evaluate("""
                            () => {
                                document.querySelectorAll('video').forEach(v => {
                                    try { v.pause(); } catch (e) {}
                                });
                            }
                        """)
                    except Exception:
                        pass

                    try:
                        await article.locator("video").first.click(timeout=3000)
                        await page.wait_for_timeout(1500)
                    except Exception:
                        pass

                text = None
                method_used = None
                text_extract_start = time.monotonic()

                try:
                    tweet_text_el = article.locator('[data-testid="tweetText"]').first
                    if await tweet_text_el.count() > 0:
                        dom_text = await tweet_text_el.inner_text(timeout=3000)
                        if dom_text and dom_text.strip():
                            text = dom_text.strip()
                            method_used = "dom"
                except Exception as e:
                    print(f"DOM text extraction failed: {e}", flush=True)

                if text is None:
                    try:
                        scripts = await page.locator('script[type="application/ld+json"]').all_inner_texts()

                        for script in scripts:
                            obj = json.loads(script)

                            if obj.get("@type") == "SocialMediaPosting":
                                text = obj.get("articleBody")
                                method_used = "json-ld"
                                break
                    except Exception as e:
                        print(f"JSON-LD text extraction failed: {e}", flush=True)

                if text is None:
                    title = await page.title()
                    title_match = re.search(r'on X: "(.+)" / X$', title)
                    if title_match:
                        text = title_match.group(1)
                        method_used = "title-tag"

                if text is None:
                    raise RuntimeError("Could not extract tweet text via any method")

                print(f"Text extraction method: {method_used} ({time.monotonic() - text_extract_start:.2f}s)", flush=True)

                try:
                    scoped_html = await article.inner_html(timeout=3000)
                except Exception:
                    scoped_html = await page.content()

                video_urls = set(re.findall(
                    r'https://video\.twimg\.com[^"\']+',
                    scoped_html
                ))
                video_urls |= captured_video_urls if has_target_video else set()

                print("Video playlists:", video_urls, flush=True)

                seen = set()
                media = []

                image_matches = re.findall(r'https://pbs\.twimg\.com/media/[^"\']+', scoped_html)
                print(f"Found {len(image_matches)} raw image URL matches in scoped article", flush=True)
                print("Image matches:", image_matches, flush=True)

                for media_url in image_matches:
                    media_url = media_url.replace("&amp;", "&")

                    if "?format=webp" in media_url:
                        continue

                    media_id = media_url.split("?")[0].rsplit("/", 1)[-1]
                    media_id = re.sub(r"\.(jpg|jpeg|png|webp|gif)(:[a-zA-Z]+)?$", "", media_id, flags=re.IGNORECASE)

                    if media_id in seen:
                        continue

                    seen.add(media_id)

                    media.append(Media(url=_upgrade_photo_quality(media_url), type="image"))

                for video_url in video_urls:
                    video_url = video_url.replace("&amp;", "&")

                    video_id = video_url.split("?")[0].rsplit("/", 1)[-1]

                    if video_id in seen:
                        continue

                    seen.add(video_id)

                    media.append(Media(url=video_url, type="video"))

                elapsed = time.monotonic() - fetch_start
                print(f"[TIMING] XFetcher.fetch (browser) succeeded in {elapsed:.2f}s", flush=True)

                return Post(platform="x", text=text, media=media)

            finally:
                elapsed = time.monotonic() - fetch_start
                print(f"[TIMING] XFetcher.fetch (browser) total (incl. cleanup): {elapsed:.2f}s", flush=True)
                page.remove_listener("response", _capture_video)
                await page.close()
