from models.post import Post, Media
from services.browser import new_page, page_semaphore
from services.fetchers.base import Fetcher
import json
import re
import time


class XFetcher(Fetcher):
    async def fetch(self, url: str) -> Post:
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
                    pass
                print(f"[TIMING] Render wait: {time.monotonic() - render_wait_start:.2f}s", flush=True)

                status_match = re.search(r"/status/(\d+)", url)
                status_id = status_match.group(1) if status_match else None

                article = None
                if status_id:
                    candidate = page.locator(
                        f'article[data-testid="tweet"]:has(a[href*="/status/{status_id}"])'
                    ).first
                    if await candidate.count() > 0:
                        article = candidate
                        print(f"Scoped to article matching status ID {status_id}", flush=True)

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

                try:
                    tweet_text_el = article.locator('[data-testid="tweetText"]').first
                    if await tweet_text_el.count() > 0:
                        dom_text = await tweet_text_el.inner_text()
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

                print(f"Text extraction method: {method_used}", flush=True)

                try:
                    scoped_html = await article.inner_html()
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

                    media.append(
                        Media(
                            url=media_url,
                            type="image"
                        )
                    )

                for video_url in video_urls:
                    video_url = video_url.replace("&amp;", "&")

                    video_id = video_url.split("?")[0].rsplit("/", 1)[-1]

                    if video_id in seen:
                        continue

                    seen.add(video_id)

                    media.append(
                        Media(
                            url=video_url,
                            type="video"
                        )
                    )

                elapsed = time.monotonic() - fetch_start
                print(f"[TIMING] XFetcher.fetch succeeded in {elapsed:.2f}s", flush=True)

                return Post(
                    platform="x",
                    text=text,
                    media=media
                )

            finally:
                elapsed = time.monotonic() - fetch_start
                print(f"[TIMING] XFetcher.fetch total (incl. cleanup): {elapsed:.2f}s", flush=True)
                page.remove_listener("response", _capture_video)
                await page.close()
