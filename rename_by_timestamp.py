#!/usr/bin/env python3
"""
Переименовывает фото/видео в формат "YYYY-MM-DD HH-MM-SS.ext".
Источники даты: exiftool -> Pillow(EXIF) -> ffprobe -> mtime (fallback).

Запуск:
python rename_by_timestamp.py --folder "D:\Media\DCIM" --recursive --dry-run
python rename_by_timestamp.py --folder "D:\Media\DCIM" --recursive
"""

import os
import argparse
import subprocess
import json
from datetime import datetime
import re
from pathlib import Path
from shutil import which

# --- конфиг расширений ---
IMAGE_EXTS = {'.jpg', '.jpeg', '.jpe', '.png', '.tif', '.tiff', '.heic', '.webp'}
VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.3gp', '.mpeg', '.mpg', '.hevc', '.webm'}

# --- опционально Pillow для фото ---
try:
    from PIL import Image
    from PIL.ExifTags import TAGS
except Exception:
    Image = None
    TAGS = {}

# --- поиск локальных бинарников в ./bin ---
BIN_DIR = Path(__file__).parent / "bin"

def which_local(name: str) -> str | None:
    candidates = [name]
    if os.name == "nt" and not name.lower().endswith(".exe"):
        candidates.insert(0, f"{name}.exe")
    for cand in candidates:
        local = BIN_DIR / cand
        if local.exists():
            return str(local)
    return which(name)

def run_cmd(cmd: list[str]):
    exe = which_local(cmd[0])
    if exe is None:
        return None, f"cmd not found: {cmd[0]}", 127
    try:
        res = subprocess.run(
            [exe] + cmd[1:],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        return res.stdout.strip(), res.stderr.strip(), res.returncode
    except KeyboardInterrupt:
        # немедленно пробрасываем вверх, чтобы main() красиво завершил
        raise
    except FileNotFoundError:
        return None, f"cmd not found: {cmd[0]}", 127


def has_exiftool():
    out, err, code = run_cmd(['exiftool', '-ver'])
    return code == 0

def has_ffprobe():
    out, err, code = run_cmd(['ffprobe', '-version'])
    return code == 0

def parse_exif_datetime(s):
    if not s:
        return None
    s = s.strip()
    m = re.match(r'^(\d{4}):(\d{2}):(\d{2})[ T](\d{2}):(\d{2}):(\d{2})', s)
    if m:
        y, mo, d, hh, mm, ss = m.groups()
        try:
            return datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss))
        except Exception:
            return None
    s2 = s.replace('T', ' ').rstrip('Z')
    s2 = re.sub(r'([+-]\d{2}):?(\d{2})$', '', s2)  # убираем смещение
    s2 = re.sub(r'\.\d+', '', s2)                  # дробные секунды
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s2, fmt)
        except Exception:
            pass
    return None

def get_datetime_with_exiftool(path: Path):
    out, err, code = run_cmd(['exiftool', '-j', str(path)])
    if code != 0 or not out:
        return None
    try:
        arr = json.loads(out)
        if not arr:
            return None
        d = arr[0]
        for key in ('DateTimeOriginal', 'CreateDate', 'MediaCreateDate', 'TrackCreateDate',
                    'ModifyDate', 'FileModifyDate', 'CreationDate', 'Create Date'):
            if key in d and d[key]:
                dt = parse_exif_datetime(d[key])
                if dt:
                    return dt
        for val in d.values():
            if isinstance(val, str):
                dt = parse_exif_datetime(val)
                if dt:
                    return dt
    except Exception:
        return None
    return None

def get_datetime_with_pillow(path: Path):
    if Image is None or path.suffix.lower() not in IMAGE_EXTS:
        return None
    try:
        img = Image.open(path)
        exif = img._getexif()
        if not exif:
            return None
        tag_map = {TAGS.get(k, k): v for k, v in exif.items()}
        for name in ('DateTimeOriginal', 'DateTime'):
            if name in tag_map:
                dt = parse_exif_datetime(tag_map[name])
                if dt:
                    return dt
    except Exception:
        return None
    return None

