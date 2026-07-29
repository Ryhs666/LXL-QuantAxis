"""
终端美化输出

提供彩色打印、表格、分隔线、状态标识等。
Windows 终端需支持 ANSI (Win10+ 自带)
"""

import sys
import os
import shutil
from typing import Optional, List, Dict

# 启用 Windows ANSI 支持
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

# ============================================================
# ANSI 颜色
# ============================================================

class Style:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"

    # 背景
    BG_RED   = "\033[41m"
    BG_GREEN = "\033[42m"

    @classmethod
    def disable(cls):
        for attr in dir(cls):
            if not attr.startswith("_") and attr.isupper():
                setattr(cls, attr, "")


def disable_colors():
    Style.disable()


# ============================================================
# 输出函数
# ============================================================

def ok(msg: str):
    print(f"  {Style.GREEN}✅ {msg}{Style.RESET}")

def fail(msg: str):
    print(f"  {Style.RED}❌ {msg}{Style.RESET}")

def warn(msg: str):
    print(f"  {Style.YELLOW}⚠️ {msg}{Style.RESET}")

def info(msg: str):
    print(f"  {Style.BLUE}ℹ️ {msg}{Style.RESET}")

def title(msg: str):
    """打印主标题"""
    width = shutil.get_terminal_size().columns - 4
    print(f"\n{Style.BOLD}{Style.CYAN}{'='*width}{Style.RESET}")
    print(f"  {Style.BOLD}{msg}{Style.RESET}")
    print(f"{Style.CYAN}{'='*width}{Style.RESET}\n")

def subtitle(msg: str):
    """打印子标题"""
    print(f"\n  {Style.BOLD}{Style.YELLOW}▸ {msg}{Style.RESET}")
    print(f"  {Style.GRAY}{'─'*50}{Style.RESET}")

def section(msg: str):
    """打印大段落标题"""
    width = shutil.get_terminal_size().columns - 4
    print(f"\n{Style.BOLD}{'─'*width}{Style.RESET}")
    print(f"  {Style.BOLD}{msg}{Style.RESET}")
    print(f"{Style.BOLD}{'─'*width}{Style.RESET}")

def metric(label: str, value, color: str = "blue", indent: int = 4):
    """打印指标行"""
    color_map = {
        "green": Style.GREEN, "red": Style.RED, "yellow": Style.YELLOW,
        "blue": Style.BLUE, "cyan": Style.CYAN, "gray": Style.GRAY,
    }
    c = color_map.get(color, "")
    space = " " * indent
    print(f"{space}{Style.DIM}{label}:{Style.RESET} {c}{value}{Style.RESET}")


def table(headers: list, rows: List[list], col_widths: list = None,
          align: str = "left", title: str = ""):
    """打印格式化表格"""
    if not rows:
        print(f"  {Style.GRAY}(无数据){Style.RESET}")
        return

    if title:
        print(f"\n  {Style.BOLD}{title}{Style.RESET}")

    # 自动计算列宽
    all_rows = [headers] + rows
    if col_widths is None:
        col_widths = []
        for i in range(len(headers)):
            max_w = max(len(str(r[i])) for r in all_rows if i < len(r))
            col_widths.append(min(max_w + 2, 40))

    # 顶线
    total_w = sum(col_widths) + len(col_widths) + 1
    print(f"  {Style.GRAY}┌{'─'*total_w}┐{Style.RESET}")

    # 表头
    header_str = " │ ".join(
        f"{Style.BOLD}{str(h):<{col_widths[i]}}{Style.RESET}"
        for i, h in enumerate(headers)
    )
    print(f"  {Style.GRAY}│{Style.RESET} {header_str} {Style.GRAY}│{Style.RESET}")

    # 分隔线
    print(f"  {Style.GRAY}├{'─'*total_w}┤{Style.RESET}")

    # 数据行
    for row in rows:
        row_str = " │ ".join(
            str(row[i])[:col_widths[i]].ljust(col_widths[i])
            if align == "left" else
            str(row[i])[:col_widths[i]].rjust(col_widths[i])
            for i in range(min(len(row), len(col_widths)))
        )
        print(f"  {Style.GRAY}│{Style.RESET} {row_str} {Style.GRAY}│{Style.RESET}")

    # 底线
    print(f"  {Style.GRAY}└{'─'*total_w}┘{Style.RESET}")


def progress_bar(current: int, total: int, label: str = "",
                 width: int = 30, start_time: float = None):
    """打印进度条（单行覆盖）"""
    pct = min(current / max(total, 1), 1.0)
    filled = int(width * pct)
    bar = f"{Style.BG_GREEN}{' ' * filled}{Style.RESET}{Style.DIM}{'░' * (width - filled)}{Style.RESET}"
    count = f"{current}/{total}"
    pct_str = f"{pct*100:.0f}%"

    # 时间估算
    eta_str = ""
    if start_time:
        import time
        elapsed = time.time() - start_time
        if pct > 0.01:
            eta = elapsed / pct * (1 - pct)
            if eta < 60:
                eta_str = f"⏱{elapsed:.0f}s<{eta:.0f}s"
            else:
                eta_str = f"⏱{elapsed/60:.1f}m<{eta/60:.1f}m"

    msg = f"\r  {Style.DIM}{label}{Style.RESET} {bar} {Style.BOLD}{count}{Style.RESET} {pct_str} {Style.GRAY}{eta_str}{Style.RESET}"
    sys.stdout.write(msg)
    sys.stdout.flush()


def divider(char: str = "─"):
    """打印分隔线"""
    width = shutil.get_terminal_size().columns - 4
    print(f"  {Style.GRAY}{char * width}{Style.RESET}")


def panel(content: str, border_color: str = "blue"):
    """打印带边框的面板"""
    colors = {"blue": Style.BLUE, "green": Style.GREEN, "red": Style.RED}
    c = colors.get(border_color, Style.BLUE)
    lines = content.strip().split("\n")
    max_w = max(len(l) for l in lines) + 4
    print(f"  {c}╔{'═'*max_w}╗{Style.RESET}")
    for line in lines:
        print(f"  {c}║{Style.RESET} {line}{' '*(max_w - len(line) - 1)}{c}║{Style.RESET}")
    print(f"  {c}╚{'═'*max_w}╝{Style.RESET}")


def status_card(title: str, items: Dict[str, str]):
    """打印状态卡片"""
    c = Style.BLUE
    max_key = max(len(k) for k in items.keys()) + 2
    max_val = max(len(v) for v in items.values()) + 2
    w = max_key + max_val + 3
    print(f"\n  {c}{Style.BOLD}╭{'─'*w}╮{Style.RESET}")
    print(f"  {c}{Style.BOLD}│{Style.RESET} {Style.BOLD}{title:^{w}}{Style.RESET} {c}{Style.BOLD}│{Style.RESET}")
    print(f"  {c}{Style.BOLD}├{'─'*w}┤{Style.RESET}")
    for k, v in items.items():
        print(f"  {c}│{Style.RESET} {Style.DIM}{k:<{max_key}}{Style.RESET} {v:<{max_val}}{c}│{Style.RESET}")
    print(f"  {c}{Style.BOLD}╰{'─'*w}╯{Style.RESET}\n")
