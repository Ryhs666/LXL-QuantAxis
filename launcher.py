"""LXL·QuantAxis — 启动入口 (供 PyInstaller 打包)"""
import sys, os

# PyInstaller 打包后路径处理
if getattr(sys, 'frozen', False):
    BASE = os.path.dirname(sys.executable)
else:
    BASE = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE)
os.chdir(BASE)

# 确保数据目录存在
DATA_DIR = os.path.join(BASE, "data")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "cache"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "dashboards"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "charts"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "logs"), exist_ok=True)

# 设置环境变量指向本地 data 目录
os.environ["TRADING_DATA_DIR"] = DATA_DIR

# 复制 config 设置
import json

# 自动更新 config 中的数据目录
try:
    from src.config import config as cfg
    cfg._data["data_dir"] = DATA_DIR
    cfg._data["cache_dir"] = os.path.join(DATA_DIR, "cache")
    cfg._data["log_dir"] = os.path.join(DATA_DIR, "logs")
except Exception:
    pass

# 启动
from src.app import App
import tkinter as tk

root = tk.Tk()
try:
    ico = os.path.join(BASE, "LXL_icon.ico")
    if os.path.exists(ico):
        root.iconbitmap(ico)
except Exception:
    pass
App(root)
root.mainloop()
