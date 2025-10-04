# 📸 Rename by Timestamp

Скрипт на Python для **переименования фото и видео** в формат:

YYYY-MM-DD HH-MM-SS.ext

Дата берётся из:
- 📷 EXIF (через **ExifTool** или **Pillow**),
- 🎬 метаданных видео (через **ffprobe**),
- 🕒 времени изменения файла (fallback, если метаданных нет).

---

## 🚀 Быстрый старт

### 1. Клонировать репозиторий
```powershell
git clone https://github.com/<your-username>/rename-by-timestamp.git
cd rename-by-timestamp

2. Создать виртуальное окружение
python -m venv .venv
.\.venv\Scripts\Activate.ps1

3. Установить зависимости
pip install -r requirements.txt


(сейчас в requirements.txt только Pillow, но можно добавить другие зависимости позже)

⚙️ Использование
Просмотр (без изменений)
python rename_by_timestamp.py --folder "C:\path\to\media" --recursive --dry-run --progress

Реальное переименование
python rename_by_timestamp.py --folder "C:\path\to\media" --recursive --progress


--folder — папка с фото/видео

--recursive — захватывать подпапки

--dry-run — показать, что будет сделано, но не переименовывать

--progress — печатать результат по каждому файлу

🛠 Требования

Python 3.10+

ExifTool

FFmpeg
 (для ffprobe)

📚 Примеры вывода

Dry-run:

OK: DSC00001.JPG -> DRY-RUN -> 2006-07-01 12-34-56.JPG
OK: IMG_1234.MP4 -> DRY-RUN -> 2021-11-03 15-22-10.MP4


Реальное переименование:

OK: DSC00001.JPG -> renamed -> 2006-07-01 12-34-56.JPG
OK: IMG_1234.MP4 -> renamed -> 2021-11-03 15-22-10.MP4

🔄 Особенности

Если файлы уже имеют формат YYYY-MM-DD HH-MM-SS.ext → они пропускаются.

При совпадении имён автоматически добавляется суффикс _1, _2, …

Поддержка расширений:

фото: .jpg, .jpeg, .png, .tif, .tiff, .heic, .webp

видео: .mp4, .mov, .avi, .mkv, .wmv, .3gp, .mpeg, .mpg, .hevc, .webm