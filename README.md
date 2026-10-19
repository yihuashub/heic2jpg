# HEIC2JPG

一个简单的 Windows 小工具,把 iPhone 等设备拍摄的 **HEIC / HEIF** 照片批量转换为 **JPG**。

- 单文件 exe,下载即用,无需安装 Python,也不需要微软商店的 HEVC 扩展
- 支持拖放文件 / 文件夹(包含子文件夹),多线程批量转换
- 可调 JPG 质量(50–100,默认 92)
- 保留 EXIF 信息(拍摄时间、相机型号、GPS 等)和色彩配置文件
- 自动按拍摄方向旋正照片
- 保留原文件的修改时间
- 同名文件自动改名为 `xxx (1).jpg`,也可选择覆盖
- 可选:转换后删除原 HEIC 文件
- 适配高分屏(125% / 150% 缩放下清晰显示)
- 支持格式:`.heic` `.heif` `.hif`

## 下载

到 [Releases](../../releases/latest) 页面下载 `HEIC2JPG.exe`,双击运行即可。

> 首次运行时 Windows SmartScreen 可能提示"未知发布者",点击「更多信息」→「仍要运行」。

## 使用方法

1. 双击 `HEIC2JPG.exe` 打开
2. 把 HEIC 文件或文件夹拖进列表(或点「添加文件」「添加文件夹」)
3. 按需调整设置,点击「开始转换」

也可以直接把文件拖到 exe 图标上打开。

### 命令行

```bat
HEIC2JPG.exe --cli D:\照片 -o D:\输出 -q 90
```

| 参数 | 说明 |
| --- | --- |
| `-o, --out` | 输出目录(默认与原文件相同) |
| `-q, --quality` | JPG 质量 1–100(默认 92) |
| `--no-exif` | 不保留 EXIF |
| `--overwrite` | 覆盖已存在的同名 JPG |
| `--delete` | 转换成功后删除原文件 |

## 从源码运行 / 打包

需要 Python 3.10+:

```bat
pip install -r requirements.txt
python heic2jpg.py
```

打包成 exe:运行 `build.bat`,生成的文件在 `dist\HEIC2JPG.exe`。

## 依赖

- [Pillow](https://github.com/python-pillow/Pillow)
- [pi-heif](https://github.com/bigcat88/pillow_heif)(仅解码版, 内置 libheif / libde265, LGPL)
- [tkinterdnd2](https://github.com/Eliav2/tkinterdnd2)(拖放支持)

## 许可证

[MIT](LICENSE)
