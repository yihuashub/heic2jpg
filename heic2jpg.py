"""HEIF/HEIC → JPG 转换工具 (Windows)

用法:
  GUI:  heic2jpg.exe                      (支持拖放文件/文件夹)
  CLI:  heic2jpg.exe 文件或文件夹 ... [-o 输出目录] [-q 质量]
"""
import argparse
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps
from pi_heif import register_heif_opener

register_heif_opener()

HEIF_EXTS = {".heic", ".heif", ".hif"}


def collect_files(paths, recursive=True):
    files = []
    for p in map(Path, paths):
        if p.is_dir():
            it = p.rglob("*") if recursive else p.glob("*")
            files.extend(f for f in it if f.is_file() and f.suffix.lower() in HEIF_EXTS)
        elif p.is_file() and p.suffix.lower() in HEIF_EXTS:
            files.append(p)
    # 去重并保持顺序
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
        # 按 EXIF 方向旋正像素, 并重置方向标记
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
    os.utime(dst, (st.st_atime, st.st_mtime))  # 保留原文件修改时间
    return dst


# ---------------------------------------------------------------- CLI
def run_cli(argv):
    for s in (sys.stdout, sys.stderr):
        if s and hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="HEIF/HEIC → JPG 批量转换")
    ap.add_argument("inputs", nargs="+", help="HEIC 文件或文件夹")
    ap.add_argument("-o", "--out", help="输出目录 (默认与原文件相同)")
    ap.add_argument("-q", "--quality", type=int, default=92, help="JPG 质量 1-100 (默认 92)")
    ap.add_argument("--no-exif", action="store_true", help="不保留 EXIF 信息")
    ap.add_argument("--overwrite", action="store_true", help="覆盖已存在的同名 JPG")
    ap.add_argument("--delete", action="store_true", help="转换成功后删除原 HEIC 文件")
    a = ap.parse_args(argv)

    files = collect_files(a.inputs)
    if not files:
        print("未找到 HEIC/HEIF 文件")
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
    print(f"完成: 成功 {ok}, 失败 {fail}")
    return 0 if fail == 0 else 2


