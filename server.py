# -*- coding: utf-8 -*-
"""力扣刷题看板 · 本地服务（后端）
浏览器打开 http://127.0.0.1:8765     界面在 ui.html

数据结构（plan.json）：
{
  "activeList": "lc100",
  "reminders": {"enabled":true,"slots":[{"time":"12:00","label":"中午提醒"}],"lastFired":{}},
  "lists": {
    "lc100": {
      "name": "LeetCode 100",
      "startDate": "2026-10-06",
      "perDay": 4,
      "categories": [{"name":"哈希","problems":[{"id":1,"name":"两数之和","difficulty":"easy","hint":"哈希表"}]}],
      "pool": [...],          # 「换一题」的备用题
      "done": [{"id":1,"date":"2026-10-06"}],
      "board": [...]          # 已展开的天
    }
  }
}
days 不落盘，运行时由 categories 按 perDay 展平切分。
"""
import json
import os
import re
import datetime
import threading
import subprocess
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

BASE = os.path.dirname(os.path.abspath(__file__))
# 测试时用 LEET_PLAN / LEET_PORT 指向副本，避免脚本动到真实 plan.json
PLAN_PATH = os.environ.get("LEET_PLAN") or os.path.join(BASE, "plan.json")
UI_PATH = os.path.join(BASE, "ui.html")
PORT = int(os.environ.get("LEET_PORT") or 8765)
_lock = threading.Lock()

# 撤销栈：每次写操作前压入快照，最多保留 30 步
_history = []
HIST_MAX = 30

DEFAULT_REMINDERS = {
    "enabled": True,
    "slots": [
        {"time": "12:00", "label": "中午提醒"},
        {"time": "18:30", "label": "晚间检查"},
    ],
    "lastFired": {},
}
DIFF_CN = {"easy": "简单", "medium": "中等", "hard": "困难"}
CN_DIFF = {"简单": "easy", "中等": "medium", "困难": "hard",
           "易": "easy", "中": "medium", "难": "hard",
           "easy": "easy", "medium": "medium", "hard": "hard"}


# ============ 基础读写 ============

def load_plan():
    with open(PLAN_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_plan(p):
    tmp = PLAN_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PLAN_PATH)


def push_history(p):
    try:
        _history.append(json.dumps(p, ensure_ascii=False))
        if len(_history) > HIST_MAX:
            _history.pop(0)
    except Exception:
        pass


def pop_history():
    if not _history:
        return None
    try:
        return json.loads(_history.pop())
    except Exception:
        return None


def can_undo():
    if not _history:
        return False
    try:
        return json.loads(_history[-1]) != load_plan()
    except Exception:
        return False


# ============ 题单结构 ============

def ensure_reminders(root):
    r = root.get("reminders")
    if not isinstance(r, dict):
        r = {}
    r.setdefault("enabled", DEFAULT_REMINDERS["enabled"])
    if not isinstance(r.get("slots"), list) or not r.get("slots"):
        r["slots"] = [dict(s) for s in DEFAULT_REMINDERS["slots"]]
    if not isinstance(r.get("lastFired"), dict):
        r["lastFired"] = {}
    root["reminders"] = r
    return r


def ensure_root(p):
    """兼容旧结构（顶层直接是题单），统一成 lists 结构"""
    if not isinstance(p.get("lists"), dict):
        legacy = {
            "name": p.get("title") or "LeetCode 100",
            "startDate": p.get("startDate") or datetime.date.today().isoformat(),
            "perDay": int(p.get("perDay", 4) or 4),
            "categories": p.get("categories") or [],
            "pool": p.get("pool") or [],
            "done": p.get("done") or [],
            "board": p.get("board") or [],
        }
        # 旧结构用 days 而非 categories：把每天的任务摊平成一个分类
        if not legacy["categories"] and p.get("days"):
            seen, probs = set(), []
            for day in p.get("days", []):
                for t in day:
                    if t.get("id") in seen:
                        continue
                    seen.add(t.get("id"))
                    probs.append(t)
            legacy["categories"] = [{"name": "默认分类", "problems": probs}]
        p = {"activeList": "lc100", "reminders": p.get("reminders"),
             "lists": {"lc100": legacy}}
    if not p.get("activeList") or p["activeList"] not in p["lists"]:
        p["activeList"] = sorted(p["lists"].keys())[0] if p["lists"] else ""
    if not isinstance(p.get("globalPool"), list):
        p["globalPool"] = []
    for k, l in p["lists"].items():
        l.setdefault("name", k)
        l.setdefault("startDate", datetime.date.today().isoformat())
        l.setdefault("perDay", 4)
        l.setdefault("limit", None)
        l.setdefault("categories", [])
        l.setdefault("pool", [])
        l.setdefault("done", [])
        l.setdefault("board", [])
    ensure_reminders(p)
    return p


def active_key(p):
    return p.get("activeList") or ""


def get_list(p, key=None):
    k = key or active_key(p)
    return p.get("lists", {}).get(k)


def flat_problems(l):
    """展平所有分类 -> [(分类名, 题目dict)]"""
    out = []
    for c in l.get("categories", []):
        cn = c.get("name", "")
        for t in c.get("problems", []):
            out.append((cn, t))
    return out


def pre_done_ids(l):
    """「之前做过」的题号集合：这些题不再进计划（总量与天数随之减少）

    数据来源就是 done 里 pre=True 的记录，不另开字段，避免两处状态不同步。
    """
    s = set()
    for it in (l.get("done") or []):
        if isinstance(it, dict) and it.get("pre"):
            s.add(it.get("id"))
    return s


def effective_problems(l):
    """按 limit 截取实际要刷的题（limit 为空/0 表示全部）

    已被标记「之前做过」的题会被剔除，因此 total / days 会动态缩短。
    """
    flat = flat_problems(l)
    pd = pre_done_ids(l)
    if pd:
        flat = [(cn, t) for cn, t in flat if t.get("id") not in pd]
    lim = l.get("limit")
    try:
        lim = int(lim) if lim else 0
    except Exception:
        lim = 0
    if lim > 0:
        flat = flat[:lim]
    return flat


def build_days(l):
    """按 perDay 把展平后的题切成每天一批"""
    flat = effective_problems(l)
    per = max(1, int(l.get("perDay", 4) or 4))
    days = []
    for i in range(0, len(flat), per):
        chunk = flat[i:i + per]
        days.append([dict(t, category=cn) for cn, t in chunk])
    return days


def total_problems(l):
    return len(effective_problems(l))


def all_problems_count(l):
    return len(flat_problems(l))


def plan_view(l):
    """计划概览：总题数 / 每天题数 / 剩余天数 / 起止日期

    剩余天数与结束日期按「还没做完的题」动态算：
      标记「之前做过」会把题从计划里剔除 -> total 变小 -> 剩余天数变少 -> 结束日期提前。
      例：100 题 / 每天 5 题，已完成 10 题时剩 18 天；再标记 10 道 -> 剩 16 天。
    """
    total = total_problems(l)
    per = max(1, int(l.get("perDay", 4) or 4))
    start = l.get("startDate") or datetime.date.today().isoformat()
    today = datetime.date.today()

    done_daily = sum(1 for d in done_list(l) if not d.get("pre"))
    left = max(0, total - done_daily)
    days_left = (left + per - 1) // per if left else 0
    # 欠账顺延出来的「补做日」也要占天数，计划随之延长
    days_left += sum(1 for b in (l.get("board") or [])
                     if b.get("extra") and not b.get("done"))

    end = (today + datetime.timedelta(days=max(0, days_left - 1))).isoformat()
    return {
        "total": total,
        "allTotal": all_problems_count(l),
        "perDay": per,
        "days": days_left,
        "left": left,
        "startDate": start,
        "endDate": end,
        "limit": l.get("limit"),
        "done": len(done_list(l)),
    }


