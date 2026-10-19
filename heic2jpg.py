"""HEIC2JPG - batch convert HEIF/HEIC images to JPG on Windows.

Usage:
  GUI:  HEIC2JPG.exe                       (drag & drop files / folders)
  CLI:  HEIC2JPG.exe --cli <files or folders> ... [-o OUT_DIR] [-q QUALITY] [--lang en|zh]
"""
import argparse
import json
import locale
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps
from pi_heif import register_heif_opener

register_heif_opener()

APP_NAME = "HEIC2JPG"
VERSION = "1.1.0"
HEIF_EXTS = {".heic", ".heif", ".hif"}
LANGS = {"en": "English", "zh": "中文"}

# ---------------------------------------------------------------- i18n
STRINGS = {
    "en": {
        "title": "HEIC → JPG Converter",
        "add_files": "Add Files",
        "add_folder": "Add Folder",
        "remove": "Remove Selected",
        "clear": "Clear",
        "language": "Language:",
        "col_name": "File",
        "col_dir": "Folder",
        "col_state": "Status",
        "settings": "Settings",
        "out_dir": "Output folder:",
        "browse": "Browse…",
        "out_hint": "(empty = same as source)",
        "quality": "JPG quality:",
        "keep_exif": "Keep EXIF",
        "overwrite": "Overwrite existing",
        "delete_src": "Delete originals after converting",
        "open_after": "Open folder when done",
        "start": "Convert",
        "st_wait": "Waiting",
        "st_busy": "Converting…",
        "st_ok": "✔ Done",
        "st_fail": "✘ Failed",
        "hint": "Drag HEIC files or folders into the list, or click “Add Files”",
        "count": "{n} file(s) in list",
        "count_new": "{n} file(s) in list ({new} added)",
        "count_none": "{n} file(s) in list, no new HEIC files found",
        "cleared": "List cleared",
        "err": "{name}: {msg}",
        "done": "Finished: {ok} succeeded, {fail} failed",
        "pick_files": "Select HEIC/HEIF files",
        "heif_images": "HEIF images",
        "all_files": "All files",
        "pick_folder": "Select a folder (subfolders included)",
        "pick_out": "Select output folder",
        "info": "Info",
        "no_files": "Please add some HEIC files first.",
        "confirm": "Confirm",
        "confirm_delete": "The original HEIC files will be deleted after a successful conversion. Continue?",
        # CLI
        "cli_desc": "Batch convert HEIF/HEIC images to JPG",
        "cli_inputs": "HEIC files or folders",
        "cli_out": "output folder (default: same as source)",
        "cli_quality": "JPG quality 1-100 (default: 92)",
        "cli_no_exif": "do not keep EXIF metadata",
        "cli_overwrite": "overwrite existing JPG files with the same name",
        "cli_delete": "delete the original file after a successful conversion",
        "cli_lang": "interface language: en or zh (default: system language)",
        "cli_none": "No HEIC/HEIF files found",
    },
    "zh": {
        "title": "HEIC → JPG 转换器",
        "add_files": "添加文件",
        "add_folder": "添加文件夹",
        "remove": "移除选中",
        "clear": "清空",
        "language": "语言:",
        "col_name": "文件名",
        "col_dir": "所在目录",
        "col_state": "状态",
        "settings": "设置",
        "out_dir": "输出目录:",
        "browse": "浏览…",
        "out_hint": "(留空 = 与原文件相同)",
        "quality": "JPG 质量:",
        "keep_exif": "保留 EXIF",
        "overwrite": "覆盖同名文件",
        "delete_src": "转换后删除原文件",
        "open_after": "完成后打开文件夹",
        "start": "开始转换",
        "st_wait": "等待",
        "st_busy": "转换中…",
        "st_ok": "✔ 完成",
        "st_fail": "✘ 失败",
        "hint": "拖放 HEIC 文件或文件夹到下方列表,或点击「添加文件」",
        "count": "共 {n} 个文件",
        "count_new": "共 {n} 个文件(新增 {new})",
        "count_none": "共 {n} 个文件,没有新的 HEIC 文件",
        "cleared": "列表已清空",
        "err": "{name}: {msg}",
        "done": "完成:成功 {ok},失败 {fail}",
        "pick_files": "选择 HEIC/HEIF 文件",
        "heif_images": "HEIF 图片",
        "all_files": "所有文件",
        "pick_folder": "选择文件夹(包含子文件夹)",
        "pick_out": "选择输出目录",
        "info": "提示",
        "no_files": "请先添加 HEIC 文件",
        "confirm": "确认",
        "confirm_delete": "转换成功后将删除原 HEIC 文件,确定继续?",
        # CLI
        "cli_desc": "HEIF/HEIC → JPG 批量转换",
        "cli_inputs": "HEIC 文件或文件夹",
        "cli_out": "输出目录 (默认与原文件相同)",
        "cli_quality": "JPG 质量 1-100 (默认 92)",
        "cli_no_exif": "不保留 EXIF 信息",
        "cli_overwrite": "覆盖已存在的同名 JPG",
        "cli_delete": "转换成功后删除原文件",
        "cli_lang": "界面语言: en 或 zh (默认跟随系统)",
        "cli_none": "未找到 HEIC/HEIF 文件",
    },
}


