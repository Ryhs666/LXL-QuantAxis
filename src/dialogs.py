"""
LXL·QuantAxis 对话框模块
三个 Toplevel 对话框：快速验证、个股诊断、因子策略构建器
"""
import tkinter as tk
from tkinter import ttk
import threading
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 主题色（与 app.py 保持一致）
BG0 = "#060912"
BG1 = "#0b0f1a"
BG2 = "#111827"
BG3 = "#1a2332"
BG4 = "#1f2a3a"
ACC = "#3b82f6"
ACC2 = "#8b5cf6"
GRN = "#10b981"
RED = "#ef4444"
YLW = "#f59e0b"
CYN = "#06b6d4"
TX1 = "#f1f5f9"
TX2 = "#94a3b8"
TX3 = "#475569"


FT = ("Segoe UI", 14, "bold")
FT2 = ("Segoe UI", 12, "bold")
F1 = ("Segoe UI", 10)
F2 = ("Segoe UI", 9)
FST = ("Segoe UI", 8)
FM = ("Cascadia Code", 10)
F3 = ("Segoe UI", 11, "bold")


def _refresh_data(sym, market="A股"):
    """检查并刷新数据到最新"""
    from src.backtest.data_feed import download_watchlist, get_data_summary
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        cache_df = get_data_summary()
        target = f"{market}_{sym}_daily.csv"
        if not cache_df.empty and target in cache_df["文件"].values:
            mask = cache_df["文件"] == target
            latest = str(cache_df[mask].iloc[0]["结束日期"]).strip()[:10]
            if latest < today_str:
                download_watchlist([{"symbol": sym, "market": market, "name": sym}], verbose=False)
    except:
        pass


# ═══════════════════════════════════════════
# 1. 快速验证对话框
# ═══════════════════════════════════════════