def do_setplan(l, data):
    """设置计划：limit（总题数）/ perDay（每天题数）
    改完会重置已展开的天（已完成的记录保留）。
    返回 (ok, msg, reset_done)
    """
    done_n = len(done_list(l))
    all_n = all_problems_count(l)

    if "limit" in data:
        try:
            lim = int(data.get("limit") or 0)
        except Exception:
            return False, "总题数格式不对", False
        if lim <= 0 or lim >= all_n:
            l["limit"] = None          # 全部
        else:
            if lim < done_n:
                return False, "总题数不能少于已完成的 %d 题" % done_n, False
            l["limit"] = lim

    if "perDay" in data:
        try:
            per = int(data.get("perDay") or 4)
        except Exception:
            return False, "每天题数格式不对", False
        l["perDay"] = max(1, min(50, per))

    # 计划变了 -> 重排（保留 done 记录）
    if data.get("reset", True):
        fresh = new_day(l, 0)
        l["board"] = [fresh] if fresh else []
        return True, None, True
    return True, None, False


def done_list(l):
    out = []
    for it in l.get("done", []):
        if isinstance(it, dict):
            out.append({
                "id": it.get("id"),
                "date": it.get("date") or "",
                "swapped": bool(it.get("swapped")),
                "pre": bool(it.get("pre")),
            })
        else:
            out.append({"id": it, "date": "", "swapped": False, "pre": False})
    return out


def make_task(x, carry=False):
    return {
        "id": x.get("id"),
        "name": x.get("name", ""),
        "difficulty": x.get("difficulty", "easy"),
        "hint": x.get("hint", ""),
        "category": x.get("category", ""),
        "checked": False,
        "carry": bool(carry),
    }


def new_day(l, day_index):
    days = build_days(l)
    if day_index < 0 or day_index >= len(days):
        return None
    start = l.get("startDate") or datetime.date.today().isoformat()
    try:
        d = datetime.date.fromisoformat(start) + datetime.timedelta(days=day_index)
    except Exception:
        d = datetime.date.today() + datetime.timedelta(days=day_index)
    return {
        "dayIndex": day_index,
        "date": d.isoformat(),
        "tasks": [make_task(x) for x in days[day_index]],
        "done": False,
        "deficit": 0,
    }


def ensure_board(l):
    if not l.get("startDate"):
        l["startDate"] = datetime.date.today().isoformat()
    if not l.get("board"):
        d0 = new_day(l, 0)
        l["board"] = [d0] if d0 else []
    return l


def used_ids(l):
    s = set()
    for b in l.get("board", []):
        s |= {t.get("id") for t in b.get("tasks", [])}
    s |= {d["id"] for d in done_list(l)}
    return s


def candidate_pool(p, l, limit=300):
    """换题 / 加题的候选题目 —— 只从「本题单」里出，不外借。

    来源（都是本题单自己的题，加起来 <= 计划总题数）：
      1. rest —— 本题单还没排上板的题（100 题里剩下的那 96 道）  ← 唯一来源

    换下来的题会自己回到 rest（它既不在板上也不在 done），所以不需要备用池。
    题排完就是真没了，不会去全局题池 / 其它题单借题。
    返回 (候选列表, 来源统计)。候选会去重，并排除本题单已用过的题。
    """
    used = used_ids(l)
    seen = set()
    out = []
    src = {"rest": 0}

    def push(t, bucket):
        if len(out) >= limit:
            return
        tid = t.get("id")
        if tid is None or tid in used or tid in seen:
            return
        seen.add(tid)
        out.append(dict(t))
        src[bucket] += 1

    # 本题单剩余未上板的题（换下来的题会自动回到这里）
    for cn, t in effective_problems(l):
        push(dict(t, category=cn), "rest")
    return out, src


def all_tasks(l):
    """题目清单：本题单要刷的题 + 已经换进来的题池题"""
    done_ids = {d["id"] for d in done_list(l)}
    out = []
    own_ids = set()
    for cn, t in effective_problems(l):
        tid = t.get("id")
        own_ids.add(tid)
        out.append({
            "id": tid,
            "name": t.get("name", ""),
            "difficulty": t.get("difficulty", "easy"),
            "hint": t.get("hint", ""),
            "category": cn,
            "done": tid in done_ids,
        })
    # 题池里被「换一题」换进来的，也要在清单里能看到
    poolmap = {t.get("id"): t for t in l.get("pool", [])}
    used_in_board = set()
    for b in l.get("board", []):
        for t in b.get("tasks", []):
            used_in_board.add(t.get("id"))
    for tid in sorted(x for x in used_in_board if x not in own_ids and x in poolmap):
        t = poolmap[tid]
        out.append({
            "id": tid,
            "name": t.get("name", ""),
            "difficulty": t.get("difficulty", "easy"),
            "hint": t.get("hint", ""),
            "category": "换题",
            "done": tid in done_ids,
        })
    return out


def categories_view(l):
    """按分类分组的题目（供弹窗显示）；超出 limit 的题标 skipped"""
    done_ids = {d["id"] for d in done_list(l)}
    keep = {t.get("id") for _, t in effective_problems(l)}
    out = []
    for c in l.get("categories", []):
        probs = []
        for t in c.get("problems", []):
            tid = t.get("id")
            probs.append({
                "id": tid,
                "name": t.get("name", ""),
                "difficulty": t.get("difficulty", "easy"),
                "hint": t.get("hint", ""),
                "done": tid in done_ids,
                "skipped": tid not in keep,
            })
        out.append({
            "name": c.get("name", ""),
            "total": len(probs),
            "done": sum(1 for x in probs if x["done"]),
            "inPlan": sum(1 for x in probs if not x["skipped"]),
            "problems": probs,
        })
    return out


def daily_counts(l):
    """每日做题量：只统计真正做的新题

    换掉的题（swapped）和标记「之前做过」的题（pre）都不计入 ——
    后者只是补记历史，不代表某天真的刷了这些题。
    """
    c = {}
    for d in done_list(l):
        if d.get("swapped") or d.get("pre"):
            continue
        dt = d["date"]
        if dt:
            c[dt] = c.get(dt, 0) + 1
    return c


def daily_detail(l):
    d = {}
    for it in done_list(l):
        if it.get("swapped") or it.get("pre"):
            continue
        dt = it["date"]
        if dt:
            d.setdefault(dt, []).append(it["id"])
    return d


# ============ 统计 ============

