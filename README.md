# 力扣刷题看板 ✧

> 一个 **Web Coding** 练手项目 —— 纯 HTML / CSS / JavaScript 前端 + Python 标准库本地服务，
> **运行时零第三方依赖**，双击 bat 就能跑。开发过程由 AI Agent（WorkBuddy）协作完成。

![screenshot](docs/screenshot.png)

每天打开看一眼：**今天该做哪几道**、做完打勾、没做完自动顺延，日历记录你的坚持。

---

## ✨ 特性

| | |
|---|---|
| 📅 **动态计划** | 总题数 / 每天题数随手改，天数与结束日期自动重算 |
| ✅ **勾选即记录** | 当天题板打勾提交，没勾的自动顺延到第二天补做 |
| 📉 **欠账上限** | 顺延最多「每天题数 × 2」道，超出的进计划末尾的**补做日**（日历上琥珀色标注） |
| 🔄 **换题零副作用** | 换一道只是换一道，总量 / 天数 / 每日量全都不变 |
| 🚩 **标记「之前做过」** | 计入已完成、但不算每日做题量，且**计划天数会跟着缩短** |
| ⏸ **暂停 / 继续** | 记录一条不丢，暂停期间日历标斜纹灰、不算空缺 |
| 🔁 **无限轮次** | 刷完一轮可以「重新开始」，往期记录归档留档 |
| 📖 **多题单** | 自带 LeetCode 100，也可粘贴力扣题单链接自动导入 |
| ↩️ **撤销 30 步** | 几乎每个操作都能 `Ctrl+Z` 退回 |
| 🎨 **氛围感** | 水墨风竹林背景 + 雾气漂移 + 细雨 + 竹叶飘落，AI 生成的插画 |
| 🔔 **每日提醒** | 到点弹 Windows 系统通知（Windows 限定，用 `PowerShell` 发通知） |
| 📊 **统计与热力日历** | 连续天数、近 7 日均量、难度分布、悬停看当天做了哪几题 |

---

## 🚀 快速开始

