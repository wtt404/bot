import aiohttp
import discord
import os
import tempfile
from .limits import MAX_UPLOAD_SIZE
from .video import get_best_mp4


async def download(media_urls):
    files = []
    video_sent = False
    media_failed_size = False

    async with aiohttp.ClientSession() as session:
        for item in media_urls:
            url = item.url

            if item.type == "video" and video_sent:
                continue  # one real video per post is enough; skip duplicate renditions

            if item.type == "video" and ".m3u8" in url:
                video_path = await get_best_mp4(url)

                if video_path is None:
                    continue

                if os.path.getsize(video_path) > MAX_UPLOAD_SIZE:
                    print("Video exceeds upload limit", flush=True)
                    os.remove(video_path)
                    media_failed_size = True
                    continue

                files.append(
                    discord.File(
                        video_path,
                        filename=os.path.basename(video_path)
                    )
                )
                video_sent = True

                continue

            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        continue

                    content_type = resp.headers.get("Content-Type", "")
                    data = await resp.read()

                    if len(data) > MAX_UPLOAD_SIZE:
                        print(f"Skipping {url}: exceeds upload limit", flush=True)
                        media_failed_size = True
                        continue

                    # Some captured "video" URLs turn out to be tiny
                    # tracking/license-check responses, not real video
                    # content. Reject anything that isn't plausibly a video.
                    if item.type == "video":
                        MIN_VIDEO_BYTES = 20 * 1024

                        if len(data) < MIN_VIDEO_BYTES or not content_type.startswith("video/"):
                            print(
                                f"Skipping {url}: not real video content "
                                f"(size={len(data)}, content-type={content_type})",
                                flush=True
                            )
                            continue

                clean_url = url.split("?")[0]
              
                if clean_url.endswith(":large"):
                    clean_url = clean_url[:-6]

                suffix = os.path.splitext(clean_url)[1] or ".jpg"

                tmp = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=suffix
                )

                tmp.write(data)
                tmp.close()

                print(clean_url)
                print(suffix)
                print(os.path.basename(clean_url))

                files.append(
                    discord.File(
                        tmp.name,
                        filename=os.path.basename(clean_url)
                    )
                )

                if item.type == "video":
                    video_sent = True

            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"Failed to download {url}: {e}", flush=True) 


    return files, media_failed_size