# 打包单文件 EXE

日常使用直接双击桌面的 `力扣刷题看板.exe`（免装Python）。
这份文档给「想自己重新打包」的人。

## 前置

```bash
pip install pyinstaller
```

## 打包命令（在项目根目录执行）

```bash
python -m PyInstaller \
  --onefile \
  --noconsole \
  --name "力扣刷题看板" \
  --add-data "ui.html;." \
  --add-data "app.js;." \
  --add-data "assets;assets" \
  --add-data "plan.example.json;." \
  --distpath "dist" \
  --workpath "build" \
  --specpath "." \
  --noupx \
  --clean \
  launcher.py
```

产物：`dist/力扣刷题看板.exe`（约 50MB，包含 Python 运行时）

## launcher.py 做了什么

单文件 exe 运行时，PyInstaller 会把 `ui.html` / `app.js` / `assets/` 解压到临时目录
`_MEIPASS`。所以 launcher 里把路径分成两类：

| 用途 | 路径 | 原因 |
|------|------|------|
| 只读资源（ui.html / app.js / assets） | `sys._MEIPASS` 临时目录 | 打进 exe 了，只能读 |
| **可写数据（plan.json / board.log）** | **exe 所在目录** | 临时目录会被清空，放那儿等于每次双击丢进度 |

启动流程：探测8765 端口 → 没在跑就起服务线程 → 等端口就绪 → 自动开浏览器 → 阻塞驻留
（关掉 exe 窗口即停服务）。已经在跑时直接开浏览器，不重复起。

## 注意

- 改完 `ui.html` / `app.js` / `assets/` 后**必须重新打包**，exe 里是旧的
- `plan.json` 不进 exe，它在 exe 旁边，属于用户数据
- 出问题看 exe 同目录的 `board.log`
