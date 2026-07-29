"""
打包脚本 — 将量化系统打包成独立 EXE

运行: python build_exe.py

输出: dist/LXL_QuantAxis_v2.0/
      ├── LXL_QuantAxis.exe     (主程序)
      ├── LXL_icon.ico           (图标)
      ├── 启动说明.txt           (使用指南)
      ├── ai_config.json         (AI配置模板)
      └── data/                  (数据目录)
"""

import os, sys, shutil, json
from pathlib import Path

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_DIR, "dist", "LXL_QuantAxis_v2.0")


def clean():
    """清理旧构建"""
    for d in ["dist", "build", "__pycache__"]:
        p = os.path.join(PROJECT_DIR, d)
        if os.path.exists(p):
            shutil.rmtree(p)


def build_exe():
    """用 PyInstaller 打包成 EXE"""
    print("\n" + "=" * 60)
    print("  LXL·QuantAxis — 打包为独立 EXE")
    print("=" * 60)

    # PyInstaller 命令
    cmd = (
        f'pyinstaller '
        f'--onefile '               # 单文件EXE
        f'--windowed '              # 无控制台窗口
        f'--name "LXL_QuantAxis" '
        f'--icon "{PROJECT_DIR}/LXL_icon.ico" '
        f'--add-data "{PROJECT_DIR}/LXL_icon.ico;." '
        f'--hidden-import tkinter '
        f'--hidden-import pandas '
        f'--hidden-import numpy '
        f'--hidden-import akshare '
        f'--hidden-import plotly '
        f'--hidden-import sqlite3 '
        f'--hidden-import json '
        f'--hidden-import threading '
        f'--hidden-import re '
        f'--hidden-import io '
        f'--hidden-import webbrowser '
        f'--hidden-import urllib '
        f'--noconfirm '
        f'--clean '
        f'"{PROJECT_DIR}/launcher.py"'
    )

    print("\n  构建中... (可能需要2-5分钟)")
    print(f"  命令: {cmd[:80]}...")
    os.system(cmd)


def create_dist_package():
    """创建可发布的完整包"""
    print("\n  创建分发包...")
    os.makedirs(DIST_DIR, exist_ok=True)

    # 1. 复制 EXE
    exe_src = os.path.join(PROJECT_DIR, "dist", "LXL_QuantAxis.exe")
    if os.path.exists(exe_src):
        shutil.copy(exe_src, DIST_DIR)
        print(f"  ✅ EXE 已复制")

    # 2. 图标
    ico_src = os.path.join(PROJECT_DIR, "LXL_icon.ico")
    if os.path.exists(ico_src):
        shutil.copy(ico_src, DIST_DIR)

    # 3. 数据目录
    data_dir = os.path.join(DIST_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)

    # 复制数据库
    for f in ["stock_names.db", "backtest_results.db"]:
        src = os.path.join("D:/trading_data", f)
        if os.path.exists(src):
            dst = os.path.join(data_dir, f)
            if not os.path.exists(dst):
                shutil.copy(src, dst)

    # 4. AI 配置模板
    ai_template = {
        "api_key": "",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "temperature": 0.3,
        "max_tokens": 2048,
    }
    with open(os.path.join(DIST_DIR, "ai_config.json"), "w", encoding="utf-8") as f:
        json.dump(ai_template, f, indent=2, ensure_ascii=False)

    # 5. 启动说明
    readme = """╔══════════════════════════════════════════════════╗
║     LXL·QuantAxis  量化交易系统  v2.0              ║
╚══════════════════════════════════════════════════╝

【快速开始】
  1. 双击 LXL_QuantAxis.exe 启动
  2. 首次使用建议:
     a) 点左侧「下载数据」下载行情
     b) 点「批量回测」测试策略
     c) 点「仪表盘」查看可视化
  3. 使用 AI 功能需要配置 API Key:
     a) 注册 DeepSeek: https://platform.deepseek.com
     b) 点左侧 AI → 配置 AI → 输入 Key

【目录结构】
  LXL_QuantAxis.exe    主程序
  data/                 数据存储(交易记录/回测结果/行情)
  ai_config.json        AI 配置

【系统要求】
  - Windows 10/11 64位
  - 需要联网 (获取行情数据)
  - 无需安装 Python

【注意事项】
  - 所有数据保存在 data/ 目录
  - AI 功能需自行注册 DeepSeek (约10元用几个月)
  - 股票名称库已内置 5000+ A股
  - 仅供学习研究，不构成投资建议

  Author: LXL
  Version: 2.0 | 2026
"""
    with open(os.path.join(DIST_DIR, "启动说明.txt"), "w", encoding="utf-8") as f:
        f.write(readme)

    # 6. 创建桌面快捷方式批处理
    shortcut_bat = f"""@echo off
start "" "{DIST_DIR}\\LXL_QuantAxis.exe"
"""
    with open(os.path.join(DIST_DIR, "启动.bat"), "w", encoding="utf-8") as f:
        f.write(shortcut_bat)

    # 7. 打包为 ZIP
    zip_path = os.path.join(PROJECT_DIR, "dist", "LXL_QuantAxis_v2.0.zip")
    shutil.make_archive(
        os.path.join(PROJECT_DIR, "dist", "LXL_QuantAxis_v2.0"),
        "zip",
        os.path.dirname(DIST_DIR),
        os.path.basename(DIST_DIR),
    )

    # 统计
    total_size = sum(
        os.path.getsize(os.path.join(dirpath, filename))
        for dirpath, _, filenames in os.walk(DIST_DIR)
        for filename in filenames
    )

    print(f"\n  ╔══════════════════════════════════════╗")
    print(f"  ║  打包完成!                           ║")
    print(f"  ╠══════════════════════════════════════╣")
    print(f"  ║  目录: {DIST_DIR}")
    print(f"  ║  大小: {total_size / 1024 / 1024:.1f} MB")
    print(f"  ║  ZIP:  {zip_path}")
    print(f"  ╚══════════════════════════════════════╝")
    print(f"\n  分享给别人: 把 {os.path.basename(DIST_DIR)} 整个文件夹打包发送")
    print(f"  或者直接发送 ZIP 文件")


if __name__ == "__main__":
    clean()
    build_exe()
    create_dist_package()