def stats_view(l):
    idmap = {}
    for cn, t in flat_problems(l):
        idmap[t.get("id")] = t
    for t in l.get("pool", []):
        idmap.setdefault(t.get("id"), t)

    # 难度分布：换题补记（历史遗留）不算，标记「之前做过」算
    dl = [d for d in done_list(l) if not d.get("swapped")]
    diff = {"easy": 0, "medium": 0, "hard": 0}
    for d in dl:
        k = (idmap.get(d["id"]) or {}).get("difficulty", "easy")
        if k in diff:
            diff[k] += 1

    daily = daily_counts(l)
    today = datetime.date.today()
    days7 = []
    for i in range(6, -1, -1):
        ds = (today - datetime.timedelta(days=i)).isoformat()
        days7.append({"date": ds, "count": daily.get(ds, 0)})

    streak = 0
    cur = today
    if daily.get(cur.isoformat(), 0) == 0:
        cur = today - datetime.timedelta(days=1)
    while daily.get(cur.isoformat(), 0) > 0:
        streak += 1
        cur -= datetime.timedelta(days=1)

    recent = [x["count"] for x in days7 if x["count"] > 0]
    avg = (sum(recent) / len(recent)) if recent else 0
    total = total_problems(l)
    left = max(0, total - len(done_list(l)))
    eta = None
    if avg > 0 and left > 0:
        eta = (today + datetime.timedelta(days=int(-(-left // avg)))).isoformat()

    return {
        "diff": diff,
        "days7": days7,
        "streak": streak,
        "avg7": round(avg, 1),
        "left": left,
        "eta": eta,
        "boardTotal": len(l.get("board", [])),
        "poolLeft": len(l.get("pool", [])),
    }


def weekly_view(l):
    daily = daily_counts(l)
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())

    def week_days(start):
        out = []
        for i in range(7):
            d = start + datetime.timedelta(days=i)
            ds = d.isoformat()
            out.append({
                "date": ds,
                "label": ["一", "二", "三", "四", "五", "六", "日"][i],
                "count": daily.get(ds, 0),
                "future": ds > today.isoformat(),
                "today": ds == today.isoformat(),
            })
        return out

    tw_days = week_days(monday)
    lw_days = week_days(monday - datetime.timedelta(days=7))
    tw = sum(x["count"] for x in tw_days)
    lw = sum(x["count"] for x in lw_days)
    delta = round((tw - lw) / lw * 100) if lw > 0 else None
    return {
        "thisWeek": tw_days,
        "lastWeekTotal": lw,
        "thisWeekTotal": tw,
        "delta": delta,
        "weekStart": monday.isoformat(),
        "weekEnd": (monday + datetime.timedelta(days=6)).isoformat(),
    }


def lists_view(p):
    out = []
    for k, l in sorted(p.get("lists", {}).items()):
        out.append({
            "key": k,
            "name": l.get("name", k),
            "total": total_problems(l),
            "done": len(done_list(l)),
            "perDay": int(l.get("perDay", 4) or 4),
            "active": k == active_key(p),
        })
    return out


def do_setplan_mark(p, done=True):
    p["setupDone"] = bool(done)
    return True


def build_stamp():
    """界面版本戳：ui.html / app.js 的修改时间，用来提示用户刷新页面"""
    try:
        a = os.path.getmtime(UI_PATH)
        b = os.path.getmtime(os.path.join(BASE, "app.js"))
        return "%d" % int(max(a, b))
    except Exception:
        return "0"


def state_view(p):
    l = get_list(p)
    if l is None:
        return {"board": [], "doneCount": 0, "preCount": 0, "target": 0,
                "totalDays": 0, "today": datetime.date.today().isoformat(),
                "poolLeft": 0, "daily": {}, "dailyDetail": {}, "tasks": [],
                "categories": [], "lists": [], "activeList": "",
                "stats": stats_view({"categories": [], "pool": [], "done": [], "board": []}),
                "weekly": weekly_view({"done": []}),
                "reminders": {"enabled": False, "slots": []},
                "canUndo": can_undo()}
    dl = done_list(l)
    r = ensure_reminders(p)
    try:
        _cands, _csrc = candidate_pool(p, l)
    except Exception:
        _cands, _csrc = [], {"rest": 0}
    return {
        "board": l.get("board", []),
        "doneCount": len(dl),
        "preCount": sum(1 for d in dl if d.get("pre")),
        "paused": bool(l.get("paused")),
        "pauses": [s for s in (l.get("pauses") or []) if isinstance(s, dict)],
        "extraDates": [b.get("date") for b in (l.get("board") or [])
                       if b.get("extra") and b.get("date")],
        "round": len([r for r in (l.get("rounds") or []) if isinstance(r, dict)]) + 1,
        "rounds": [{"no": r.get("no"), "from": r.get("from") or "", "to": r.get("to") or "",
                    "count": r.get("count") or 0, "done": r.get("done") or []}
                   for r in (l.get("rounds") or []) if isinstance(r, dict)],
        "preDone": [{"id": d["id"]} for d in dl if d.get("pre")],
        "target": total_problems(l),
        "totalDays": len(build_days(l)),
        "today": datetime.date.today().isoformat(),
        "poolLeft": len(l.get("pool", [])),
        "candLeft": len(_cands),
        "candSrc": _csrc,
        "daily": daily_counts(l),
        "dailyDetail": daily_detail(l),
        "tasks": all_tasks(l),
        "categories": categories_view(l),
        "lists": lists_view(p),
        "activeList": active_key(p),
        "activeName": l.get("name", ""),
        "perDay": int(l.get("perDay", 4) or 4),
        "plan": plan_view(l),
        "setupDone": bool(p.get("setupDone")),
        "stats": stats_view(l),
        "weekly": weekly_view(l),
        "reminders": {"enabled": bool(r.get("enabled")), "slots": r.get("slots", [])},
        "canUndo": can_undo(),
        "build": build_stamp(),
    }


# ============ 写操作（都作用于当前题单） ============

def do_toggle(l, di, ti):
    board = l.get("board", [])
    if not (0 <= di < len(board)):
        return False
    tasks = board[di].get("tasks", [])
    if not (0 <= ti < len(tasks)):
        return False
    tasks[ti]["checked"] = not tasks[ti].get("checked", False)
    return True


def refill_gap(l, di, want):
    """标记「之前做过」后补位，避免后续天跳题。

    原理：某题被移出计划后，effective_problems 整体前移一位，
    若不补位，后面已展开的天会与新序列错位（表现为漏掉一道题）。
    这里从新序列里取第一道尚未使用的题补进当前天，
    正好抵消这次前移，使所有天与计划保持一致。

    want: 补位后这一天期望的题数（= 弹出前的长度）
    """
    board = l.get("board", [])
    if not (0 <= di < len(board)):
        return False
    tasks = board[di].get("tasks", [])
    if len(tasks) >= want:
        return False
    used = used_ids(l)
    for _cn, t in effective_problems(l):
        tid = t.get("id")
        if tid is None or tid in used:
            continue
        tasks.append(make_task(t))
        board[di]["done"] = False
        return True
    return False


def do_mark_pre(l, di, ti):
    """标记「这题之前做过」

    效果：
      - 计入已完成题数（doneCount +1）
      - **不计入**每日做题量（刷题日历不变）
      - 该题移出计划 -> 总量与计划天数动态减少
    """
    board = l.get("board", [])
    if not (0 <= di < len(board)):
        return False, "bad_index"
    tasks = board[di].get("tasks", [])
    if not (0 <= ti < len(tasks)):
        return False, "bad_index"
    t = tasks[ti]
    tid = t.get("id")
    if tid is None:
        return False, "bad_index"
    done = l.setdefault("done", [])
    if tid in {d["id"] for d in done_list(l)}:
        return False, "already"
    was_len = len(tasks)
    done.append({"id": tid, "date": "", "pre": True})
    tasks.pop(ti)
    # 补位：把因前移而"顶上来"的那道题填进这一天
    refill_gap(l, di, was_len)
    return True, None


def do_unmark_pre(l, tid):
    """撤销「之前做过」的标记，把这题放回计划"""
    done = l.get("done", [])
    hit = None
    for i, it in enumerate(done):
        if isinstance(it, dict) and it.get("pre") and it.get("id") == tid:
            hit = i
            break
    if hit is None:
        return False, "not_found"
    done.pop(hit)
    return True, None


def do_swap(p, l, di, ti):
    """换一题（纯换，无副作用）

    只把这一格的题换成另一道：不动 done、不计入任何统计，
    已完成题数与刷题日历都不变。

    候选来源见 candidate_pool()：只从本题单还没上板的题里取。
    被换下来的题既不在板上也不在 done，会自动回到候选里，之后还能换回来。
    本题单的题排完时返回 (False, "no_candidate")。
    """
    board = l.get("board", [])
    if not (0 <= di < len(board)):
        return False, "bad_index"
    tasks = board[di].get("tasks", [])
    if not (0 <= ti < len(tasks)):
        return False, "bad_index"
    cands, _src = candidate_pool(p, l)
    if not cands:
        return False, "no_candidate"
    tasks[ti] = make_task(cands[0])
    return True, None


def do_add(p, l, di, n=1):
    """加题：候选来源同 do_swap（本题单剩余未上板的题 → 本题单备用池）"""
    board = l.get("board", [])
    if not (0 <= di < len(board)):
        return 0, "bad_index"
    cands, _src = candidate_pool(p, l)
    if not cands:
        return 0, "no_candidate"
    b = board[di]
    added = 0
    for cand in cands:
        if added >= n:
            break
        b["tasks"].append(make_task(cand))
        added += 1
    if added:
        b["done"] = False
    return added, (None if added else "no_candidate")


def _reflow_extra(l):
    """把「补做日」统一排到普通天之后

    补做日是计划末尾追加的一（多）天，序号和日期都必须落在最后一个普通天之后，
    否则它会跟还没展开的计划天撞号 —— 「展开下一天」会直接跳过那一批题。
    """
    board = l.get("board", [])
    normals = [b for b in board if not b.get("extra")]
    extras = [b for b in board if b.get("extra")]
    if not extras:
        return
    if not normals:
        return
    base_i = max(b.get("dayIndex", 0) for b in normals)
    try:
        base_d = datetime.date.fromisoformat(
            max(b.get("date", "") for b in normals))
    except Exception:
        base_d = datetime.date.today()
    for k, b in enumerate(extras, start=1):
        b["dayIndex"] = base_i + k
        b["date"] = (base_d + datetime.timedelta(days=k)).isoformat()
    l["board"] = normals + extras


def _push_to_extra(l, tasks):
    """把超出上限的欠账顺延到计划末尾的「补做日」

    优先塞进已有的、还没做完的补做日（避免无限多开天），装不下再新开一天。
    返回真正放进去的题数。
    """
    board = l.get("board", [])
    per = max(1, int(l.get("perDay", 4) or 4))
    cap = per * 2

    for bb in board:
        if bb.get("extra") and not bb.get("done"):
            if len(bb.get("tasks", [])) + len(tasks) <= cap:
                have = {t.get("id") for t in bb.get("tasks", [])}
                n = 0
                for c in tasks:
                    if c.get("id") not in have:
                        bb["tasks"].append(make_task(c, carry=True))
                        have.add(c.get("id"))
                        n += 1
                bb["done"] = False
                return n

    last_date = None
    for bb in board:
        d = bb.get("date")
        if d and (last_date is None or d > last_date):
            last_date = d
    try:
        base = datetime.date.fromisoformat(last_date) if last_date else datetime.date.today()
    except Exception:
        base = datetime.date.today()

    board.append({
        "dayIndex": max([bb.get("dayIndex", 0) for bb in board] or [0]) + 1,
        "date": (base + datetime.timedelta(days=1)).isoformat(),
        "tasks": [make_task(c, carry=True) for c in tasks],
        "done": False,
        "deficit": 0,
        "extra": True,          # 补做日：日历上换一种颜色

    })
    return len(tasks)


def do_submit(l, di):
    """提交：勾选的记入 done；未勾选的滚到后一天（欠账补回）

    欠账上限：下一天最多只接 perDay×2 道，**超出的不再往后续天堆**，
    而是顺延到计划末尾新增的「补做日」（extra=True，日历上换颜色标注）。
    这样欠账不会雪球式越滚越大、某天突然冒出十几道题。
    返回 (added, moved, remain, extra_n)
    """
    board = l.get("board", [])
    if not (0 <= di < len(board)):
        return 0, 0, 0, 0
    b = board[di]
    done = l.setdefault("done", [])
    existing = {d["id"] for d in done_list(l)}
    carry, added = [], 0
    for x in b.get("tasks", []):
        if x.get("checked"):
            if x.get("id") not in existing:
                done.append({"id": x.get("id"), "date": b.get("date")})
                existing.add(x.get("id"))
                added += 1
        else:
            carry.append(x)

    if not carry:
        b["tasks"] = []
        b["done"] = True
        b["deficit"] = 0
        b["completed"] = added
        return added, 0, 0, 0

    per = max(1, int(l.get("perDay", 4) or 4))
    cap = per * 2
    to_next, to_extra = carry, []
    if len(carry) > cap:                 # 超过两倍 -> 多出来的进补做日
        to_next = carry[:cap]
        to_extra = carry[cap:]

    # 先安置「下一天」——注意排除补做日，否则会把补做日当成下一天
    nxt = None
    for bb in board:
        if not bb.get("extra") and bb.get("dayIndex") == b.get("dayIndex", 0) + 1:
            nxt = bb
            break
    if nxt is None:
        nxt = new_day(l, b.get("dayIndex", 0) + 1)
        if nxt is not None:
            board.append(nxt)

    if nxt is None:
        b["tasks"] = to_next + to_extra
        b["done"] = False
        return added, 0, len(b["tasks"]), 0

    have = {t.get("id") for t in nxt.get("tasks", [])}
    moved = 0
    for c in to_next:
        if c.get("id") not in have:
            nxt["tasks"].append(make_task(c, carry=True))
            have.add(c.get("id"))
            moved += 1

    # 超出上限的再顺延到末尾补做日
    extra_n = _push_to_extra(l, to_extra) if to_extra else 0
    _reflow_extra(l)          # 补做日始终排在最后一个普通天之后

    b["tasks"] = []
    b["done"] = True
    b["deficit"] = moved
    b["completed"] = added
    if moved:
        nxt["done"] = False
    return added, moved, 0, extra_n


def do_expand(l):
    board = l.get("board", [])
    if not board:
        d0 = new_day(l, 0)
        if d0 is None:
            return False
        l["board"] = [d0]
        return True
    # 只看普通天：补做日的序号在末尾，不能用它来推算下一个计划天
    nxt_i = max(b.get("dayIndex", 0) for b in board if not b.get("extra")) + 1
    nxt = new_day(l, nxt_i)
    if nxt is None:
        return False
    board.append(nxt)
    _reflow_extra(l)          # 新天插进来后，补做日继续往后顺延
    return True


def do_reset_day(l, di):
    board = l.get("board", [])
    if not (0 <= di < len(board)):
        return False
    fresh = new_day(l, board[di].get("dayIndex", 0))
    if fresh is None:
        return False
    fresh["deficit"] = 0
    board[di] = fresh
    return True


def do_reset_plan(p, l, mode="progress"):
    """重置计划（只影响当前题单，其它题单不受影响）

    mode='progress'：清空完成记录与已展开的天，保留计划设置（总题数 / 每天题数），
                     起始日改回今天，重新排第一天。
    mode='all'     ：在上面基础上把计划设置也恢复默认（limit / perDay），
                     并回到首次使用的初始化向导（setupDone=False）。

    提醒时段属于个人偏好，两种模式都保留。
    """
    l["done"] = []
    l["pool"] = []
    l["board"] = []
    l["startDate"] = datetime.date.today().isoformat()
    if mode == "all":
        l["limit"] = None
        l["perDay"] = 4
        p["setupDone"] = False
    ensure_board(l)
    return True


def do_set_paused(l, pause):
    """暂停 / 继续计划（只影响当前题单）

    - 暂停期间的日子**不算空缺**，日历不标红；已完成记录原样保留。
    - 继续之后，结束日期仍按「剩余题数 ÷ 每天题数」从今天往后算，等于自动顺延。
    - 每次暂停记成一段 {from, to} 区间，多次暂停互不覆盖，日历可还原哪几天是暂停的。

    返回 True 表示状态确实变了（没变就不用存盘）。
    """
    today = datetime.date.today().isoformat()
    segs = [s for s in (l.get("pauses") or []) if isinstance(s, dict)]
    cur = bool(l.get("paused"))

    if pause and not cur:
        l["paused"] = True
        segs.append({"from": today, "to": None})
        l["pauses"] = segs
        return True

    if (not pause) and cur:
        l["paused"] = False
        for s in reversed(segs):
            if s.get("to") is None:
                s["to"] = today
                break
        l["pauses"] = segs
        return True

    return False


def do_restart_round(l):
    """重新开启一轮（再来一遍这个计划）

    跟「重置进度」的区别：**本轮的记录会归档保留**，不是清空。
    归档后进 `l["rounds"]`，当前进度清零、从今天重新排第一天。

    归档记录不参与当前轮的统计与日历（否则一开轮就显示「全做完了」），
    但可以在「往期轮次」里回看每轮做了多少题、什么时候做的。
    """
    today = datetime.date.today().isoformat()
    dl = done_list(l)

    if dl:                                   # 有记录才值得归档
        rounds = [r for r in (l.get("rounds") or []) if isinstance(r, dict)]
        dates = [d["date"] for d in dl if d.get("date")]
        rounds.append({
            "no": len(rounds) + 1,
            "from": min(dates) if dates else (l.get("startDate") or today),
            "to": max(dates) if dates else today,
            "count": len(dl),
            "done": [{"id": d["id"], "date": d.get("date") or "",
                      "pre": bool(d.get("pre"))} for d in dl],
        })
        l["rounds"] = rounds

    l["done"] = []
    l["board"] = []
    l["pauses"] = []
    l["paused"] = False
    l["startDate"] = today
    ensure_board(l)
    return True


def do_undo(p):
    prev = pop_history()
    return prev


# ============ 题单管理 ============

def slugify(name, existing):
    s = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fa5]+", "-", str(name)).strip("-").lower()
    if not s:
        s = "list"
    key, i = s, 1
    while key in existing:
        i += 1
        key = "%s-%d" % (s, i)
    return key


# ---- 力扣题单 URL 导入 ----
# 官方 GraphQL 端点；favoriteQuestionList 支持公开题单（problem-list/<slug>）
LC_GQL = "https://leetcode.cn/graphql/"
LC_HDR = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Origin": "https://leetcode.cn",
    "Referer": "https://leetcode.cn/",
}
LC_QUERY = """
query favoriteQuestionList($favoriteSlug: String!, $limit: Int, $skip: Int) {
  favoriteQuestionList(favoriteSlug: $favoriteSlug, limit: $limit, skip: $skip) {
    totalLength
    hasMore
    questions {
      questionFrontendId
      title
      titleSlug
      difficulty
      paidOnly
      topicTags { name }
    }
  }
}
"""

# 考点标签中英映射（力扣返回英文）
TAG_CN = {
    "Array": "数组", "String": "字符串", "Hash Table": "哈希表", "Math": "数学",
    "Dynamic Programming": "动态规划", "Sorting": "排序", "Greedy": "贪心",
    "Depth-First Search": "深度优先搜索", "Breadth-First Search": "广度优先搜索",
    "Binary Search": "二分查找", "Two Pointers": "双指针", "Stack": "栈",
    "Queue": "队列", "Linked List": "链表", "Tree": "树", "Binary Tree": "二叉树",
    "Binary Search Tree": "二叉搜索树", "Matrix": "矩阵", "Simulation": "模拟",
    "Backtracking": "回溯", "Divide and Conquer": "分治", "Heap (Priority Queue)": "堆",
    "Bit Manipulation": "位运算", "Recursion": "递归", "Memoization": "记忆化",
    "Sliding Window": "滑动窗口", "Prefix Sum": "前缀和", "Design": "设计",
    "Graph": "图", "Union Find": "并查集", "Trie": "字典树", "Monotonic Stack": "单调栈",
    "Monotonic Queue": "单调队列", "Topological Sort": "拓扑排序",
    "Quickselect": "快速选择", "Counting": "计数", "Merge Sort": "归并排序",
    "Ordered Set": "有序集合", "Binary Indexed Tree": "树状数组",
    "Segment Tree": "线段树", "Data Stream": "数据流", "Doubly-Linked List": "双向链表",
    "Probability and Statistics": "概率统计", "Enumeration": "枚举",
    "Brainteaser": "脑筋急转弯", "Binary Lifting": "倍增", "Iterator": "迭代器",
    "Number Theory": "数论", "Geometry": "几何", "Game Theory": "博弈",
    "Database": "数据库", "String Matching": "字符串匹配",
    "Rolling Hash": "滚动哈希", "Hash Function": "哈希函数",
    "Shortest Path": "最短路", "Minimum Spanning Tree": "最小生成树",
    "Bucket Sort": "桶排序", "Radix Sort": "基数排序", "Shell": "Shell",
    "Concurrency": "并发", "Randomized": "随机化", "Reservoir Sampling": "蓄水池抽样",
}


def tag_to_cn(name):
    return TAG_CN.get(name, name)


def parse_lc_url(url):
    """从力扣题单链接里提取 slug
    支持：
      https://leetcode.cn/problem-list/8LSpuXqD/
      https://leetcode.cn/problem-list/8LSpuXqD
      https://leetcode-cn.com/problem-list/xxxx/
    """
    s = str(url or "").strip()
    m = re.search(r"problem-list/([A-Za-z0-9_-]+)", s)
    if m:
        return m.group(1)
    # 也允许用户直接粘 slug
    if re.fullmatch(r"[A-Za-z0-9_-]{4,40}", s):
        return s
    return None


_lc_cache = {}          # slug -> (timestamp, problems)
LC_CACHE_TTL = 600      # 缓存 10 分钟


def fetch_lc_list(slug, max_n=400, use_cache=True):
    """调力扣 GraphQL 拉题单（用 Playwright 绕过反爬虫）。返回 (problems, err)"""
    now = time.time()
    if use_cache and slug in _lc_cache:
        ts, cached = _lc_cache[slug]
        if now - ts < LC_CACHE_TTL:
            return cached, None

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, "Playwright 未安装，无法导入力扣题单"

    out, skip = [], 0
    page_size = 100
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled",
                      "--no-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = browser.new_context(
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
                locale="zh-CN",
            )
            page = ctx.new_page()
            # 直接打开题单页：页面本身稳定，不会像首页那样被 SPA 路由重建
            page.goto("https://leetcode.cn/problem-list/%s/" % slug,
                      wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1200)

            while skip < max_n:
                result = page.evaluate("""async (params) => {
                    const resp = await fetch('https://leetcode.cn/graphql/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                        },
                        body: JSON.stringify({
                            query: params.query,
                            variables: params.vars,
                            operationName: 'favoriteQuestionList',
                        }),
                    });
                    return await resp.json();
                }""", {"query": LC_QUERY, "vars": {"favoriteSlug": slug, "limit": page_size, "skip": skip}})

                if result.get("errors"):
                    msg = result["errors"][0].get("message", "未知错误")
                    browser.close()
                    return None, "力扣返回错误：%s" % msg

                node = (result.get("data") or {}).get("favoriteQuestionList")
                if not node:
                    browser.close()
                    return None, "题单不存在或未公开"

                qs = node.get("questions") or []
                if not qs:
                    break
                for q in qs:
                    fid = q.get("questionFrontendId") or ""
                    tags = [tag_to_cn(t.get("name", "")) for t in (q.get("topicTags") or [])]
                    out.append({
                        "id": fid,
                        "name": q.get("title") or "",
                        "difficulty": (q.get("difficulty") or "medium").lower(),
                        "hint": " / ".join(tags[:3]),
                        "slug": q.get("titleSlug") or "",
                    })
                skip += len(qs)
                if not node.get("hasMore"):
                    break

            browser.close()
    except Exception as e:
        return None, "Playwright 请求失败：%s" % e

    if not out:
        return None, "这个题单里没有题目"
    _lc_cache[slug] = (now, out)
    return out, None


