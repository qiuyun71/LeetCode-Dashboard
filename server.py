# -*- coding: utf-8 -*-
"""力扣刷题看板 · 本地服务（后端）
浏览器打开 http://127.0.0.1:8765     界面在 ui.html

数据结构（plan.json）：
{
  "activeList": "lc100",
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
import html
import json
import os
import random
import re
import datetime
import shutil
import sys
import tempfile
import threading
import subprocess
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode

BASE = os.path.dirname(os.path.abspath(__file__))
# 测试时用 LEET_PLAN / LEET_PORT 指向副本，避免脚本动到真实 plan.json
PLAN_PATH = os.environ.get("LEET_PLAN") or os.path.join(BASE, "plan.json")
UI_PATH = os.path.join(BASE, "ui.html")
PORT = int(os.environ.get("LEET_PORT") or 8765)
_lock = threading.Lock()

# 撤销栈：每次写操作前压入快照，最多保留 30 步
_history = []
HIST_MAX = 30
_last_saved = ""        # 最近一次落盘内容的内存快照，can_undo 用它免读文件

DIFF_CN = {"easy": "简单", "medium": "中等", "hard": "困难"}


# ============ 基础读写 ============

def load_plan():
    try:
        with open(PLAN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        # 文件损坏（多半是手工编辑出错）：备份坏文件后重新初始化，看板不至于白屏
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        bad = "%s.broken-%s" % (PLAN_PATH, ts)
        try:
            os.replace(PLAN_PATH, bad)
            print("plan.json 损坏（%s），已备份为 %s 并重新初始化" % (e, bad), flush=True)
        except Exception:
            pass
        ensure_plan_file()
        with open(PLAN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        ensure_plan_file()
        with open(PLAN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)


def save_plan(p):
    global _last_saved
    tmp = PLAN_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PLAN_PATH)
    _last_saved = json.dumps(p, ensure_ascii=False)


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
    return _history[-1] != _last_saved


# ============ 题单结构 ============

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
        p = {"activeList": "lc100",
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


# ============ 错题本 / 经典题标记 ============
# marks: { 题号(str): {"kind": "classic"|"wrong", "at": "日期", "note": "备注"} }
MARK_KINDS = {"classic": "经典", "wrong": "错题"}


def _pid_key(pid):
    """题号统一按字符串处理

    plan.json 里所有 id 都是字符串（"1" / "LCR 001"），board 任务、done 记录
    同理。历史上 marks_view 把 key int() 过，于是字符串 id 永远匹配不上 marks
    （"66" !== 66），标记按钮因此死活不亮；剑指那种 "LCR 001" 更是 int() 失败
    被整条跳过。所有 id 相关比较都走这里，别再混用 int / str。
    """
    if pid is None:
        return None
    s = str(pid).strip()
    return s or None


def _norm_mark(m):
    """归一一条 marks 记录 -> {"classic":bool,"wrong":bool,"at","note"}

    兼容旧格式 {"kind":"wrong"}：以前一题只能有一种标记，现在可以同时是
    经典和错题，所以拆成两个布尔位。
    """
    if not isinstance(m, dict):
        return None
    c = bool(m.get("classic"))
    w = bool(m.get("wrong"))
    if not (c or w) and m.get("kind") in MARK_KINDS:
        if m["kind"] == "classic":
            c = True
        else:
            w = True
    return {"classic": c, "wrong": w,
            "at": m.get("at") or "", "note": m.get("note") or ""}


def marks_view(l):
    """错题本视图：一题一条，classic / wrong 可同时为真"""
    idmap = {}
    for cn, t in flat_problems(l):
        x = dict(t)
        x["category"] = cn                # 分类名只在展平时带着，这里补回题目体
        idmap[_pid_key(t.get("id"))] = x
    for t in l.get("pool", []):
        x = dict(t)
        x.setdefault("category", "")
        idmap.setdefault(_pid_key(t.get("id")), x)

    done_ids = {str(d.get("id")) for d in done_list(l)}
    out = []
    for pid, m in (l.get("marks") or {}).items():
        key = _pid_key(pid)
        nm = _norm_mark(m)
        if key is None or nm is None:
            continue                      # 脏数据直接跳过
        if not (nm["classic"] or nm["wrong"]):
            continue                      # 两类都空的空壳条目
        t = idmap.get(key) or {}
        kinds = [k for k in ("wrong", "classic") if nm[k]]   # 错题排前
        out.append({
            "id": key,
            "name": t.get("name") or ("题 %s" % key),
            "difficulty": t.get("difficulty") or "easy",
            "category": t.get("category") or "",
            "hint": t.get("hint") or "",
            "classic": nm["classic"],
            "wrong": nm["wrong"],
            "kinds": kinds,
            "kind": kinds[0],             # 兼容旧字段：主类型
            "kindLabel": MARK_KINDS[kinds[0]],
            "at": nm["at"],
            "note": nm["note"],
            "done": key in done_ids,      # 有没有做出来过
        })
    # 错题在前、其次经典；同组按标记日期倒序
    order = {"wrong": 0, "classic": 1}
    out.sort(key=lambda x: x["at"] or "", reverse=True)
    out.sort(key=lambda x: order.get(x["kind"], 9))
    return out


def marks_stats(items):
    """错题本统计：总数 / 分类分布 / 难度分布 / 做出来过多少"""
    by_diff = {"easy": 0, "medium": 0, "hard": 0}
    by_cat = {}
    done_n = 0
    for m in items:
        d = m.get("difficulty")
        if d in by_diff:
            by_diff[d] += 1
        cn = m.get("category") or "未分类"
        by_cat[cn] = by_cat.get(cn, 0) + 1
        if m.get("done"):
            done_n += 1
    top = sorted(by_cat.items(), key=lambda kv: -kv[1])[:8]
    # 一题一条：total 是题数（不是标记数），classic / wrong 各自数（可重叠）
    return {
        "total": len(items),
        "classic": sum(1 for m in items if m.get("classic")),
        "wrong": sum(1 for m in items if m.get("wrong")),
        "solved": done_n,
        "byDiff": by_diff,
        "topCat": [{"name": k, "n": v} for k, v in top],
    }


def do_mark(l, pid, kind=None, note=None, on=None, clear=False):
    """标记 / 取消标记。一题可以同时是「经典」又是「错题」，两类互不干扰。

    kind  = "classic" | "wrong"   置这一类标记（on=False 表示只关掉这一类）
    note  = 字符串                只改备注，不动标记
    clear = True                  两类标记全取消（错题本列表里的 × 按钮）

    marks 结构（按题号一条，id 是字符串）：
      {"classic": true, "wrong": false, "at": "2026-10-09", "note": ""}
    两类都为假时把这一条删掉，不留空壳。
    """
    key = _pid_key(pid)
    if key is None:
        return False, "bad_id"
    marks = l.setdefault("marks", {})
    if clear:
        marks.pop(key, None)
        return True, None
    if note is not None:
        cur = _norm_mark(marks.get(key))
        if cur is not None and (cur["classic"] or cur["wrong"]):
            cur["note"] = str(note)[:200]
            cur.setdefault("at", datetime.date.today().isoformat())
            marks[key] = cur
        return True, None
    if kind not in MARK_KINDS:
        return False, "bad_kind"
    cur = _norm_mark(marks.get(key)) or {"classic": False, "wrong": False,
                                         "at": "", "note": ""}
    val = True if on is None else bool(on)
    cur[kind] = val
    if not (cur["classic"] or cur["wrong"]):
        marks.pop(key, None)             # 两类都没了，条目直接删掉
        return True, None
    if val and not cur["at"]:
        cur["at"] = datetime.date.today().isoformat()
    marks[key] = cur
    return True, None


def plan_view(l):
    """计划概览：总题数 / 每天题数 / 总天数 / 起止日期

    总天数（days）= 原计划天数 + 补做日天数 - 已提前做掉的天数：
      · 欠账超出「当天上限」（每天题数×2）顺延出去的补做日挂在原计划
        最后一天之后，计划随之 +1 天（25 天变 26 天）；
      · 提前把后面的题做掉（如一天做完两天的量），计划相应缩短，
        总天数变少、结束日期提前——日历上那些天标薄荷青「提前完成」。
    结束日期不早于名义结束日：落后 / 暂停过，就按剩余题数从今天往后顺延。
    """
    total = total_problems(l)
    per = max(1, int(l.get("perDay", 4) or 4))
    start = l.get("startDate") or datetime.date.today().isoformat()
    try:
        d0 = datetime.date.fromisoformat(start)
    except Exception:
        d0 = datetime.date.today()
    today = datetime.date.today()

    board = l.get("board") or []
    extras = [b for b in board if b.get("extra")]
    extra_open = sum(1 for b in extras if not b.get("done"))
    plan_len = len(build_days(l))
    done_daily = sum(1 for d in done_list(l) if not d.get("pre"))
    left = max(0, total - done_daily)

    total_days = max(1, plan_len + len(extras) - eaten_days(l))

    # 剩余天数（含今天）：题板上还没做完的天，和「剩余题数 ÷ 每天题数」取小
    frontier = max([b.get("dayIndex", 0) for b in board
                    if not b.get("extra")] or [0])
    slot_left = max(0, plan_len - frontier) + extra_open
    days_left = min(slot_left, (left + per - 1) // per + extra_open)

    nominal_end = d0 + datetime.timedelta(days=total_days - 1)
    dyn_end = today + datetime.timedelta(days=max(0, days_left - 1))
    end = max(nominal_end, dyn_end)
    return {
        "total": total,
        "allTotal": all_problems_count(l),
        "perDay": per,
        "days": total_days,
        "daysLeft": days_left,
        "left": left,
        "startDate": start,
        "endDate": end.isoformat(),
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
    # build_days 是按顺序的「虚拟切分」，不知道哪些题已经被别的天占用。
    # 「加题/ 换题」可能把后续某天的计划题提前拿到今天，导致那天的题板上
    # 出现同一道题两次 —— 这里把已被其它天占用的题剔掉。
    taken = set()
    for bb in (l.get("board") or []):
        if bb.get("dayIndex") != day_index:
            taken |= {t.get("id") for t in (bb.get("tasks") or [])}
    tasks = [make_task(x) for x in days[day_index] if x.get("id") not in taken]
    return {
        "dayIndex": day_index,
        "date": d.isoformat(),
        "tasks": tasks,
        "done": False,
        "deficit": 0,
    }


def ensure_board(l):
    """确保有起始日和第一天的板面。返回 True 表示真的补建了东西（需要写盘）"""
    changed = False
    if not l.get("startDate"):
        l["startDate"] = datetime.date.today().isoformat()
        changed = True
    if not l.get("board"):
        d0 = new_day(l, 0)
        l["board"] = [d0] if d0 else []
        changed = True
    return changed


def used_ids(l):
    s = set()
    for b in l.get("board", []):
        s |= {t.get("id") for t in b.get("tasks", [])}
    s |= {d["id"] for d in done_list(l)}
    return s


def candidate_pool(p, l):
    """换题 / 加题的候选题目 —— 只从「本题单」里出，不外借。

    来源（都是本题单自己的题，加起来 <= 计划总题数）：
      1. rest —— 本题单还没排上板的题  ← 唯一来源

    换下来的题会自己回到 rest（它既不在板上也不在 done），所以不需要备用池。
    题排完就是真没了，不会去全局题池 / 其它题单借题。
    返回 (候选列表, 来源统计)。候选会去重，并排除本题单已用过的题。
    """
    used = used_ids(l)
    seen = set()
    out = []
    src = {"rest": 0}

    def push(t, bucket):
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


def cross_plan_record(p):
    """跨所有题单（含各自历史轮次归档）的单日完成纪录

    「所有计划里完成最多题的那一天」：遍历 lists 下每个题单当前的 done
    记录和 rounds 归档（重新开轮时存的一份 {id, date, pre}），按日期聚合
    真正做完的新题，取题数最多的一天；并列取更早的日期——纪录属于
    第一次达成它的那天。返回 {date, count, list}，没有记录时 count=0。

    归档轮次只记了 pre、没记 swapped，所以旧轮次里「换题补记」那几道会被
    算进来；那是历史遗留数据、量极小，接受。
    """
    best = {"date": "", "count": 0, "list": ""}

    def feed(counts, lname):
        for dt, n in counts.items():
            if not dt or n <= 0:
                continue
            if n > best["count"] or (n == best["count"] and dt < best["date"]):
                best["date"], best["count"], best["list"] = dt, n, lname

    for k, l in sorted((p.get("lists") or {}).items()):
        if not isinstance(l, dict):
            continue
        lname = l.get("name") or k
        feed(daily_counts(l), lname)
        for r in (l.get("rounds") or []):
            if not isinstance(r, dict):
                continue
            c = {}
            for d in (r.get("done") or []):
                if d.get("pre"):
                    continue
                dt = d.get("date")
                if dt:
                    c[dt] = c.get(dt, 0) + 1
            feed(c, "%s · 第 %s 轮" % (lname, r.get("no") or "?"))
    return best


# ============ 统计 ============

def early_dates(l):
    """「提前日」：原定那天的题已经提前做掉的日子（日历标薄荷青 + ↑）

    判定：到这一天开始之前，累计完成量已经覆盖了它原定的配额，
    即 cumDone(D-1) >= perDay × (D - startDate + 1)。
      · 今天不算——它正在进行，当天超量完成由当天格子自己的样式表达；
      · 过去的日子也算：它的题早就做掉了，不该被日历判成「空缺」标红；
      · 只算真正做的新题，标记「之前做过」的补记不算。
    返回日期字符串列表（升序）。
    """
    per = max(1, int(l.get("perDay", 4) or 4))
    start = l.get("startDate") or ""
    try:
        d0 = datetime.date.fromisoformat(start)
    except Exception:
        return []
    days = build_days(l)
    if not days:
        return []
    daily = daily_counts(l)
    today = datetime.date.today().isoformat()
    cum, out = 0, []
    for k in range(len(days)):
        ds = (d0 + datetime.timedelta(days=k)).isoformat()
        if ds != today and cum >= per * (k + 1):
            out.append(ds)
        cum += daily.get(ds, 0)
    return out


def eaten_days(l):
    """已经提前做掉的计划天数（整数天）——总天数要相应缩短

    累计完成量超出「按日历走到今天」的配额，超出部分折算成整天：
    例：每天 4 题，今天一天做完 8 题 -> 超出 4 题 = 1 天 -> 总天数 -1。
    欠账（落后）时为 0，不会把计划「缩短」成负数。
    """
    per = max(1, int(l.get("perDay", 4) or 4))
    start = l.get("startDate") or ""
    try:
        d0 = datetime.date.fromisoformat(start)
    except Exception:
        return 0
    elapsed = (datetime.date.today() - d0).days + 1
    if elapsed <= 0:
        return 0
    done_n = sum(1 for d in done_list(l) if not d.get("pre"))
    return max(0, (done_n - per * elapsed) // per)


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

    avg = sum(x["count"] for x in days7) / 7.0   # 名副其实的「近 7 天日均」
    total = total_problems(l)
    # 剩余 = 计划总量 - 计划内已完成的题。
    # 注意不能写 total - len(done_list(l))：done 里含「之前做过」的题，而那些题
    # 已经不算进 total（effective_problems 会排除 pre），两边各扣一次，
    # 于是点一次「之前做过」剩余就掉 2 —— 实测三个题单都是这样。
    _dl = done_list(l)
    left = max(0, total - (len(_dl) - sum(1 for d in _dl if d.get("pre"))))
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
        return {        "board": [], "doneCount": 0, "preCount": 0, "target": 0,
                "totalDays": 0, "today": datetime.date.today().isoformat(),
                "poolLeft": 0, "daily": {}, "dailyDetail": {}, "tasks": [],
                "categories": [], "lists": [], "activeList": "",
                "extraDates": [], "earlyDates": [],
                "stats": stats_view({"categories": [], "pool": [], "done": [], "board": []}),
                "marks": [], "markStats": marks_stats([]),
                "weekly": weekly_view({"done": []}),
                "recAll": cross_plan_record(p),
                "canUndo": can_undo()}
    dl = done_list(l)
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
        # 「提前日」：原定那天的题已经提前做掉（日历薄荷青 + ↑）
        "earlyDates": early_dates(l),
        "round": len([r for r in (l.get("rounds") or []) if isinstance(r, dict)]) + 1,
        "rounds": [{"no": r.get("no"), "from": r.get("from") or "", "to": r.get("to") or "",
                    "count": r.get("count") or 0, "done": r.get("done") or []}
                   for r in (l.get("rounds") or []) if isinstance(r, dict)],
        "preDone": [{"id": d["id"]} for d in dl if d.get("pre")],
        "target": total_problems(l),
        # 总天数 = 原计划 + 补做日 - 提前做掉的天（「已展开 X / N 天」的分母）
        "totalDays": max(1, len(build_days(l))
                         + sum(1 for b in (l.get("board") or []) if b.get("extra"))
                         - eaten_days(l)),
        "today": datetime.date.today().isoformat(),
        "poolLeft": len(l.get("pool", [])),
        "candLeft": len(_cands),
        "candSrc": _csrc,
        "daily": daily_counts(l),
        "dailyDetail": daily_detail(l),
        "recAll": cross_plan_record(p),
        "tasks": all_tasks(l),
        "categories": categories_view(l),
        "lists": lists_view(p),
        "activeList": active_key(p),
        "activeName": l.get("name", ""),
        "perDay": int(l.get("perDay", 4) or 4),
        "plan": plan_view(l),
        "setupDone": bool(p.get("setupDone")),
        "stats": stats_view(l),
        "marks": marks_view(l),
        "markStats": marks_stats(marks_view(l)),
        "weekly": weekly_view(l),
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

    选取策略：**随机**挑，且最近 8 次换过的题临时拉黑。
    否则取 cands[0] 会和「换下来的题又回到候选池」形成死循环——
    表现为连点换题只在两三道题之间来回换（实测 25 次只换来 2 道不同的题）。
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

    recent = l.setdefault("swapLog", [])
    fresh = [c for c in cands if c.get("id") not in recent[-8:]]
    pick = random.choice(fresh or cands)      # 全被拉黑时才退回全池
    recent.append(pick.get("id"))
    del recent[:-24]                          # 只留最近 24 条，别无限增长

    tasks[ti] = make_task(pick)
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


def do_custom_day(p, l, di, ids):
    """自定义当天的题：把当天没勾的题整批换成自己挑的题

    「系统出题」之外的手动通道：从本题单还没做过的题里挑今天做哪几道。
    当天**已勾选**的题原样保留（半天提交过的进度不能丢）；换下来的题
    回到本题单候选池（它们没 done，自然回到 rest）。
    只接受本题单的、没做过（done /「之前做过」都算做过）的题；
    **不限数量**（perDay 只是系统出题的默认量，想一天做七八道不拦着）。
    返回 (n, err)：n = 实际换进来的题数。
    """
    board = l.get("board", [])
    if not (0 <= di < len(board)):
        return 0, "bad_index"
    b = board[di]

    keep = [t for t in b.get("tasks", []) if t.get("checked")]
    keep_ids = {t.get("id") for t in keep}

    probs = {}
    for _cn, t in effective_problems(l):
        probs[t.get("id")] = t
    done_ids = {d.get("id") for d in done_list(l)}

    seen, picked = set(), []
    for raw in (ids or []):
        try:
            tid = int(raw)
        except Exception:
            return 0, "bad_ids"
        if tid in seen:
            continue
        seen.add(tid)
        if tid in keep_ids:
            continue                     # 已勾选的题不用重复选（原样保留）
        x = probs.get(tid)
        if x is None or tid in done_ids:
            return 0, "bad_ids"          # 不是本题单的题 / 已经做过
        picked.append(x)

    if not picked:
        return 0, "nothing"              # 一道都没选

    b["tasks"] = keep + [make_task(x) for x in picked]
    b["done"] = False
    return len(picked), None


def _plan_end(l):
    """原计划的最后一天（不含补做日）：startDate + 计划天数 - 1"""
    start = l.get("startDate") or datetime.date.today().isoformat()
    try:
        d0 = datetime.date.fromisoformat(start)
    except Exception:
        d0 = datetime.date.today()
    return d0 + datetime.timedelta(days=max(0, len(build_days(l)) - 1))


def _reflow_extra(l):
    """把「补做日」统一排到原计划最后一天之后

    补做日是计划末尾追加的一（多）天，序号和日期都必须落在原计划最后一天
    （以及已展开的最后一个普通天）之后，否则它会跟还没展开的计划天撞号——
    「展开下一天」会直接跳过那一批题；日历上也会落进计划区间里，
    分不清是补做日还是普通天。补做日与提前日的界限也以原计划最后一天为准：
    超出它的都算补做日，早于它的算提前日。
    """
    board = l.get("board", [])
    normals = [b for b in board if not b.get("extra")]
    extras = [b for b in board if b.get("extra")]
    if not extras:
        return
    if not normals:
        return
    base_i = max(b.get("dayIndex", 0) for b in normals)
    base_d = _plan_end(l)
    try:
        last_n = datetime.date.fromisoformat(
            max(b.get("date", "") for b in normals))
        base_d = max(base_d, last_n)
    except Exception:
        pass
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


def do_submit(l, di, rec_date=None):
    """提交：勾选的记入 done；未勾选的怎么处理，分两种情况：

    1. 手动提交（rec_date=None，点「确定完成」）：没勾的题**留在当天**，
       当天 done 保持 False，回题板「一鼓作气」把剩下的做完再交就行。
       没做完不欠账、不挪窝——当天只有真正结束（午夜 auto_settle）才翻篇。
    2. 午夜自动结算 / 一题没勾的「确认翻篇」（rec_date 传值）：没勾的按
       欠账规则顺延——下一天连自己的题最多接 perDay×2 道，**超出的不再往
       后续天堆**，而是顺延到计划末尾新增的「补做日」（extra=True，日历上
       换颜色标注，排在原计划最后一天之后）。这样欠账不会雪球式越滚越大、
       某天突然冒出十几道题。

    完成记录的日期：手动提交 = 今天（提前做后面几天的题也算今天的做题量）；
    自动结算传 rec_date = 那天的计划日期（昨晚忘了点提交，记录仍算昨天）。

    返回 (added, moved, remain, extra_n)
    """
    board = l.get("board", [])
    if not (0 <= di < len(board)):
        return 0, 0, 0, 0
    b = board[di]
    done = l.setdefault("done", [])
    existing = {d["id"] for d in done_list(l)}
    today = rec_date or datetime.date.today().isoformat()
    carry, added = [], 0
    for x in b.get("tasks", []):
        if x.get("checked"):
            if x.get("id") not in existing:
                done.append({"id": x.get("id"), "date": today})
                existing.add(x.get("id"))
                added += 1
        else:
            carry.append(x)

    if not carry:
        b["tasks"] = []
        b["done"] = True
        # completed 有值 = 这天之前交过了（半途交过 /「挑战自我」加题后的二次提交）：
        # 这次是增量，累计而不是覆盖，否则当天总数会被冲掉
        prev = b.get("completed")
        b["deficit"] = (b.get("deficit") or 0) if prev is not None else 0
        b["completed"] = (prev + added) if prev is not None else added
        return added, 0, 0, 0

    if rec_date is None:
        # 手动提交：没勾的题留在今天。不算欠账（deficit 不动）、不往下天挪，
        # 做完剩下的随时回来补交；一题没勾时added=0，除了 remain 什么都不改。
        if added:
            prev = b.get("completed")
            b["completed"] = (prev + added) if prev is not None else added
        b["tasks"] = carry
        b["done"] = False
        return added, 0, len(carry), 0

    per = max(1, int(l.get("perDay", 4) or 4))
    cap = per * 2

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
        # 计划已经排满、没有下一天：没地方顺延，题留在当天
        b["tasks"] = carry
        b["done"] = False
        return added, 0, len(carry), 0

    # 当天上限 = 原计划每天题数×2：下一天连自己的题带顺延进来的都不能超，
    # 超出的部分才挪到计划末尾的「补做日」——欠账不滚雪球，也不会某天突然十几题
    room = max(0, cap - len(nxt.get("tasks") or []))
    to_next, to_extra = carry[:room], carry[room:]

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
    prev = b.get("completed")      # None = 这天第一次交；有值 = 挑战自我加题后的二次提交
    b["deficit"] = ((b.get("deficit") or 0) + moved) if prev is not None else moved
    b["completed"] = (prev + added) if prev is not None else added
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


def auto_settle(l):
    """跨天自动结算：把落在昨天及以前的题板天处理掉，打开就是今天的题。

    - 没提交的过去天：自动「确定完成」——勾选的记完成（记在那天的计划日期），
      没勾的按欠账规则顺延；那天一题没做的话日历照常标红
    - 已经交完但今天还没排上的：自动展开下一天，追到今天为止
    - 暂停中的计划不动；提前做了后面的天（当前天在未来）也不动；
      计划排满、没有下一天时停下来，留给用户手动处理

    日期驱动，不依赖某个时刻服务必须活着：停机几天后再启动会一次性补齐。
    返回 dict：{settled 结算天数, added 入库题数, carried 顺延题数,
                expanded 展开天数, dates 结算掉的日期(升序)}
    """
    if l.get("paused"):
        return {"settled": 0, "added": 0, "carried": 0,
                "expanded": 0, "dates": []}
    today = datetime.date.today().isoformat()
    settled = added = carried = expanded = 0
    dates = []

    # 第一步：把所有「已经过去、还没提交」的天按日期顺序结算掉。
    # 原来只处理最后一个普通天（last_n），关机几天后再开会发现前几天
    # 永远卡在「未交」状态——勾选的题不入库、日历上也不留痕，数据等于丢了。
    for _ in range(500):
        board = l.get("board", [])
        target = None
        for i, b in enumerate(board):
            if b.get("extra"):
                continue
            if (b.get("date") or today) >= today:
                continue# 今天或未来，留给用户
            if b.get("done") or not b.get("tasks"):
                continue                      # 已交 / 空板，无需结算
            target = i
            break                           # 按板面顺序 = 按日期顺序
        if target is None:
            break
        b = board[target]
        a, c, _r, _e = do_submit(l, target, rec_date=b.get("date"))
        settled += 1
        added += a
        carried += c
        dates.append(b.get("date"))

    # 第二步：还没追上今天就继续展开，直到今天（或计划排满）
    for _ in range(500):
        board = l.get("board", [])
        last_n = -1
        for i, b in enumerate(board):
            if not b.get("extra"):
                last_n = i
        if last_n < 0:
            break
        b = board[last_n]
        if (b.get("date") or today) >= today:
            break                            # 已经是今天（或超前做了后面的天）
        if not (b.get("done") or not b.get("tasks")):
            break                            # 最后一天还有没交的题，交给用户
        if not do_expand(l):
            break                            # 计划排满，没有下一天：不硬动
        expanded += 1
    return {"settled": settled, "added": added, "carried": carried,
            "expanded": expanded, "dates": dates}


def settle_msg(info):
    """把auto_settle 的结果拼成一句人话，写进启动日志用。"""
    n = info.get("settled", 0)
    added = info.get("added", 0)
    carried = info.get("carried", 0)
    dates = info.get("dates") or []
    if n <= 0:
        return "题板已自动切换到今天"
    if n == 1 and dates:
        try:
            _, m, d = dates[0].split("-")
            head = "已自动提交 %d 月 %d 日" % (int(m), int(d))
        except Exception:
            head = "已自动提交 1 天"
    else:
        head = "已自动结算 %d 天" % n
    parts = [head]
    if added:
        parts.append("%d 题入库" % added)
    if carried:
        parts.append("%d 题顺延到今天" % carried)
    if not added and not carried:
        parts.append("当天没做，题已顺延")
    return "，".join(parts)


def do_reset_day(l, di):
    """重置该天：恢复成当天的原始题目（勾选、换题、加题都还原）。

    顺延进来的题（carry）不在当天的静态分块里，必须单独保留——
    否则重置一次它们就从计划里消失了。补做日没有静态分块可恢复，
    重置等于清空全部勾选。
    """
    board = l.get("board", [])
    if not (0 <= di < len(board)):
        return False
    keeps = [t for t in board[di].get("tasks", []) if t.get("carry")]
    # 补做日不重建（没有"原始题目"可言，重建还会丢掉 extra 标记和顺延日期）
    fresh = None if board[di].get("extra") else new_day(l, board[di].get("dayIndex", 0))
    if fresh is None:
        # 补做日 / 已无静态分块可恢复：只清空勾选，题目原样保留
        for t in board[di].get("tasks", []):
            t["checked"] = False
        board[di]["done"] = False
        board[di]["deficit"] = 0
        return True
    have = {t.get("id") for t in fresh["tasks"]}
    for t in keeps:
        if t.get("id") not in have:
            fresh["tasks"].append(make_task(t, carry=True))
            have.add(t.get("id"))
    fresh["deficit"] = 0
    board[di] = fresh
    return True


def do_reset_plan(p, l, mode="progress"):
    """重置计划（只影响当前题单，其它题单不受影响）

    mode='progress'：清空完成记录与已展开的天，保留计划设置（总题数 / 每天题数），
                     起始日改回今天，重新排第一天。
    mode='all'     ：在上面基础上把计划设置也恢复默认（limit / perDay），
                     并回到首次使用的初始化向导（setupDone=False）。
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
# 官方 GraphQL 端点（GET 版，favoriteQuestionList 支持公开题单与官方标签题单，
# 如 problem-list/hash-table/）。leetcode.cn 对非浏览器请求会弹 WAF 挑战页，
# 所以这里借用系统里现成的 Chromium 系浏览器（Windows 自带 Edge）无头访问：
# 真浏览器会自己执行挑战拿到放行 cookie，GraphQL 的 JSON 就渲染在 <pre> 里，
# dump-dom 抠出来即可 —— 全程只用标准库，不需要 Playwright。
LC_GQL = "https://leetcode.cn/graphql/"
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
      https://leetcode.cn/problem-list/8LSpuXqD/     （分享题单）
      https://leetcode.cn/problem-list/hash-table/   （官方标签题单）
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

