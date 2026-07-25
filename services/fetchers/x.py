from models.post import Post, Media
from services.browser import new_page
from services.fetchers.base import Fetcher
import json
import re


class XFetcher(Fetcher):
    async def fetch(self, url: str) -> Post:

        page = await new_page()
        captured_video_urls = set()

        def _capture_video(response):
            resp_url = response.url
            if "video.twimg.com" in resp_url and (".m3u8" in resp_url or ".mp4" in resp_url):
                captured_video_urls.add(resp_url)

        page.on("response", _capture_video)

        try:
            print("FETCH START", flush=True)

            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000
            )
            print("Navigation finished", flush=True)

            print(f"Status: {response.status if response else 'None'}", flush=True)

            print("Current URL:", page.url, flush=True)

            print("Title:", await page.title(), flush=True)

            try:
                await page.wait_for_selector(
                    '[data-testid="tweetPhoto"], video',
                    timeout=8000
                )
                await page.wait_for_timeout(750)
            except Exception:
                pass 
            article = page.locator('article[data-testid="tweet"]').first

            has_target_video = False
            try:
                has_target_video = await article.locator("video").count() > 0
            except Exception:
                pass

            if has_target_video:
                try:
                    await article.locator("video").first.click(timeout=3000)
                    await page.wait_for_timeout(1500)
                except Exception:
                    pass
            else:
                captured_video_urls.clear()

            scripts = await page.locator('script[type="application/ld+json"]').all_inner_texts()

            data = None

            for script in scripts:
                obj = json.loads(script)
          
                if obj.get("@type") == "SocialMediaPosting":
                    data = obj
                    break

            if data is None:
                raise RuntimeError("SocialMediaPosting not found")

            text = data["articleBody"]

            try:
                scoped_html = await article.inner_html()
            except Exception:
                scoped_html = await page.content()  # best-effort fallback

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

            return Post(
                platform="x",
                text=text,
                media=media
            )

        finally:
            page.remove_listener("response", _capture_video)
            await page.close()