def group_by_tag(problems):
    """按考点标签分组（取每题的第一个标签作为分类）"""
    order, buckets = [], {}
    for p in problems:
        tags = [t for t in (p.get("hint") or "").split(" / ") if t]
        cat = tags[0] if tags else "其他"
        if cat not in buckets:
            buckets[cat] = []
            order.append(cat)
        buckets[cat].append({
            "id": p["id"],
            "name": p["name"],
            "difficulty": p["difficulty"],
            "hint": " / ".join(tags[1:3]) if len(tags) > 1 else "",
        })
    return [{"name": c, "problems": buckets[c]} for c in order]


def do_import_url(p, data):
    """从力扣题单 URL 导入为新题单"""
    url = data.get("url", "")
    slug = parse_lc_url(url)
    if not slug:
        return None, "链接格式不对，应形如 https://leetcode.cn/problem-list/xxxxxx/"
    name = str(data.get("name", "")).strip()
    # 同一个链接只导一次，避免重复
    src = "https://leetcode.cn/problem-list/%s/" % slug
    for k, v in (p.get("lists") or {}).items():
        if v.get("source") == src:
            return None, "这个题单已经导入过了（%s）" % v.get("name", k)
    problems, err = fetch_lc_list(slug)
    if err:
        return None, err
    if not name:
        name = "力扣题单 " + slug
    try:
        per = max(1, min(50, int(data.get("perDay", 4))))
    except Exception:
        per = 4
    mode = data.get("group", "tag")   # tag=按考点分组 / none=不分
    if mode == "none":
        cats = [{"name": "全部题目", "problems": [
            {"id": x["id"], "name": x["name"], "difficulty": x["difficulty"],
             "hint": x["hint"]} for x in problems]}]
    else:
        cats = group_by_tag(problems)

    key = slugify(data.get("key") or name, set(p.get("lists", {}).keys()))
    p.setdefault("lists", {})[key] = {
        "name": name,
        "startDate": datetime.date.today().isoformat(),
        "perDay": per,
        "limit": None,
        "categories": cats,
        "pool": [],
        "done": [],
        "board": [],
        "source": "https://leetcode.cn/problem-list/%s/" % slug,
    }
    p["activeList"] = key
    return {"key": key, "count": len(problems), "name": name, "groups": len(cats)}, None