_lc_browser = None      # 浏览器路径缓存（None=还没找，""=找不到）
_lc_profile = None      # 无头浏览器的临时 profile（保留挑战 cookie，二次导入更快）


def _browser_candidates():
    """各平台常见的 Chromium 系浏览器安装位置"""
    if os.name == "nt":
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local = os.environ.get("LOCALAPPDATA", "")
        return [
            os.path.join(pf86, r"Microsoft\Edge\Application\msedge.exe"),
            os.path.join(pf, r"Microsoft\Edge\Application\msedge.exe"),
            os.path.join(pf, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(pf86, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(local, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(local, r"Chromium\Application\chrome.exe"),
        ]
    if sys.platform == "darwin":
        return [
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ]
    return []       # Linux 走 PATH 查找


def find_browser():
    """找一个现成的 Chromium 系浏览器；Windows 10/11 自带 Edge，基本必中"""
    global _lc_browser
    if _lc_browser is not None:
        return _lc_browser or None
    for p in _browser_candidates():
        if os.path.isfile(p):
            _lc_browser = p
            return p
    for name in ("msedge", "chrome", "chromium", "chromium-browser",
                 "google-chrome", "brave-browser"):
        w = shutil.which(name)
        if w:
            _lc_browser = w
            return w
    _lc_browser = ""
    return None


def _lc_profile_dir(fresh=False):
    global _lc_profile
    if fresh and _lc_profile:
        shutil.rmtree(_lc_profile, ignore_errors=True)
        _lc_profile = None
    if _lc_profile is None:
        _lc_profile = tempfile.mkdtemp(prefix="lc-board-browser-")
    return _lc_profile


def _browser_get_json(gql_url, timeout=90):
    """无头浏览器打开 GET 版 GraphQL，把渲染出的 <pre> JSON 抠出来。

    首次访问会吃一次 WAF 挑战（浏览器自己解掉），同一 profile 下后续访问直接放行。
    返回 dict；拿不到（没浏览器 / 超时 / 仍被拦）返回 None。
    """
    exe = find_browser()
    if not exe:
        return None
    args = [exe,
            "--headless=new", "--disable-gpu",
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox", "--disable-dev-shm-usage",
            "--dump-dom", "--virtual-time-budget=30000",
            "--user-data-dir=" + _lc_profile_dir(),
            gql_url]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        r = subprocess.run(args, capture_output=True, timeout=timeout,
                           creationflags=flags, stdin=subprocess.DEVNULL)
    except Exception:
        return None
    out = r.stdout.decode("utf-8", "replace")
    i = out.find("<pre")
    if i < 0:
        return None
    gt = out.find(">", i)
    j = out.find("</pre>", gt)
    if j < 0:
        return None
    try:
        return json.loads(html.unescape(out[gt + 1:j]))
    except Exception:
        return None


def fetch_lc_list(slug, max_n=3000, use_cache=True):
    """调力扣 GraphQL 拉题单（标准库 + 系统浏览器，无第三方依赖）。返回 (problems, err)

    端点对 limit 参数不敏感（多数题单一次就全量返回，hasMore=false），
    翻页循环只为大题单兜底。取 translatedTitle（中文题名），无则退回英文 title。
    """
    now = time.time()
    if use_cache and slug in _lc_cache:
        ts, cached = _lc_cache[slug]
        if now - ts < LC_CACHE_TTL:
            return cached, None

    if find_browser() is None:
        return None, ("没找到可用的浏览器（Edge / Chrome），无法导入力扣题单；"
                      "也可以手动复制题目，用「手动输入」创建题单")

    out, skip = [], 0
    page_size = 100
    fresh_once = False
    try:
        while skip < max_n:
            qs_url = LC_GQL + "?" + urlencode({
                "query": LC_QUERY,
                "variables": json.dumps({"favoriteSlug": slug,
                                         "limit": page_size, "skip": skip}),
                "operationName": "favoriteQuestionList",
            })
            result = _browser_get_json(qs_url)
            if result is None:
                # 常见于挑战没过或 profile 里旧 cookie 失效：换新 profile 再试一次
                if not fresh_once:
                    fresh_once = True
                    _lc_profile_dir(fresh=True)
                    continue
                return None, "力扣请求失败：浏览器访问被拦截或超时，请稍后重试"
            if result.get("errors"):
                msg = result["errors"][0].get("message", "未知错误")
                return None, "力扣返回错误：%s" % msg

            node = (result.get("data") or {}).get("favoriteQuestionList")
            if not node:
                return None, "题单不存在或未公开"

            qs = node.get("questions") or []
            if not qs:
                if not out:          # 第一页就空 -> 多半是 slug 不存在（力扣不报错，只给空列表）
                    return None, "题单不存在或未公开"
                break
            for q in qs:
                fid = q.get("questionFrontendId") or ""
                tags = [tag_to_cn(t.get("name", "")) for t in (q.get("topicTags") or [])]
                out.append({
                    "id": fid,
                    "name": q.get("translatedTitle") or q.get("title") or "",
                    "difficulty": (q.get("difficulty") or "medium").lower(),
                    "hint": " / ".join(tags[:3]),
                    "slug": q.get("titleSlug") or "",
                })
            skip += len(qs)
            if not node.get("hasMore"):
                break
    except Exception as e:
        return None, "导入失败：%s" % e

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
        l["perDay"] = max(1, min(50, int(n)))
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


# ============ 系统通知 ============

def send_toast(title, body):
    """弹 Windows 系统通知。返回 (ok, msg)：ok=已提交给系统；msg=失败原因（前端可见）"""
    ps = os.path.join(BASE, "start", "toast.ps1")
    if not os.path.isfile(ps):
        return False, "start/toast.ps1 不存在"
    if os.name != "nt":
        return False, "系统通知仅支持 Windows"
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", ps, "-Title", title, "-Body", body],
            creationflags=flags, timeout=60,
            stdin=subprocess.DEVNULL, capture_output=True,
        )
    except Exception as e:
        return False, "通知脚本执行失败：%s" % e
    raw = r.stdout or b""
    try:
        out = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            out = raw.decode("gbk")
        except Exception:
            out = raw.decode("utf-8", "replace")
    if "TOAST_OK" in out:
        return True, None
    if "TOAST_FAIL:" in out:
        return False, "通知被系统拒绝：" + out.split("TOAST_FAIL:", 1)[1].strip()[:160]
    return False, "通知脚本没有返回结果"


def settle_worker():
    """后台巡检：跨天自动结算（20s 一巡，日期驱动，停机重启会补齐）。
    静默结算：不弹 Windows 通知，安安静静把账结掉。"""
    while True:
        try:
            with _lock:
                p = ensure_root(load_plan())
                # 跨天自动结算：把昨天及以前没提交的天自动「确定完成」并切到今天
                l0 = get_list(p)
                if l0 is not None:
                    push_history(p)
                    info = auto_settle(l0)
                    if info["settled"] or info["expanded"]:
                        save_plan(p)
                    else:
                        _history.pop()   # 没动数据就不留撤销点
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
    cols = ["题号", "题目", "难度", "完成日期", "标记来源"]
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
ALLOWED_STATIC = {"ui.html", "app.js", "favicon.svg"}
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

    def _host_ok(self):
        """只接受本机 Host 头：挡掉恶意网页跨站 POST（CSRF）和 DNS 重绑定"""
        host = (self.headers.get("Host") or "").lower()
        return host in ("127.0.0.1:%d" % PORT, "localhost:%d" % PORT,
                        "127.0.0.1", "localhost")

    def do_GET(self):
        if not self._host_ok():
            self._send(403, "text/plain; charset=utf-8", b"forbidden")
            return
        path = self.path.split("?")[0]
        if path.startswith("/api/state"):
            with _lock:
                p = ensure_root(load_plan())
                l = get_list(p)
                if l is not None and ensure_board(l):
                    save_plan(p)          # 只有真的补建了板面才写盘
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
            self._serve_file("favicon.svg")   # 浏览器兜底探测 .ico 时也给出图标
        else:
            self._serve_file(path.lstrip("/"))

    def do_POST(self):
        if not self._host_ok():
            self._send(403, "text/plain; charset=utf-8", b"forbidden")
            return
        ln = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(ln) if ln else b"{}"
        try:
            data = json.loads(raw or b"{}")
        except Exception:
            data = {}
        path = self.path.split("?")[0]

        with _lock:
            p = ensure_root(load_plan())
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
            elif path.startswith("/api/mark"):
                # 标记经典 / 错题：{id, kind:"classic"|"wrong", on:true|false}
                # {id, note:"..."} 只改备注；{id, clear:true} 两类标记全取消
                note = data.get("note")
                ok, err = do_mark(l, data.get("id"),
                                  data.get("kind") or None,
                                  note if note is not None else None,
                                  data.get("on"),
                                  bool(data.get("clear")))
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
            elif path.startswith("/api/customday"):
                # 自定义当天的题：换进来用户自己挑的题（已勾选的保留）
                n, err = do_custom_day(p, l, di, data.get("ids") or [])
                if err:
                    _history.pop()
                save_plan(p)
                self._json({"ok": not err, "n": n, "err": err,
                            "state": state_view(p)})
            elif path.startswith("/api/submit"):
                # 先记下这次勾了哪些题（do_submit 会清空当天 tasks，之后就取不到了）
                _bd = l.get("board", [])
                _day = _bd[di] if 0 <= di < len(_bd) else {}
                picked = [{"id": t.get("id"), "name": t.get("name") or "",
                           "difficulty": t.get("difficulty") or "easy",
                           "category": t.get("category") or ""}
                          for t in (_day.get("tasks") or []) if t.get("checked")]
                plan_date = _day.get("date") or ""
                # 一题没勾也允许「确认翻篇」：rec_date 传今天 -> 按当天结束处理
                # （没勾的按欠账顺延，超当天上限的进补做日）
                zero = bool(data.get("zero"))
                rec = datetime.date.today().isoformat() if zero else None
                added, carried, remain, extra_n = do_submit(l, di, rec_date=rec)
                save_plan(p)
                self._json({"ok": True, "added": added, "carried": carried,
                            "remain": remain, "extra": extra_n, "zero": zero,
                            "picked": picked, "planDate": plan_date,
                            "recDate": datetime.date.today().isoformat(),
                            "state": state_view(p)})
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
            # 启动即补结算：停机几天后再打开，把欠的天一次性结清、切到今天
            # （静默结算，不弹通知，只打日志）
            push_history(p)
            info = auto_settle(l)
            if info["settled"] or info["expanded"]:
                save_plan(p)
                print("auto-settle: %s" % settle_msg(info), flush=True)
            else:
                _history.pop()
        save_plan(p)
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        print("端口 %d 已被占用：看板可能已经在运行了，不要重复启动" % PORT, flush=True)
        return
    srv.daemon_threads = True
    t = threading.Thread(target=settle_worker, daemon=True)
    t.start()
    print("leetcode board on http://127.0.0.1:%d" % PORT, flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
