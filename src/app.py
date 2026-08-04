"""
LXL·QuantAxis v2.0 — 高级量化交易桌面应用
"""

import sys, os, json, threading, time, re, io
import tkinter as tk
from tkinter import ttk, scrolledtext

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ═══════════════════════════════════════════════════════════
# 主题
# ═══════════════════════════════════════════════════════════
BG0  = "#060912"
BG1  = "#0b0f1a"
BG2  = "#111827"
BG3  = "#1a2332"
BG4  = "#1f2a3a"
ACC  = "#3b82f6"
ACC2 = "#8b5cf6"
GRN  = "#10b981"
RED  = "#ef4444"
YLW  = "#f59e0b"
CYN  = "#06b6d4"
PNK  = "#ec4899"
TX1  = "#f1f5f9"
TX2  = "#94a3b8"
TX3  = "#475569"

F1   = ("Segoe UI", 10)
F2   = ("Segoe UI", 9)
F3   = ("Segoe UI", 12, "bold")
F4   = ("Segoe UI", 7, "bold")
FM   = ("Cascadia Code", 10)
FT   = ("Segoe UI", 22, "bold")
FST  = ("Segoe UI", 8)


class PrintRedirector:
    def __init__(self, w): self.w = w
    def write(self, t):
        try: self.w.insert(tk.END, t); self.w.see(tk.END); self.w.update()
        except: pass
    def flush(self): pass


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("LXL·QuantAxis v2.0")
        self.root.geometry("1300x900")
        self.root.minsize(1100, 720)
        self.root.configure(bg=BG0)

        # 图标
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "LXL_icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except: pass

        self._build()
        self._welcome()

    # ═══════════════ 布局 ═══════════════
    def _build(self):
        # ── 顶栏 ──
        tb = tk.Frame(self.root, bg=BG0, height=52)
        tb.pack(fill=tk.X, padx=20, pady=(14, 0)); tb.pack_propagate(False)

        logo = tk.Frame(tb, bg=BG0); logo.pack(side=tk.LEFT)
        tk.Label(logo, text="LXL", font=("Segoe UI", 20, "bold"),
                bg=BG0, fg=ACC).pack(side=tk.LEFT)
        tk.Label(logo, text="·QuantAxis", font=("Segoe UI", 20, "bold"),
                bg=BG0, fg="#f1f5f9").pack(side=tk.LEFT)
        tk.Label(logo, text="v2.0", font=FST, bg=BG0, fg=TX3).pack(side=tk.LEFT, padx=(8,0))

        self.sts = tk.Label(tb, text="", font=FST, bg=BG0, fg=GRN)
        self.sts.pack(side=tk.RIGHT, padx=(0,8))
        self._upd_sts()

        # ── 主体 ──
        main = tk.Frame(self.root, bg=BG0)
        main.pack(fill=tk.BOTH, expand=True, padx=16, pady=(10, 14))

        # ── 左侧栏 ──
        sw = 280
        sb = tk.Frame(main, bg=BG1, width=sw)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        sb.pack_propagate(False)

        sc = tk.Canvas(sb, bg=BG1, highlightthickness=0, width=sw-4)
        ss = tk.Scrollbar(sb, orient=tk.VERTICAL, command=sc.yview, width=6)
        ss.pack(side=tk.RIGHT, fill=tk.Y)
        sc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4,0))

        si = tk.Frame(sc, bg=BG1)
        sc.create_window((0,0), window=si, anchor=tk.NW, width=sw-12)
        si.bind("<Configure>", lambda e: sc.configure(scrollregion=sc.bbox("all")))
        sc.configure(yscrollcommand=ss.set)
        def _mw(e): sc.yview_scroll(int(-1*(e.delta/120)), "units")
        sc.bind_all("<MouseWheel>", _mw)

        groups = [
            ("DASHBOARD", "管理中枢", ACC, [
                ("仪表盘 (浏览器)", self._dashboard),
                ("下载数据", self._download),
                ("系统状态", self._status),
            ]),
            ("TRADING", "交易实战", GRN, [
                ("快速验证", self._quick_backtest_dialog),
                ("个股诊断", self._diagnosis_dialog),
                ("智能推荐", self._recommend_dialog),
                ("因子策略", self._factor_strategy_dialog),
                ("每日快扫", self._daily_scan_gui),
                ("交易日志 (终端)", self._journal),
            ]),
            ("STRATEGIES", "策略研发", ACC2, [
                ("策略管理中枢", self._strategy_hub),
                ("AI策略战法", self._strategy_lab),
            ]),
            ("ALPHA MEMORY", "Alpha 记忆 (v2.0)", CYN, [
                ("Alpha 信号面板", self._alpha_panel),
                ("因子健康度", self._factor_health),
                ("策略银行 (统一)", self._unified_bank),
                ("IC 衰减状态", self._ic_decay_status),
            ]),
            ("PAPER BROKER", "纸面券商 (v2.0)", PNK, [
                ("券商状态", self._broker_status),
                ("订单管理", self._broker_orders),
                ("自动交易开关", self._broker_auto_trade),
            ]),
            ("DATA", "数据中心 (v2.0)", YLW, [
                ("宏观数据面板", self._macro_panel),
                ("基本面数据", self._fundamental_panel),
                ("行业分类", self._industry_panel),
            ]),
            ("INDEX", "指数增强", YLW, [
                ("指数估值快照", self._valuation),
                ("轮动+定投对比", self._rotation),
            ]),
            ("AI", "AI 智能体", CYN, [
                ("AI 对话", self._chat),
                ("策略工厂 (自进化)", self._factory),
                ("策略银行", self._bank),
                ("配置 AI", self._ai_cfg),
                ("AI 复盘 & 顾问", self._ai_review),
                ("AI 市场简报", self._ai_brief),
            ]),
            ("ANALYSIS", "分析复盘", PNK, [
                ("绩效分析报告", self._analysis),
                ("因子体系 (28)", self._factors),
            ]),
        ]

        for tag, name, accent, btns in groups:
            # 组头
            h = tk.Frame(si, bg=BG1); h.pack(fill=tk.X, padx=14, pady=(14,2))
            tk.Label(h, text=tag, font=F4, bg=BG1, fg=TX3).pack(side=tk.LEFT)
            tk.Label(h, text=name, font=F2, bg=BG1, fg=accent).pack(side=tk.LEFT, padx=(4,0))

            for label, cmd in btns:
                self._side_btn(si, label, cmd, accent)

        tk.Label(si, text="LXL·QuantAxis v2.0", font=FST, bg=BG1, fg=TX3).pack(pady=(20,10))

        # ── 右侧 ──
        rt = tk.Frame(main, bg=BG0)
        rt.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(12,0))

        # KPI 卡片行
        kf = tk.Frame(rt, bg=BG0, height=96)
        kf.pack(fill=tk.X, pady=(0, 12)); kf.pack_propagate(False)
        self._kpi = {}
        for i, (k, lbl, v, clr) in enumerate([
            ("trades", "交易记录", "0", ACC),
            ("pos", "当前持仓", "0", YLW),
            ("pnl", "总盈亏", "¥0", GRN),
            ("bt", "回测次数", "0", ACC2),
        ]):
            c = tk.Frame(kf, bg=BG2); c.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0 if i==0 else 4, 0 if i==3 else 4))
            tk.Label(c, text=lbl, font=("Segoe UI", 9), bg=BG2, fg=TX3).pack(pady=(16, 0))
            vl = tk.Label(c, text=v, font=("Segoe UI", 26, "bold"), bg=BG2, fg=clr)
            vl.pack(pady=(2, 8)); self._kpi[k] = vl

        # 输出面板 — 现代化风格
        cw = tk.Frame(rt, bg=BG2)
        cw.pack(fill=tk.BOTH, expand=True)

        ch = tk.Frame(cw, bg=BG2, height=38)
        ch.pack(fill=tk.X, padx=16)
        ch.pack_propagate(False)
        tk.Label(ch, text="📋 输出面板", font=("Segoe UI", 10, "bold"), bg=BG2, fg=TX2).pack(side=tk.LEFT, pady=(10, 0))
        clear_btn = tk.Label(ch, text="CLEAR", font=("Segoe UI", 9, "bold"), bg=BG2, fg=ACC, cursor="hand2")
        clear_btn.pack(side=tk.RIGHT, pady=(10, 0))
        clear_btn.bind("<Button-1>", lambda e: self._clr())

        self.con = scrolledtext.ScrolledText(cw, font=("Cascadia Code", 11), bg="#080c16",
            fg="#c9d1d9", insertbackground=GRN, relief=tk.FLAT, bd=0, padx=18, pady=14,
            wrap=tk.WORD)
        self.con.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0, 2))

        # 彩色标签配置
        self.con.tag_configure("time", foreground="#C9A227", font=("Cascadia Code", 9))
        self.con.tag_configure("success", foreground="#10b981", font=("Cascadia Code", 11))
        self.con.tag_configure("error", foreground="#ef4444", font=("Cascadia Code", 11))
        self.con.tag_configure("warn", foreground="#f59e0b", font=("Cascadia Code", 11))
        self.con.tag_configure("info", foreground="#3b82f6", font=("Cascadia Code", 11))

        # 输入栏 — 更现代
        inf = tk.Frame(rt, bg=BG0, height=44)
        inf.pack(fill=tk.X, pady=(10, 0))
        inf.pack_propagate(False)
        tk.Label(inf, text="❯", font=("Cascadia Code", 12, "bold"), bg=BG0, fg=GRN).pack(side=tk.LEFT, padx=(4, 10))
        self.inp = tk.Entry(inf, font=("Cascadia Code", 11), bg=BG3, fg=TX1,
                           insertbackground=GRN, relief=tk.FLAT, bd=0, insertwidth=2)
        self.inp.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        self.inp.bind("<Return>", self._input)
        self.inp.insert(0, "help")

        self._upd_kpi()

    def _side_btn(self, parent, text, cmd, accent):
        """绘制侧边栏按钮 — 金色悬停效果"""
        f = tk.Frame(parent, bg=BG1, cursor="hand2"); f.pack(fill=tk.X, pady=1, padx=8)
        # 色条
        bar = tk.Canvas(f, width=3, height=28, bg=BG1, highlightthickness=0)
        bar.pack(side=tk.LEFT, padx=(0,6))
        bar.create_rectangle(0,0,3,28, fill=accent, outline="")
        # 文字
        lbl = tk.Label(f, text=text, font=F2, bg=BG1, fg=TX2, anchor=tk.W, padx=4, pady=5)
        lbl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # 箭头
        arw = tk.Label(f, text="›", font=("Segoe UI", 14), bg=BG1, fg=TX3, padx=4)
        arw.pack(side=tk.RIGHT)

        def _on(e):
            f.configure(bg=BG2); lbl.configure(bg=BG2); arw.configure(bg=BG2, fg=accent)
            bar.configure(bg=BG2); bar.create_rectangle(0,0,3,28, fill=accent, outline="")
        def _off(e):
            f.configure(bg=BG1); lbl.configure(bg=BG1, fg="#f1f5f9"); arw.configure(bg=BG1, fg=TX3)
            bar.configure(bg=BG1); bar.create_rectangle(0,0,3,28, fill=accent, outline="")
        def _clk(e): cmd()

        for w in [f, lbl, arw, bar]:
            w.bind("<Enter>", _on); w.bind("<Leave>", _off); w.bind("<Button-1>", _clk)

    # ═══════════════ 工具 ═══════════════
    def _log(self, msg, tag=None):
        """带彩色标签的日志输出"""
        try:
            now = __import__('datetime').datetime.now().strftime("%H:%M:%S")
            if tag == "success" or tag == "ok":
                self.con.insert(tk.END, f"[{now}] ", "time")
                self.con.insert(tk.END, f"{msg}\n", "success")
            elif tag == "error" or tag == "err":
                self.con.insert(tk.END, f"[{now}] ", "time")
                self.con.insert(tk.END, f"{msg}\n", "error")
            elif tag == "warn":
                self.con.insert(tk.END, f"[{now}] ", "time")
                self.con.insert(tk.END, f"{msg}\n", "warn")
            elif tag == "info":
                self.con.insert(tk.END, f"[{now}] ", "time")
                self.con.insert(tk.END, f"{msg}\n", "info")
            else:
                self.con.insert(tk.END, f"[{now}] {msg}\n")
            self.con.see(tk.END)
            self.con.update()
        except:
            pass

    def _clr(self): self.con.delete(1.0, tk.END); self._welcome()

    def _welcome(self):
        """欢迎信息"""
        self._log("╔══════════════════════════════════════╗")
        self._log("║   LXL·QuantAxis v2.0  量化交易平台   ║")
        self._log("║   输入 help 查看可用命令             ║")
        self._log("╚══════════════════════════════════════╝")

    def _upd_sts(self):
        try:
            from src.models.trade import TradeRepository
            n = TradeRepository().count()
            self.sts.configure(text=f"SYS OK · {n} TRADES")
        except: self.sts.configure(text="SYS OK")

    def _upd_kpi(self):
        try:
            from src.models.trade import TradeRepository
            from src.backtest.batch_runner import ResultDB
            repo = TradeRepository(); db = ResultDB()
            pnl = [p["net_pnl"] for p in repo.get_all_pnl()]
            tp = sum(pnl) if pnl else 0
            self._kpi["trades"].configure(text=str(repo.count()))
            self._kpi["pos"].configure(text=str(len(repo.find_open_positions())))
            c = GRN if tp >= 0 else RED
            self._kpi["pnl"].configure(text=f"¥{tp:+,.0f}", fg=c)
            self._kpi["bt"].configure(text=str(db.summary().get("总回测数",0)))
        except: pass

    def _bg(self, fn, label="RUNNING"):
        def w():
            old = sys.stdout; sys.stdout = PrintRedirector(self.con)
            try:
                self.root.after(0, lambda: self.sts.configure(text=label, fg=YLW))
                fn()
            except Exception as e: self._log(f"\n[ERR] {e}")
            finally:
                sys.stdout = old; self._upd_sts(); self._upd_kpi()
        threading.Thread(target=w, daemon=True).start()

    def _input(self, ev):
        c = self.inp.get().strip(); self.inp.delete(0, tk.END)
        if not c: return
        self._log(f"\n$ {c}")
        cm = {
            "help": lambda: self._log(
                "  命令: status batch valuation rotation optimize ai bank factory clear exit\n"
                "  v2.0: alpha health bank2 ic broker orders autotrade macro pe <code>"
            ),
            "status": self._status, "batch": self._batch, "valuation": self._valuation,
            "rotation": self._rotation, "optimize": self._optimize, "ai": self._ai_brief,
            "ai-config": self._ai_cfg, "bank": self._bank, "factory": self._factory,
            "clear": self._clr, "exit": self.root.destroy,
            # v2.0 命令
            "alpha": lambda: self._bg(lambda: self._run_alpha_panel(), "ALPHA"),
            "health": lambda: self._bg(lambda: self._run_factor_health(), "HEALTH"),
            "bank2": lambda: self._bg(lambda: self._run_unified_bank(), "BANK2"),
            "ic": lambda: self._bg(lambda: self._run_ic_decay_status(), "IC"),
            "broker": lambda: self._bg(lambda: self._run_broker_status(), "BROKER"),
            "orders": lambda: self._bg(lambda: self._run_broker_orders(), "ORDERS"),
            "autotrade": self._broker_auto_trade,
            "macro": lambda: self._bg(lambda: self._run_macro_panel(), "MACRO"),
            "pe": lambda: self._bg(lambda: self._run_pe_lookup("600519"), "PE"),
        }
        # 特殊: pe <code> 查询
        if c.lower().startswith("pe "):
            sym = c[3:].strip()
            self._bg(lambda s=sym: self._run_pe_lookup(s), "PE_LOOKUP")
            return
        if c.lower() in cm: cm[c.lower()]()
        else: self._log(f"  未知。help=命令列表")

    # ═══════════════ AI 聊天 ═══════════════
    def _chat(self):
        dlg = tk.Toplevel(self.root); dlg.title("LXL · AI 助手"); dlg.geometry("740x660")
        dlg.configure(bg=BG0); dlg.transient(self.root)

        tk.Label(dlg, text="LXL · AI 量化智能体", font=FT, bg=BG0, fg=TX1).pack(pady=(14,2))
        tk.Label(dlg, text="对话提问 · 语音操控系统 · Ctrl+Enter", font=FST, bg=BG0, fg=TX3).pack(pady=(0,10))

        mf = tk.Frame(dlg, bg=BG0); mf.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0,8))
        mc = tk.Canvas(mf, bg=BG0, highlightthickness=0)
        ms = tk.Scrollbar(mf, orient=tk.VERTICAL, command=mc.yview, width=6)
        ms.pack(side=tk.RIGHT, fill=tk.Y); mc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        msgs = tk.Frame(mc, bg=BG0)
        mc.create_window((0,0), window=msgs, anchor=tk.NW, width=680)
        msgs.bind("<Configure>", lambda e: mc.configure(scrollregion=mc.bbox("all")))
        mc.configure(yscrollcommand=ms.set)

        hist = [{"role":"system","content":"你是LXL的量化智能体。可以聊天，也可以操控系统(回测/估值/进化等)。涉及投资声明仅供参考。"}]

        def add(role, text, color=None):
            is_u = role=="user"; is_s = role=="system"
            bf = tk.Frame(msgs, bg=BG0); bf.pack(fill=tk.X, pady=4, padx=(48 if is_u else 0, 0 if is_u else 48))
            c = color or (BG3 if not is_u else "#1e3a5f")
            inner = tk.Frame(bf, bg=c); inner.pack(side=tk.RIGHT if is_u else tk.LEFT, fill=tk.X)
            tk.Label(inner, text="YOU" if is_u else ("SYS" if is_s else "AI"),
                    font=F4, bg=inner["bg"], fg=ACC if is_u else (YLW if is_s else GRN)
                    ).pack(anchor=tk.W, padx=10, pady=(8,0))
            l = tk.Label(inner, text=text, font=F1, bg=inner["bg"], fg=TX1,
                        justify=tk.LEFT, wraplength=520, padx=10, pady=(4,8))
            l.pack(); mc.yview_moveto(1.0); return l

        def exec_cmd(action, arg=""):
            buf = io.StringIO(); old = sys.stdout; sys.stdout = buf
            try:
                if action == "backtest":
                    sym = arg or "601398"
                    add("system", f"[回测] {sym} ...", BG3)
                    from src.backtest.data_feed import get_data
                    from src.backtest.engine import BacktestEngine
                    from src.backtest.batch_runner import _make_strategy_instance
                    d = get_data(sym,"A股",start_date="2024-01-01")
                    s = _make_strategy_instance("ma_cross",{},sym)
                    r = BacktestEngine().run(s,d)
                    res = f"[回测: {sym}] {len(d)}条\n"
                    for k,v in r["metrics"].items(): res += f"  {k}: {v}\n"
                    return res
                elif action == "batch":
                    add("system", "[批量回测] 5x5 ...", BG3)
                    from src.backtest.batch_runner import BatchRunner
                    ru = BatchRunner()
                    ru.add_symbols(["601398","000858","600036","600900","000333"])
                    ru.add_strategies(["ma_cross","rsi","macd","contrarian_v1","trend_following_v1"])
                    ru.start_date="2024-01-01"
                    df = ru.run(verbose=False)
                    if not df.empty: ru.show_ranking()
                    return f"\n[批量回测] {len(df)} 条结果"
                elif action == "valuation":
                    add("system", "[估值快照]", BG3)
                    from src.index.valuation import show_valuation; show_valuation()
                elif action == "rotation":
                    add("system", "[指数对比]", BG3)
                    from src.index.rotation import compare_index_strategies; compare_index_strategies("2022-01-01")
                elif action == "factory":
                    add("system", "[AI策略工厂] 启动进化...", BG3)
                    from src.ai.factory import auto_evolve
                    auto_evolve(symbol="601398", generations=3, use_ai=True)
                    return "[进化完成] 最佳策略已存入银行"
                elif action == "bank":
                    from src.ai.factory import show_bank; show_bank()
                elif action == "status":
                    self._status()
                elif action == "dashboard":
                    from src.dashboard.visual import open_all; open_all()
                    return "[仪表盘] 已打开"
                elif action == "download":
                    from src.backtest.data_feed import download_all_default; download_all_default()
                    return "[下载] 完成"
                elif action == "factors":
                    from src.factors.definitions import FACTOR_REGISTRY
                    res = f"[因子] {len(FACTOR_REGISTRY)}个:\n"
                    for n,f in FACTOR_REGISTRY.items(): res+=f"  [{f.category}] {n}\n"
                    return res
                else: return f"[?] {action}"
                return buf.getvalue() or "[OK]"
            except Exception as e: return f"[FAIL] {e}"
            finally: sys.stdout = old

        def quick(text):
            t=text.lower().replace(" ","")
            for ks, act in [
                (["回测","跑一下","backtest"],"backtest"),
                (["批量回测","batch","全部回测"],"batch"),
                (["估值","valuation"],"valuation"),
                (["轮动","定投","rotation"],"rotation"),
                (["进化","策略工厂","factory","evolve"],"factory"),
                (["策略银行","银行","bank"],"bank"),
                (["优化","optimize"],"optimize"),
                (["下载","download"],"download"),
                (["仪表盘","dashboard","图表"],"dashboard"),
                (["状态","status"],"status"),
                (["因子","factors"],"factors"),
            ]:
                if any(k in t for k in ks):
                    codes = re.findall(r'\b(60\d{4}|00\d{4}|30\d{4}|68\d{4})\b', text)
                    return act, (codes[0] if codes else "")
            return None, None

        def send():
            txt = ci.get("1.0",tk.END).strip()
            if not txt: return
            ci.delete("1.0",tk.END); add("user", txt)

            # 快速匹配
            act, arg = quick(txt)
            if act:
                res = exec_cmd(act, arg)
                if res: add("system", res)
                # AI 总结
                hist.append({"role":"user","content":f"[系统执行:{act}]\n{res[:300]}\n简短总结一下。"})
                b = add("assistant","")
                full=[]
                def s2():
                    try:
                        from src.ai.engine import LLMClient
                        for ck in LLMClient().chat_stream(hist):
                            full.append(ck)
                            try: b.configure(text="".join(full)); mc.yview_moveto(1.0); dlg.update()
                            except: pass
                        hist.append({"role":"assistant","content":"".join(full)})
                    except: pass
                threading.Thread(target=s2,daemon=True).start()
                return

            # AI 对话
            hist.append({"role":"user","content":txt})
            b = add("assistant","")
            full=[]
            def s1():
                try:
                    from src.ai.engine import LLMClient
                    for ck in LLMClient().chat_stream(hist):
                        full.append(ck)
                        try: b.configure(text="".join(full)); mc.yview_moveto(1.0); dlg.update()
                        except: pass
                    reply = "".join(full)
                    # 检测 JSON 命令
                    jm = re.search(r'\{[^{}]*"action"\s*:\s*"(\w+)"[^{}]*\}', reply)
                    if jm:
                        a2=jm.group(1); aa=""
                        am=re.search(r'"arg"\s*:\s*"([^"]*)"',reply)
                        if am: aa=am.group(1)
                        r2=exec_cmd(a2,aa)
                        if r2: add("system", r2)
                    hist.append({"role":"assistant","content":reply})
                    if len(hist)>20: del hist[1:3]
                except Exception as e:
                    b.configure(text=f"[连接失败] {e}\n请先配置AI(左侧→AI→配置AI)")
            threading.Thread(target=s1,daemon=True).start()

        # 输入
        fi = tk.Frame(dlg, bg=BG0, height=68); fi.pack(fill=tk.X, padx=14, pady=(4,12)); fi.pack_propagate(False)
        ci = tk.Text(fi, font=F1, bg=BG3, fg=TX1, insertbackground=GRN,
                    relief=tk.FLAT, bd=0, padx=12, pady=10, wrap=tk.WORD, height=3)
        ci.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ci.bind("<Control-Return>", lambda e: send())
        tk.Button(fi, text="发送", font=F3, bg=ACC, fg="white", relief=tk.FLAT, bd=0,
                 padx=16, pady=8, cursor="hand2", command=send).pack(side=tk.RIGHT, padx=(8,0))

        # 快捷
        qf = tk.Frame(dlg, bg=BG0); qf.pack(fill=tk.X, padx=14, pady=(0,8))
        for lbl, txt in [
            ("跑回测","跑一下601398的回测"),
            ("批量回测","批量回测全部"),
            ("估值","查看指数估值"),
            ("进化","启动策略工厂进化"),
            ("自由聊","分析当前市场应该用什么策略"),
        ]:
            b = tk.Label(qf, text=lbl, font=FST, bg=BG3, fg=TX2, padx=10, pady=4, cursor="hand2")
            b.pack(side=tk.LEFT, padx=2)
            b.bind("<Button-1>", lambda e,t=txt: (ci.delete("1.0",tk.END), ci.insert("1.0",t), send()))
            b.bind("<Enter>", lambda e,w=b: w.configure(fg=TX1, bg=BG4))
            b.bind("<Leave>", lambda e,w=b: w.configure(fg=TX2, bg=BG3))

    # ═══════════════ 功能 ═══════════════
    def _dashboard(self):
        self._log("\n[仪表盘] 打开浏览器...")
        try:
            from src.dashboard.visual import open_all; open_all()
            self._log("[OK] 3个面板已在浏览器中打开")
        except Exception as e: self._log(f"[FAIL] {e}")

    def _download(self):
        self._bg(lambda: (
            self._log("\n[数据下载]"),
            __import__('src.backtest.data_feed', fromlist=['download_all_default']).download_all_default(),
            self._log("[OK] 完成")
        ), "DOWNLOADING")

    def _journal(self):
        """交易日志 GUI"""
        j = tk.Toplevel(self.root); j.title("LXL · 交易日志"); j.geometry("780x620")
        j.configure(bg=BG0); j.transient(self.root)

        tk.Label(j, text="LXL · 交易日志", font=FT, bg=BG0, fg=TX1).pack(pady=(14,2))
        tk.Label(j, text="记录买卖 · 持仓管理 · 复盘笔记 · 盈亏汇总", font=FST, bg=BG0, fg=TX3).pack(pady=(0,10))

        # 标签栏
        nb = ttk.Notebook(j); nb.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0,14))
        s1 = ttk.Style(); s1.theme_use("clam")
        s1.configure("TNotebook", background=BG0, borderwidth=0)
        s1.configure("TNotebook.Tab", background=BG2, foreground=TX2, padding=[20,8],
                     font=F1, borderwidth=0)
        s1.map("TNotebook.Tab", background=[("selected", BG3)], foreground=[("selected", TX1)])

        # ═══ Tab 1: 记录买卖 ═══
        t1 = tk.Frame(nb, bg=BG0); nb.add(t1, text=" 记录买卖 ")
        self._journal_trade_tab(t1)

        # ═══ Tab 2: 持仓 ═══
        t2 = tk.Frame(nb, bg=BG0); nb.add(t2, text=" 当前持仓 ")

        pos_tree = ttk.Treeview(t2, columns=("id","market","sym","name","dir","date","price","qty","reason"),
                               show="headings", height=15)
        for col, txt, w in [
            ("id","ID",35),("market","市场",50),("sym","代码",80),("name","名称",80),
            ("dir","方向",50),("date","买入日",90),("price","成本",70),("qty","数量",60),
            ("reason","理由",150),
        ]:
            pos_tree.heading(col, text=txt); pos_tree.column(col, width=w, anchor="center")
        pos_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def _refresh_positions():
            pos_tree.delete(*pos_tree.get_children())
            from src.models.trade import TradeRepository
            for p in TradeRepository().find_open_positions():
                pos_tree.insert("","end", values=(p.id,p.market,p.symbol,p.name,p.direction,
                    p.trade_date,f"¥{p.price:.2f}",p.quantity,p.reason or ""))
        _refresh_positions()

        rf = tk.Frame(t2, bg=BG0); rf.pack(fill=tk.X, padx=10, pady=(0,10))
        tk.Button(rf, text="刷新", font=F1, bg=ACC, fg="white", relief=tk.FLAT, bd=0,
                 padx=14, pady=4, cursor="hand2", command=_refresh_positions).pack(side=tk.LEFT)

        # ═══ Tab 3: 交易记录 ═══
        t3 = tk.Frame(nb, bg=BG0); nb.add(t3, text=" 交易记录 ")

        hist_tree = ttk.Treeview(t3, columns=("id","date","market","sym","name","type","price","qty","pnl"),
                                show="headings", height=15)
        for col, txt, w in [
            ("id","ID",35),("date","日期",90),("market","市场",50),("sym","代码",80),
            ("name","名称",80),("type","类型",50),("price","价格",70),("qty","数量",60),
            ("pnl","盈亏",90),
        ]:
            hist_tree.heading(col, text=txt); hist_tree.column(col, width=w, anchor="center")
        hist_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def _refresh_history():
            hist_tree.delete(*hist_tree.get_children())
            from src.models.trade import TradeRepository
            repo = TradeRepository()
            for t in repo.find_all(limit=100):
                pnl_str = ""
                if t.trade_type == "买入" and t.paired_trade_id:
                    p = repo.calc_pnl(t.id)
                    if p: pnl_str = f"¥{p['net_pnl']:+,.2f}"
                hist_tree.insert("","end", values=(t.id,t.trade_date,t.market,t.symbol,t.name,
                    t.trade_type,f"¥{t.price:.2f}",t.quantity,pnl_str))
        _refresh_history()

        hf = tk.Frame(t3, bg=BG0); hf.pack(fill=tk.X, padx=10, pady=(0,10))
        tk.Button(hf, text="刷新", font=F1, bg=ACC, fg="white", relief=tk.FLAT, bd=0,
                 padx=14, pady=4, cursor="hand2", command=_refresh_history).pack(side=tk.LEFT)

        # ═══ Tab 4: 盈亏汇总 ═══
        t4 = tk.Frame(nb, bg=BG0); nb.add(t4, text=" 盈亏汇总 ")
        pnl_text = tk.Text(t4, font=FM, bg=BG0, fg=TX1, relief=tk.FLAT, bd=0, padx=14, pady=14)
        pnl_text.pack(fill=tk.BOTH, expand=True)

        def _refresh_pnl():
            pnl_text.delete(1.0,tk.END)
            from src.models.trade import TradeRepository
            repo = TradeRepository()
            pnl = repo.get_all_pnl()
            if not pnl:
                pnl_text.insert(1.0,"暂无已完成交易")
                return
            tp = sum(p["net_pnl"] for p in pnl)
            ws = len([p for p in pnl if p["net_pnl"]>0])
            ls = len([p for p in pnl if p["net_pnl"]<=0])
            pnl_text.insert(tk.END, f"已完成交易: {len(pnl)}笔\n")
            pnl_text.insert(tk.END, f"总盈亏: ¥{tp:+,.2f}\n")
            pnl_text.insert(tk.END, f"胜率: {ws/max(len(pnl),1)*100:.1f}% ({ws}赢/{ls}亏)\n")
            pnl_text.insert(tk.END, "─"*40+"\n")
            for p in sorted(pnl, key=lambda x: x["net_pnl"], reverse=True)[:20]:
                em = "+" if p["net_pnl"]>=0 else ""
                pnl_text.insert(tk.END,
                    f"{p['sell_date']} {p['market']} {p['symbol']} {p['name']}: "
                    f"¥{p['net_pnl']:+,.2f} ({p['pnl_pct']:+4.1f}%)\n")
        _refresh_pnl()

        pf2 = tk.Frame(t4, bg=BG0); pf2.pack(fill=tk.X, padx=10, pady=(0,10))
        tk.Button(pf2, text="刷新", font=F1, bg=ACC, fg="white", relief=tk.FLAT, bd=0,
                 padx=14, pady=4, cursor="hand2", command=_refresh_pnl).pack(side=tk.LEFT)

        # ═══ Tab 5: 复盘笔记 ═══
        t5 = tk.Frame(nb, bg=BG0); nb.add(t5, text=" 复盘 ")
        rv_frame = tk.Frame(t5, bg=BG0); rv_frame.pack(fill=tk.X, padx=14, pady=(14,0))

        tk.Label(rv_frame, text="交易ID:", font=F1, bg=BG0, fg=TX2).pack(side=tk.LEFT, padx=(0,6))
        rv_id = tk.Entry(rv_frame, font=F1, bg=BG3, fg=TX1, relief=tk.FLAT, bd=0, width=8)
        rv_id.pack(side=tk.LEFT, padx=(0,8))
        rv_info = tk.Label(rv_frame, text="", font=FST, bg=BG0, fg=TX3)
        rv_info.pack(side=tk.LEFT, padx=(8,0))

        def _load_trade():
            tid = rv_id.get().strip()
            if not tid: return
            try:
                from src.models.trade import TradeRepository
                t = TradeRepository().get_by_id(int(tid))
                if t:
                    rv_info.configure(text=f"{t.trade_date} {t.symbol} {t.name} {t.trade_type} ¥{t.price:.2f}×{t.quantity}")
                    rv_notes.delete(1.0,tk.END); rv_notes.insert(1.0, t.review_notes or "")
                    rv_score.set(str(t.review_score) if t.review_score else "0")
                else:
                    rv_info.configure(text="未找到")
            except: pass

        tk.Button(rv_frame, text="加载", font=F1, bg=ACC, fg="white", relief=tk.FLAT, bd=0,
                 padx=10, pady=2, cursor="hand2", command=_load_trade).pack(side=tk.LEFT, padx=(0,12))

        tk.Label(rv_frame, text="评分(1-5):", font=F1, bg=BG0, fg=TX2).pack(side=tk.LEFT, padx=(0,4))
        rv_score = tk.StringVar(value="0")
        tk.Spinbox(rv_frame, from_=0, to=5, textvariable=rv_score, font=F1, width=4,
                  bg=BG3, fg=TX1, relief=tk.FLAT, bd=0).pack(side=tk.LEFT)

        rv_notes = tk.Text(t5, font=F1, bg=BG3, fg=TX1, insertbackground=GRN,
                          relief=tk.FLAT, bd=0, padx=14, pady=14, height=12)
        rv_notes.pack(fill=tk.BOTH, expand=True, padx=14, pady=(8,8))

        def _save_review():
            tid = rv_id.get().strip()
            if not tid: return
            try:
                from src.models.trade import TradeRepository
                TradeRepository().update_review(int(tid), rv_notes.get(1.0,tk.END).strip(),
                                                int(rv_score.get()))
                self._log(f"[复盘] ID={tid} 已保存")
            except Exception as e: self._log(f"[复盘失败] {e}")

        bf3 = tk.Frame(t5, bg=BG0); bf3.pack(fill=tk.X, padx=14, pady=(0,10))
        tk.Button(bf3, text="保存复盘", font=F3, bg=GRN, fg="white", relief=tk.FLAT, bd=0,
                 padx=16, pady=6, cursor="hand2", command=_save_review).pack(side=tk.LEFT)

    def _journal_trade_tab(self, parent):
        """交易录入表单"""
        f = tk.Frame(parent, bg=BG0); f.pack(fill=tk.BOTH, padx=14, pady=14)

        def _field(row, label, var=None, default="", width=20):
            tk.Label(f, text=label, font=F1, bg=BG0, fg=TX2).grid(row=row, column=0,
                     sticky=tk.W, padx=(0,10), pady=4)
            v = var or tk.StringVar(value=default)
            e = tk.Entry(f, textvariable=v, font=F1, bg=BG3, fg=TX1, relief=tk.FLAT, bd=0, width=width)
            e.grid(row=row, column=1, sticky=tk.EW, pady=4, ipady=4)
            return v, e

        market_var, _ = _field(0, "市场", default="A股")
        sym_var, sym_entry = _field(1, "代码", default="601398")
        name_var, name_entry = _field(2, "名称", default="工商银行")

        # 自动补全 — 输入代码自动填名称
        def _auto_name(*args):
            code = sym_var.get().strip()
            if len(code) >= 4:
                try:
                    from src.data.stock_db import ensure_stock_db
                    db = ensure_stock_db()
                    n = db.get_name(code)
                    if n and n != code:
                        name_var.set(n)
                    # 也显示匹配列表
                    suggestions = db.autocomplete(code, limit=5)
                    if suggestions:
                        suggest_var.set(" | ".join(suggestions))
                except Exception:
                    pass
            else:
                suggest_var.set("")

        sym_var.trace_add("write", _auto_name)

        # 名称搜索 — 输入名称找代码
        def _auto_code(*args):
            kw = name_var.get().strip()
            if len(kw) >= 2:
                try:
                    from src.data.stock_db import ensure_stock_db
                    results = ensure_stock_db().search(kw, limit=3)
                    if results:
                        r = results[0]
                        if r["code"] != sym_var.get().strip():
                            sym_var.set(r["code"])
                except Exception:
                    pass

        name_var.trace_add("write", _auto_code)

        # 建议栏
        suggest_var = tk.StringVar()
        tk.Label(f, text="", textvariable=suggest_var, font=FST, bg=BG0, fg=TX3,
                wraplength=400).grid(row=3, column=1, sticky=tk.W, pady=(0,8))
        dir_var = _field(3, "方向", default="做多")

        from datetime import datetime
        date_var = _field(4, "日期", default=datetime.now().strftime("%Y-%m-%d"))

        type_var = tk.StringVar(value="买入")
        tf = tk.Frame(f, bg=BG0); tf.grid(row=5, column=1, sticky=tk.W, pady=4)
        tk.Radiobutton(tf, text="买入", variable=type_var, value="买入",
                      font=F1, bg=BG0, fg=GRN, selectcolor=BG0, activebackground=BG0,
                      activeforeground=GRN).pack(side=tk.LEFT, padx=(0,12))
        tk.Radiobutton(tf, text="卖出", variable=type_var, value="卖出",
                      font=F1, bg=BG0, fg=RED, selectcolor=BG0, activebackground=BG0,
                      activeforeground=RED).pack(side=tk.LEFT)
        tk.Label(f, text="类型", font=F1, bg=BG0, fg=TX2).grid(row=5, column=0,
                 sticky=tk.W, padx=(0,10), pady=4)

        price_var = _field(6, "价格", default="5.00")
        qty_var = _field(7, "数量", default="1000")
        fee_var = _field(8, "手续费", default="0")
        reason_var = _field(9, "理由", default="")
        tag_var = _field(10, "标签", default="")

        result_lbl = tk.Label(f, text="", font=F1, bg=BG0, fg=GRN)
        result_lbl.grid(row=12, column=0, columnspan=2, pady=(12,0))

        def _submit():
            try:
                from src.models.trade import Trade
                from src.models.trade import TradeRepository
                t = Trade(
                    market=market_var.get(), symbol=sym_var.get().upper(),
                    name=name_var.get(), direction=dir_var.get(),
                    trade_type=type_var.get(), trade_date=date_var.get(),
                    price=float(price_var.get()), quantity=int(qty_var.get()),
                    fee=float(fee_var.get()), reason=reason_var.get(), tags=tag_var.get(),
                )
                tid = TradeRepository().add(t)
                result_lbl.configure(text=f"已保存! ID={tid}", fg=GRN)
                self._log(f"[交易日志] {t.trade_type} {t.symbol} {t.name} ¥{t.price}×{t.quantity} ID={tid}")
                self._upd_kpi(); self._upd_sts()
            except Exception as e:
                result_lbl.configure(text=f"失败: {e}", fg=RED)

        bf4 = tk.Frame(f, bg=BG0); bf4.grid(row=11, column=1, sticky=tk.E, pady=(12,0))
        tk.Button(bf4, text="保存交易", font=F3, bg=GRN, fg="white", relief=tk.FLAT, bd=0,
                 padx=20, pady=8, cursor="hand2", command=_submit).pack()
        f.columnconfigure(1, weight=1)

    # ═══════════════ 策略管理中枢 ═══════════════
    def _strategy_hub(self):
        """策略管理中枢 — 所有策略集中管理"""
        h = tk.Toplevel(self.root); h.title("LXL · 策略管理中枢"); h.geometry("920x700")
        h.configure(bg=BG0); h.transient(self.root)

        tk.Label(h, text="LXL · 策略管理中枢", font=FT, bg=BG0, fg=TX1).pack(pady=(14,2))
        tk.Label(h, text="策略总览 | 单策略回测 | 批量对比 | 参数优化 | 策略进化",
                font=FST, bg=BG0, fg=TX3).pack(pady=(0,10))

        nb = ttk.Notebook(h); nb.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0,14))
        s2 = ttk.Style(); s2.theme_use("clam")
        s2.configure("TNotebook", background=BG0, borderwidth=0)
        s2.configure("TNotebook.Tab", background=BG2, foreground=TX2, padding=[18,8],
                     font=F1, borderwidth=0)
        s2.map("TNotebook.Tab", background=[("selected", BG3)], foreground=[("selected", TX1)])

        # ═══ Tab 1: 策略总览 ═══
        t1 = tk.Frame(nb, bg=BG0); nb.add(t1, text=" 策略总览 ")
        self._build_strategy_overview(t1)

        # ═══ Tab 2: 单策略回测 ═══
        t2 = tk.Frame(nb, bg=BG0); nb.add(t2, text=" 单策略回测 ")
        self._build_single_backtest_tab(t2)

        # ═══ Tab 3: 批量对比 ═══
        t3 = tk.Frame(nb, bg=BG0); nb.add(t3, text=" 批量对比 ")
        self._build_batch_compare_tab(t3)

        # ═══ Tab 4: 参数优化 ═══
        t4 = tk.Frame(nb, bg=BG0); nb.add(t4, text=" 参数优化 ")
        self._build_optimize_tab(t4)

        # ═══ Tab 5: 策略进化 ═══
        t5 = tk.Frame(nb, bg=BG0); nb.add(t5, text=" 策略进化 ")
        self._build_evolve_tab(t5)

    def _build_strategy_overview(self, parent):
        """策略总览 — 展示所有策略的详细信息"""
        from src.strategies.library import STRATEGIES
        from src.factors.composer import PRESET_STRATEGIES
        from src.factors.definitions import FACTOR_REGISTRY

        # 左侧策略列表
        left = tk.Frame(parent, bg=BG0, width=280); left.pack(side=tk.LEFT, fill=tk.Y, padx=(10,6), pady=10)
        left.pack_propagate(False)

        tk.Label(left, text="策略列表", font=F3, bg=BG0, fg=TX1).pack(anchor=tk.W, pady=(0,8))

        detail_text = tk.Text(parent, font=F1, bg=BG0, fg=TX1, relief=tk.FLAT, bd=0, padx=14, pady=10)
        detail_text.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=10, padx=(6,10))

        def show_detail(name, info, is_preset=False):
            detail_text.delete(1.0, tk.END)
            tag = "独有模板" if is_preset else "经典策略"
            detail_text.insert(tk.END, f"═══ {info['name']} ═══\n")
            detail_text.insert(tk.END, f"类型: {tag}\n")
            detail_text.insert(tk.END, f"描述: {info['description']}\n\n")

            # 从回测数据库加载该策略的表现
            from src.backtest.batch_runner import ResultDB
            db = ResultDB()
            results = db.query(strategy=name, limit=50)
            if results:
                import numpy as np
                sharpe_vals = [r["sharpe"] for r in results if r["sharpe"] != 0]
                ret_vals = [r["total_return"] for r in results]
                detail_text.insert(tk.END, "── 历史表现 ──\n")
                detail_text.insert(tk.END, f"  回测次数: {len(results)}\n")
                if sharpe_vals:
                    detail_text.insert(tk.END, f"  平均夏普: {np.mean(sharpe_vals):.2f}\n")
                    detail_text.insert(tk.END, f"  最佳夏普: {max(sharpe_vals):.2f}\n")
                if ret_vals:
                    detail_text.insert(tk.END, f"  平均收益: {np.mean(ret_vals):.1f}%\n")
                    detail_text.insert(tk.END, f"  最佳收益: {max(ret_vals):.1f}%\n")
                detail_text.insert(tk.END, f"  测试标的数: {len(set(r['symbol'] for r in results))}\n")
            else:
                detail_text.insert(tk.END, "暂无回测记录\n")

            if not is_preset and "params" in info:
                detail_text.insert(tk.END, "\n── 可调参数 ──\n")
                for k, v in info["params"].items():
                    detail_text.insert(tk.END, f"  {k}: {v}\n")

        # 经典策略按钮
        tk.Label(left, text="── 经典策略 (7) ──", font=FST, bg=BG0, fg=TX3).pack(anchor=tk.W, pady=(8,4))
        for name, info in STRATEGIES.items():
            b = tk.Label(left, text=f"  {info['name']}", font=F1, bg=BG1, fg=TX2,
                        anchor=tk.W, padx=10, pady=5, cursor="hand2")
            b.pack(fill=tk.X, pady=1)
            b.bind("<Button-1>", lambda e,n=name,i=info: show_detail(n, i))
            b.bind("<Enter>", lambda e,w=b: w.configure(bg=BG3, fg=TX1))
            b.bind("<Leave>", lambda e,w=b: w.configure(bg=BG1, fg=TX2))

        # 独有策略按钮
        tk.Label(left, text="── 独有模板 (4) ──", font=FST, bg=BG0, fg=TX3).pack(anchor=tk.W, pady=(12,4))
        for name, info in PRESET_STRATEGIES.items():
            b = tk.Label(left, text=f"  {info['name']}", font=F1, bg=BG1, fg=CYN,
                        anchor=tk.W, padx=10, pady=5, cursor="hand2")
            b.pack(fill=tk.X, pady=1)
            b.bind("<Button-1>", lambda e,n=name,i=info: show_detail(n, i, True))
            b.bind("<Enter>", lambda e,w=b: w.configure(bg=BG3, fg=TX1))
            b.bind("<Leave>", lambda e,w=b: w.configure(bg=BG1, fg=CYN))

        # 因子库
        tk.Label(left, text="── 可用因子 (18) ──", font=FST, bg=BG0, fg=TX3).pack(anchor=tk.W, pady=(12,4))
        cats = {}
        for fn, f in FACTOR_REGISTRY.items():
            cats.setdefault(f.category, []).append(fn)
        for cat, factors in cats.items():
            tk.Label(left, text=f"  {cat}: {', '.join(factors[:4])}{'...' if len(factors)>4 else ''}",
                    font=FST, bg=BG0, fg=TX3, wraplength=260).pack(anchor=tk.W, padx=4, pady=1)

        show_detail("ma_cross", STRATEGIES["ma_cross"])

    def _build_single_backtest_tab(self, parent):
        """单策略回测标签页"""
        f = tk.Frame(parent, bg=BG0); f.pack(fill=tk.BOTH, padx=14, pady=14)

        # 配置区
        cfg = tk.Frame(f, bg=BG2); cfg.pack(fill=tk.X, pady=(0,10))
        def _fl(row, label, var=None, default="", width=15):
            tk.Label(cfg, text=label, font=F1, bg=BG2, fg=TX2).grid(row=row, column=0, sticky=tk.W, padx=(10,6), pady=4)
            v = var or tk.StringVar(value=default)
            tk.Entry(cfg, textvariable=v, font=F1, bg=BG3, fg=TX1, relief=tk.FLAT, bd=0, width=width).grid(row=row, column=1, sticky=tk.W, pady=4, ipady=4, padx=(0,8))
            return v

        sym_var = _fl(0, "股票代码", default="601398")
        start_var = _fl(0, "起始日期", default="2024-01-01"); start_var.grid(row=0, column=3, sticky=tk.W, padx=(16,6))

        # 策略选择
        tk.Label(cfg, text="策略", font=F1, bg=BG2, fg=TX2).grid(row=1, column=0, sticky=tk.W, padx=(10,6), pady=6)
        from src.strategies.library import STRATEGIES
        from src.factors.composer import PRESET_STRATEGIES
        all_strats = list(STRATEGIES.keys()) + list(PRESET_STRATEGIES.keys())
        strat_var = tk.StringVar(value="ma_cross")
        strat_menu = tk.OptionMenu(cfg, strat_var, *all_strats)
        strat_menu.configure(font=F1, bg=BG3, fg=TX1, relief=tk.FLAT, bd=0)
        strat_menu["menu"].configure(bg=BG2, fg=TX2, font=F1, relief=tk.FLAT, bd=0)
        strat_menu.grid(row=1, column=1, sticky=tk.W, pady=4)

        # 名称自动补全
        name_var = tk.StringVar()
        tk.Label(cfg, text="名称", font=F1, bg=BG2, fg=TX3).grid(row=1, column=2, sticky=tk.W, padx=(16,6))
        name_lbl = tk.Label(cfg, textvariable=name_var, font=F1, bg=BG2, fg=GRN)
        name_lbl.grid(row=1, column=3, sticky=tk.W, pady=6)

        def _lookup(*_):
            try:
                from src.data.stock_db import ensure_stock_db
                n = ensure_stock_db().get_name(sym_var.get())
                name_var.set(n if n and n != sym_var.get() else "")
            except: pass
        sym_var.trace_add("write", _lookup)
        _lookup()

        # 结果区
        result_text = tk.Text(f, font=FM, bg=BG0, fg=TX1, relief=tk.FLAT, bd=0, padx=14, pady=14)
        result_text.pack(fill=tk.BOTH, expand=True)

        # 运行按钮
        bf = tk.Frame(f, bg=BG0); bf.pack(fill=tk.X, pady=(10,0))
        status_lbl = tk.Label(bf, text="", font=F1, bg=BG0, fg=YLW)
        status_lbl.pack(side=tk.LEFT, padx=(0,10))

        def _run():
            result_text.delete(1.0,tk.END)
            sym = sym_var.get().strip()
            sk = strat_var.get()
            if not sym or not sk: return
            status_lbl.configure(text="运行中...")

            def _do():
                try:
                    from src.backtest.data_feed import get_data
                    from src.backtest.engine import BacktestEngine
                    from src.backtest.batch_runner import _make_strategy_instance
                    data = get_data(sym,"A股",start_date=start_var.get())
                    result_text.insert(tk.END, f"数据: {len(data)}条 ({str(data['date'].iloc[0])[:10]}~{str(data['date'].iloc[-1])[:10]})\n\n")
                    s = _make_strategy_instance(sk,{},sym)
                    r = BacktestEngine().run(s,data)
                    result_text.insert(tk.END,"═══ 回测结果 ═══\n")
                    for k,v in r["metrics"].items():
                        result_text.insert(tk.END,f"  {k}: {v}\n")
                    result_text.insert(tk.END,f"\n交易记录: {len(r['portfolio'].trade_log)}笔\n")
                    for t in r['portfolio'].trade_log[-10:]:
                        result_text.insert(tk.END,f"  {t['date']} {t['action']} ¥{t['price']:.2f}×{t['quantity']}\n")
                    status_lbl.configure(text="完成!", fg=GRN)
                except Exception as e:
                    result_text.insert(tk.END,f"[失败] {e}")
                    status_lbl.configure(text="失败", fg=RED)
            threading.Thread(target=_do, daemon=True).start()

        tk.Button(bf, text="运行回测", font=F3, bg=ACC, fg="white", relief=tk.FLAT, bd=0,
                 padx=20, pady=8, cursor="hand2", command=_run).pack(side=tk.LEFT)

    def _build_batch_compare_tab(self, parent):
        """批量对比标签页"""
        f = tk.Frame(parent, bg=BG0); f.pack(fill=tk.BOTH, padx=14, pady=14)

        cfg = tk.Frame(f, bg=BG2); cfg.pack(fill=tk.X, pady=(0,10))
        tk.Label(cfg, text="股票(空格分隔):", font=F1, bg=BG2, fg=TX2).grid(row=0, column=0, sticky=tk.W, padx=(10,6), pady=6)
        syms_var = tk.StringVar(value="601398 000858 600036 600900 000333")
        tk.Entry(cfg, textvariable=syms_var, font=F1, bg=BG3, fg=TX1, relief=tk.FLAT, bd=0, width=40).grid(row=0, column=1, sticky=tk.W, pady=6, ipady=4)

        tk.Label(cfg, text="起始:", font=F1, bg=BG2, fg=TX2).grid(row=0, column=2, sticky=tk.W, padx=(16,6))
        date_var = tk.StringVar(value="2024-01-01")
        tk.Entry(cfg, textvariable=date_var, font=F1, bg=BG3, fg=TX1, relief=tk.FLAT, bd=0, width=12).grid(row=0, column=3, sticky=tk.W, ipady=4)

        result_text = tk.Text(f, font=FM, bg=BG0, fg=TX1, relief=tk.FLAT, bd=0, padx=14, pady=14)
        result_text.pack(fill=tk.BOTH, expand=True)

        bf = tk.Frame(f, bg=BG0); bf.pack(fill=tk.X, pady=(10,0))
        st_lbl = tk.Label(bf, text="", font=F1, bg=BG0, fg=YLW); st_lbl.pack(side=tk.LEFT)

        def _run_batch():
            result_text.delete(1.0,tk.END)
            syms = syms_var.get().strip().split()
            if not syms: return
            st_lbl.configure(text="批量回测中...")
            def _do():
                try:
                    from src.backtest.batch_runner import BatchRunner
                    from src.strategies.library import STRATEGIES
                    from src.factors.composer import PRESET_STRATEGIES
                    all_s = list(STRATEGIES.keys()) + list(PRESET_STRATEGIES.keys())
                    runner = BatchRunner()
                    runner.add_symbols(syms); runner.add_strategies(all_s)
                    runner.start_date = date_var.get()
                    df = runner.run(verbose=False)
                    if not df.empty:
                        result_text.insert(tk.END, f"═══ 批量回测结果 ({len(df)}条) ═══\n\n")
                        for _, r in df.iterrows():
                            bar = "█"*max(1,int(r['夏普比率']*8)) if r['夏普比率']>0 else "░░"
                            result_text.insert(tk.END,
                                f"{r['strategy']:<22} | {r['symbol']:<8} | "
                                f"夏普{r['夏普比率']:>5.2f} | 收益{str(r['总收益率']):>10} | {bar}\n")
                        runner.show_ranking()
                    st_lbl.configure(text=f"完成! {len(df)}条", fg=GRN)
                except Exception as e:
                    result_text.insert(tk.END, f"[失败] {e}")
                    st_lbl.configure(text="失败", fg=RED)
            threading.Thread(target=_do, daemon=True).start()

        tk.Button(bf, text="全部策略×全部股票", font=F3, bg=ACC, fg="white", relief=tk.FLAT, bd=0,
                 padx=20, pady=8, cursor="hand2", command=_run_batch).pack(side=tk.LEFT)

        tk.Label(bf, text=f"  共 11个策略 × N只股票", font=FST, bg=BG0, fg=TX3).pack(side=tk.LEFT, padx=(10,0))

    def _build_optimize_tab(self, parent):
        """参数优化标签页"""
        f = tk.Frame(parent, bg=BG0); f.pack(fill=tk.BOTH, padx=14, pady=14)

        cfg = tk.Frame(f, bg=BG2); cfg.pack(fill=tk.X, pady=(0,10))

        tk.Label(cfg, text="股票:", font=F1, bg=BG2, fg=TX2).grid(row=0, column=0, sticky=tk.W, padx=(10,6), pady=6)
        sym_var2 = tk.StringVar(value="601398")
        tk.Entry(cfg, textvariable=sym_var2, font=F1, bg=BG3, fg=TX1, relief=tk.FLAT, bd=0, width=12).grid(row=0, column=1, sticky=tk.W, pady=6, ipady=4)

        tk.Label(cfg, text="策略:", font=F1, bg=BG2, fg=TX2).grid(row=0, column=2, sticky=tk.W, padx=(16,6))
        from src.strategies.library import STRATEGIES
        strat_var2 = tk.StringVar(value="ma_cross")
        sm = tk.OptionMenu(cfg, strat_var2, *list(STRATEGIES.keys()))
        sm.configure(font=F1, bg=BG3, fg=TX1, relief=tk.FLAT, bd=0)
        sm["menu"].configure(bg=BG2, fg=TX2, font=F1, relief=tk.FLAT, bd=0)
        sm.grid(row=0, column=3, sticky=tk.W, pady=6)

        tk.Label(cfg, text="起始:", font=F1, bg=BG2, fg=TX2).grid(row=0, column=4, sticky=tk.W, padx=(16,6))
        start_var2 = tk.StringVar(value="2022-01-01")
        tk.Entry(cfg, textvariable=start_var2, font=F1, bg=BG3, fg=TX1, relief=tk.FLAT, bd=0, width=12).grid(row=0, column=5, sticky=tk.W, ipady=4)

        # 参数输入
        tk.Label(cfg, text="参数 (JSON):", font=F1, bg=BG2, fg=TX2).grid(row=1, column=0, sticky=tk.W, padx=(10,6), pady=(2,8))
        params_var = tk.StringVar(value='{"fast_period":[5,10,20],"slow_period":[20,30,60]}')
        tk.Entry(cfg, textvariable=params_var, font=F1, bg=BG3, fg=TX1, relief=tk.FLAT, bd=0, width=60).grid(row=1, column=1, columnspan=5, sticky=tk.EW, pady=(2,8), ipady=4)

        # 快捷预设
        presets_frame = tk.Frame(cfg, bg=BG2)
        presets_frame.grid(row=2, column=1, columnspan=5, sticky=tk.W, pady=(0,8))
        presets = [
            ("均线快慢", '{"fast_period":[5,10,20],"slow_period":[20,30,60]}'),
            ("RSI参数", '{"rsi_period":[7,14,21],"oversold":[20,30,40],"overbought":[60,70,80]}'),
            ("布林带", '{"period":[10,20,30],"std_dev":[1.5,2.0,2.5]}'),
        ]
        for lbl, pjson in presets:
            b = tk.Label(presets_frame, text=lbl, font=FST, bg=BG3, fg=TX2, padx=8, pady=3, cursor="hand2")
            b.pack(side=tk.LEFT, padx=2)
            b.bind("<Button-1>", lambda e,j=pjson: params_var.set(j))

        result_text = tk.Text(f, font=FM, bg=BG0, fg=TX1, relief=tk.FLAT, bd=0, padx=14, pady=14, height=18)
        result_text.pack(fill=tk.BOTH, expand=True)

        bf = tk.Frame(f, bg=BG0); bf.pack(fill=tk.X, pady=(10,0))
        st_lbl = tk.Label(bf, text="", font=F1, bg=BG0, fg=YLW); st_lbl.pack(side=tk.LEFT)

        def _run_opt():
            result_text.delete(1.0,tk.END)
            st_lbl.configure(text="优化中...")
            def _do():
                try:
                    import json
                    from src.backtest.optimizer import GridSearch
                    pg = json.loads(params_var.get())
                    gs = GridSearch(sym_var2.get(),"A股",start_date=start_var2.get(),rank_by="sharpe")
                    df = gs.run(strat_var2.get(), pg, verbose=False)
                    if not df.empty:
                        result_text.insert(tk.END,f"═══ 参数优化 ({len(df)}组合) ═══\n\n")
                        result_text.insert(tk.END,df.head(15).to_string()+"\n")
                        best = df.iloc[0]
                        result_text.insert(tk.END,f"\n🏆 最佳: 夏普{best['score']:.2f}\n")
                    st_lbl.configure(text="完成!", fg=GRN)
                except Exception as e:
                    result_text.insert(tk.END,f"[失败] {e}")
                    st_lbl.configure(text="失败", fg=RED)
            threading.Thread(target=_do, daemon=True).start()

        tk.Button(bf, text="网格搜索", font=F3, bg=ACC2, fg="white", relief=tk.FLAT, bd=0,
                 padx=20, pady=8, cursor="hand2", command=_run_opt).pack(side=tk.LEFT)

        tk.Button(bf, text="Walk-Forward", font=F1, bg=BG3, fg=TX2, relief=tk.FLAT, bd=0,
                 padx=14, pady=8, cursor="hand2",
                 command=lambda: self._bg(lambda: __import__('src.backtest.optimizer',fromlist=['quick_walkforward']).quick_walkforward(sym_var2.get(),strat_var2.get()))).pack(side=tk.LEFT, padx=(8,0))

    def _build_evolve_tab(self, parent):
        """策略进化标签页"""
        f = tk.Frame(parent, bg=BG0); f.pack(fill=tk.BOTH, padx=14, pady=14)

        tk.Label(f, text="AI + 遗传算法 自动进化策略", font=F3, bg=BG0, fg=ACC2).pack(pady=(10,4))
        tk.Label(f, text="流程: AI分析回测数据 → 生成种子策略 → 遗传算法杂交突变 → 回测验证 → 最优策略入银行",
                font=FST, bg=BG0, fg=TX3).pack(pady=(0,16))

        cfg = tk.Frame(f, bg=BG2); cfg.pack(fill=tk.X, pady=(0,10))
        tk.Label(cfg, text="标的:", font=F1, bg=BG2, fg=TX2).grid(row=0, column=0, padx=(10,6), pady=8)
        sym_var3 = tk.StringVar(value="601398")
        tk.Entry(cfg, textvariable=sym_var3, font=F1, bg=BG3, fg=TX1, relief=tk.FLAT, bd=0, width=10).grid(row=0, column=1, sticky=tk.W, pady=8, ipady=4)

        tk.Label(cfg, text="代数:", font=F1, bg=BG2, fg=TX2).grid(row=0, column=2, padx=(16,6))
        gen_var = tk.StringVar(value="5")
        tk.Entry(cfg, textvariable=gen_var, font=F1, bg=BG3, fg=TX1, relief=tk.FLAT, bd=0, width=6).grid(row=0, column=3, sticky=tk.W)

        tk.Label(cfg, text="种群:", font=F1, bg=BG2, fg=TX2).grid(row=0, column=4, padx=(16,6))
        pop_var = tk.StringVar(value="20")
        tk.Entry(cfg, textvariable=pop_var, font=F1, bg=BG3, fg=TX1, relief=tk.FLAT, bd=0, width=6).grid(row=0, column=5, sticky=tk.W)

        use_ai_var = tk.BooleanVar(value=True)
        tk.Checkbutton(cfg, text="用AI生成种子", variable=use_ai_var, font=F1, bg=BG2, fg=TX2,
                      selectcolor=BG3, activebackground=BG2, activeforeground=TX1).grid(row=0, column=6, padx=(16,6))

        result_text = tk.Text(f, font=FM, bg=BG0, fg=TX1, relief=tk.FLAT, bd=0, padx=14, pady=14, height=16)
        result_text.pack(fill=tk.BOTH, expand=True)

        bf = tk.Frame(f, bg=BG0); bf.pack(fill=tk.X, pady=(10,0))
        st_lbl = tk.Label(bf, text="", font=F1, bg=BG0, fg=YLW); st_lbl.pack(side=tk.LEFT)

        def _run_evolve():
            result_text.delete(1.0,tk.END)
            st_lbl.configure(text="进化中...")
            def _do():
                old_out = sys.stdout
                buf = io.StringIO(); sys.stdout = buf
                try:
                    from src.ai.factory import auto_evolve
                    auto_evolve(symbol=sym_var3.get(), generations=int(gen_var.get()),
                               use_ai=use_ai_var.get())
                    result_text.insert(tk.END, buf.getvalue())
                    st_lbl.configure(text="进化完成!", fg=GRN)
                except Exception as e:
                    result_text.insert(tk.END, f"[失败] {e}")
                    st_lbl.configure(text="失败", fg=RED)
                finally: sys.stdout = old_out
            threading.Thread(target=_do, daemon=True).start()

        tk.Button(bf, text="启动进化", font=F3, bg=GRN, fg="white", relief=tk.FLAT, bd=0,
                 padx=24, pady=10, cursor="hand2", command=_run_evolve).pack(side=tk.LEFT)

        tk.Button(bf, text="策略银行", font=F1, bg=BG3, fg=TX2, relief=tk.FLAT, bd=0,
                 padx=14, pady=10, cursor="hand2", command=self._bank).pack(side=tk.LEFT, padx=(8,0))

    def _backtest(self):
        self._bg(lambda: (
            self._log("\n[单策略回测] 双均线 x 601398"),
            (d:=__import__('src.backtest.data_feed',fromlist=['get_data']).get_data("601398","A股",start_date="2024-01-01")),
            self._log(f"  数据: {len(d)}条"),
            (s:=__import__('src.backtest.batch_runner',fromlist=['_make_strategy_instance'])._make_strategy_instance("ma_cross",{},"601398")),
            (r:=__import__('src.backtest.engine',fromlist=['BacktestEngine']).BacktestEngine().run(s,d)),
            self._log("  ────────────────"),
            [self._log(f"  {k}: {v}") for k,v in r["metrics"].items()]
        ), "BACKTESTING")

    def _batch(self):
        self._bg(lambda: (
            self._log("\n[批量回测] 5 stocks x 5 strategies"),
            (ru:=__import__('src.backtest.batch_runner',fromlist=['BatchRunner']).BatchRunner()),
            ru.add_symbols(["601398","000858","600036","600900","000333"]),
            ru.add_strategies(["ma_cross","rsi","macd","contrarian_v1","trend_following_v1"]),
            setattr(ru,'start_date',"2024-01-01"),
            (df:=ru.run()),
            ru.show_ranking() if not df.empty else None
        ), "BATCH")

    def _optimize(self):
        self._bg(lambda: (
            self._log("\n[参数优化] Grid Search ma_cross x 601398"),
            __import__('src.backtest.optimizer',fromlist=['GridSearch']).GridSearch(
                "601398","A股",start_date="2022-01-01",rank_by="sharpe"
            ).run("ma_cross",{"fast_period":[5,10,20],"slow_period":[20,30,60]})
        ), "OPTIMIZING")

    def _valuation(self):
        self._bg(lambda: (
            self._log("\n[指数估值]"),
            __import__('src.index.valuation',fromlist=['show_valuation']).show_valuation()
        ), "VALUATION")

    def _rotation(self):
        self._bg(lambda: (
            self._log("\n[指数策略]"),
            __import__('src.index.rotation',fromlist=['compare_index_strategies']).compare_index_strategies("2022-01-01")
        ), "COMPUTING")

    def _factory(self):
        self._bg(lambda: (
            self._log("\n[AI策略工厂] 分析→生成→进化→入库"),
            __import__('src.ai.factory',fromlist=['auto_evolve']).auto_evolve(symbol="601398",generations=5,use_ai=True)
        ), "EVOLVING")

    def _bank(self):
        self._log("\n[策略银行]")
        __import__('src.ai.factory',fromlist=['show_bank']).show_bank()

    def _ai_cfg(self):
        dlg = tk.Toplevel(self.root); dlg.title("AI 配置"); dlg.geometry("500x400")
        dlg.configure(bg=BG2); dlg.transient(self.root)
        tk.Label(dlg, text="AI Connection", font=FT, bg=BG2, fg=TX1).pack(pady=(14,2))
        tk.Label(dlg, text="OpenAI / DeepSeek / Qwen / Ollama", font=FST, bg=BG2, fg=TX3).pack(pady=(0,14))

        cp = "D:/trading_data/ai_config.json"
        ex = {}
        if os.path.exists(cp):
            try:
                with open(cp,encoding="utf-8") as f: ex = json.load(f)
            except: pass

        ents = {}
        for lb, ky, dv in [
            ("API Key", "api_key", ex.get("api_key","")),
            ("Base URL", "base_url", ex.get("base_url","https://api.deepseek.com")),
            ("Model", "model", ex.get("model","deepseek-chat")),
        ]:
            tk.Label(dlg, text=lb, font=FST, bg=BG2, fg=TX3).pack(anchor=tk.W, padx=30, pady=(8,0))
            e = tk.Entry(dlg, font=FM, bg=BG3, fg=TX1, insertbackground=GRN, relief=tk.FLAT, bd=0,
                        show="*" if "key" in lb.lower() else "")
            e.pack(fill=tk.X, padx=30, pady=(2,0), ipady=6); e.insert(0, dv); ents[ky]=e

        pf = tk.Frame(dlg, bg=BG2); pf.pack(fill=tk.X, padx=30, pady=(10,0))
        tk.Label(pf, text="预设:", font=FST, bg=BG2, fg=TX3).pack(side=tk.LEFT)
        for n, u, m in [("DeepSeek","https://api.deepseek.com","deepseek-chat"),
                         ("OpenAI","https://api.openai.com/v1","gpt-4o"),
                         ("Qwen","https://dashscope.aliyuncs.com/compatible-mode/v1","qwen-plus")]:
            b = tk.Label(pf, text=n, font=FST, bg=BG3, fg=TX2, padx=8, pady=3, cursor="hand2")
            b.pack(side=tk.LEFT, padx=2)
            b.bind("<Button-1>", lambda e,u=u,m=m: (ents["base_url"].delete(0,tk.END),
                    ents["base_url"].insert(0,u), ents["model"].delete(0,tk.END), ents["model"].insert(0,m)))
        def sv():
            c2 = {k:e.get().strip() for k,e in ents.items()}
            os.makedirs(os.path.dirname(cp),exist_ok=True)
            with open(cp,"w",encoding="utf-8") as f: json.dump(c2,f,indent=2,ensure_ascii=False)
            self._log(f"\n[AI] 已保存 ({c2['model']})"); dlg.destroy()
        bf = tk.Frame(dlg, bg=BG2); bf.pack(pady=(16,0))
        tk.Button(bf, text="保存", font=F3, bg=GRN, fg="white", relief=tk.FLAT, bd=0,
                 padx=20, pady=8, cursor="hand2", command=sv).pack(side=tk.LEFT, padx=4)
        tk.Button(bf, text="取消", font=F1, bg=BG3, fg=TX2, relief=tk.FLAT, bd=0,
                 padx=20, pady=8, cursor="hand2", command=dlg.destroy).pack(side=tk.LEFT, padx=4)

    def _ai_review(self):
        self._bg(lambda: (
            self._log("\n[AI复盘]"), (r:=__import__('src.ai.assistants',fromlist=['AITradeReviewer']).AITradeReviewer().review()), self._log(f"\n{r}")
        ), "AI")

    def _ai_brief(self):
        self._bg(lambda: (
            self._log("\n[AI简报]"), (r:=__import__('src.ai.assistants',fromlist=['AIMarketAnalyst']).AIMarketAnalyst().daily_brief()), self._log(f"\n{r}")
        ), "AI")

    def _analysis(self):
        self._log("\n[绩效分析]")
        __import__('src.analysis.reports',fromlist=['run_report']).run_report()

    def _factors(self):
        self._log("\n[因子体系] 28 Factors:")
        from src.factors.definitions import FACTOR_REGISTRY
        for n,f in FACTOR_REGISTRY.items(): self._log(f"  [{f.category}] {n}  {f.description}")

    # ═══ v2.0 新增: Alpha Memory / Paper Broker / Data Center ═══

    def _alpha_panel(self):
        """Alpha 信号记忆面板"""
        self._bg(lambda: self._run_alpha_panel(), "ALPHA_MEMORY")

    def _run_alpha_panel(self):
        self._log("\n═══ Alpha 信号记忆 ═══")
        try:
            from src.ai.alpha_store import alpha_store
            stats = alpha_store.stats()
            self._log(f"  总信号: {stats['total_signals']}")
            self._log(f"  股票数: {stats['unique_symbols']}")
            self._log(f"  因子数: {stats['unique_factors']}")
            self._log(f"  结果分布: {stats['outcomes']}")

            self._log("\n── 因子胜率 TOP 10 ──")
            wr = alpha_store.get_win_rate_by_factor(days=90)
            for name, s in sorted(wr.items(), key=lambda x: x[1].get("total", 0), reverse=True)[:10]:
                tag = "+" if s["win_rate"] >= 0.5 else "-"
                self._log(f"  {tag} {name}: {s['total']}信号 胜率{s['win_rate']:.0%} 均PnL{s['avg_pnl_pct']:.2%}")

            self._log("\n── 市场状态矩阵 ──")
            regime_labels = {0: "高波动上涨", 1: "高波动下跌", 2: "低波动震荡", 3: "高波动反转"}
            matrix = alpha_store.get_regime_performance_matrix(days=180)
            for rid, s in sorted(matrix.items()):
                label = regime_labels.get(rid, str(rid))
                self._log(f"  [{label}] {s['total_signals']}信号 胜率{s['win_rate']:.0%} "
                         f"均PnL{s['avg_pnl_pct']:.2%} 最佳:{s.get('best_factors',[])}")

            self._log("\n── 最近 10 条信号 ──")
            for r in alpha_store.get_recent(10):
                outcome = r.get("outcome", "-") or "-"
                self._log(f"  {r['date']} {r['symbol']} {r['factor_name']} "
                         f"{r.get('signal_action','')} → {outcome}")
        except Exception as e:
            self._log(f"  [失败] {e}")

    def _factor_health(self):
        """因子健康度评估"""
        self._bg(lambda: self._run_factor_health(), "FACTOR_HEALTH")

    def _run_factor_health(self):
        self._log("\n═══ 因子健康度评估 ═══")
        try:
            from src.ai.alpha_store import alpha_store
            health = alpha_store.get_factor_health()
            for name, h in sorted(health.items(), key=lambda x: x[1].get("total", 0), reverse=True):
                status_icon = {"strong": "[+]", "moderate": "[~]", "weak": "[-]", "stale": "[x]", "ineffective": "[x]"}
                icon = status_icon.get(h["health"], "[?]")
                stale = " STALE" if h["health"] == "stale" else ""
                self._log(f"  {icon} {name}: {h['total']}信号 胜率{h['win_rate']:.0%} "
                         f"{h['health'].upper()}{stale}")
        except Exception as e:
            self._log(f"  [失败] {e}")

    def _unified_bank(self):
        """统一策略银行"""
        self._bg(lambda: self._run_unified_bank(), "BANK")

    def _run_unified_bank(self):
        self._log("\n═══ 统一策略银行 ═══")
        try:
            from src.ai.bank_bridge import unified_bank
            stats = unified_bank.stats()
            self._log(f"  进化银行: {stats['evolution_bank']} | 用户银行: {stats['user_bank']} | 总计: {stats['total']}")
            best = unified_bank.get_best(n=10)
            self._log(f"\n── TOP 10 ──")
            for i, s in enumerate(best, 1):
                source_tag = "[E]" if s.get("source") == "evolution" else "[U]"
                self._log(f"  {i}. {source_tag} {s.get('name','?')} (fitness={s.get('fitness',0):.2f})")
        except Exception as e:
            self._log(f"  [失败] {e}")

    def _ic_decay_status(self):
        """IC 衰减状态"""
        self._bg(lambda: self._run_ic_decay_status(), "IC_DECAY")

    def _run_ic_decay_status(self):
        self._log("\n═══ IC 衰减状态 ═══")
        try:
            from src.factors.definitions import FactorCalculator
            from src.backtest.data_feed import get_data
            data = get_data("601398", "A股", start_date="2024-06-01")
            if data is not None and len(data) > 60:
                calc = FactorCalculator(data)
                for name in ["rsi_norm", "ma_deviation", "volume_ratio", "momentum_score"]:
                    try:
                        status = calc.compute_decay_curve(data, name)
                        tag = "DECAY!" if status.get("decaying") else "OK"
                        self._log(f"  [{tag}] {name}: IC={status.get('current_ic',0):.3f} "
                                 f"streak={status.get('below_zero_streak',0)}d "
                                 f"→ {status.get('recommendation','')}")
                    except Exception:
                        self._log(f"  [--] {name}: 计算失败")
        except Exception as e:
            self._log(f"  [失败] {e}")

    # ── Paper Broker ───────────────────────────────────

    def _broker_status(self):
        self._bg(lambda: self._run_broker_status(), "BROKER")

    def _run_broker_status(self):
        self._log("\n═══ Paper Broker 状态 ═══")
        try:
            from src.execution.paper_broker import paper_broker
            s = paper_broker.stats()
            self._log(f"  现金: ¥{s['cash']:,.2f}")
            self._log(f"  初始资金: ¥{s['initial_cash']:,.2f}")
            pnl_tag = "+" if s['pnl'] >= 0 else ""
            self._log(f"  总盈亏: {pnl_tag}¥{s['pnl']:,.2f} ({s['pnl_pct']:+.2f}%)")
            self._log(f"  待执行订单: {s['pending_orders']}")

            # 当前持仓
            try:
                pos = paper_broker.get_positions()
                if pos is not None and not pos.empty:
                    self._log(f"\n── 当前持仓 ──")
                    for _, r in pos.iterrows():
                        self._log(f"  {r['symbol']} {r.get('name','')} x{r['quantity']} "
                                 f"成本¥{r['avg_cost']:.2f}")
                else:
                    self._log("  持仓: 空")
            except Exception:
                self._log("  持仓: 查询失败")
        except Exception as e:
            self._log(f"  [失败] {e}")

    def _broker_orders(self):
        self._bg(lambda: self._run_broker_orders(), "ORDERS")

    def _run_broker_orders(self):
        self._log("\n═══ 订单管理 ═══")
        try:
            from src.execution.paper_broker import OrderDB
            db = OrderDB()
            orders = db.load_all_orders(1, limit=20)
            if not orders:
                self._log("  暂无订单")
                return
            for o in orders:
                status_icon = {"pending": "[ ]", "partial": "[~]", "filled": "[+]",
                               "cancelled": "[x]", "rejected": "[!]"}.get(o.status, "[?]")
                self._log(f"  {status_icon} {o.order_id[:8]}... {o.symbol} {o.action} "
                         f"x{o.quantity} @{o.price:.2f} status={o.status}")
        except Exception as e:
            self._log(f"  [失败] {e}")

    def _broker_auto_trade(self):
        """自动交易开关"""
        self._log("\n═══ 自动纸面交易 ═══")
        try:
            from src.execution.bridge import bridge
            current = bridge.auto_trade_enabled
            new_state = not current
            bridge.toggle_auto_trade(new_state)
            self._log(f"  状态: {'ON (自动执行实时信号)' if new_state else 'OFF (仅记录信号)'}")
            self._log(f"  缓存信号: {len(bridge.get_recent_signals())} 条")
        except Exception as e:
            self._log(f"  [失败] {e}")

    # ── Data Center ────────────────────────────────────

    def _macro_panel(self):
        self._bg(lambda: self._run_macro_panel(), "MACRO")

    def _run_macro_panel(self):
        self._log("\n═══ 宏观数据面板 ═══")
        try:
            from src.data.macro_fetchers import FETCHER_MAP, register_all_macro_fetchers
            self._log(f"  已注册: {len(FETCHER_MAP)} 个宏观指标")
            for code in FETCHER_MAP:
                self._log(f"    {code}")

            # 尝试获取最新 CPI
            try:
                from src.data.macro_fetchers import get_macro_data
                df = get_macro_data("CN_CPI_YOY")
                if df is not None and not df.empty:
                    latest = df.iloc[-1]
                    self._log(f"\n  最新 CPI: {latest['date']} → {latest['value']}%")
            except Exception as e:
                self._log(f"  CPI 获取: {e}")
        except Exception as e:
            self._log(f"  [失败] {e}")

    def _fundamental_panel(self):
        self._bg(lambda: self._run_fundamental_panel(), "FUNDAMENTAL")

    def _run_fundamental_panel(self):
        self._log("\n═══ 基本面数据 ═══")
        try:
            from src.data.financials import financial_db
            for symbol in ["600519", "000858", "601398"]:
                needs = financial_db.needs_update(symbol)
                tag = "需更新" if needs else "已最新"
                pe = financial_db.get_pe_series(symbol)
                pe_count = len(pe) if pe is not None else 0
                self._log(f"  {symbol}: PE数据{pe_count}条 ({tag})")

            self._log("\n  输入股票代码查看详细基本面:")
            self._log("    示例: 在输入框输入 'pe 600519' 查询PE历史")
        except Exception as e:
            self._log(f"  [失败] {e}")

    def _industry_panel(self):
        self._bg(lambda: self._run_industry_panel(), "INDUSTRY")

    def _run_industry_panel(self):
        self._log("\n═══ 申万行业分类 ═══")
        try:
            from src.data.stock_db import industry_classifier
            ind = industry_classifier.get_industry("600519")
            peers = industry_classifier.get_industry_peers("600519")
            self._log(f"  600519(茅台) 行业: {ind or '未分类'}")
            if peers:
                self._log(f"  同行业标的 ({len(peers)}): {peers[:10]}...")
        except Exception as e:
            self._log(f"  [失败] {e}")

    def _run_pe_lookup(self, symbol: str):
        """查询 PE/PB/ROE 历史"""
        self._log(f"\n═══ 基本面查询: {symbol} ═══")
        try:
            from src.data.financials import financial_db
            from src.data.stock_db import ensure_stock_db

            name = ensure_stock_db().get_name(symbol) if ensure_stock_db().count() > 0 else symbol
            self._log(f"  名称: {name}")

            for label, series in [("PE", financial_db.get_pe_series(symbol)),
                                   ("PB", financial_db.get_pb_series(symbol)),
                                   ("ROE", financial_db.get_roe_series(symbol))]:
                if series is not None and not series.empty:
                    col = [c for c in series.columns if c != "date"][0]
                    latest = series.iloc[-1]
                    self._log(f"  {label}: {latest[col]:.2f} ({latest['date'].strftime('%Y-%m-%d') if hasattr(latest['date'], 'strftime') else str(latest['date'])[:10]})")
                else:
                    self._log(f"  {label}: 无数据 (可能需要下载)")

            needs = financial_db.needs_update(symbol)
            if needs:
                self._log(f"\n  提示: 数据需要更新, 运行 download 下载行情后自动拉取")
        except Exception as e:
            self._log(f"  [失败] {e}")

    # ═══ 新增: 快速验证 · 个股诊断 · 每日快扫 ═══

    # ═══ 快速验证 · 个股诊断 · 因子策略 · 每日快扫 ═══

    def _quick_backtest_dialog(self):
        from src.dialogs import QuickBacktestDialog
        QuickBacktestDialog(self.root)

    def _diagnosis_dialog(self):
        from src.dialogs import DiagnosisDialog
        DiagnosisDialog(self.root)

    def _factor_strategy_dialog(self):
        from src.dialogs import FactorStrategyDialog
        FactorStrategyDialog(self.root)

    def _recommend_dialog(self):
        """智能推荐 — 跑全策略+因子, 给买卖价位"""
        dlg = tk.Toplevel(self.root); dlg.title("智能推荐"); dlg.geometry("750x680")
        dlg.configure(bg=BG0); dlg.transient(self.root)
        tk.Label(dlg, text="智能推荐 — 最优策略 · 买卖价位 · 止损建议", font=FT, bg=BG0, fg=TX1).pack(pady=(14,2))
        tk.Label(dlg, text="全策略+全因子分析, 给出具体操作建议", font=FST, bg=BG0, fg=TX3).pack(pady=(0,8))
        cfg = tk.Frame(dlg, bg=BG2); cfg.pack(fill=tk.X, padx=14, pady=(0,6))
        tk.Label(cfg, text="股票代码", font=F1, bg=BG2, fg=TX2).grid(row=0, column=0, sticky="w", padx=(10,6), pady=10)
        sym_var = tk.StringVar(value="600498")
        tk.Entry(cfg, textvariable=sym_var, font=F1, bg=BG3, fg=TX1, relief="flat", bd=0, width=12).grid(row=0, column=1, sticky="w", pady=10, ipady=5)
        name_var = tk.StringVar()
        tk.Label(cfg, textvariable=name_var, font=F1, bg=BG2, fg=GRN).grid(row=0, column=2, sticky="w", padx=(10,0), pady=10)
        def _lookup(*_):
            try:
                from src.data.stock_db import ensure_stock_db
                n = ensure_stock_db().get_name(sym_var.get())
                name_var.set(n if n and n!=sym_var.get() else "")
            except: pass
        sym_var.trace_add("write", _lookup); _lookup()
        result_text = tk.Text(dlg, font=("Cascadia Code", 10), bg=BG0, fg=TX1, relief="flat", bd=0, padx=14, pady=14, height=12)
        result_text.pack(fill=tk.BOTH, expand=True, padx=14)

        # AI 讨论区
        ai_label = tk.Label(dlg, text="💬 AI顾问讨论 (输入你的交易思路)", font=F1, bg=BG0, fg=TX2)
        ai_label.pack(anchor="w", padx=14, pady=(8,2))
        ai_chat = tk.Text(dlg, font=("Cascadia Code", 9), bg=BG0, fg=TX2, relief="flat", bd=0, padx=10, pady=8, height=6)
        ai_chat.pack(fill=tk.X, padx=14, pady=(0,4))
        ai_chat.insert("1.0", "AI顾问: 获取推荐后,在这里输入你的思路和我讨论...\n")
        ai_input = tk.Frame(dlg, bg=BG0); ai_input.pack(fill=tk.X, padx=14, pady=(0,8))
        msg_var = tk.StringVar()
        tk.Entry(ai_input, textvariable=msg_var, font=F1, bg=BG3, fg=TX1, relief="flat", bd=0).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        def _send_ai():
            msg = msg_var.get().strip()
            if not msg: return
            ai_chat.insert(tk.END, f"\n你: {msg}\n")
            ai_chat.insert(tk.END, "AI: 分析中...\n")
            msg_var.set("")
            def _ai_reply():
                try:
                    from src.ai.engine import LLMClient
                    ctx = result_text.get("1.0", tk.END)[:1500]
                    sym = sym_var.get().strip()
                    system = f"""你是LXL QuantAxis的AI量化顾问。用户正在分析股票{sym}。
推荐结果:{ctx}
请根据用户描述的交易思路,判断匹配什么策略,是否可行,给出具体建议。150字以内。"""
                    reply = LLMClient().ask(msg, system=system)
                    ai_chat.insert(tk.END, f"AI: {reply}\n")
                    ai_chat.see(tk.END)
                except Exception as e:
                    ai_chat.insert(tk.END, f"AI: 连接失败 - {e}\n")
            threading.Thread(target=_ai_reply, daemon=True).start()
        tk.Button(ai_input, text="发送", font=F1, bg=ACC, fg="white", relief="flat", bd=0, padx=12, pady=4, cursor="hand2", command=_send_ai).pack(side=tk.RIGHT, padx=(6,0))
        msg_var.trace_add("write", lambda *_: None)
        ai_input.bind("<Return>", lambda e: _send_ai())

        bf = tk.Frame(dlg, bg=BG0); bf.pack(fill=tk.X, padx=14, pady=(4,14))
        status_lbl = tk.Label(bf, text="", font=F1, bg=BG0, fg=YLW); status_lbl.pack(side=tk.LEFT, padx=(0,10))
        def _run():
            result_text.delete(1.0, tk.END); sym = sym_var.get().strip()
            result_text.insert(tk.END, f"分析 {sym}...\n"); status_lbl.configure(text="运行中...")
            def _do():
                try:
                    from src.backtest.data_feed import get_data, download_watchlist, get_data_summary
                    from src.backtest.engine import BacktestEngine
                    from src.backtest.batch_runner import _make_strategy_instance
                    from src.strategies.library import STRATEGIES
                    from src.factors.composer import PRESET_STRATEGIES
                    from src.factors.definitions import FactorCalculator
                    from datetime import datetime
                    today = datetime.now().strftime("%Y-%m-%d")
                    try:
                        cdf = get_data_summary(); tgt = f"A股_{sym}_daily.csv"
                        if not cdf.empty and tgt in cdf["文件"].values:
                            msk = cdf["文件"] == tgt; lat = str(cdf[msk].iloc[0]["结束日期"]).strip()[:10]
                            if lat < today: download_watchlist([{"symbol":sym,"market":"A股","name":sym}], verbose=False)
                    except: pass
                    data = get_data(sym, "A股", start_date="2022-01-01")
                    price = float(data["close"].iloc[-1])
                    all_s = list(STRATEGIES.keys()) + list(PRESET_STRATEGIES.keys())
                    results = []
                    for key in all_s:
                        name = key
                        for src in [STRATEGIES, PRESET_STRATEGIES]:
                            if key in src: name = src[key].get("name", key); break
                        try:
                            s = _make_strategy_instance(key, {}, sym)
                            r = BacktestEngine().run(s, data); m = r["metrics"]
                            try: sh = float(str(m.get("夏普比率",-99)))
                            except: sh = -99
                            results.append((sh, name, m.get("总收益率","-"), m.get("胜率","-"), m.get("最大回撤","-")))
                        except: pass
                    results.sort(key=lambda x: x[0], reverse=True)
                    calc = FactorCalculator(data); cf = calc.compute_all().iloc[-1]
                    def _fv(n,d=0.5):
                        try: return float(cf.get(n,d))
                        except: return d
                    rsi = _fv("rsi_norm"); bb_pos = _fv("bollinger_pos")
                    bb = data["close"].rolling(20).mean().iloc[-1]
                    bb_std = data["close"].rolling(20).std().iloc[-1]
                    bb_low = float(bb - 2*bb_std); bb_up = float(bb + 2*bb_std)
                    atr_r = _fv("atr_ratio", 0.0001); atr = atr_r * price if atr_r > 0 else price * 0.02
                    buy_p = round((bb_low + price * (1 - max(0, 0.3-rsi))) / 2, 2)
                    if buy_p > price: buy_p = round(price * 0.98, 2)
                    sell_p = round(min(bb_up, price + 3*atr), 2)
                    stop_p = round(max(bb_low * 0.95, price - 2*atr), 2)
                    risk_amt = 100000 * 0.015
                    shares = max(100, int(risk_amt/(buy_p-stop_p))//100*100) if (buy_p-stop_p)>0 else 100
                    lines = [f"═══ 智能推荐: {sym} ═══", f"价格: ¥{price:.2f} | 数据: {len(data)}条", ""]
                    lines.append("── TOP 5 策略 ──")
                    for i,(sh,nm,ret,wr,dd) in enumerate(results[:5],1):
                        lines.append(f"  {i}. {nm:<14} Sharpe={sh:>6.2f} 收益={ret} 胜率={wr} 回撤={dd}")
                    lines.append(""); lines.append("── 买卖价位 ──")
                    lines.append(f"  建议买入: ¥{buy_p:.2f}"); lines.append(f"  建议卖出: ¥{sell_p:.2f}")
                    lines.append(f"  止损价位: ¥{stop_p:.2f}"); lines.append(f"  建议仓位: {shares}股 ({shares//100}手)")
                    lines.append(""); lines.append("── 当前因子 ──")
                    lines.append(f"  RSI:{rsi*100:.0f} 布林:{bb_pos:.2f} 均线:{_fv('ma_alignment'):.2f} MACD:{_fv('macd_hist',0.5):.2f}")
                    result_text.delete(1.0, tk.END)
                    result_text.insert(tk.END, "\n".join(lines))
                    ai_chat.delete(1.0, tk.END)
                    ai_chat.insert(tk.END, "AI顾问: 推荐已生成。在下方输入你的交易思路,我帮你分析可行性。\n")
                    status_lbl.configure(text="推荐完成!", fg=GRN)
                except Exception as e:
                    result_text.insert(tk.END, f"\n错误: {e}"); status_lbl.configure(text="失败", fg=RED)
            threading.Thread(target=_do, daemon=True).start()
        tk.Button(bf, text="获取推荐", font=F3, bg=ACC, fg="white", relief="flat", bd=0,
                  padx=20, pady=10, cursor="hand2", command=_run).pack(side=tk.LEFT)

    def _strategy_lab(self):
        """AI策略战法实验室"""
        dlg = tk.Toplevel(self.root); dlg.title("AI策略战法实验室"); dlg.geometry("800x700")
        dlg.configure(bg=BG0); dlg.transient(self.root)
        tk.Label(dlg, text="AI策略战法实验室", font=FT, bg=BG0, fg=TX1).pack(pady=(14,2))
        tk.Label(dlg, text="用自然语言描述你的交易思路,AI帮你转成可回测的策略", font=FST, bg=BG0, fg=TX3).pack(pady=(0,8))
        cfg = tk.Frame(dlg, bg=BG2); cfg.pack(fill=tk.X, padx=14, pady=(0,6))
        tk.Label(cfg, text="回测股票", font=F1, bg=BG2, fg=TX2).grid(row=0, column=0, sticky="w", padx=(10,6), pady=8)
        sym_var = tk.StringVar(value="600498")
        tk.Entry(cfg, textvariable=sym_var, font=F1, bg=BG3, fg=TX1, relief="flat", bd=0, width=12).grid(row=0, column=1, sticky="w", pady=8, ipady=5)
        tk.Label(cfg, text="起始日期", font=F1, bg=BG2, fg=TX2).grid(row=0, column=2, sticky="w", padx=(16,6), pady=8)
        date_var = tk.StringVar(value="2024-01-01")
        tk.Entry(cfg, textvariable=date_var, font=F1, bg=BG3, fg=TX1, relief="flat", bd=0, width=12).grid(row=0, column=3, sticky="w", pady=8, ipady=5)
        idea_text = tk.Text(dlg, font=F1, bg=BG3, fg=TX1, relief="flat", bd=0, padx=12, pady=10, height=6)
        idea_text.pack(fill=tk.X, padx=14, pady=(0,6))
        idea_text.insert("1.0", "描述你的交易战法...\n例: 当RSI低于25且MACD金叉时买入,RSI高于70或跌破5日低点卖出")
        result_text = tk.Text(dlg, font=("Cascadia Code", 9), bg=BG0, fg=TX1, relief="flat", bd=0, padx=12, pady=10)
        result_text.pack(fill=tk.BOTH, expand=True, padx=14)
        bf = tk.Frame(dlg, bg=BG0); bf.pack(fill=tk.X, padx=14, pady=(8,14))
        status_lbl = tk.Label(bf, text="", font=F1, bg=BG0, fg=YLW); status_lbl.pack(side=tk.LEFT)
        def _run():
            idea = idea_text.get("1.0", tk.END).strip()
            if len(idea) < 10: result_text.insert(tk.END, "请描述你的交易思路(至少10个字)\n"); return
            result_text.delete(1.0, tk.END); result_text.insert(tk.END, "AI分析中: 1)解析战法 2)提取因子 3)构建策略 4)回测\n")
            status_lbl.configure(text="AI生成中...")
            def _do():
                try:
                    from src.ai.engine import LLMClient
                    from src.factors.definitions import FACTOR_REGISTRY
                    from src.backtest.data_feed import get_data
                    from src.backtest.engine import BacktestEngine
                    from src.factors.composer import SignalComposer
                    from src.models.strategy import StrategyConfig
                    import json, re
                    flist = "\n".join([f"{n}({f.category}): {f.description}" for n,f in FACTOR_REGISTRY.items()])
                    prompt = f"""你是量化策略构建专家。解析用户的交易思路为JSON。
可用因子:{flist}
运算符:lt(小于),gt(大于) 逻辑:weighted(加权),and(全部),or(任一)
关键:仔细分析每个条件,至少3个因子,形态类(锤子/吞没)阈值0.5,其他阈值范围0-1
只返回JSON:{{"name":"策略名","explanation":"解析说明","conditions":[{{"factor":"rsi_norm","operator":"lt","threshold":0.3,"weight":2}}],"logic":"weighted","threshold":3.0}}
用户思路: {idea}"""
                    reply = LLMClient().ask(prompt, system="你是量化策略构建专家。只返回JSON。")
                    jm = re.search(r'\{.*\}', reply, re.DOTALL)
                    if not jm: result_text.insert(tk.END, f"AI解析失败,请重试\n{reply[:300]}"); return
                    sd = json.loads(jm.group(0))
                    data = get_data(sym_var.get(), "A股", start_date=date_var.get())
                    composer = SignalComposer(sd.get("name","AI策略"))
                    for c in sd.get("conditions",[]):
                        composer.add_condition(c["factor"],c["operator"],float(c["threshold"]),weight=int(c.get("weight",1)),action="BUY")
                    composer.set_logic(sd.get("logic","weighted"),float(sd.get("threshold",3.0)),action="BUY")
                    strategy = composer.to_strategy(StrategyConfig(name=sym_var.get()))
                    r = BacktestEngine().run(strategy, data)
                    lines = [f"策略: {sd.get('name','AI策略')}","",f"AI解析: {sd.get('explanation','')}","","因子条件:"]
                    for c in sd.get("conditions",[]): lines.append(f"  {c['factor']} {c['operator']} {c['threshold']} (权重{c.get('weight',1)})")
                    lines.append(f"\n逻辑: {sd.get('logic','weighted')} 阈值: {sd.get('threshold',3.0)}")
                    lines.append(f"\n═══ 回测结果 ═══")
                    for k,v in r["metrics"].items(): lines.append(f"  {k}: {v}")
                    result_text.delete(1.0, tk.END); result_text.insert(tk.END, "\n".join(lines))
                    status_lbl.configure(text="策略创建完成!", fg=GRN)
                except Exception as e: result_text.insert(tk.END, f"\n错误: {e}"); status_lbl.configure(text="失败", fg=RED)
            threading.Thread(target=_do, daemon=True).start()
        tk.Button(bf, text="🧬 AI生成策略", font=F3, bg=ACC, fg="white", relief="flat", bd=0, padx=20, pady=10, cursor="hand2", command=_run).pack(side=tk.LEFT)

    def _daily_scan_gui(self):
        """每日快扫"""
        self._bg(lambda: self._run_daily_scan(), "DAILY_SCAN")

    def _run_daily_scan(self):
        import io
        self._log("\n════ 每日快扫 ════")
        self._log("  刷新行情 · 因子评分 · 信号排名")
        try:
            from daily_runner import run_daily_scan
            buf = io.StringIO()
            old = sys.stdout; sys.stdout = buf
            run_daily_scan()
            sys.stdout = old
            for line in buf.getvalue().split("\n"):
                if line.strip(): self._log(f"  {line.strip()}")
        except Exception as e:
            self._log(f"  扫描失败: {e}")
        self._log("  快扫完成")

    def _status(self):
        self._log("\n═══ SYSTEM STATUS ═══")
        from src.models.trade import TradeRepository
        from src.backtest.data_feed import get_data_summary
        from src.backtest.batch_runner import ResultDB
        repo=TradeRepository(); cache=get_data_summary(); db=ResultDB()
        pnl=[p["net_pnl"] for p in repo.get_all_pnl()]
        tp=sum(pnl) if pnl else 0
        self._log(f"  Trades: {repo.count()}  |  Positions: {len(repo.find_open_positions())}")
        self._log(f"  P&L: ¥{tp:+,.0f}  |  WinRate: {len([p for p in pnl if p>0])/max(len(pnl),1)*100:.0f}%")
        self._log(f"  Cache: {len(cache)} files / {int(cache['行数'].sum()) if not cache.empty else 0} rows")
        self._log(f"  Backtests: {db.summary().get('总回测数',0)}")
        self._upd_kpi()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        ico = os.path.join(os.path.dirname(os.path.dirname(__file__)), "LXL_icon.ico")
        if os.path.exists(ico): root.iconbitmap(ico)
    except: pass
    App(root)
    root.mainloop()