def settings_path() -> Path:
    return Path(os.environ.get("APPDATA") or Path.home()) / APP_NAME / "settings.json"


def load_settings() -> dict:
    try:
        return json.loads(settings_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_settings(data: dict):
    try:
        p = settings_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def system_lang() -> str:
    """Chinese if the Windows UI language is Chinese, otherwise English."""
    try:
        import ctypes
        if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x04:  # LANG_CHINESE
            return "zh"
        return "en"
    except Exception:
        pass
    name = (locale.getlocale()[0] or os.environ.get("LANG") or "").lower()
    return "zh" if name.startswith(("zh", "chinese")) else "en"


def resolve_lang(explicit=None) -> str:
    for cand in (explicit, os.environ.get("HEIC2JPG_LANG"), load_settings().get("lang")):
        if cand:
            cand = cand.lower()[:2]
            if cand in STRINGS:
                return cand
    return system_lang()


# ---------------------------------------------------------------- core
def collect_files(paths, recursive=True):
    files = []
    for p in map(Path, paths):
        if p.is_dir():
            it = p.rglob("*") if recursive else p.glob("*")
            files.extend(f for f in it if f.is_file() and f.suffix.lower() in HEIF_EXTS)
        elif p.is_file() and p.suffix.lower() in HEIF_EXTS:
            files.append(p)
    # de-duplicate, keep order
    return list(dict.fromkeys(f.resolve() for f in files))


def target_path(src: Path, out_dir, overwrite: bool) -> Path:
    folder = Path(out_dir) if out_dir else src.parent
    folder.mkdir(parents=True, exist_ok=True)
    dst = folder / (src.stem + ".jpg")
    if overwrite:
        return dst
    n = 1
    while dst.exists():
        dst = folder / f"{src.stem} ({n}).jpg"
        n += 1
    return dst


def convert_one(src: Path, out_dir=None, quality=92, keep_exif=True, overwrite=False) -> Path:
    with Image.open(src) as im:
        exif = im.getexif()
        icc = im.info.get("icc_profile")
        # rotate pixels according to EXIF orientation, then reset the tag
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        kwargs = {"quality": quality, "optimize": True, "subsampling": 0 if quality >= 90 else 2}
        if keep_exif and exif:
            exif[0x0112] = 1
            kwargs["exif"] = exif.tobytes()
        if icc:
            kwargs["icc_profile"] = icc
        dst = target_path(src, out_dir, overwrite)
        im.save(dst, "JPEG", **kwargs)
    st = src.stat()
    os.utime(dst, (st.st_atime, st.st_mtime))  # keep original modified time
    return dst


# ---------------------------------------------------------------- CLI
def run_cli(argv):
    for s in (sys.stdout, sys.stderr):
        if s and hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    # pick the language before building --help text
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--lang")
    known, _ = pre.parse_known_args(argv)
    t = STRINGS[resolve_lang(known.lang)]

    ap = argparse.ArgumentParser(prog=APP_NAME, description=t["cli_desc"])
    ap.add_argument("inputs", nargs="+", help=t["cli_inputs"])
    ap.add_argument("-o", "--out", help=t["cli_out"])
    ap.add_argument("-q", "--quality", type=int, default=92, help=t["cli_quality"])
    ap.add_argument("--no-exif", action="store_true", help=t["cli_no_exif"])
    ap.add_argument("--overwrite", action="store_true", help=t["cli_overwrite"])
    ap.add_argument("--delete", action="store_true", help=t["cli_delete"])
    ap.add_argument("--lang", choices=list(STRINGS), help=t["cli_lang"])
    ap.add_argument("--version", action="version", version=f"{APP_NAME} {VERSION}")
    a = ap.parse_args(argv)

    files = collect_files(a.inputs)
    if not files:
        print(t["cli_none"])
        return 1
    ok = fail = 0
    for i, f in enumerate(files, 1):
        try:
            dst = convert_one(f, a.out, a.quality, not a.no_exif, a.overwrite)
            if a.delete:
                f.unlink()
            ok += 1
            print(f"[{i}/{len(files)}] OK  {f.name} -> {dst}")
        except Exception as e:
            fail += 1
            print(f"[{i}/{len(files)}] ERR {f.name}: {e}")
    print(t["done"].format(ok=ok, fail=fail))
    return 0 if fail == 0 else 2


# ---------------------------------------------------------------- GUI
def run_gui(initial_paths=()):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    # must be declared before the window exists, otherwise Windows bitmap-stretches it on HiDPI
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD
        root = TkinterDnD.Tk()
        dnd = True
    except Exception:
        root = tk.Tk()
        dnd = False

    import tkinter.font as tkfont

    # scale the UI with the system DPI (100% = 96 DPI)
    dpi = root.winfo_fpixels("1i")
    scale = max(1.0, dpi / 96)
    root.tk.call("tk", "scaling", dpi / 72)

    def px(n):
        return int(n * scale)

    family = "Microsoft YaHei UI" if "Microsoft YaHei UI" in tkfont.families() else "Segoe UI"
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont"):
        tkfont.nametofont(name).configure(family=family, size=11)
    style = ttk.Style(root)
    row_h = tkfont.nametofont("TkDefaultFont").metrics("linespace") + px(8)
    style.configure("Treeview", rowheight=row_h)
    style.configure("Treeview.Heading", font=(family, 11, "bold"))
    style.configure("TButton", padding=(px(10), px(4)))
    style.configure("Accent.TButton", font=(family, 12, "bold"), padding=(px(18), px(6)))

    root.geometry(f"{px(920)}x{px(640)}")
    root.minsize(px(780), px(520))

    settings = load_settings()
    lang = [resolve_lang()]

    def tr(key, **kw):
        s = STRINGS[lang[0]].get(key) or STRINGS["en"][key]
        return s.format(**kw) if kw else s

    # widgets whose text follows the current language: (widget, key)
    i18n_widgets = []

    def L(widget, key):
        i18n_widgets.append((widget, key))
        widget.config(text=tr(key))
        return widget

    files: list[Path] = []
    item_state: dict[str, str] = {}
    out_dir = tk.StringVar(value="")
    quality = tk.IntVar(value=92)
    keep_exif = tk.BooleanVar(value=True)
    overwrite = tk.BooleanVar(value=False)
    delete_src = tk.BooleanVar(value=False)
    open_after = tk.BooleanVar(value=True)
    status = tk.StringVar()
    status_src = [("hint", {})]  # (key, kwargs) so the status line can be re-translated

    def set_status(key, **kw):
        status_src[0] = (key, kw)
        status.set(tr(key, **kw))

    pad = {"padx": px(12), "pady": px(6)}

    # top bar
    top = ttk.Frame(root)
    top.pack(fill="x", **pad)

    def add_paths(paths):
        new = [f for f in collect_files(paths) if f not in files]
        for f in new:
            files.append(f)
            item_state[str(f)] = "st_wait"
            tree.insert("", "end", iid=str(f), values=(f.name, str(f.parent), tr("st_wait")))
        if new:
            set_status("count_new", n=len(files), new=len(new))
        else:
            set_status("count_none", n=len(files))

    def add_files():
        sel = filedialog.askopenfilenames(
            title=tr("pick_files"),
            filetypes=[(tr("heif_images"), "*.heic *.heif *.hif"), (tr("all_files"), "*.*")])
        if sel:
            add_paths(sel)

    def add_folder():
        d = filedialog.askdirectory(title=tr("pick_folder"))
        if d:
            add_paths([d])

    def clear():
        files.clear()
        item_state.clear()
        tree.delete(*tree.get_children())
        set_status("cleared")

    def remove_selected():
        for iid in tree.selection():
            files.remove(Path(iid))
            item_state.pop(iid, None)
            tree.delete(iid)
        set_status("count", n=len(files))

    L(ttk.Button(top, command=add_files), "add_files").pack(side="left")
    L(ttk.Button(top, command=add_folder), "add_folder").pack(side="left", padx=px(8))
    L(ttk.Button(top, command=remove_selected), "remove").pack(side="left")
    L(ttk.Button(top, command=clear), "clear").pack(side="left", padx=px(8))

    lang_box = ttk.Combobox(top, values=list(LANGS.values()), state="readonly", width=8)
    lang_box.set(LANGS[lang[0]])
    lang_box.pack(side="right")
    L(ttk.Label(top), "language").pack(side="right", padx=(0, px(6)))

    # file list
    mid = ttk.Frame(root)
    mid.pack(fill="both", expand=True, **pad)
    tree = ttk.Treeview(mid, columns=("name", "dir", "state"), show="headings", selectmode="extended")
    tree.column("name", width=px(220))
    tree.column("dir", width=px(460))
    tree.column("state", width=px(110), anchor="center")
    sb = ttk.Scrollbar(mid, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    tree.bind("<Delete>", lambda e: remove_selected())

    if dnd:
        def on_drop(event):
            add_paths(root.tk.splitlist(event.data))
        tree.drop_target_register(DND_FILES)
        tree.dnd_bind("<<Drop>>", on_drop)

    # settings
    opts = L(ttk.LabelFrame(root), "settings")
    opts.pack(fill="x", **pad)

    r1 = ttk.Frame(opts)
    r1.pack(fill="x", padx=px(10), pady=px(6))
    L(ttk.Label(r1), "out_dir").pack(side="left")
    ttk.Entry(r1, textvariable=out_dir).pack(side="left", fill="x", expand=True, padx=px(6), ipady=px(3))

    def pick_out():
        d = filedialog.askdirectory(title=tr("pick_out"))
        if d:
            out_dir.set(d)
    L(ttk.Button(r1, command=pick_out), "browse").pack(side="left")
    L(ttk.Label(r1, foreground="gray"), "out_hint").pack(side="left", padx=px(6))

    r2 = ttk.Frame(opts)
    r2.pack(fill="x", padx=px(10), pady=px(6))
    L(ttk.Label(r2), "quality").pack(side="left")
    qlabel = ttk.Label(r2, width=4, font=(family, 11, "bold"))
    q_scale = ttk.Scale(r2, from_=50, to=100, orient="horizontal", length=px(260),
                        command=lambda v: (quality.set(int(float(v))), qlabel.config(text=str(quality.get()))))
    q_scale.set(quality.get())
    q_scale.pack(side="left", padx=px(6))
    qlabel.config(text=str(quality.get()))
    qlabel.pack(side="left")

    r3 = ttk.Frame(opts)
    r3.pack(fill="x", padx=px(10), pady=(0, px(8)))
    L(ttk.Checkbutton(r3, variable=keep_exif), "keep_exif").pack(side="left")
    L(ttk.Checkbutton(r3, variable=overwrite), "overwrite").pack(side="left", padx=px(20))
    L(ttk.Checkbutton(r3, variable=delete_src), "delete_src").pack(side="left")

    # bottom bar
    bottom = ttk.Frame(root)
    bottom.pack(fill="x", **pad)
    progress = ttk.Progressbar(bottom, mode="determinate")
    progress.pack(fill="x", pady=(0, px(8)), ipady=px(2))
    ttk.Label(bottom, textvariable=status).pack(side="left")
    start_btn = L(ttk.Button(bottom, style="Accent.TButton"), "start")
    start_btn.pack(side="right")
    L(ttk.Checkbutton(bottom, variable=open_after), "open_after").pack(side="right", padx=px(12))

    def apply_lang():
        root.title(f"{tr('title')}  v{VERSION}")
        for w, key in i18n_widgets:
            w.config(text=tr(key))
        tree.heading("name", text=tr("col_name"))
        tree.heading("dir", text=tr("col_dir"))
        tree.heading("state", text=tr("col_state"))
        for iid, key in item_state.items():
            if tree.exists(iid):
                tree.set(iid, "state", tr(key))
        key, kw = status_src[0]
        status.set(tr(key, **kw))

    def on_lang(_event=None):
        code = next(c for c, name in LANGS.items() if name == lang_box.get())
        if code != lang[0]:
            lang[0] = code
            settings["lang"] = code
            save_settings(settings)
            apply_lang()
    lang_box.bind("<<ComboboxSelected>>", on_lang)

    def set_state(iid, key):
        item_state[iid] = key
        if tree.exists(iid):
            tree.set(iid, "state", tr(key))
            tree.see(iid)

    def start():
        if not files:
            messagebox.showinfo(tr("info"), tr("no_files"))
            return
        if delete_src.get() and not messagebox.askyesno(tr("confirm"), tr("confirm_delete")):
            return
        todo = list(files)
        opts_ = (out_dir.get().strip() or None, quality.get(), keep_exif.get(), overwrite.get(), delete_src.get())
        start_btn.config(state="disabled")
        progress.config(maximum=len(todo), value=0)
        threading.Thread(target=worker, args=(todo, opts_), daemon=True).start()

    def worker(todo, opts_):
        od, q, ex, ow, dl = opts_
        counts = {"ok": 0, "fail": 0}
        last_dst = [None]
        lock = threading.Lock()

        def job(f):
            iid = str(f)
            root.after(0, set_state, iid, "st_busy")
            try:
                dst = convert_one(f, od, q, ex, ow)
                if dl:
                    f.unlink()
                with lock:
                    counts["ok"] += 1
                    last_dst[0] = dst
                root.after(0, set_state, iid, "st_ok")
            except Exception as e:
                with lock:
                    counts["fail"] += 1
                root.after(0, set_state, iid, "st_fail")
                root.after(0, lambda n=f.name, m=str(e): set_status("err", name=n, msg=m))
            root.after(0, progress.step, 1)

        with ThreadPoolExecutor(max_workers=max(1, min(8, (os.cpu_count() or 2)))) as ex_:
            list(ex_.map(job, todo))

        def done():
            start_btn.config(state="normal")
            set_status("done", ok=counts["ok"], fail=counts["fail"])
            if open_after.get() and last_dst[0]:
                os.startfile(last_dst[0].parent)
        root.after(0, done)

    start_btn.config(command=start)
    apply_lang()

    # files passed on the command line (e.g. dropped onto the exe icon)
    if initial_paths:
        add_paths(initial_paths)

    root.mainloop()


if __name__ == "__main__":
    args = sys.argv[1:]
    # CLI mode when --cli or any option is given, otherwise open the GUI
    if args and (args[0] == "--cli" or any(a.startswith("-") for a in args)):
        sys.exit(run_cli([a for a in args if a != "--cli"]))
    run_gui(args)