def get_datetime_with_ffprobe(path: Path):
    if path.suffix.lower() not in VIDEO_EXTS:
        return None
    out, err, code = run_cmd([
        'ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_entries', 'format_tags=creation_time', str(path)
    ])
    if code != 0 or not out:
        return None
    try:
        j = json.loads(out)
        tags = j.get('format', {}).get('tags', {})
        for key in ('creation_time', 'Creation_time', 'com.apple.quicktime.creationdate', 'DATE'):
            if key in tags:
                dt = parse_exif_datetime(tags[key])
                if dt:
                    return dt
    except Exception:
        return None
    return None

def format_for_filename(dt: datetime):
    return dt.strftime("%Y-%m-%d %H-%M-%S")

def safe_rename(path: Path, new_stem: str):
    parent = path.parent
    ext = path.suffix
    candidate = parent / (new_stem + ext)
    i = 1
    while candidate.exists():
        candidate = parent / f"{new_stem}_{i}{ext}"
        i += 1
    path.rename(candidate)
    return candidate

def get_file_mtime_dt(path: Path):
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts)

def process_file(path: Path, fallback_mtime=True, dry_run=False):
    # если имя уже вида YYYY-MM-DD HH-MM-SS.ext — пропускаем
    if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2}\.[^.]+$', path.name):
        return True, "skip (already named)"
    dt = None
    if has_exiftool():
        dt = get_datetime_with_exiftool(path)
    if dt is None:
        dt = get_datetime_with_pillow(path)
    if dt is None and has_ffprobe():
        dt = get_datetime_with_ffprobe(path)
    if dt is None and fallback_mtime:
        dt = get_file_mtime_dt(path)
    if dt is None:
        return False, "no-datetime"
    new_stem = format_for_filename(dt)
    new_path = path.parent / (new_stem + path.suffix)
    if dry_run:
        return True, f"DRY-RUN -> {new_path.name}"
    try:
        result = safe_rename(path, new_stem)
        return True, f"renamed -> {result.name}"
    except Exception as e:
        return False, str(e)

def walk_and_process(folder: Path, recursive=False, progress=False, **kwargs):
    processed = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in IMAGE_EXTS.union(VIDEO_EXTS):
                ok, msg = process_file(p, **kwargs)
                processed.append((p, ok, msg))
                if progress:
                    status = "OK" if ok else "ERR"
                    print(f"{status}: {p} -> {msg}")
        if not recursive:
            break
    return processed

def main():
    parser = argparse.ArgumentParser(description="Rename photos/videos to 'YYYY-MM-DD HH-MM-SS.ext' using metadata")
    parser.add_argument('--folder', '-f', required=True, help='target folder')
    parser.add_argument('--recursive', '-r', action='store_true', help='process subfolders')
    parser.add_argument('--dry-run', action='store_true', help='only print what would be done')
    parser.add_argument('--no-fallback-mtime', action='store_true', help="don't use file mtime as fallback")
    parser.add_argument('--progress', action='store_true', help='print result per file immediately')

    args = parser.parse_args()

    folder = Path(args.folder)

    fallback_mtime = not args.no_fallback_mtime

    print("Settings:")
    print(" folder:", folder)
    print(" recursive:", args.recursive)
    print(" dry-run:", args.dry_run)
    print(" exiftool available:", has_exiftool())
    print(" ffprobe available:", has_ffprobe())
    print(" fallback to mtime:", fallback_mtime)
    print()

    results = walk_and_process(
    folder,
    recursive=args.recursive,
    progress=args.progress,
    fallback_mtime=fallback_mtime,
    dry_run=args.dry_run
)

    ok_count = sum(1 for _p, ok, _m in results if ok)
    err_count = len(results) - ok_count

    for p, ok, msg in results:
        status = "OK" if ok else "ERR"
        print(f"{status}: {p.name} -> {msg}")

    print()
    print(f"Processed {len(results)} files: {ok_count} OK, {err_count} errors/warnings.")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Остановлено пользователем (Ctrl+C). Часть файлов уже могла быть обработана.")