def QuickBacktestDialog(parent):
    dlg = tk.Toplevel(parent)
    dlg.title("快速验证")
    dlg.geometry("760x680")
    dlg.minsize(600, 500)
    dlg.configure(bg=BG0)
    dlg.transient(parent)

    # 标题
    tk.Label(dlg, text="快速验证", font=FT, bg=BG0, fg="#f1f5f9").pack(pady=(14, 0))
    tk.Label(dlg, text="选股票 · 设时间 · 选策略 · 一键回测验证", font=F1, bg=BG0, fg=TX3).pack(pady=(2, 8))

    # 参数卡片
    card = tk.Frame(dlg, bg=BG2)
    card.pack(fill=tk.X, padx=16, pady=(0, 6))

    # Row 0: 股票代码 + 名称 + 搜索建议
    tk.Label(card, text="股票代码", font=F1, bg=BG2, fg=TX2).grid(row=0, column=0, sticky="w", padx=(14, 6), pady=(10, 4))
    sym_var = tk.StringVar(value="601398")
    sym_entry = tk.Entry(card, textvariable=sym_var, font=F1, bg=BG3, fg=TX1, relief="flat", bd=0, width=14,
             insertbackground=TX1)
    sym_entry.grid(row=0, column=1, sticky="w", pady=(10, 4), ipady=5)

    name_var = tk.StringVar()
    tk.Label(card, textvariable=name_var, font=F1, bg=BG2, fg=GRN).grid(row=0, column=2, sticky="w", padx=(10, 0), pady=(10, 4))

    # 搜索建议列表
    suggest_frame = tk.Frame(card, bg=BG2)
    suggest_list = tk.Listbox(suggest_frame, font=FST, bg=BG3, fg=TX2, relief="flat", bd=0, height=0)
    suggest_list.pack(fill=tk.X, expand=True)

    def _hide_suggest():
        suggest_frame.grid_remove()
        suggest_list.delete(0, tk.END)

    def _on_suggest_select(e):
        if suggest_list.curselection():
            sel = suggest_list.get(suggest_list.curselection()[0])
            code = sel.split(" - ")[0].strip()
            sym_var.set(code)
            _hide_suggest()

    suggest_list.bind("<<ListboxSelect>>", _on_suggest_select)
    suggest_list.bind("<FocusOut>", lambda e: _hide_suggest())

    def _lookup(*_):
        val = sym_var.get().strip()
        if not val:
            name_var.set("")
            _hide_suggest()
            return
        try:
            from src.data.stock_db import ensure_stock_db
            db = ensure_stock_db()
            # 精确查找
            n = db.get_name(val)
            if n and n != val:
                name_var.set(n)
                _hide_suggest()
            else:
                # 模糊搜索建议
                results = db.search(val, limit=8)
                if results and len(val) >= 2:
                    suggest_list.delete(0, tk.END)
                    for r in results:
                        suggest_list.insert(tk.END, f"{r['code']} - {r['name']} ({r['market']})")
                    h = min(len(results), 6)
                    suggest_list.configure(height=h)
                    suggest_frame.grid(row=1, column=1, columnspan=2, sticky="we", padx=(0, 10), pady=(0, 6))
                else:
                    _hide_suggest()
        except:
            pass

    sym_var.trace_add("write", _lookup)
    sym_entry.bind("<FocusIn>", lambda e: _lookup())
    _lookup()

    # Row 1: 起始日期 + 截止日期
    tk.Label(card, text="起始日期", font=F1, bg=BG2, fg=TX2).grid(row=1, column=0, sticky="w", padx=(14, 6), pady=4)
    start_var = tk.StringVar(value="2024-01-01")
    tk.Entry(card, textvariable=start_var, font=F1, bg=BG3, fg=TX1, relief="flat", bd=0, width=14,
             insertbackground=TX1).grid(row=1, column=1, sticky="w", pady=4, ipady=5)

    tk.Label(card, text="截止日期", font=F1, bg=BG2, fg=TX2).grid(row=1, column=2, sticky="w", padx=(10, 6), pady=4)
    end_var = tk.StringVar(value="")
    tk.Entry(card, textvariable=end_var, font=F1, bg=BG3, fg=TX1, relief="flat", bd=0, width=14,
             insertbackground=TX1).grid(row=1, column=3, sticky="w", pady=4, ipady=5, padx=(0, 10))

    # Row 2: 策略选择
    tk.Label(card, text="选择策略", font=F1, bg=BG2, fg=TX2).grid(row=2, column=0, sticky="w", padx=(14, 6), pady=(6, 10))

    from src.strategies.library import STRATEGIES
    from src.factors.composer import PRESET_STRATEGIES

    strat_map = {}
    strat_list = []
    for key, info in STRATEGIES.items():
        strat_map[info["name"]] = key
        strat_list.append(info["name"])
    for key, info in PRESET_STRATEGIES.items():
        strat_map[info["name"]] = key
        strat_list.append(info["name"])

    strat_var = tk.StringVar(value=strat_list[0])
    strat_menu = tk.OptionMenu(card, strat_var, *strat_list)
    strat_menu.configure(font=F1, bg=BG3, fg=TX1, relief="flat", bd=0)
    strat_menu["menu"].configure(bg=BG2, fg=TX2, font=F1, activebackground=BG3, activeforeground=TX1)
    strat_menu.grid(row=2, column=1, columnspan=3, sticky="w", pady=(8, 14))

    # 结果区
    result_frame = tk.Frame(dlg, bg=BG2)
    result_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 4))

    result_text = tk.Text(result_frame, font=FM, bg="#060912", fg="#f1f5f9", relief="flat", bd=0,
                          padx=14, pady=12, wrap="word", insertbackground=TX1)
    result_text.pack(fill=tk.BOTH, expand=True)
    result_text.insert("1.0", "输入股票代码和日期，选择策略，点击运行验证...\n")

    # 底部按钮 — 大而显眼
    bf = tk.Frame(dlg, bg=BG0)
    bf.pack(fill=tk.X, padx=16, pady=(6, 14))

    status_lbl = tk.Label(bf, text="", font=F1, bg=BG0, fg=YLW)
    status_lbl.pack(side=tk.LEFT, padx=(0, 12))

    def _run():
        result_text.delete("1.0", tk.END)
        sym = sym_var.get().strip()
        market = "A股"
        start = start_var.get().strip() or "2024-01-01"
        end = end_var.get().strip() or None
        strat_name = strat_var.get()
        strat_key = strat_map.get(strat_name, "ma_cross")

        result_text.insert(tk.END, f"▸ 标的: {sym}  |  区间: {start} ~ {end or '最新'}\n")
        result_text.insert(tk.END, f"▸ 策略: {strat_name}\n\n")
        status_lbl.configure(text="运行中...", fg=YLW)

        def _do():
            try:
                from src.backtest.data_feed import get_data
                from src.backtest.engine import BacktestEngine
                from src.backtest.batch_runner import _make_strategy_instance

                _refresh_data(sym, market)

                data = get_data(sym, market, start_date=start, end_date=end)
                result_text.insert(tk.END,
                                   f"数据: {len(data)} 条  "
                                   f"({str(data['date'].iloc[0])[:10]} ~ {str(data['date'].iloc[-1])[:10]})\n\n")

                strategy = _make_strategy_instance(strat_key, {}, sym)
                engine = BacktestEngine()
                result = engine.run(strategy, data)

                result_text.insert(tk.END, "══════ 回测结果 ══════\n\n")
                metrics = result["metrics"]
                for k, v in metrics.items():
                    result_text.insert(tk.END, f"  {k}: {v}\n")

                trades = result["portfolio"].trade_log
                if trades:
                    result_text.insert(tk.END, f"\n──── 最近交易 ({len(trades)}笔) ────\n")
                    for t in trades[-15:]:
                        icon = "B" if t["action"] == "BUY" else "S"
                        result_text.insert(tk.END,
                                           f"  [{icon}] {t['date']}  {t['action']}  "
                                           f"${t['price']:.2f} x {t['quantity']}\n")

                status_lbl.configure(text="验证完成", fg=GRN)
            except Exception as e:
                result_text.insert(tk.END, f"\n错误: {e}\n")
                status_lbl.configure(text="运行失败", fg=RED)

        threading.Thread(target=_do, daemon=True).start()

    tk.Button(bf, text="▶  运行验证", font=("Segoe UI", 13, "bold"), bg=ACC, fg="white",
              relief="flat", bd=0, padx=32, pady=12, cursor="hand2", command=_run,
              activebackground=ACC2, activeforeground="white").pack(side=tk.LEFT)


