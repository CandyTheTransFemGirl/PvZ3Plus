#!/usr/bin/env python3
"""Audit and normalize PvZ3+ portraits. Install Pillow: python -m pip install Pillow."""
import argparse
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from PIL import Image, ImageFile, ImageOps

ImageFile.LOAD_TRUNCATED_IMAGES = False
ROOT = Path(__file__).resolve().parent
HTML = ROOT / "index.html"
ASSETS = ROOT / "assets"
EXTS = {".png", ".webp", ".jpg", ".jpeg"}

def decode(path):
    data = path.read_bytes()
    with Image.open(io.BytesIO(data)) as im:
        im.verify()
    with Image.open(io.BytesIO(data)) as im:
        im.load()
        return ImageOps.exif_transpose(im).convert("RGBA")

def restore_archive(html, archive):
    targets = {"doubleagentimp": "222-doubleagentimp", "snowmachineimp": "230-snowmachineimp"}
    def norm(name):
        return re.sub(r"[^a-z0-9]", "", re.sub(r"^\d+[-_]", "", Path(name).stem.lower()))
    with zipfile.ZipFile(archive) as z:
        for key, stem in targets.items():
            candidates = []
            for info in z.infolist():
                if info.is_dir() or Path(info.filename).suffix.lower() not in EXTS:
                    continue
                if norm(info.filename) not in {key, "portrait"+key, key+"portrait"}:
                    continue
                try:
                    data = z.read(info)
                    with Image.open(io.BytesIO(data)) as im:
                        im.verify()
                    with Image.open(io.BytesIO(data)) as im:
                        im.load()
                        img = im.convert("RGBA")
                    if min(img.size) >= 16:
                        candidates.append((info.filename, img))
                except Exception as exc:
                    print(f"INVALID ARCHIVE IMAGE {info.filename}: {exc}")
            if not candidates:
                raise RuntimeError(f"No usable archive portrait for {key}")
            name, img = candidates[0]
            if any(other.size != img.size or other.tobytes() != img.tobytes() for _, other in candidates[1:]):
                raise RuntimeError(f"Ambiguous archive portraits for {key}: {[n for n, _ in candidates]}")
            dest = ASSETS / (stem + ".png")
            temp = dest.with_suffix(".tmp")
            img.save(temp, "PNG")
            decode(temp)
            temp.replace(dest)
            html, count = re.subn(r'("' + key + r'"\s*:\s*)"\./assets/[^"]+"', lambda m: m.group(1) + json.dumps("./assets/" + dest.name), html)
            if not count:
                raise RuntimeError(f"Missing HTML mapping for {key}")
            print(f"RESTORED {key} from {name}")
    return html

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix", action="store_true", help="Normalize WebP/JPEG portraits to PNG and repair unambiguous missing mappings")
    parser.add_argument("--contact-sheet", type=Path, help="Write a visual review sheet of mapped portraits")
    parser.add_argument("--restore-archive", nargs="?", type=Path, const=ROOT / "PvZ3Plus_v50_assets.zip", help="Restore the two known visually corrupted portraits from the original ZIP")
    args = parser.parse_args()
    html = HTML.read_text(encoding="utf-8")
    if args.restore_archive:
        html = restore_archive(html, args.restore_archive)
        HTML.write_text(html, encoding="utf-8")
    pattern = r'"([a-zA-Z0-9_]+)"\s*:\s*"(\./assets/[^"]+)"'
    mappings = dict(re.findall(pattern, html))
    roster = set(re.findall(r'\["([^"]+)",\s*"[^"]+",\s*"zombies",\s*"[^"]+"\]', html))
    files = [p for p in ASSETS.rglob("*") if p.is_file() and p.suffix.lower() in EXTS]
    decoded = {}
    bad = set()
    for p in files:
        try:
            im = decode(p)
            if im.width < 16 or im.height < 16:
                raise ValueError("unexpectedly small image")
            decoded[p] = im
        except Exception as exc:
            bad.add(p)
            print(f"INVALID {p.relative_to(ROOT)}: {exc}")
    updates = {}
    unresolved = []
    for key in sorted(roster | set(mappings)):
        old = mappings.get(key)
        path = ROOT / old if old else None
        if path not in decoded:
            candidates = [p for p in decoded if re.sub(r"^\d+[-_]", "", p.stem).lower() == key.lower()]
            if len(candidates) != 1:
                unresolved.append(key)
                print(f"MISSING OR INVALID {key}: {old or 'no mapping'}")
                continue
            path = candidates[0]
        if args.fix:
            if path.suffix.lower() != ".png":
                dest = path.with_suffix(".png")
                if dest.exists() and dest not in decoded:
                    unresolved.append(key)
                    print(f"REFUSING TO OVERWRITE {dest}")
                    continue
                if not dest.exists():
                    decoded[path].save(dest, "PNG")
                    decode(dest)
                elif decode(dest).tobytes() != decoded[path].tobytes() or decode(dest).size != decoded[path].size:
                    unresolved.append(key)
                    print(f"PNG COLLISION {dest}")
                    continue
                path = dest
            new = "./" + path.relative_to(ROOT).as_posix()
            if new != old:
                updates[key] = new
    if args.fix and updates:
        for key, new in updates.items():
            if key in mappings:
                html = re.sub(r'("' + re.escape(key) + r'"\s*:\s*)"\./assets/[^"]+"', lambda m: m.group(1) + json.dumps(new), html)
            else:
                match = re.search(r'(?:const|let|var)\s+portraits\s*=\s*\{', html)
                if not match:
                    unresolved.append(key)
                    print(f"Cannot locate portraits object for {key}")
                    continue
                html = html[:match.end()] + json.dumps(key) + ":" + json.dumps(new) + "," + html[match.end():]
            print(f"FIXED {key}: {new}")
        HTML.write_text(html, encoding="utf-8")
    if args.contact_sheet:
        from PIL import ImageDraw
        entries = sorted(mappings.items())
        cols, w, h = 6, 180, 155
        sheet = Image.new("RGB", (cols*w, max(1, (len(entries)+cols-1)//cols)*h), "#eeeeee")
        draw = ImageDraw.Draw(sheet)
        for i, (key, url) in enumerate(entries):
            x, y = (i%cols)*w, (i//cols)*h
            im = decoded.get(ROOT / url)
            if im:
                thumb = ImageOps.contain(im, (w-12, h-28))
                sheet.paste(thumb, (x+(w-thumb.width)//2, y), thumb)
            else:
                draw.text((x+8,y+30), "INVALID / MISSING", fill="red")
            draw.text((x+5,y+h-22), key[:26], fill="black")
        sheet.save(args.contact_sheet)
    print(f"Scanned {len(files)} images; {len(bad)} invalid; {len(unresolved)} unresolved mappings.")
    print("Visual corruption can survive decoding: inspect the contact sheet and replace damaged source artwork.")
    return int(bool(bad or unresolved))

if __name__ == "__main__":
    sys.exit(main())
