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

        print("===== MASTER PLAYLIST =====", flush=True)
        print(text, flush=True)

        variants = []

        for match in re.finditer(
            r"#EXT-X-STREAM-INF:([^\n]*)\n([^\n]+\.m3u8)",
            text,
        ):
            attrs = match.group(1)
            playlist = match.group(2).strip()

            res_match = re.search(r"RESOLUTION=(\d+)x(\d+)", attrs)
            if not res_match:
                continue

            width, height = int(res_match.group(1)), int(res_match.group(2))

            audio_group_match = re.search(r'AUDIO="([^"]+)"', attrs)
            audio_group = audio_group_match.group(1) if audio_group_match else None

            variants.append(
                (
                    width * height,
                    urljoin(playlist_url, playlist),
                    audio_group,
                )
            )

        print("Variants:", variants, flush=True)

        if not variants:
            return None

        variants.sort(key=lambda v: v[0], reverse=True)

        best = variants[0][1]
        best_audio_group = variants[0][2]

        audio_url = None

        def _find_audio_uri(group_id):
            for line in text.splitlines():
                if (
                    line.startswith("#EXT-X-MEDIA:")
                    and "TYPE=AUDIO" in line
                    and (group_id is None or f'GROUP-ID="{group_id}"' in line)
                ):
                    uri_match = re.search(r'URI="([^"]+)"', line)
                    if uri_match:
                        return uri_match.group(1)
            return None

        audio_uri = _find_audio_uri(best_audio_group)

        if audio_uri is None and best_audio_group is not None:
            print(f"Couldn't find audio group '{best_audio_group}', falling back to any audio track", flush=True)
            audio_uri = _find_audio_uri(None)

        if audio_uri:
            audio_url = urljoin(playlist_url, audio_uri)
            print("Audio playlist:", audio_url, flush=True)
        else:
            print("No separate audio track found in master playlist", flush=True)

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

    if audio_url:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            best,
            "-i",
            audio_url,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c",
            "copy",
            output,
        ]
    else:
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

        if audio_url:
            print("Muxed ffmpeg attempt failed, retrying video-only", flush=True)

            if os.path.exists(output):
                os.remove(output)

            fallback_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                best,
                "-c",
                "copy",
                output,
            ]

            fallback_result = subprocess.run(
                fallback_cmd,
                capture_output=True,
                text=True
            )

            if fallback_result.returncode != 0:
                print(fallback_result.stderr, flush=True)

                if os.path.exists(output):
                    os.remove(output)

                return None
        else:
            if os.path.exists(output):
                os.remove(output)

            return None

    print("Video saved:", output, flush=True)

    return output