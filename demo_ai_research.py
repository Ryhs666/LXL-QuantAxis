#!/usr/bin/env python
"""LXL·QuantAxis V2.0 — AI Research Demo Pipeline.

One command to run the full AI research pipeline:
  python demo_ai_research.py "看好AI服务器产业链"

Stages:
  1. AI Thesis Extraction
  2. Factor Model Mapping
  3. Strategy DSL Building
  4. Backtest Validation
  5. AI Analysis
  6. Research Report Generation
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))


def run_demo(idea: str, symbol: str = "000001", start_date: str = "2024-01-01",
             use_llm: bool = True, output_dir: str = "reports") -> dict:
    """Run the complete AI research pipeline and return all results."""

    results = {
        "input": idea,
        "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
        "stages": {},
    }

    print(f"\n{'='*60}")
    print(f"  LXL·QuantAxis V2.0 — AI Research Pipeline")
    print(f"  Idea: {idea[:80]}")
    print(f"  Symbol: {symbol}")
    print(f"{'='*60}\n")

    # Stage 1: AI Thesis Extraction
    print("[1/6] AI Thesis Extraction...")
    try:
        from src.lxl_quantaxis.research.ai_parser import parse_and_save
        note_id = parse_and_save(idea, use_llm=use_llm)
        from src.lxl_quantaxis.research.notebook import get_note
        note = get_note(note_id)
        results["stages"]["thesis"] = {
            "note_id": note_id,
            "title": note.title if note else "",
            "thesis": note.investment_thesis if note else "",
            "source": "llm" if use_llm else "rule",
        }
        print(f"  -> Note #{note_id}: {note.title if note else 'N/A'}")
    except Exception as e:
        results["stages"]["thesis"] = {"error": str(e)}
        print(f"  -> FAILED: {e}")

    # Stage 2: Factor Model Mapping
    print("[2/6] Factor Model Mapping...")
    try:
        from src.lxl_quantaxis.research.factor_mapper import map_thesis_to_factors
        model = map_thesis_to_factors(text=idea, use_llm=use_llm)
        factor_dict = model.to_dict()
        results["stages"]["factor_model"] = factor_dict
        print(f"  -> Theme: {factor_dict['theme']}, "
              f"Factors: {len(factor_dict['factors'])}, "
              f"Source: {factor_dict['source']}")
    except Exception as e:
        results["stages"]["factor_model"] = {"error": str(e)}
        print(f"  -> FAILED: {e}")

    # Stage 3: Strategy DSL Building
    print("[3/6] Strategy Building...")
    try:
        from src.lxl_quantaxis.research.strategy_builder import build_and_compile
        spec = build_and_compile(factor_model=model, use_llm=use_llm)
        results["stages"]["strategy"] = {
            "name": spec.name,
            "entry_rule": spec.entry_rule[:100],
            "exit_rule": spec.exit_rule[:100],
            "source": spec.source,
        }
        print(f"  -> Strategy: {spec.name}, Source: {spec.source}")
    except Exception as e:
        results["stages"]["strategy"] = {"error": str(e)}
        print(f"  -> FAILED: {e}")

    # Stage 4: Backtest
    print(f"[4/6] Backtest ({symbol}, {start_date})...")
    try:
        from src.lxl_quantaxis.strategy.backtest_bridge import run_backtest
        bridge = run_backtest(spec, symbol=symbol, start_date=start_date)
        results["stages"]["backtest"] = {
            "status": bridge.status,
            "metrics": bridge.backtest_metrics,
            "validation": bridge.validation.to_dict() if bridge.validation else {},
        }
        status = bridge.status
        sharpe = bridge.backtest_metrics.get("夏普比率", "N/A")
        print(f"  -> Status: {status}, Sharpe: {sharpe}")
    except Exception as e:
        results["stages"]["backtest"] = {"error": str(e)}
        print(f"  -> FAILED: {e}")

    # Stage 5: AI Analysis
    print("[5/6] AI Backtest Analysis...")
    try:
        metrics = results["stages"].get("backtest", {}).get("metrics", {})
        from src.lxl_quantaxis.ai.backtest_analyzer import analyze_and_log
        assessment = analyze_and_log(metrics, strategy_name=idea[:50], use_llm=use_llm)
        results["stages"]["analysis"] = assessment.to_dict()
        print(f"  -> Summary: {assessment.summary[:80]}")
    except Exception as e:
        results["stages"]["analysis"] = {"error": str(e)}
        print(f"  -> FAILED: {e}")

    # Stage 6: Report Generation
    print("[6/6] Research Report...")
    try:
        from src.lxl_quantaxis.research.report_generator import generate_report
        from src.lxl_quantaxis.research.thesis import InvestmentThesis
        thesis = InvestmentThesis(
            symbol=symbol, title=idea[:60],
            core_argument=results["stages"].get("thesis", {}).get("thesis", ""),
        )
        report = generate_report(
            symbol=symbol, thesis=thesis,
            factor_model=model,
            strategy_spec=spec,
            backtest_metrics=metrics,
            backtest_assessment=assessment,
        )
        os.makedirs(output_dir, exist_ok=True)
        paths = report.save(output_dir)
        results["stages"]["report"] = {"paths": paths}
        print(f"  -> Report saved: {paths['markdown']}")
    except Exception as e:
        results["stages"]["report"] = {"error": str(e)}
        print(f"  -> FAILED: {e}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  Pipeline Complete")
    print(f"  Report: {output_dir}/")
    print(f"{'='*60}\n")

    return results


if __name__ == "__main__":
    idea = sys.argv[1] if len(sys.argv) > 1 else "看好AI服务器产业链。云厂商资本开支提升利好算力。风险：估值过高。"
    symbol = sys.argv[2] if len(sys.argv) > 2 else "000001"
    results = run_demo(idea, symbol=symbol, use_llm=False)
    json_path = f"reports/demo_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs("reports", exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"Results saved: {json_path}")