**要求：Python 3.8+**（[官网下载](https://www.python.org/downloads/)，安装时勾选 *Add to PATH*）。
**不需要** `pip install` 任何东西 —— 本项目只用 Python 标准库。

### 方式一：Windows 双击（最省事）

下载解压后，双击 **`打开看板.bat`**，浏览器会自动打开。

`打开看板.bat` 会按顺序找 Python：`python` → `py -3` → `python3` →
`%LOCALAPPDATA%\Programs\Python\Python3xx\` → 项目内 `python\`。
所以**装 Python 时没勾 *Add to PATH* 也能跑**（只要装在标准位置）。

### 方式二：命令行（macOS / Linux / 任何平台）

```bash
git clone <你的仓库地址> && cd leetcode-board

python3 start.py        # 起服务 + 自动开浏览器
# 或者
./start.sh              # 同上（macOS / Linux）
```

### 方式三：手动起服务（推荐给开发者）

```bash
python3 server.py       # 只起服务，浏览器访问 http://127.0.0.1:8765
```

| 命令 | 作用 |
|------|------|
| `python3 server.py` | 只起本地服务（前台，日志打在终端） |
| `python3 start.py` | 检测端口 → 未运行则静默拉起服务 → 开浏览器 |
| `python3 seed_lc100.py` | 重建 LeetCode 100 题单（**会清空进度**，谨慎） |
| `python3 _x.py` | 跑回归测试（在副本上跑，不碰你的真实数据） |

### 环境变量（进阶）

| 变量 | 说明 | 默认 |
|------|------|------|
| `LEET_PORT` | 服务端口 | `8765` |
| `LEET_PLAN` | 数据文件路径 | `./plan.json` |

```bash
# 在副本上跑，不动真实数据（测试就是这么做的）
LEET_PLAN=_t_plan.json LEET_PORT=8799 python3 server.py
```

---

## 🖥 前台 / 后台运行

| 方式 | 命令 | 表现 | 怎么停 |
|------|------|------|--------|
| **前台**（调试用） | `python3 server.py` | 终端占着，日志直接打屏 | `Ctrl+C` |
| **后台 + 开浏览器**（日常推荐） | `python3 start.py` | 立刻返回控制台，不留窗口 | 任务管理器结束 `python` / `pythonw` |
| **后台无窗口** | `pythonw server.py` | Windows 上完全没有黑框 | 任务管理器 |
| **后台 + 日志**（mac/Linux） | `nohup python3 server.py > server.log 2>&1 &` | 无窗口，日志落盘 | `pkill -f server.py` |

> `start.py` 用 `CREATE_NO_WINDOW | DETACHED_PROCESS` 创建子进程，
> 服务彻底脱离控制台；它还会先探测 8765 端口，已经在跑就直接开浏览器不重复起。
>
> 想彻底当后台服务（开机自启、崩溃自动拉起），可以再套一层系统服务：
> Windows 用任务计划程序 / NSSM，macOS 用 launchd，Linux 用 systemd —— 但对这个
> 一次性小工具来说没必要，`start.py` 足够了。

---

## 📁 项目结构

```
leetcode-board/
├── server.py            # 本地服务（HTTP + API + 提醒后台线程）
├── ui.html              # 界面结构 + 全部样式
├── app.js               # 前端逻辑
├── plan.json            # 你的刷题数据（本地文件，不进仓库）
├── plan.example.json    # 数据模板（复制成 plan.json 即可用）
├── start.py             # 启动器（静默拉起服务 + 开浏览器）
├── start.sh             # macOS / Linux 启动脚本
├── 打开看板.bat         # Windows 一键启动
├── seed_lc100.py        # LeetCode 100 题库（重建用）
├── toast.ps1            # Windows 系统通知
├── _x.py                # 回归测试（副本服务，不碰真实数据）
├── assets/              # 背景图（AI 生成：默认水墨风 + 备用吉卜力风）
├── docs/screenshot.png  # README 配图
├── LICENSE              # MIT
├── .gitignore           # 排除 plan.json 等个人数据
├── .gitattributes       # 统一换行符，保证 start.sh 在 mac/Linux 能跑
└── README.md
```

---

## 💾 数据说明

**所有数据都在 `plan.json` 这一个文件里**，纯本地、不联网、不上传。

仓库里放的是 `plan.example.json`（空模板）。首次启动时若没有 `plan.json`，
服务会自动用默认题库生成一份。想备份进度，复制 `plan.json` 即可。

```bash
cp plan.example.json plan.json     # 手动初始化
```

`plan.json` 已在 `.gitignore` 里 —— **不要把自己的刷题进度传到公开仓库**。

### 关键字段

| 字段 | 含义 |
|------|------|
| `perDay` | 每天几题 |
| `limit` | 总题数上限（`null` = 全部） |
| `categories` | 题库：`[{name:"哈希", problems:[{id,name,difficulty,hint}]}]` |
| `done` | 完成记录 `{id, date}`；带 `pre:true` 是「之前做过」 |
| `board` | 已展开的天，含当天题目与勾选状态 |
| `rounds` | 往期归档轮次（重新开始一轮时留档） |
| `pauses` | 暂停区间 `[{from,to}]` |

**days 不落盘**：每天的题目是运行时由 `categories` 按 `perDay` 展平切分出来的，
所以改计划立即生效，也不会和已完成记录打架。

---

## 📖 功能说明

### 首次打开：欢迎页
第一次打开会弹出引导，两步走：设定计划（总题数 + 每天题数，天数自动算，实时显示强度提示）
+ 四张卡片讲清楚「勾选 / 换题 / 左侧面板 / 撤销」。也可以点「稍后再设」，
随时点主区顶部 **「⚙ 修改计划」** 再改。

### 当天题板
- 标题栏显示「第 N / M 天」，每题行尾两个按钮：
  - **⇄ 换一道**：纯换题，零副作用；被换下来的题回到本题单候选池
  - **⚑ 之前做过**：计入已完成、不计入每日量、计划天数随之缩短
- **换题 / 加题只从本题单里出题**：就是「本题单还没上板的那 N 道」，
  不去全局题池或其它题单借题，题目排完就是真没了
- **确定完成**：勾选的记入记录，没勾的顺延到第二天（见下方「欠账机制」）
- 卡片底部：**+ 展开下一天** 和 **↶ 撤销**
- 悬停「确定完成」按钮的问号，可以看到顺延规则的完整说明

### 欠账机制（重点）
今天只做了一半就点「确定完成」→ 剩下的题**自动滚到第二天**（标「补做」）。

**欠账上限**：顺延到第二天最多 **每天题数 × 2** 道。超出的部分不再往后堆，
而是**顺延到计划末尾新增的「补做日」**：

- 补做日 = 计划外多出来的一天，计划总天数 +1，结束日期自动后移
- 题板上是琥珀色「补做日」卡片，日历上对应日期也是琥珀色（区别于绿=做过、红=空缺）
- 补做日永远排在最后一个普通天之后，「展开下一天」不会跳过计划内的天

### 左侧栏（精简版 · 一屏放下）
- **题单切换器**：只摆当前题单一行，点开是二级菜单（题目清单 / 切换题单 / 新建 / 删除）
- **统计**：已完成 / 剩余题数，以及「已标记 N 题 · 还有 N 题可换」
- **刷题日历**（可翻月）：
  - 只把「计划区间内」的空白日子标红；区间外（开始前 / 结束后）是中性灰，不算空缺
  - 已做题按 1-2 / 3-4 / 5-7 / 8+ 四档深浅着色；暂停期间是斜纹灰
  - **悬停某天直接看当天做了哪几道**
- **更多**（弹窗）：学习统计（连续天数 / 7 日均量 / 难度分布 / 本周进度）、
  每日提醒（时间点设置）、数据管理（导出 JSON / CSV、重置计划、重新开始一轮）

### 重置与重来
| 操作 | 清掉 | 保留 |
|------|------|------|
| **重置进度** | 完成记录、已展开的天、换题池 | 总题数、每天题数；起始日改回今天 |
| **恢复默认** | 上面全部 + 计划设置 | 提醒时段；回到初始化向导 |
| **重新开始一轮** | 当前轮进度 | **本轮记录归档进「往期轮次」**，可回看 |

都带二次确认，都能撤销，都**只影响当前题单**。

### 多题单
默认自带 LeetCode 100（100 题 / 17 个分类）。加新题单两种方式：
- **手动输入**：每行 `题号 题目名 难度`；单独一行不带题号的文字 → 自动识别为分类名
- **从力扣 URL 导入**：粘贴题单分享链接（`https://leetcode.cn/problem-list/xxxxxx/`），
  自动拉取并按考点标签分组（需联网，首次约 5~8 秒）

---

## 🛠 技术栈

| 层 | 用什么 |
|----|--------|
| 前端 | 原生 HTML / CSS / JavaScript，**无框架、无构建步骤**，改完刷新即生效 |
| 后端 | Python **标准库** `http.server` + `json`，无 Flask / 无 FastAPI |
| 数据 | 单个 JSON 文件，原子写入（tmp + `os.replace`）防损坏 |
| 样式 | CSS 自定义属性 + 玻璃拟态 + `@keyframes` + 内联 SVG 图标 |
| 背景 | AI 生成的插画（`assets/*.jpg`）+ CSS 雾气 / 雨丝 / 竹叶动画 |

一些实现细节：
- **撤销栈**：每次写操作前压一份 JSON 快照，最多 30 步
- **DOM 搬运**：侧栏面板的节点常驻隐藏容器 `#dock`，打开弹窗时搬进去、关闭时搬回来，
  渲染逻辑完全复用
- **自定义 tooltip**：不用浏览器原生 `title`（黑框太丑），事件委托统一处理
- **版本自检**：服务端下发 ui.html / app.js 的时间戳，页面发现不一致会自己刷新
- **静态白名单**：只放行 `ui.html`、`app.js` 和 `assets/` 下的图片，禁止目录遍历

### API
<details>
<summary>点开看接口表</summary>

| 接口 | 方法 | 参数 | 作用 |
|------|------|------|------|
| `/api/state` | GET | — | 全部状态（board / tasks / plan / lists / weekly / reminders） |
| `/api/export` | GET | `?fmt=json\|csv` | 下载当前题单进度 |
| `/api/setplan` | POST | `{limit,perDay,reset,markSetup}` | 设置计划，自动重排 |
| `/api/restartplan` | POST | `{}` | 重新开启一轮（先归档，可撤销） |
| `/api/resetplan` | POST | `{mode}` | `progress` 只清进度 / `all` 连设置一起恢复 |
| `/api/pauseplan` | POST | `{pause}` | 暂停（`true`）/ 继续（`false`） |
| `/api/switch` | POST | `{key}` | 切换题单 |
| `/api/newlist` | POST | `{name,raw,perDay}` | 新建题单（自动解析文本） |
| `/api/importurl` | POST | `{url}` | 预览力扣题单（不写盘） |
| `/api/importurlsave` | POST | `{url,name,perDay,group}` | 从 URL 导入为新题单 |
| `/api/dellist` | POST | `{key}` | 删除题单 |
| `/api/toggle` | POST | `{day,index}` | 勾选 / 取消 |
| `/api/swap` | POST | `{day,index}` | 换一道题（纯换） |
| `/api/markpre` | POST | `{day,index}` | 标记「之前做过」 |
| `/api/unmarkpre` | POST | `{id}` | 撤销「之前做过」 |
| `/api/add` | POST | `{day,n}` | 加 n 题 |
| `/api/submit` | POST | `{day}` | 提交，未勾选顺延 |
| `/api/expand` | POST | — | 展开下一天 |
| `/api/resetday` | POST | `{day}` | 重置该天 |
| `/api/remind` | POST | `{enabled,slots}` | 保存提醒配置 |
| `/api/testremind` | POST | — | 立即弹测试通知 |
| `/api/undo` | POST | — | 撤销上一步 |
| `/api/welcomeskip` / `/api/welcomereset` | POST | — | 欢迎页开关 |

</details>

---

## 🧪 测试

回归测试需要额外装一个开发依赖（**运行看板本身不需要任何第三方包**）：

```bash
pip install playwright && python -m playwright install chromium

python3 _x.py
```

回归测试会：把 `plan.json` 复制成 `_t_plan.json` → 用 `LEET_PLAN` / `LEET_PORT`
在 8799 端口起**副本服务** → 跑一组断言（提交 / 欠账分流 / 补做日 / 界面结构）→
关闭副本并删除临时文件。**你的真实数据全程只读。**

---

## 🤖 AI 协作开发

本项目由 **WorkBuddy**（AI Agent 工作台）与人协作完成 —— 需求、功能实现、UI 迭代、
Bug 排查均由 Agent 执行并验证。主力模型 **LongCat-2.5-Preview**，全程用量：

| 模型 | Token | 费用 | 占比 |
|------|------:|-----:|-----:|
| LongCat-2.5-Preview | 96.6M | $1.63 | 51.4% |
| hy4-preview | 49.9M | $3.03 | 26.5% |
| space-bunny | 41.1M | — | 21.8% |
| deepseek-v4-flash-ga-260731 | 579.6K | $0.02 | 0.3% |
| **合计** | **188.2M** | **$4.69** | 100% |

> 统计窗口 2026-10-05 ~ 2026-10-11。背景插画由 AI 图像生成 API 出图，
> 人工裁掉水印、调色压缩后作为页面背景。

整个项目从零到可用：**零第三方依赖、零构建工具、零部署**，一个 Python 文件就能跑起来。

---

## 📄 License

[MIT](LICENSE) © 2026 王小虎

题目内容来自 LeetCode 官方题库，仅供学习练习使用。