# ---------------------------------------------------------------- GUI
def run_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    # 必须在创建窗口之前声明 DPI 感知, 否则高分屏下会被系统拉伸变糊
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor
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

    # 按系统缩放比例放大界面 (100% = 96 DPI)
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

    root.title("HEIC → JPG 转换器")
    root.geometry(f"{px(900)}x{px(640)}")
    root.minsize(px(760), px(520))

    files: list[Path] = []
    out_dir = tk.StringVar(value="")
    quality = tk.IntVar(value=92)
    keep_exif = tk.BooleanVar(value=True)
    overwrite = tk.BooleanVar(value=False)
    delete_src = tk.BooleanVar(value=False)
    open_after = tk.BooleanVar(value=True)
    status = tk.StringVar(value="拖放 HEIC 文件或文件夹到下方列表,或点击「添加文件」")

    pad = {"padx": px(12), "pady": px(6)}

    # 顶部按钮
    top = ttk.Frame(root)
    top.pack(fill="x", **pad)

    def add_paths(paths):
        new = [f for f in collect_files(paths) if f not in files]
        for f in new:
            files.append(f)
            tree.insert("", "end", iid=str(f), values=(f.name, str(f.parent), "等待"))
        status.set(f"共 {len(files)} 个文件" + (f"(新增 {len(new)})" if new else ",没有新的 HEIC 文件"))

    def add_files():
        sel = filedialog.askopenfilenames(
            title="选择 HEIC/HEIF 文件",
            filetypes=[("HEIF 图片", "*.heic *.heif *.hif"), ("所有文件", "*.*")])
        if sel:
            add_paths(sel)

    def add_folder():
        d = filedialog.askdirectory(title="选择文件夹(包含子文件夹)")
        if d:
            add_paths([d])

    def clear():
        files.clear()
        tree.delete(*tree.get_children())
        status.set("列表已清空")

    def remove_selected():
        for iid in tree.selection():
            files.remove(Path(iid))
            tree.delete(iid)
        status.set(f"共 {len(files)} 个文件")

    ttk.Button(top, text="添加文件", command=add_files).pack(side="left")
    ttk.Button(top, text="添加文件夹", command=add_folder).pack(side="left", padx=px(8))
    ttk.Button(top, text="移除选中", command=remove_selected).pack(side="left")
    ttk.Button(top, text="清空", command=clear).pack(side="left", padx=px(8))

    # 文件列表
    mid = ttk.Frame(root)
    mid.pack(fill="both", expand=True, **pad)
    tree = ttk.Treeview(mid, columns=("name", "dir", "state"), show="headings", selectmode="extended")
    tree.heading("name", text="文件名")
    tree.heading("dir", text="所在目录")
    tree.heading("state", text="状态")
    tree.column("name", width=px(220))
    tree.column("dir", width=px(460))
    tree.column("state", width=px(100), anchor="center")
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

    # 设置
    opts = ttk.LabelFrame(root, text="设置")
    opts.pack(fill="x", **pad)

    r1 = ttk.Frame(opts)
    r1.pack(fill="x", padx=px(10), pady=px(6))
    ttk.Label(r1, text="输出目录:").pack(side="left")
    ttk.Entry(r1, textvariable=out_dir).pack(side="left", fill="x", expand=True, padx=px(6), ipady=px(3))

    def pick_out():
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            out_dir.set(d)
    ttk.Button(r1, text="浏览…", command=pick_out).pack(side="left")
    ttk.Label(r1, text="(留空 = 与原文件相同)", foreground="gray").pack(side="left", padx=px(6))

    r2 = ttk.Frame(opts)
    r2.pack(fill="x", padx=px(10), pady=px(6))
    ttk.Label(r2, text="JPG 质量:").pack(side="left")
    qlabel = ttk.Label(r2, width=4, font=(family, 11, "bold"))
    q_scale = ttk.Scale(r2, from_=50, to=100, orient="horizontal", length=px(260),
                      command=lambda v: (quality.set(int(float(v))), qlabel.config(text=str(quality.get()))))
    q_scale.set(quality.get())
    q_scale.pack(side="left", padx=px(6))
    qlabel.config(text=str(quality.get()))
    qlabel.pack(side="left")
    r3 = ttk.Frame(opts)
    r3.pack(fill="x", padx=px(10), pady=(0, px(8)))
    ttk.Checkbutton(r3, text="保留 EXIF", variable=keep_exif).pack(side="left")
    ttk.Checkbutton(r3, text="覆盖同名文件", variable=overwrite).pack(side="left", padx=px(20))
    ttk.Checkbutton(r3, text="转换后删除原文件", variable=delete_src).pack(side="left")

    # 底部
    bottom = ttk.Frame(root)
    bottom.pack(fill="x", **pad)
    progress = ttk.Progressbar(bottom, mode="determinate")
    progress.pack(fill="x", pady=(0, px(8)), ipady=px(2))
    ttk.Label(bottom, textvariable=status).pack(side="left")
    start_btn = ttk.Button(bottom, text="开始转换", style="Accent.TButton")
    start_btn.pack(side="right")
    ttk.Checkbutton(bottom, text="完成后打开文件夹", variable=open_after).pack(side="right", padx=px(12))

    def set_state(iid, text):
        if tree.exists(iid):
            tree.set(iid, "state", text)
            tree.see(iid)

    def start():
        if not files:
            messagebox.showinfo("提示", "请先添加 HEIC 文件")
            return
        if delete_src.get() and not messagebox.askyesno("确认", "转换成功后将删除原 HEIC 文件,确定继续?"):
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
            root.after(0, set_state, iid, "转换中…")
            try:
                dst = convert_one(f, od, q, ex, ow)
                if dl:
                    f.unlink()
                with lock:
                    counts["ok"] += 1
                    last_dst[0] = dst
                root.after(0, set_state, iid, "✔ 完成")
            except Exception as e:
                with lock:
                    counts["fail"] += 1
                root.after(0, set_state, iid, "✘ 失败")
                root.after(0, status.set, f"{f.name}: {e}")
            root.after(0, progress.step, 1)

        with ThreadPoolExecutor(max_workers=max(1, min(8, (os.cpu_count() or 2)))) as ex_:
            list(ex_.map(job, todo))

        def done():
            start_btn.config(state="normal")
            status.set(f"完成:成功 {counts['ok']},失败 {counts['fail']}")
            if open_after.get() and last_dst[0]:
                os.startfile(last_dst[0].parent)
        root.after(0, done)

    start_btn.config(command=start)

    # 命令行带了文件 (例如拖到 exe 图标上) 时直接加入列表
    if len(sys.argv) > 1:
        add_paths(sys.argv[1:])

    root.mainloop()


if __name__ == "__main__":
    args = sys.argv[1:]
    # 有 -o/-q 等参数或显式 --cli 时走命令行模式, 否则打开 GUI
    if args and (args[0] == "--cli" or any(a.startswith("-") for a in args)):
        sys.exit(run_cli([a for a in args if a != "--cli"]))
    run_gui()
