# HEIC2JPG

**English** | [简体中文](README.zh-CN.md)

A simple Windows tool to batch convert **HEIC / HEIF** photos (e.g. from iPhone) to **JPG**.

- Single-file exe – just download and run. No Python and no Microsoft HEVC extension needed
- Drag & drop files or folders (subfolders included), multi-threaded batch conversion
- Adjustable JPG quality (50–100, default 92)
- Keeps EXIF metadata (date taken, camera model, GPS, …) and the color profile
- Auto-rotates photos according to their orientation
- Keeps the original file's modified time
- Name conflicts are resolved as `name (1).jpg`, or you can choose to overwrite
- Optional: delete the original HEIC files after converting
- Sharp on high-DPI displays (125% / 150% scaling)
- English and Chinese interface (follows the system language, switchable in the app)
- Supported formats: `.heic` `.heif` `.hif`

## Download

Get `HEIC2JPG.exe` from the [Releases](../../releases/latest) page and double-click to run.

> On first launch Windows SmartScreen may show "Windows protected your PC". Click **More info** → **Run anyway**.

## Usage

1. Double-click `HEIC2JPG.exe`
2. Drag HEIC files or folders into the list (or click **Add Files** / **Add Folder**)
3. Adjust the settings if needed and click **Convert**

You can also drop files directly onto the exe icon.

The interface language follows your Windows display language. Use the **Language** box in the top-right corner to switch between English and 中文; your choice is remembered.

### Command line

```bat
HEIC2JPG.exe --cli D:\Photos -o D:\Output -q 90
```

| Option | Description |
| --- | --- |
| `-o, --out` | Output folder (default: same as source) |
| `-q, --quality` | JPG quality 1–100 (default: 92) |
| `--no-exif` | Do not keep EXIF metadata |
| `--overwrite` | Overwrite existing JPG files with the same name |
| `--delete` | Delete the original file after a successful conversion |
| `--lang en\|zh` | Message language (default: system language) |

## Run from source / build

Requires Python 3.10+:

```bat
pip install -r requirements.txt
python heic2jpg.py
```

To build the exe, run `build.bat`. The output is `dist\HEIC2JPG.exe`.

## Dependencies

- [Pillow](https://github.com/python-pillow/Pillow)
- [pi-heif](https://github.com/bigcat88/pillow_heif) (decode-only build, bundles libheif / libde265, LGPL)
- [tkinterdnd2](https://github.com/Eliav2/tkinterdnd2) (drag & drop)

## License

[MIT](LICENSE)
