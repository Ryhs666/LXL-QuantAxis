# -*- coding: utf-8 -*-
"""
Research Manifest — 研究复现清单生成器

捕获当前运行环境的完整元数据, 生成 JSON 审计文件。

集成方式:
    1. 手动: from src.journal.manifest import generate_manifest
    2. 自动: BatchRunner.run() 结束时自动调用
    3. CLI:  python -m src.journal.manifest

清单内容:
    - 实验名称 / 时间戳 / Git 版本
    - Python 版本 / 操作系统
    - 回测参数 (策略/资金/日期…)
    - 数据来源 (起止日期/标的数/数据源)
    - 自定义扩展元数据
"""

import json
import os
import sys
import platform
import hashlib
import subprocess
from datetime import datetime
from typing import Any, Dict, Optional, List
from pathlib import Path

import pandas as pd
import numpy as np


# ═══════════════════════════════════════════
# 环境元数据
# ═══════════════════════════════════════════

def _project_root() -> Path:
    """项目根目录 (manifest.py → journal/ → src/ → root)"""
    return Path(__file__).resolve().parent.parent.parent


def get_git_hash() -> Optional[str]:
    """获取当前 Git Commit 短哈希"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True,
            cwd=str(_project_root()), timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:8]
    except Exception:
        pass
    return None


def get_git_branch() -> Optional[str]:
    """获取当前 Git 分支名"""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True,
            cwd=str(_project_root()), timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_git_status() -> Optional[str]:
    """获取工作区是否干净"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True,
            cwd=str(_project_root()), timeout=5,
        )
        if result.returncode == 0:
            return "clean" if not result.stdout.strip() else "dirty"
    except Exception:
        pass
    return None


def hash_dataframe(df: pd.DataFrame) -> str:
    """生成 DataFrame 哈希指纹 (数据版本检测)"""
    sample = (
        df.head(100).fillna(0).values.tobytes()
        + df.columns.values.tobytes()
    )
    return hashlib.md5(sample).hexdigest()[:8]


def hash_file(filepath: str) -> Optional[str]:
    """生成文件 MD5 哈希"""
    try:
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()[:8]
    except Exception:
        return None


# ═══════════════════════════════════════════
# 清单生成
# ═══════════════════════════════════════════

def generate_manifest(
    experiment_name: str,
    params: Dict[str, Any] = None,
    data_source_info: Dict[str, Any] = None,
    output_dir: str = None,
    extra_meta: Dict[str, Any] = None,
    data_hashes: Dict[str, Any] = None,
) -> str:
    """
    生成并保存研究复现清单。

    Args:
        experiment_name: 实验名称 (如 "ma_cross_batch_20240804")
        params:          策略/回测参数
        data_source_info: 数据来源信息
        output_dir:      输出目录 (默认 D:/trading_data/journal/)
        extra_meta:      自定义扩展元数据
        data_hashes:     数据文件哈希字典 {filename: md5}

    Returns:
        保存的 JSON 文件路径
    """
    # 构建清单
    manifest = {
        # ── 实验标识 ──
        "experiment_name": experiment_name,
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "timestamp_local": datetime.now().isoformat(),

        # ── 环境 ──
        "environment": {
            "python_version": sys.version.split()[0],
            "python_full": sys.version,
            "platform": platform.platform(),
            "system": platform.system(),
            "machine": platform.machine(),
        },

        # ── 代码版本 ──
        "code_version": {
            "git_branch": get_git_branch(),
            "git_commit": get_git_hash(),
            "git_status": get_git_status(),
        },

        # ── 策略参数 ──
        "parameters": params or {},

        # ── 数据来源 ──
        "data_source": data_source_info or {},

        # ── 数据哈希 ──
        "data_hashes": data_hashes or {},

        # ── 扩展 ──
        "extra": extra_meta or {},
    }

    # 确保输出目录存在
    output_dir = output_dir or os.path.join(
        os.environ.get("QUANT_DATA_DIR", os.environ.get("TRADING_DATA_DIR", "D:/trading_data")),
        "journal",
    )
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 生成文件名
    safe_name = experiment_name.replace(" ", "_").replace("/", "_")
    filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = str(Path(output_dir) / filename)

    # 写入
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)

    print(f"[Manifest] 复现清单已保存: {filepath}")
    return filepath


