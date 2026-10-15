#!/usr/bin/env python3
"""Builds the web deck from the native Sampler folder.

    python3 tools/import.py [../sampler]

Reads <src>/clips/*.mp4 and <src>/images/*, and writes next to index.html:
  clips/<id>.mp4   re-encoded for the web (lighter, fast start)
  images/<id>.jpg  copied as is
  thumbs/<id>.jpg  key thumbnail (frame at 40 % of the clip, like the app)
  deck.js          the list read by the page (a script, so index.html also opens from disk)

<id> is the file name prefix ("c07b" for "c07b_ÇA_FARTE_?__Brice_de_Nice_·_….mp4"), so published
URLs stay plain ASCII. Titles follow the app's rules: "__" separates the short title from the full one,
"_" is a space. Files already converted are skipped; delete them to force a rebuild.
"""
import json
import shutil
import subprocess
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT.parent / "sampler").resolve()
VIDEO_EXT = {".mp4", ".mov", ".m4v"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
# Same order and letters as Item.Group in the app.
GROUPS = {"c": "cinema", "v": "tv", "p": "politics", "t": "trump", "d": "music", "m": "memes", "y": "myriam"}
ORDER = list(GROUPS.values()) + ["images", "other"]


def titles(stem):
    name = stem.split("_", 1)[1] if "_" in stem else stem
    parts = name.split("__")
    short = parts[0].replace("_", " ")
    label = (" ".join(parts[1:]) if len(parts) > 1 else parts[0]).replace("_", " ")
    return short, label


def group_of(item_id, kind):
    if kind == "image":
        return "images"
    if len(item_id) > 1 and item_id[1].isdigit():
        return GROUPS.get(item_id[0].lower(), "other")
    return "other"


def run(*args):
    subprocess.run(args, check=True, stdin=subprocess.DEVNULL)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         check=True, capture_output=True, text=True).stdout
    return float(out.strip())


def convert_video(src, item_id):
    clip, thumb = ROOT / "clips" / f"{item_id}.mp4", ROOT / "thumbs" / f"{item_id}.jpg"
    if not clip.exists():
        tmp = clip.with_suffix(".tmp.mp4")
        run("ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-y", "-i", str(src),
            "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(tmp))
        tmp.rename(clip)
    if not thumb.exists():
        run("ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-y", "-ss", f"{duration(src) * 0.4:.3f}",
            "-i", str(src), "-frames:v", "1", "-vf", "scale=480:270:flags=lanczos", "-q:v", "4", str(thumb))
    return item_id


def main():
    for d in ("clips", "images", "thumbs"):
        (ROOT / d).mkdir(exist_ok=True)

    items, jobs = [], []
    for kind, folder, exts in (("video", "clips", VIDEO_EXT), ("image", "images", IMAGE_EXT)):
        files = sorted((p for p in (SRC / folder).iterdir() if p.suffix.lower() in exts),
                       key=lambda p: unicodedata.normalize("NFC", p.name).lower())
        for path in files:
            stem = unicodedata.normalize("NFC", path.stem)
            item_id = stem.split("_", 1)[0]
            short, label = titles(stem)
            if kind == "video":
                src_url = f"clips/{item_id}.mp4"
                jobs.append((path, item_id))
            else:
                ext = path.suffix.lower()
                src_url = f"images/{item_id}{ext}"
                shutil.copyfile(path, ROOT / src_url)
            thumb = f"thumbs/{item_id}.jpg" if kind == "video" else src_url
            items.append({"id": item_id, "kind": kind, "group": group_of(item_id, kind),
                          "short": short, "label": label, "src": src_url, "thumb": thumb})

    ids = [i["id"] for i in items]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        sys.exit(f"Préfixes en double : {', '.join(sorted(dupes))}")

    with ThreadPoolExecutor(max_workers=4) as pool:
        for done in pool.map(lambda job: convert_video(*job), jobs):
            print("ok", done, flush=True)

    items.sort(key=lambda i: ORDER.index(i["group"]))  # stable: keeps name order inside a group
    (ROOT / "deck.js").write_text("window.DECK = " + json.dumps(items, ensure_ascii=False, indent=1) + ";\n",
                                  encoding="utf-8")
    print(f"{len(items)} éléments -> deck.js")


if __name__ == "__main__":
    main()
