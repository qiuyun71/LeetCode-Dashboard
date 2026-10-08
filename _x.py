# -*- coding: utf-8 -*-
"""欠账上限 + 补做日 + 按钮搬进题板

跑在「副本 + 独立端口」上（LEET_PLAN / LEET_PORT），绝不碰真实 plan.json。
"""
import json, os, shutil, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TPLAN = os.path.join(BASE_DIR, "_t_plan.json")
PORT = 8799
BASE = "http://127.0.0.1:%d" % PORT
PY = sys.executable

SRC = os.path.join(BASE_DIR, "plan.json")
if not os.path.exists(SRC):        # 全新 clone 没有 plan.json：用模板兜底
    SRC = os.path.join(BASE_DIR, "plan.example.json")
shutil.copy(SRC, TPLAN)
env = dict(os.environ, LEET_PLAN=TPLAN, LEET_PORT=str(PORT))
proc = subprocess.Popen([PY, "server.py"], cwd=BASE_DIR, env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def post(p, d=None):
    req = urllib.request.Request(BASE + p, data=json.dumps(d or {}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def get(p):
    with urllib.request.urlopen(BASE + p, timeout=10) as r:
        return json.loads(r.read().decode())


ok = False
try:
    for _ in range(40):
        try:
            get("/api/state")
            break
        except Exception:
            time.sleep(0.3)

    s0 = get("/api/state")
    per = s0["plan"]["perDay"]
    cap = per * 2
    cur = len(s0["board"]) - 1
    print("题单=%s 每天=%s 题 -> 上限=%s" % (s0["activeList"], per, cap))

    # 造场景：每天 1 题（上限 2），把当天堆到 5 题，全不勾选提交 -> 应分流成 2 顺延 + 3 补做日
    post("/api/setplan", {"perDay": 1, "reset": False})
    s0 = get("/api/state")
    per = s0["plan"]["perDay"]
    cap = per * 2
    cur = len(s0["board"]) - 1

    # 关键前置：恢复当天原题并清掉手动勾选（真实数据里用户可能勾了没提交）
    post("/api/resetday", {"day": cur})
    s0 = get("/api/state")
    cur = len(s0["board"]) - 1
    ntasks = len(s0["board"][cur]["tasks"])
    assert not any(t.get("checked") for t in s0["board"][cur]["tasks"]), "重置后不该有勾选"
    post("/api/add", {"day": cur, "n": 5 - ntasks})      # 堆到 5 题
    s0 = get("/api/state")
    cur = len(s0["board"]) - 1
    ntasks = len(s0["board"][cur]["tasks"])
    print("   重置+加题后：当天 %s 题，勾选数=%s（上限 %s）"
          % (ntasks, sum(1 for t in s0["board"][cur]["tasks"] if t.get("checked")), cap))
    assert ntasks > cap, "需要一天题数超过上限(%s)才能测出分流，实际 %s" % (cap, ntasks)
    days0 = s0["plan"]["days"]

    print("\n== 1. 整题提交（一道都不勾，全部变欠账）==")
    j = post("/api/submit", {"day": cur})
    print("   added=%s carried=%s extra=%s" % (j.get("added"), j.get("carried"), j.get("extra")))
    assert j.get("carried") <= cap, "顺延到明天不应超过上限 %s 题，实际 %s" % (cap, j.get("carried"))
    assert j.get("carried") > 0, "应该有题顺延下去"
    assert j.get("extra") > 0, "超过上限的部分应进补做日"
    # 守恒：当天没做完的题 =顺延到明天的 + 进补做日的
    assert j.get("carried") + j.get("extra") == ntasks, \
        "顺延 %s + 补做 %s 应等于当天 %s 题" % (j.get("carried"), j.get("extra"), ntasks)
    # 上限确实是「顺延到明天」的量：顺延数应该正好卡在 cap
    assert j.get("carried") == cap, \
        "欠账超上限时应恰好顺延 %s 道，实际 %s" % (cap, j.get("carried"))

    ids0 = {t["id"] for t in s0["board"][cur]["tasks"]}
    s1 = get("/api/state")
    nx = [b for b in s1["board"]
          if not b.get("extra") and b["dayIndex"] == s0["board"][cur]["dayIndex"] + 1]
    print("   当天 %s 题 -> 顺延 %s 道（上限 %s）+ 补做日 %s 道"
          % (ntasks, j.get("carried"), cap, j.get("extra")))

    print("\n== 1b. 补做日 ==")
    extras = [b for b in s1["board"] if b.get("extra")]
    print("   补做日: %s 个, 日期=%s, 题数=%s"
          % (len(extras), s1["extraDates"], [len(b["tasks"]) for b in extras]))
    assert len(extras) == 1, "应生成 1 个补做日"
    assert len(extras[0]["tasks"]) == j.get("extra"), "补做日题数不对"
    # 补做日里应该就是当天没做完的那批题（不含已被明天占用的）
    exids = {t["id"] for t in extras[0]["tasks"]}
    assert exids and exids <= ids0, "补做日的题应来自当天未完成的题"
    assert s1["extraDates"], "state 应返回 extraDates"
    nlast = max(b["dayIndex"] for b in s1["board"] if not b.get("extra"))
    print("   板面顺序 idx=%s extra=%s" %
          ([b["dayIndex"] for b in s1["board"]], [b.get("extra") for b in s1["board"]]))
    assert s1["board"][-1].get("extra"), "补做日应在板面最后"
    assert extras[0]["dayIndex"] > nlast, "补做日序号应大于最后一个普通天"
    print("   计划天数: %s -> %s (补做日让计划延长)" % (days0, s1["plan"]["days"]))
    assert s1["plan"]["days"] > days0, "补做日应让计划天数 +1"

    print("\n== 2. 顺延不会把第二天塞爆 ==")
    cur_di = s0["board"][cur]["dayIndex"]
    nxt_day = [b for b in s1["board"]
               if not b.get("extra") and b["dayIndex"] == cur_di + 1]
    assert nxt_day, "应该存在第二天"
    n = len(nxt_day[0].get("tasks", []))
    print("   第二天共 %s 题（自身 %s + 顺延上限 %s）" % (n, per, cap))
    assert n <= per + cap, "第二天不应超过 %s 题，实际 %s" % (per + cap, n)
    assert n >= cap, "第二天应接到了顺延的 %s 道" % cap

    print("\n== 2b. 有补做日时再展开，不能跳过计划天 ==")
    before = [(b["dayIndex"], b.get("extra"), len(b.get("tasks", []))) for b in s1["board"]]
    j2 = post("/api/expand", {})
    s2 = get("/api/state")
    print("   展开前 %s" % before)
    print("   展开后 %s" % [(b["dayIndex"], b.get("extra"), len(b.get("tasks", []))) for b in s2["board"]])
    assert j2.get("ok"), "展开应成功"
    ni = max(b["dayIndex"] for b in s2["board"] if not b.get("extra"))
    assert ni == nlast + 1, "新展开的普通天序号应为 %s，实际 %s" % (nlast + 1, ni)
    assert s2["board"][-1].get("extra"), "展开后补做日仍应在最后"

    print("\n== 3. 界面 ==")
    errs = []
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(viewport={"width": 1440, "height": 900})
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.goto(BASE)
        pg.wait_for_timeout(1500)

        inboard = pg.eval_on_selector_all(
            ".day .dayacts .tbtn", "els => els.map(e=>e.textContent.trim())")
        print("   题板内按钮:", inboard)
        assert len(inboard) == 2, "题板里应有 2 个按钮（展开/撤销）"
        assert any("展开" in x for x in inboard) and any("撤销" in x for x in inboard)
        toolbar = pg.eval_on_selector_all(".toolbar", "els => els.length")
        print("   顶部 toolbar 数量:", toolbar, "(应为 0，已移除)")
        assert toolbar == 0, "顶部工具栏应已移除"

        s3 = get("/api/state")
        d = (s3.get("extraDates") or [None])[0]
        print("   当前 extraDates:", s3.get("extraDates"))
        assert d, "state 里应有补做日"
        sel = '.cell[data-date="%s"]' % d
        if pg.query_selector(sel):
            cls = pg.eval_on_selector(sel, "e => e.className")
            bg = pg.eval_on_selector(sel, "e => getComputedStyle(e).backgroundColor")
            print("   补做日 %s class=%s 底色=%s" % (d, cls, bg))
            assert "extra" in cls, "补做日应带 extra 标记"
            assert bg != "rgb(255, 255, 255)", "补做日应有独立底色"
        else:
            print("   补做日 %s 不在本月日历上（需翻月），跳过样式检查" % d)
        br.close()
    print("   JS 错误:", errs if errs else "无")
    assert not errs, "JS 错误: %s" % errs

    # ---- 错题本 ----
    print("\n== 4. 错题本 ==")
    s = get("/api/state")
    assert s.get("marks") == [] or s.get("marks") is not None, "state 应带 marks 字段"
    assert "markStats" in s, "state 应带 markStats 字段"
    tid = s["tasks"][0]["id"]
    r = post("/api/mark", {"id": tid, "kind": "classic"})
    assert r.get("ok"), "标记应成功"
    mk = [m for m in r["state"]["marks"] if m["id"] == tid]
    assert mk, "标记后应出现在 marks 里"
    assert mk[0]["kind"] == "classic" and mk[0]["kindLabel"] == "经典"
    assert mk[0]["name"], "应带题目名"
    r = post("/api/mark", {"id": tid, "kind": "wrong", "note": "测试备注"})
    mk = [m for m in r["state"]["marks"] if m["id"] == tid]
    assert mk[0]["kind"] == "wrong", "应改成错题"
    assert mk[0]["note"] == "测试备注", "备注应保存"
    st = r["state"]["markStats"]
    assert st["total"] >= 1 and st["wrong"] >= 1, "统计应计数"
    r = post("/api/mark", {"id": tid, "kind": ""})
    assert not [m for m in r["state"]["marks"] if m["id"] == tid], "取消标记后应移除"
    print("   标记/改类型/备注/取消 全部正常，统计:", st["total"], "条")

    print("\n全部断言通过")
    ok = True
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    if os.path.exists(TPLAN):
        os.remove(TPLAN)
    print("(副本服务已关闭，真实 plan.json 全程未被改动)")
sys.exit(0 if ok else 1)