# ═══════════════════════════════════════════
# 2. 个股诊断对话框
# ═══════════════════════════════════════════

def DiagnosisDialog(parent):
    dlg = tk.Toplevel(parent)
    dlg.title("个股诊断")
    dlg.geometry("820x760")
    dlg.minsize(650, 550)
    dlg.configure(bg=BG0)
    dlg.transient(parent)

    tk.Label(dlg, text="个股诊断", font=FT, bg=BG0, fg="#f1f5f9").pack(pady=(14, 0))
    tk.Label(dlg, text="全策略扫描 · 投资者适配 · 入场时机 · 仓位建议", font=F1, bg=BG0, fg=TX3).pack(pady=(2, 8))

    # 参数卡片
    card = tk.Frame(dlg, bg=BG2)
    card.pack(fill=tk.X, padx=16, pady=(0, 8))

    tk.Label(card, text="股票代码", font=F1, bg=BG2, fg=TX2).grid(row=0, column=0, sticky="w", padx=(14, 6), pady=(10, 4))
    sym_var = tk.StringVar(value="601398")
    tk.Entry(card, textvariable=sym_var, font=F1, bg=BG3, fg=TX1, relief="flat", bd=0, width=12,
             insertbackground=TX1).grid(row=0, column=1, sticky="w", pady=(10, 4), ipady=5)

    tk.Label(card, text="起始日期", font=F1, bg=BG2, fg=TX2).grid(row=0, column=2, sticky="w", padx=(16, 6), pady=(10, 4))
    start_var = tk.StringVar(value="2022-01-01")
    tk.Entry(card, textvariable=start_var, font=F1, bg=BG3, fg=TX1, relief="flat", bd=0, width=12,
             insertbackground=TX1).grid(row=0, column=3, sticky="w", pady=(10, 4), ipady=5)

    name_var = tk.StringVar()
    tk.Label(card, textvariable=name_var, font=F1, bg=BG2, fg=GRN).grid(row=0, column=4, sticky="w", padx=(10, 0), pady=(10, 4))

    def _lookup(*_):
        try:
            from src.data.stock_db import ensure_stock_db
            n = ensure_stock_db().get_name(sym_var.get())
            name_var.set(n if n and n != sym_var.get() else "")
        except:
            pass

    sym_var.trace_add("write", _lookup)
    _lookup()

    # 策略选择卡片
    strat_card = tk.Frame(dlg, bg=BG2)
    strat_card.pack(fill=tk.X, padx=16, pady=(0, 8))

    tk.Label(strat_card, text="选择策略 (默认全选):", font=F1, bg=BG2, fg=TX2).pack(anchor="w", padx=14, pady=(10, 4))

    from src.strategies.library import STRATEGIES
    from src.factors.composer import PRESET_STRATEGIES

    all_strats = [(key, info["name"]) for key, info in STRATEGIES.items()]
    all_strats += [(key, info["name"]) for key, info in PRESET_STRATEGIES.items()]
    strat_vars = {}

    row1 = tk.Frame(strat_card, bg=BG2)
    row1.pack(fill=tk.X, padx=10)
    row2 = tk.Frame(strat_card, bg=BG2)
    row2.pack(fill=tk.X, padx=10, pady=(2, 10))

    for i, (key, name) in enumerate(all_strats):
        parent = row1 if i < 6 else row2
        v = tk.BooleanVar(value=True)
        strat_vars[key] = v
        tk.Checkbutton(parent, text=name, variable=v, font=FST, bg=BG2, fg=TX2,
                       selectcolor=BG3, activebackground=BG2, activeforeground=TX1,
                       relief="flat", bd=0).pack(side=tk.LEFT, padx=(0, 14))

    # 结果区
    result_text = tk.Text(dlg, font=("Cascadia Code", 10), bg=BG0, fg=TX1, relief="flat", bd=0,
                          padx=16, pady=16, wrap="word")
    result_text.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 8))
    result_text.insert("1.0", "选择股票和策略，点击开始诊断...\n")

    # 底部
    bf = tk.Frame(dlg, bg=BG0)
    bf.pack(fill=tk.X, padx=16, pady=(4, 16))
    status_lbl = tk.Label(bf, text="", font=F1, bg=BG0, fg=YLW)
    status_lbl.pack(side=tk.LEFT, padx=(0, 12))

    def _run():
        selected = [k for k, v in strat_vars.items() if v.get()]
        if not selected:
            result_text.delete("1.0", tk.END)
            result_text.insert("1.0", "请至少选择一个策略\n")
            return

        result_text.delete("1.0", tk.END)
        sym = sym_var.get().strip()
        start = start_var.get().strip() or "2022-01-01"
        result_text.insert(tk.END, f"▸ 诊断标的: {sym}  |  策略: {len(selected)} 个\n\n")
        status_lbl.configure(text="运行中...", fg=YLW)

        def _do():
            try:
                from src.backtest.data_feed import get_data
                from src.backtest.engine import BacktestEngine
                from src.backtest.batch_runner import _make_strategy_instance
                from src.factors.definitions import FactorCalculator
                from datetime import datetime

                _refresh_data(sym, "A股")

                data = get_data(sym, "A股", start_date=start)
                date_end = str(data["date"].iloc[-1])[:10]
                today_str = datetime.now().strftime("%Y-%m-%d")
                fresh = "今日" if date_end >= today_str else f"仅到{date_end}"
                price = float(data["close"].iloc[-1])

                result_text.insert(tk.END,
                                   f"数据: {len(data)} 条  |  {fresh}  |  价格: ${price:.2f}\n\n")

                # 运行选中的策略
                results = []
                for i, key in enumerate(selected):
                    name = key
                    for src in [STRATEGIES, PRESET_STRATEGIES]:
                        if key in src:
                            name = src[key].get("name", key)
                            break
                    result_text.insert(tk.END, f"  [{i + 1}/{len(selected)}] {name} ... ")
                    try:
                        s = _make_strategy_instance(key, {}, sym)
                        r = BacktestEngine().run(s, data)
                        results.append({"key": key, "name": name, "metrics": r["metrics"]})
                        result_text.insert(tk.END, "OK\n")
                    except Exception as e:
                        result_text.insert(tk.END, f"失败: {e}\n")

                result_text.insert(tk.END, "\n")

                # 排名
                def _ps(r):
                    try:
                        return float(str(r["metrics"].get("夏普比率", -999)))
                    except:
                        return -999

                results.sort(key=_ps, reverse=True)

                result_text.insert(tk.END, "══════ 策略排名 (按夏普) ══════\n\n")
                hdr = f"{'#':<3} {'策略':<16} {'总收益':>8} {'夏普':>6} {'回撤':>8} {'胜率':>6}"
                result_text.insert(tk.END, hdr + "\n")
                result_text.insert(tk.END, "-" * 50 + "\n")
                for i, r in enumerate(results, 1):
                    m = r["metrics"]
                    line = (f"{i:<3} {r['name']:<16} "
                            f"{str(m.get('总收益率', '-')):>8} "
                            f"{str(m.get('夏普比率', '-')):>6} "
                            f"{str(m.get('最大回撤', '-')):>8} "
                            f"{str(m.get('胜率', '-')):>6}")
                    result_text.insert(tk.END, line + "\n")

                # 入场评分
                result_text.insert(tk.END, "\n──── 当前入场时机 ────\n\n")
                try:
                    calc = FactorCalculator(data)
                    cf = calc.compute_all().iloc[-1]

                    def _fv(n, dft=0.5):
                        try:
                            return float(cf.get(n, dft))
                        except:
                            return dft

                    score = 50
                    rsi = _fv("rsi_norm")
                    if rsi < 0.3:
                        score += int((0.3 - rsi) / 0.3 * 20)
                    elif rsi > 0.7:
                        score -= int((rsi - 0.7) / 0.3 * 20)
                    else:
                        score += 5
                    bb = _fv("bollinger_pos")
                    if bb < 0.2:
                        score += int((0.2 - bb) / 0.2 * 20)
                    elif bb > 0.8:
                        score -= int((bb - 0.8) / 0.2 * 20)
                    else:
                        score += 5
                    ma = _fv("ma_alignment")
                    if ma > 0.7:
                        score += 15
                    elif ma < 0.3:
                        score -= 10
                    macd_h = _fv("macd_hist", 0.5)
                    if macd_h > 0.55:
                        score += 15
                    elif macd_h < 0.45:
                        score -= 10
                    score = max(0, min(100, score))

                    bar_filled = "█" * int(score / 5)
                    bar_empty = "░" * (20 - int(score / 5))
                    lvl = ("强烈买入" if score >= 80 else
                           "谨慎买入" if score >= 60 else
                           "观望等待" if score >= 40 else "建议回避")

                    result_text.insert(tk.END,
                                       f"  RSI: {rsi * 100:.0f}  布林: {bb:.2f}  均线: {ma:.2f}  MACD: {macd_h:.2f}\n")
                    result_text.insert(tk.END,
                                       f"  评分: {score}/100  [{bar_filled}{bar_empty}]  {lvl}\n")
                except Exception as e:
                    result_text.insert(tk.END, f"  因子分析失败: {e}\n")

                status_lbl.configure(text="诊断完成", fg=GRN)
            except Exception as e:
                result_text.insert(tk.END, f"\n错误: {e}\n")
                status_lbl.configure(text="运行失败", fg=RED)

        threading.Thread(target=_do, daemon=True).start()

    tk.Button(bf, text="▶  开始诊断", font=("Segoe UI", 13, "bold"), bg=GRN, fg="white",
              relief="flat", bd=0, padx=32, pady=12, cursor="hand2", command=_run,
              activebackground=ACC, activeforeground="white").pack(side=tk.LEFT)