def parse_list_text(raw):
    """解析用户输入的题单文本
    规则：
      - 一行只有文字（不含题号）→ 分类名
      - 一行以数字开头 → 题目：「题号 题名 [难度]」
      - 用 | 或 , 或 Tab 分隔也可以
    """
    cats, cur = [], None
    for line in str(raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(\d+)[\s|,，\t]+(.+)$", line)
        if m:
            pid = int(m.group(1))
            rest = m.group(2).strip()
            diff = "medium"
            # 末尾难度词
            mm = re.search(r"[\s|,，\t]+(简单|中等|困难|easy|medium|hard)\s*$", rest, re.I)
            if mm:
                diff = CN_DIFF.get(mm.group(1).lower(), CN_DIFF.get(mm.group(1), "medium"))
                rest = rest[:mm.start()].strip()
            if cur is None:
                cur = {"name": "默认分类", "problems": []}
                cats.append(cur)
            cur["problems"].append({"id": pid, "name": rest,
                                    "difficulty": diff, "hint": ""})
        else:
            cur = {"name": line, "problems": []}
            cats.append(cur)
    return [c for c in cats if c["problems"]]


def do_newlist(p, data):
    name = str(data.get("name", "")).strip() or "新题单"
    raw = data.get("raw", "")
    cats = parse_list_text(raw)
    if not cats:
        return None, "没解析到题目，请按「题号 题名 难度」每行一道"
    key = slugify(data.get("key") or name, set(p.get("lists", {}).keys()))
    try:
        per = max(1, min(20, int(data.get("perDay", 4))))
    except Exception:
        per = 4
    p.setdefault("lists", {})[key] = {
        "name": name,
        "startDate": datetime.date.today().isoformat(),
        "perDay": per,
        "categories": cats,
        "pool": [],
        "done": [],
        "board": [],
    }
    p["activeList"] = key
    return key, None


def do_dellist(p, key):
    lists = p.get("lists", {})
    if key not in lists:
        return False, "题单不存在"
    if len(lists) <= 1:
        return False, "至少要保留一个题单"
    del lists[key]
    if p.get("activeList") == key:
        p["activeList"] = sorted(lists.keys())[0]
    return True, None


def do_switch(p, key):
    if key not in p.get("lists", {}):
        return False
    p["activeList"] = key
    ensure_board(p["lists"][key])
    return True


def do_rename(p, key, name):
    l = p.get("lists", {}).get(key)
    if l is None or not str(name).strip():
        return False
    l["name"] = str(name).strip()
    return True


def do_setperday(p, key, n):
    l = p.get("lists", {}).get(key)
    if l is None:
        return False
    try:
        l["perDay"] = max(1, min(20, int(n)))
    except Exception:
        return False
    return True


def do_setstart(p, key, date):
    l = p.get("lists", {}).get(key)
    if l is None:
        return False
    try:
        datetime.date.fromisoformat(date)
    except Exception:
        return False
    l["startDate"] = date
    return True


# ============ 提醒 ============

def send_toast(title, body):
    ps = os.path.join(BASE, "toast.ps1")
    if not os.path.isfile(ps):
        return False
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", ps, "-Title", title, "-Body", body],
            creationflags=flags, timeout=30,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def today_summary(p):
    l = get_list(p)
    if l is None:
        return 0, 0, []
    board = l.get("board", [])
    if not board:
        return 0, 0, []
    b = board[-1]
    tasks = b.get("tasks", [])
    total = len(tasks)
    done = sum(1 for t in tasks if t.get("checked"))
    names = [t.get("name", "") for t in tasks if not t.get("checked")]
    return done, total, names


def do_remind_config(p, data):
    r = ensure_reminders(p)
    if "enabled" in data:
        r["enabled"] = bool(data.get("enabled"))
    slots = data.get("slots")
    if isinstance(slots, list):
        clean = []
        for s in slots:
            if not isinstance(s, dict):
                continue
            t = str(s.get("time", "")).strip()
            try:
                hh, mm = t.split(":")
                if 0 <= int(hh) <= 23 and 0 <= int(mm) <= 59:
                    clean.append({"time": "%02d:%02d" % (int(hh), int(mm)),
                                  "label": str(s.get("label", "提醒")).strip() or "提醒"})
            except Exception:
                continue
        clean.sort(key=lambda x: x["time"])
        r["slots"] = clean
    return r


def reminder_worker():
    while True:
        try:
            now = datetime.datetime.now()
            hm = now.strftime("%H:%M")
            today = now.date().isoformat()
            with _lock:
                p = ensure_root(load_plan())
                r = ensure_reminders(p)
                if r.get("enabled"):
                    for slot in r.get("slots", []):
                        st = str(slot.get("time", "")).strip()
                        if st != hm or r["lastFired"].get(st) == today:
                            continue
                        done, total, names = today_summary(p)
                        left = total - done
                        l = get_list(p)
                        lname = l.get("name", "刷题") if l else "刷题"
                        if total == 0:
                            body = "今天的题都清完了，休息一下 🎉"
                        elif left == 0:
                            body = "今天的 %d 题已全部勾选，记得点「确定完成」" % total
                        else:
                            tip = "、".join(names[:3])
                            if len(names) > 3:
                                tip += " 等"
                            body = "还剩 %d 题：%s" % (left, tip)
                        r["lastFired"][st] = today
                        save_plan(p)
                        send_toast("%s · %s" % (lname, slot.get("label", "提醒")), body)
                        break
        except Exception:
            pass
        time.sleep(20)


# ============ 导出 ============

def export_payload(p):
    l = get_list(p) or {"categories": [], "pool": [], "done": [], "board": []}
    idmap = {}
    for cn, t in flat_problems(l):
        idmap[t.get("id")] = t
    for t in l.get("pool", []):
        idmap.setdefault(t.get("id"), t)

    records = []
    for d in done_list(l):
        t = idmap.get(d["id"]) or {}
        if d.get("pre"):
            src = "之前做过"
        elif d.get("swapped"):
            src = "换题补记（历史）"
        else:
            src = "当天完成"
        records.append({
            "题号": d["id"],
            "题目": t.get("name", ""),
            "难度": DIFF_CN.get(t.get("difficulty", ""), ""),
            "完成日期": d.get("date", ""),
            "标记来源": src,
        })
    return {
        "题单": l.get("name", ""),
        "导出时间": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "目标题数": total_problems(l),
        "已完成": len(done_list(l)),
        "其中之前做过": sum(1 for d in done_list(l) if d.get("pre")),
        "开始日期": l.get("startDate", ""),
        "统计": {"每日做题量": daily_counts(l), "周视图": weekly_view(l)},
        "明细": records,
    }


def export_csv(payload):
    rows = payload.get("明细", [])
    cols = ["题号", "题目", "难度", "完成日期", "是否换题补记"]
    lines = [",".join(cols)]
    for r in rows:
        vals = []
        for c in cols:
            v = str(r.get(c, "")).replace('"', '""')
            vals.append('"%s"' % v)
        lines.append(",".join(vals))
    return "\n".join(lines) + "\n"


# ============ HTTP ============

STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
}
ALLOWED_STATIC = {"ui.html", "app.js"}
ALLOWED_DIRS = ("assets",)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, "application/json; charset=utf-8",
                   json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def _download(self, body, ctype, filename):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Disposition",
                         'attachment; filename="%s"' % filename)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, name):
        """只放行白名单文件 + assets 目录下的图片，不开放目录遍历"""
        rel = name.replace("\\", "/").lstrip("/")
        if ".." in rel.split("/"):
            self._send(404, "text/plain; charset=utf-8", b"not found")
            return
        if rel in ALLOWED_STATIC:
            path = os.path.join(BASE, rel)
        else:
            parts = rel.split("/")
            if len(parts) == 2 and parts[0] in ALLOWED_DIRS:
                path = os.path.join(BASE, parts[0], os.path.basename(parts[1]))
            else:
                self._send(404, "text/plain; charset=utf-8", b"not found")
                return
        if not os.path.isfile(path):
            self._send(404, "text/plain; charset=utf-8", b"not found")
            return
        ext = os.path.splitext(path)[1].lower()
        ctype = STATIC_TYPES.get(ext, "application/octet-stream")
        with open(path, "rb") as f:
            self._send(200, ctype, f.read())

    def do_GET(self):
        path = self.path.split("?")[0]
        if path.startswith("/api/state"):
            with _lock:
                p = ensure_root(load_plan())
                l = get_list(p)
                if l is not None:
                    ensure_board(l)
                save_plan(p)
                self._json(state_view(p))
        elif path.startswith("/api/export"):
            with _lock:
                p = ensure_root(load_plan())
                payload = export_payload(p)
            qs = parse_qs(urlparse(self.path).query)
            fmt = (qs.get("fmt", ["json"])[0] or "json").lower()
            if fmt == "csv":
                self._download(export_csv(payload).encode("utf-8-sig"),
                               "text/csv; charset=utf-8", "leetcode-progress.csv")
            else:
                self._download(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
                               "application/json; charset=utf-8", "leetcode-progress.json")
        elif path in ("/", "/index", "/index.html"):
            self._serve_file("ui.html")
        elif path == "/favicon.ico":
            self._send(204, "image/x-icon", b"")
        else:
            self._serve_file(path.lstrip("/"))

    def do_POST(self):
        ln = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(ln) if ln else b"{}"
        try:
            data = json.loads(raw or b"{}")
        except Exception:
            data = {}
        with _lock:
            p = ensure_root(load_plan())
            path = self.path.split("?")[0]
            di = int(data.get("day", -1))
            ti = int(data.get("index", -1))
            l = get_list(p)

            # 撤销
            if path.startswith("/api/undo"):
                prev = do_undo(p)
                if prev is None:
                    self._json({"ok": False, "msg": "没有可撤销的操作",
                                "state": state_view(p)})
                    return
                prev = ensure_root(prev)
                save_plan(prev)
                self._json({"ok": True, "state": state_view(prev)})
                return

            # 题单管理（不需要题单上下文）
            if path.startswith("/api/switch"):
                push_history(p)
                ok = do_switch(p, data.get("key", ""))
                save_plan(p)
                self._json({"ok": ok, "state": state_view(p)})
                return
            if path.startswith("/api/newlist"):
                push_history(p)
                key, err = do_newlist(p, data)
                if err:
                    _history.pop()
                    self._json({"ok": False, "msg": err, "state": state_view(p)})
                    return
                l = get_list(p)
                ensure_board(l)
                save_plan(p)
                self._json({"ok": True, "key": key, "state": state_view(p)})
                return
            if path.startswith("/api/importurlsave"):
                push_history(p)
                info, err = do_import_url(p, data)
                if err:
                    _history.pop()
                    self._json({"ok": False, "msg": err, "state": state_view(p)})
                    return
                l = get_list(p)
                ensure_board(l)
                save_plan(p)
                self._json({"ok": True, "info": info, "state": state_view(p)})
                return
            if path.startswith("/api/importurl"):
                # 仅预览：不写盘
                slug = parse_lc_url(data.get("url", ""))
                if not slug:
                    self._json({"ok": False, "msg": "链接格式不对，应形如 "
                                "https://leetcode.cn/problem-list/xxxxxx/"})
                    return
                probs, err = fetch_lc_list(slug)
                if err:
                    self._json({"ok": False, "msg": err})
                    return
                cats = group_by_tag(probs)
                self._json({"ok": True, "slug": slug, "count": len(probs),
                            "groups": len(cats),
                            "preview": [{"name": c["name"], "count": len(c["problems"])}
                                        for c in cats],
                            "sample": [{"id": x["id"], "name": x["name"],
                                        "difficulty": x["difficulty"]}
                                       for x in probs[:5]]})
                return
            if path.startswith("/api/dellist"):
                push_history(p)
                ok, err = do_dellist(p, data.get("key", ""))
                if not ok:
                    _history.pop()
                    self._json({"ok": False, "msg": err, "state": state_view(p)})
                    return
                l = get_list(p)
                ensure_board(l)
                save_plan(p)
                self._json({"ok": True, "state": state_view(p)})
                return
            if path.startswith("/api/rename"):
                push_history(p)
                ok = do_rename(p, data.get("key", ""), data.get("name", ""))
                save_plan(p)
                self._json({"ok": ok, "state": state_view(p)})
                return
            if path.startswith("/api/setperday"):
                push_history(p)
                ok = do_setperday(p, data.get("key", ""), data.get("n", 4))
                save_plan(p)
                self._json({"ok": ok, "state": state_view(p)})
                return
            if path.startswith("/api/setplan"):
                if l is None:
                    self._json({"ok": False, "msg": "没有可用题单"}, 400)
                    return
                push_history(p)
                ok, msg, reset = do_setplan(l, data)
                if not ok:
                    _history.pop()
                    self._json({"ok": False, "msg": msg, "state": state_view(p)})
                    return
                if data.get("markSetup"):
                    p["setupDone"] = True
                save_plan(p)
                self._json({"ok": True, "reset": reset, "state": state_view(p)})
                return
            if path.startswith("/api/pauseplan"):
                if l is None:
                    self._json({"ok": False, "msg": "没有可用题单"}, 400)
                    return
                pause = bool(data.get("pause", True))
                push_history(p)          # 暂停/继续也能撤销
                if not do_set_paused(l, pause):
                    _history.pop()       # 状态没变就不留撤销点
                save_plan(p)
                self._json({"ok": True, "state": state_view(p)})
                return
            if path.startswith("/api/restartplan"):
                if l is None:
                    self._json({"ok": False, "msg": "没有可用题单"}, 400)
                    return
                push_history(p)          # 归档 + 重开也能撤销
                do_restart_round(l)
                save_plan(p)
                self._json({"ok": True, "state": state_view(p)})
                return
            if path.startswith("/api/resetplan"):
                if l is None:
                    self._json({"ok": False, "msg": "没有可用题单"}, 400)
                    return
                mode = data.get("mode", "progress")
                if mode not in ("progress", "all"):
                    self._json({"ok": False, "msg": "mode 只能是 progress / all"}, 400)
                    return
                push_history(p)          # 留撤销点，误点了还能撤回
                do_reset_plan(p, l, mode)
                save_plan(p)
                self._json({"ok": True, "state": state_view(p)})
                return
            if path.startswith("/api/welcomeskip"):
                push_history(p)
                p["setupDone"] = True
                save_plan(p)
                self._json({"ok": True, "state": state_view(p)})
                return
            if path.startswith("/api/welcomereset"):
                push_history(p)
                p["setupDone"] = False
                save_plan(p)
                self._json({"ok": True, "state": state_view(p)})
                return
            if path.startswith("/api/remind"):
                push_history(p)
                do_remind_config(p, data)
                save_plan(p)
                self._json({"ok": True, "state": state_view(p)})
                return
            if path.startswith("/api/testremind"):
                done, total, names = today_summary(p)
                left = total - done
                lname = l.get("name", "刷题") if l else "刷题"
                if total == 0:
                    body = "今天的题都清完了 🎉"
                elif left == 0:
                    body = "今天的 %d 题已全部勾选" % total
                else:
                    body = "还剩 %d 题：%s" % (left, "、".join(names[:3]))
                ok = send_toast("%s · 测试提醒" % lname, body)
                self._json({"ok": ok, "body": body})
                return

            # 以下操作需要当前题单
            if l is None:
                self._json({"ok": False, "msg": "没有可用题单"}, 400)
                return

            push_history(p)
            if path.startswith("/api/toggle"):
                ok = do_toggle(l, di, ti)
                save_plan(p)
                self._json({"ok": ok, "state": state_view(p)})
            elif path.startswith("/api/markpre"):
                ok, err = do_mark_pre(l, di, ti)
                if not ok:
                    _history.pop()
                save_plan(p)
                self._json({"ok": ok, "err": err, "state": state_view(p)})
            elif path.startswith("/api/unmarkpre"):
                ok, err = do_unmark_pre(l, int(data.get("id", -1)))
                if not ok:
                    _history.pop()
                save_plan(p)
                self._json({"ok": ok, "err": err, "state": state_view(p)})
            elif path.startswith("/api/swap"):
                ok, err = do_swap(p, l, di, ti)
                if not ok:
                    _history.pop()          # 没改动就不留撤销点
                save_plan(p)
                self._json({"ok": ok, "err": err, "state": state_view(p)})
            elif path.startswith("/api/add"):
                n, err = do_add(p, l, di, int(data.get("n", 1)))
                if n <= 0:
                    _history.pop()
                save_plan(p)
                self._json({"ok": n > 0, "added": n, "err": err,
                            "state": state_view(p)})
            elif path.startswith("/api/submit"):
                added, carried, remain, extra_n = do_submit(l, di)
                save_plan(p)
                self._json({"ok": True, "added": added, "carried": carried,
                            "remain": remain, "extra": extra_n, "state": state_view(p)})
            elif path.startswith("/api/resetday"):
                ok = do_reset_day(l, di)
                save_plan(p)
                self._json({"ok": ok, "state": state_view(p)})
            elif path.startswith("/api/expand"):
                ok = do_expand(l)
                save_plan(p)
                self._json({"ok": ok, "state": state_view(p)})
            else:
                _history.pop()
                self._json({"ok": False}, 404)


