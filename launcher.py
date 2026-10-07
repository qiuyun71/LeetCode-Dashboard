# -*- coding: utf-8 -*-
"""力扣刷题看板 · 单文件 EXE 入口

双击即用，目标机器不需要装 Python。

和 server.py 的区别：
  server.py  —— 纯服务，命令行前台跑
  launcher.py —— 打包用。探测端口 -> 没跑就起服务 -> 打开浏览器 -> 阻塞驻留

关键点（打包成 onefile 后必须这么处理）：
  PyInstaller 会把 ui.html / app.js / assets 解压到临时目录 _MEIPASS，
  所以**只读资源** BASE 要指向 _MEIPASS，而**可写数据** plan.json 必须放在
  exe 所在目录 —— 否则双击一次就丢一次进度。
"""
import os
import sys
import socket
import threading
import time
import webbrowser

# 冻结后：静态资源在 _MEIPASS，数据在 exe 所在目录
if getattr(sys, "frozen", False):
    RES_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    APP_DIR = os.path.dirname(sys.executable)          # exe 旁边，放 plan.json / log
else:
    RES_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = RES_DIR

sys.path.insert(0, RES_DIR)
import server  # noqa: E402  复用后端全部逻辑

# 覆盖路径：资源只读（临时目录），数据可写（exe 旁边）
server.BASE = RES_DIR
server.UI_PATH = os.path.join(RES_DIR, "ui.html")
server.PLAN_PATH = os.path.join(APP_DIR, "plan.json")
server.PORT = int(os.environ.get("LEET_PORT") or 8765)

URL = "http://127.0.0.1:%d" % server.PORT
LOG = os.path.join(APP_DIR, "board.log")


def log(msg):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


def port_open():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        return s.connect_ex(("127.0.0.1", server.PORT)) == 0
    finally:
        s.close()


def main():
    log("launcher start, app dir = %s" % APP_DIR)

    if port_open():
        log("port already in use -> just open browser")
        webbrowser.open(URL)
        return

    def run():
        try:
            server.main()                # 内部：确保数据文件 + 起提醒线程 + serve_forever
        except Exception as e:
            log("server crashed: %r" % (e,))

    t = threading.Thread(target=run, daemon=True)
    t.start()

    for _ in range(40):# 最多等 10 秒
        if port_open():
            break
        time.sleep(0.25)

    if port_open():
        log("server ready -> open browser")
        webbrowser.open(URL)
    else:
        log("server failed to start in 10s")
        # 无控制台模式下给用户一个可看的提示
        try:
            os.startfile(LOG)            # Windows：打开日志
        except Exception:
            pass

    t.join()                              # 驻留：关掉窗口才停服务


if __name__ == "__main__":
    main()