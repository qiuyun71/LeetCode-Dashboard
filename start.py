# -*- coding: utf-8 -*-
"""力扣看板 · 启动器（静默，不弹窗口）
检测服务 -> 未运行则后台拉起 -> 打开浏览器
用法：python start.py     （已运行则直接打开浏览器）
"""
import os
import socket
import subprocess
import sys
import time
import webbrowser

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = 8765
URL = "http://127.0.0.1:%d" % PORT
PY = sys.executable


def port_open():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        return s.connect_ex(("127.0.0.1", PORT)) == 0
    finally:
        s.close()


def launch_server():
    """后台拉起 server.py：脱离控制台、不弹窗。

    依次尝试三种启动方式，哪个能把端口拉起来就用哪个：
      1. CREATE_NO_WINDOW | DETACHED_PROCESS —— 完全脱离父进程
      2. CREATE_NO_WINDOW                    —— 不弹窗但同会话
      3. 无标志                              —— 兜底
    输出写入 server.log 方便排查。
    """
    logf = open(os.path.join(BASE, "server.log"), "ab")
    base_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    detach = getattr(subprocess, "DETACHED_PROCESS", 0)
    for flags in (base_flags | detach, base_flags, 0):
        try:
            subprocess.Popen(
                [PY, os.path.join(BASE, "server.py")],
                creationflags=flags,
                close_fds=True,
                cwd=BASE,
                stdin=subprocess.DEVNULL,
                stdout=logf,
                stderr=logf,
            )
        except Exception:
            continue
        for _ in range(24):          # 每种方式最多等 6 秒
            if port_open():
                return True
            time.sleep(0.25)
    return False


def main():
    if not port_open():
        if not launch_server():
            print("启动失败：服务未能在超时内就绪，详见 server.log")
            return
    webbrowser.open(URL)
    print("board ->", URL)


if __name__ == "__main__":
    main()