def ensure_plan_file():
    """首次运行：没有 plan.json 就用 plan.example.json 模板建一份。

    换了机器 / 删了数据 / 第一次 clone 下来直接跑，都靠这一步兜底。
    """
    if os.path.isfile(PLAN_PATH):
        return
    tpl = os.path.join(BASE, "plan.example.json")
    try:
        if os.path.isfile(tpl):
            with open(tpl, "r", encoding="utf-8") as f:
                p = json.load(f)
        else:                                   # 连模板都没有：建一个最小骨架
            p = {"activeList": "lc100", "setupDone": False,
                 "reminders": {"enabled": False, "slots": [], "lastFired": {}},
                 "lists": {"lc100": {"name": "LeetCode 100", "startDate":
                                     datetime.date.today().isoformat(),
                                     "perDay": 4, "categories": []}}}
        d = os.path.dirname(PLAN_PATH)
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        with open(PLAN_PATH, "w", encoding="utf-8") as f:
            json.dump(p, f, ensure_ascii=False, indent=2)
        print("plan.json not found -> initialized from template", flush=True)
    except Exception as e:
        print("init plan.json failed: %s" % e, flush=True)


def main():
    ensure_plan_file()
    with _lock:
        p = ensure_root(load_plan())
        l = get_list(p)
        if l is not None:
            ensure_board(l)
        save_plan(p)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    srv.daemon_threads = True
    t = threading.Thread(target=reminder_worker, daemon=True)
    t.start()
    print("leetcode board on http://127.0.0.1:%d" % PORT, flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
