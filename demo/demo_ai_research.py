#!/usr/bin/env python
"""LXL·QuantAxis V2.0 — AI Research Demo.

One command to experience the full AI quant research pipeline.

Usage:
    python demo/demo_ai_research.py
    python demo/demo_ai_research.py "Your investment thesis"
    python demo/demo_ai_research.py --example 1
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from demo.demo_config import DEMO_SYMBOL, DEMO_START_DATE, DEMO_USE_LLM, DEMO_OUTPUT_DIR, EXAMPLE_THESES


def print_header(text: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def print_step(n: int, total: int, name: str, status: str) -> None:
    icon = "OK" if status == "ok" else "FAIL"
    print(f"  [{n}/{total}] {name:<30s} [{icon}]")


def run_demo(idea: str, symbol: str = DEMO_SYMBOL, start_date: str = DEMO_START_DATE,
             use_llm: bool = DEMO_USE_LLM, output_dir: str = DEMO_OUTPUT_DIR) -> dict:
    """Run the complete AI research pipeline and return all results."""

    results = {
        "input": idea,
        "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
        "stages": {},
    }

    total_steps = 7
    print_header("LXL·QuantAxis V2.0 — AI Research Demo")
    print(f"  Input: {idea[:80]}...")
    print(f"  Symbol: {symbol} | Start: {start_date} | LLM: {use_llm}")

    # ── Step 1: Thesis Extraction ──
    try:
        from src.lxl_quantaxis.research.ai_parser import parse_and_save
        from src.lxl_quantaxis.research.notebook import get_note
        nid = parse_and_save(idea, use_llm=use_llm)
        note = get_note(nid)
        results["stages"]["thesis"] = {
            "note_id": nid,
            "title": note.title if note else idea[:60],
            "thesis": note.investment_thesis if note else "",
            "bull": note.bull_case if note else "",
            "bear": note.bear_case if note else "",
            "risk": note.risk if note else "",
        }
        print_step(1, total_steps, "Thesis Extraction", "ok")
    except Exception as e:
        results["stages"]["thesis"] = {"error": str(e)}
        print_step(1, total_steps, "Thesis Extraction", "fail")
        print(f"         Error: {e}")

    # ── Step 2: Factor Mapping ──
    try:
        from src.lxl_quantaxis.research.factor_mapper import map_thesis_to_factors
        model = map_thesis_to_factors(text=idea, use_llm=use_llm)
        fd = model.to_dict()
        results["stages"]["factor_model"] = fd
        print_step(2, total_steps, "Factor Mapping", "ok")
        for f in fd["factors"][:4]:
            print(f"         {f['name']}: {f['weight']:.0%} — {f['reason'][:40]}")
    except Exception as e:
        results["stages"]["factor_model"] = {"error": str(e)}
        print_step(2, total_steps, "Factor Mapping", "fail")

    # ── Step 3: Strategy Building ──
    spec = None
    try:
        from src.lxl_quantaxis.research.strategy_builder import build_and_compile
        spec = build_and_compile(factor_model=model, use_llm=use_llm)
        results["stages"]["strategy"] = {
            "name": spec.name,
            "entry": spec.entry_rule[:120],
            "exit": spec.exit_rule[:120],
        }
        print_step(3, total_steps, "Strategy Generation", "ok")
        print(f"         Entry: {spec.entry_rule[:80]}")
    except Exception as e:
        results["stages"]["strategy"] = {"error": str(e)}
        print_step(3, total_steps, "Strategy Generation", "fail")

    # ── Step 4: Validation ──
    try:
        if spec is None:
            raise ValueError("Strategy building failed")
        from src.lxl_quantaxis.strategy.validator import validate_strategy_spec
        validation = validate_strategy_spec(spec)
        results["stages"]["validation"] = validation.to_dict()
        status = "ok" if validation.valid else "fail"
        print_step(4, total_steps, "Validation", status)
        if not validation.valid:
            for e in validation.errors[:2]:
                print(f"         Error: {e}")
    except Exception as e:
        results["stages"]["validation"] = {"error": str(e)}
        print_step(4, total_steps, "Validation", "fail")

    # ── Step 5: Backtest ──
    metrics = {}
    try:
        if spec is None:
            raise ValueError("No strategy to backtest")
        from src.lxl_quantaxis.strategy.backtest_bridge import run_backtest
        bridge = run_backtest(spec, symbol=symbol, start_date=start_date)
        metrics = bridge.backtest_metrics
        results["stages"]["backtest"] = {
            "status": bridge.status,
            "metrics": metrics,
        }
        status = "ok" if bridge.status == "backtested" else "fail"
        print_step(5, total_steps, "Backtest", status)
        sharpe = metrics.get("夏普比率", metrics.get("sharpe", "N/A"))
        ret = metrics.get("总收益率", metrics.get("total_return", "N/A"))
        print(f"         Sharpe: {sharpe} | Return: {ret}")
    except Exception as e:
        results["stages"]["backtest"] = {"error": str(e)}
        print_step(5, total_steps, "Backtest", "fail")

    # ── Step 6: AI Analysis ──
    try:
        from src.lxl_quantaxis.ai.backtest_analyzer import analyze_and_log
        assessment = analyze_and_log(metrics, strategy_name=idea[:50], use_llm=use_llm)
        results["stages"]["analysis"] = assessment.to_dict()
        print_step(6, total_steps, "AI Analysis", "ok")
        print(f"         {assessment.summary[:80]}")
    except Exception as e:
        results["stages"]["analysis"] = {"error": str(e)}
        print_step(6, total_steps, "AI Analysis", "fail")

    # ── Step 7: Report Generation ──
    try:
        from src.lxl_quantaxis.research.report_generator import generate_report
        from src.lxl_quantaxis.research.thesis import InvestmentThesis
        thesis_obj = InvestmentThesis(
            symbol=symbol, title=idea[:60],
            core_argument=results["stages"].get("thesis", {}).get("thesis", ""),
        )
        report = generate_report(
            symbol=symbol, thesis=thesis_obj,
            factor_model=model, strategy_spec=spec,
            backtest_metrics=metrics, backtest_assessment=assessment,
        )
        os.makedirs(output_dir, exist_ok=True)
        paths = report.save(output_dir)
        results["stages"]["report"] = {"paths": paths}
        print_step(7, total_steps, "Report Generation", "ok")
        print(f"         Markdown: {paths['markdown']}")
        print(f"         HTML:     {paths['html']}")
    except Exception as e:
        results["stages"]["report"] = {"error": str(e)}
        print_step(7, total_steps, "Report Generation", "fail")

    # ── Summary ──
    success = sum(1 for s in results["stages"].values() if "error" not in s)
    print_header(f"Complete: {success}/{total_steps} stages passed")
    return results


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="LXL·QuantAxis AI Research Demo")
    p.add_argument("idea", nargs="?", default="",
                   help="Investment thesis text")
    p.add_argument("--example", "-e", type=int, choices=[1, 2, 3], default=0,
                   help="Run a pre-built example (1-3)")
    p.add_argument("--symbol", "-s", default=DEMO_SYMBOL)
    p.add_argument("--llm", action="store_true", default=DEMO_USE_LLM)
    p.add_argument("--output", "-o", default=DEMO_OUTPUT_DIR)
    args = p.parse_args()

    if args.example:
        ex = EXAMPLE_THESES[args.example - 1]
        idea = ex["text"]
        symbol = ex.get("symbol", args.symbol)
        print(f"\n  Using example #{args.example}: {ex['title']}")
    else:
        idea = args.idea or EXAMPLE_THESES[0]["text"]
        symbol = args.symbol

    results = run_demo(idea, symbol=symbol, use_llm=args.llm, output_dir=args.output)

    json_path = os.path.join(args.output, f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    os.makedirs(args.output, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Results saved: {json_path}")
