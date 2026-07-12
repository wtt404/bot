import aiohttp
import re
from urllib.parse import urljoin
import traceback
import os
import subprocess
import tempfile


async def get_best_mp4(playlist_url: str):
    async with aiohttp.ClientSession() as session:

        async with session.get(playlist_url) as resp:
            if resp.status != 200:
                print("Failed to fetch playlist", flush=True)
                return None

            text = await resp.text()

        print("===== PLAYLIST =====", flush=True)

        variants = []

        for match in re.finditer(
            r"RESOLUTION=(\d+)x(\d+).*?\n([^\n]+\.m3u8)",
            text,
            re.DOTALL,
        ):
            width = int(match.group(1))
            height = int(match.group(2))
            playlist = match.group(3).strip()

            variants.append(
                (
                    width * height,
                    urljoin(playlist_url, playlist),
                )
            )

        print("Variants:", variants, flush=True)

        if not variants:
            return None

        variants.sort(reverse=True)

        best = variants[0][1]

        print("Best playlist:", best, flush=True)
        print("Fetching best playlist...", flush=True)

        try:
            async with session.get(best, timeout=30) as resp:
                print("Best playlist status:", resp.status, flush=True)

                if resp.status != 200:
                    return None

                best_text = await resp.text()

                print("Downloaded best playlist", flush=True)
                print("Length:", len(best_text), flush=True)

        except Exception:
            traceback.print_exc()
            return None

    print("===== BEST PLAYLIST =====", flush=True)
    print(best_text, flush=True)

    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp4"
    )
    tmp.close()

    output = tmp.name

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        best,
        "-c",
        "copy",
        output,
    ]

    print("Running FFmpeg...", flush=True)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(result.stderr, flush=True)

        if os.path.exists(output):
            os.remove(output)

        return None

    print("Video saved:", output, flush=True)

    return output