# ═══════════════════════════════════════════
# 便捷: 从回测结果生成清单
# ═══════════════════════════════════════════

def manifest_from_backtest(
    strategy_name: str,
    symbol: str,
    metrics: Dict[str, Any],
    params: Dict[str, Any] = None,
    extra: Dict[str, Any] = None,
) -> str:
    """
    从回测结果一键生成复现清单。

    Args:
        strategy_name: 策略名称
        symbol:        标的代码
        metrics:       回测指标字典 (来自 BacktestEngine.run())
        params:        策略参数
        extra:         扩展信息

    Returns:
        清单文件路径
    """
    experiment_name = f"backtest_{strategy_name}_{symbol}"

    return generate_manifest(
        experiment_name=experiment_name,
        params={
            "strategy": strategy_name,
            "symbol": symbol,
            **(params or {}),
        },
        data_source_info={
            "symbol": symbol,
            "metrics_summary": {
                k: v for k, v in metrics.items()
                if isinstance(v, (int, float, str, bool))
            },
        },
        extra_meta={
            "type": "single_backtest",
            **({k: str(v) for k, v in metrics.items()} if metrics else {}),
            **(extra or {}),
        },
    )


def manifest_from_batch_run(
    symbols: List[str],
    strategies: List[str],
    start_date: str,
    end_date: str = None,
    result_count: int = 0,
    top_sharpe: float = 0.0,
    params: Dict[str, Any] = None,
    extra: Dict[str, Any] = None,
) -> str:
    """
    从批量回测结果生成复现清单。

    Args:
        symbols:      标的列表
        strategies:   策略列表
        start_date:   起始日期
        end_date:     结束日期
        result_count: 回测结果总数
        top_sharpe:   最高夏普比率
        params:       额外参数
        extra:        扩展信息
    """
    experiment_name = f"batch_{len(symbols)}syms_{len(strategies)}strats"

    return generate_manifest(
        experiment_name=experiment_name,
        params={
            "symbols": symbols,
            "strategies": strategies,
            "start_date": start_date,
            "end_date": end_date or datetime.now().strftime("%Y-%m-%d"),
            **(params or {}),
        },
        data_source_info={
            "symbol_count": len(symbols),
            "strategy_count": len(strategies),
            "result_count": result_count,
            "top_sharpe": round(top_sharpe, 3),
        },
        extra_meta={
            "type": "batch_backtest",
            **(extra or {}),
        },
    )


# ═══════════════════════════════════════════
# CLI / 测试
# ═══════════════════════════════════════════

if __name__ == "__main__":
    test_params = {
        "strategy": "DualThrust",
        "lookback": 20,
        "k1": 0.5,
        "k2": 0.5,
        "stop_loss": 0.02,
    }
    data_info = {
        "start_date": "2023-01-01",
        "end_date": "2024-12-31",
        "symbol_count": 5500,
        "source": "akshare",
    }
    path = generate_manifest(
        experiment_name="dual_thrust_optimize_v3",
        params=test_params,
        data_source_info=data_info,
        extra_meta={"note": "基准测试 — 时钟修正前"},
    )
    print(f"\n清单文件: {path}")

    # 也测试从回测生成
    path2 = manifest_from_backtest(
        strategy_name="ma_cross",
        symbol="601398",
        metrics={"夏普比率": 1.25, "总收益率": "+15.3%", "胜率": "55.0%"},
        params={"fast_period": 5, "slow_period": 20},
    )
    print(f"回测清单: {path2}")