# ═══════════════════════════════════════════
# 3. 因子策略构建器
# ═══════════════════════════════════════════

def FactorStrategyDialog(parent):
    dlg = tk.Toplevel(parent)
    dlg.title("因子策略构建器")
    dlg.geometry("860x760")
    dlg.minsize(680, 560)
    dlg.configure(bg=BG0)
    dlg.transient(parent)

    tk.Label(dlg, text="因子策略构建器", font=FT, bg=BG0, fg="#f1f5f9").pack(pady=(14, 0))
    tk.Label(dlg, text="选因子 · 配参数 · 建策略 · 直接回测", font=F1, bg=BG0, fg=TX3).pack(pady=(2, 8))

    # 股票 + 策略名
    card = tk.Frame(dlg, bg=BG2)
    card.pack(fill=tk.X, padx=16, pady=(0, 8))

    tk.Label(card, text="股票代码", font=F1, bg=BG2, fg=TX2).grid(row=0, column=0, sticky="w", padx=(14, 6), pady=(10, 4))
    sym_var = tk.StringVar(value="601398")
    tk.Entry(card, textvariable=sym_var, font=F1, bg=BG3, fg=TX1, relief="flat", bd=0, width=12,
             insertbackground=TX1).grid(row=0, column=1, sticky="w", pady=(10, 4), ipady=5)

    tk.Label(card, text="策略名称", font=F1, bg=BG2, fg=TX2).grid(row=0, column=2, sticky="w", padx=(16, 6), pady=(10, 4))
    name_var = tk.StringVar(value="我的因子策略")
    tk.Entry(card, textvariable=name_var, font=F1, bg=BG3, fg=TX1, relief="flat", bd=0, width=18,
             insertbackground=TX1).grid(row=0, column=3, sticky="w", pady=(10, 4), ipady=5)

    # 因子 Notebook
    from src.factors.definitions import FACTOR_REGISTRY

    nb = ttk.Notebook(dlg)
    nb.pack(fill=tk.X, padx=16, pady=(0, 8))

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TNotebook", background=BG0, borderwidth=0)
    style.configure("TNotebook.Tab", background=BG2, foreground=TX2, padding=[16, 8], font=F1, borderwidth=0)
    style.map("TNotebook.Tab", background=[("selected", BG3)], foreground=[("selected", TX1)])

    categories = {
        "trend": "趋势 (4)",
        "momentum": "动量 (5)",
        "volatility": "波动 (4)",
        "volume": "成交量 (3)",
        "pattern": "形态 (2)",
    }
    cat_factors = {}
    for fname, f in FACTOR_REGISTRY.items():
        cat_factors.setdefault(f.category, []).append((fname, f.description))

    factor_vars = {}
    threshold_vars = {}
    weight_vars = {}
    operator_vars = {}

    for cat_key, cat_label in categories.items():
        tab = tk.Frame(nb, bg=BG2)
        nb.add(tab, text=cat_label)
        factors = cat_factors.get(cat_key, [])
        for fname, fdesc in factors:
            rf = tk.Frame(tab, bg=BG2)
            rf.pack(fill=tk.X, padx=10, pady=2)

            v = tk.BooleanVar(value=False)
            factor_vars[fname] = v
            cb = tk.Checkbutton(rf, text=fname, variable=v, font=F1, bg=BG2, fg=TX2,
                                selectcolor=BG3, activebackground=BG2, width=18, anchor="w",
                                relief="flat", bd=0)
            cb.pack(side=tk.LEFT)

            tk.Label(rf, text=fdesc[:22], font=FST, bg=BG2, fg=TX3).pack(side=tk.LEFT, padx=(6, 10))

            op_var = tk.StringVar(value="lt")
            operator_vars[fname] = op_var
            om = tk.OptionMenu(rf, op_var, "lt", "gt")
            om.configure(font=FST, bg=BG3, fg=TX1, relief="flat", bd=0, width=3)
            om["menu"].configure(bg=BG2, fg=TX2, font=FST)
            om.pack(side=tk.LEFT, padx=(0, 6))

            th_var = tk.StringVar(value="0.5")
            threshold_vars[fname] = th_var
            tk.Entry(rf, textvariable=th_var, font=FST, bg=BG3, fg=TX1, relief="flat", bd=0,
                     width=5, insertbackground=TX1).pack(side=tk.LEFT)

            tk.Label(rf, text=" 权重:", font=FST, bg=BG2, fg=TX3).pack(side=tk.LEFT)
            w_var = tk.StringVar(value="1")
            weight_vars[fname] = w_var
            tk.Entry(rf, textvariable=w_var, font=FST, bg=BG3, fg=TX1, relief="flat", bd=0,
                     width=4, insertbackground=TX1).pack(side=tk.LEFT)

    # 逻辑选择
    logic_card = tk.Frame(dlg, bg=BG2)
    logic_card.pack(fill=tk.X, padx=16, pady=(0, 8))

    tk.Label(logic_card, text="买入逻辑:", font=F1, bg=BG2, fg=TX2).pack(side=tk.LEFT, padx=(14, 8), pady=10)
    logic_var = tk.StringVar(value="weighted")
    for mode in ["weighted", "and", "or"]:
        tk.Radiobutton(logic_card, text=mode, variable=logic_var, value=mode,
                       font=F1, bg=BG2, fg=TX2, selectcolor=BG3, activebackground=BG2).pack(side=tk.LEFT, padx=(0, 14))

    tk.Label(logic_card, text="触发阈值:", font=F1, bg=BG2, fg=TX2).pack(side=tk.LEFT, padx=(16, 6), pady=10)
    th_var = tk.StringVar(value="3.0")
    tk.Entry(logic_card, textvariable=th_var, font=F1, bg=BG3, fg=TX1, relief="flat", bd=0,
             width=6, insertbackground=TX1).pack(side=tk.LEFT, pady=10)

    # 结果区
    result_text = tk.Text(dlg, font=FM, bg=BG0, fg=TX1, relief="flat", bd=0,
                          padx=16, pady=16, wrap="word", height=8)
    result_text.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 8))
    result_text.insert("1.0", "选择因子，设定条件和权重，点击构建并回测...\n")

    # 底部
    bf = tk.Frame(dlg, bg=BG0)
    bf.pack(fill=tk.X, padx=16, pady=(4, 16))
    status_lbl = tk.Label(bf, text="", font=F1, bg=BG0, fg=YLW)
    status_lbl.pack(side=tk.LEFT, padx=(0, 12))

    def _run():
        selected = []
        for fname in factor_vars:
            if factor_vars[fname].get():
                try:
                    th = float(threshold_vars[fname].get())
                except ValueError:
                    th = 0.5
                try:
                    w = float(weight_vars[fname].get())
                except ValueError:
                    w = 1
                selected.append({
                    "factor": fname,
                    "operator": operator_vars[fname].get(),
                    "threshold": th,
                    "weight": w,
                })

        if not selected:
            result_text.delete("1.0", tk.END)
            result_text.insert("1.0", "请至少选择一个因子\n")
            return

        result_text.delete("1.0", tk.END)
        result_text.insert(tk.END, f"▸ 策略名称: {name_var.get()}\n")
        result_text.insert(tk.END, f"▸ 买入逻辑: {logic_var.get()}  触发阈值: {th_var.get()}\n")
        result_text.insert(tk.END, "▸ 选中因子:\n")
        for s in selected:
            result_text.insert(tk.END,
                               f"     {s['factor']}  {s['operator']}  {s['threshold']:.2f}  (权重 {s['weight']})\n")
        result_text.insert(tk.END, "\n")
        status_lbl.configure(text="运行中...", fg=YLW)

        def _do():
            try:
                from src.backtest.data_feed import get_data
                from src.backtest.engine import BacktestEngine
                from src.factors.composer import SignalComposer
                from src.models.strategy import StrategyConfig

                sym = sym_var.get().strip()
                _refresh_data(sym, "A股")

                data = get_data(sym, "A股", start_date="2024-01-01")
                result_text.insert(tk.END,
                                   f"数据: {len(data)} 条  "
                                   f"({str(data['date'].iloc[0])[:10]} ~ {str(data['date'].iloc[-1])[:10]})\n\n")

                composer = SignalComposer(name_var.get())
                for s in selected:
                    composer.add_condition(s["factor"], s["operator"], s["threshold"],
                                           weight=s["weight"], action="BUY")
                try:
                    buy_th = float(th_var.get())
                except ValueError:
                    buy_th = 3.0
                composer.set_logic(logic_var.get(), buy_th, action="BUY")

                strategy = composer.to_strategy(StrategyConfig(name=sym))
                engine = BacktestEngine()
                result = engine.run(strategy, data)

                result_text.insert(tk.END, "══════ 回测结果 ══════\n\n")
                for k, v in result["metrics"].items():
                    result_text.insert(tk.END, f"  {k}: {v}\n")

                trades = result["portfolio"].trade_log
                if trades:
                    result_text.insert(tk.END, f"\n──── 交易记录 ({len(trades)}笔) ────\n")
                    for t in trades[-10:]:
                        icon = "B" if t["action"] == "BUY" else "S"
                        result_text.insert(tk.END,
                                           f"  [{icon}] {t['date']}  {t['action']}  "
                                           f"${t['price']:.2f} x {t['quantity']}\n")

                status_lbl.configure(text="因子策略回测完成", fg=GRN)
            except Exception as e:
                result_text.insert(tk.END, f"\n错误: {e}\n")
                status_lbl.configure(text="运行失败", fg=RED)

        threading.Thread(target=_do, daemon=True).start()

    tk.Button(bf, text="▶  构建并回测", font=("Segoe UI", 13, "bold"), bg=ACC2, fg="white",
              relief="flat", bd=0, padx=32, pady=12, cursor="hand2", command=_run,
              activebackground=ACC, activeforeground="white").pack(side=tk.LEFT)