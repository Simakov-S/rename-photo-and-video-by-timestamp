# Rename by Timestamp

Скрипт на Python для переименования фото и видео в формат:

YYYY-MM-DD HH-MM-SS.ext

Берёт дату из:
- EXIF (через ExifTool/Pillow)
- metadata видео (через ffprobe)
- или время изменения файла (если больше ничего нет).

## Быстрый старт

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install Pillow
python rename_by_timestamp.py --folder "C:\path\to\media" --recursive --dry-run