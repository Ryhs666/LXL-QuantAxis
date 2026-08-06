#!/usr/bin/env python3

"""LXL·QuantAxis V3 Memory Showcase — Interactive Demo.

Demonstrates the complete Investment Memory System workflow:
  1. Initialize demo data (4 cases, 16 entries)
  2. Walk through each case's memory lifecycle
  3. Generate and display the Investor Profile
  4. Show key analytics insights

Usage:
    python scripts/demo_v3_memory.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.v3.memory import MemoryAnalytics, MemoryConfig, MemoryDatabase, MemoryEntry, MemoryRepository

# ═══════════════════════════════════════════════════════════════
# Terminal styling
# ═══════════════════════════════════════════════════════════════

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
RESET = "\033[0m"


def header(text: str) -> None:
    print(f"\n{BOLD}{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 60}{RESET}\n")


def step(n: int, text: str) -> None:
    print(f"{BOLD}{BLUE}[{n}]{RESET} {text}")


def info(label: str, value: str = "") -> None:
    print(f"  {DIM}{label}:{RESET} {value}")


def success(text: str) -> None:
    print(f"  {GREEN}✓{RESET} {text}")


def failure(text: str) -> None:
    print(f"  {RED}✗{RESET} {text}")


def pause() -> None:
    input(f"\n{DIM}Press Enter to continue...{RESET}")


# ═══════════════════════════════════════════════════════════════
# Demo data (mirrors seed_v3_memory.py with key entries only)
# ═══════════════════════════════════════════════════════════════

def init_demo_data(repo: MemoryRepository) -> None:
    """Seed minimal demo entries for the interactive walkthrough."""
    entries = [
        # Case 1: NVIDIA — correct
        MemoryEntry(type="note", ticker=["NVDA"],
                    title="AI GPU Market Analysis — NVIDIA Dominance",
                    content="NVIDIA 85% share, H100 sold out, TSMC CoWoS bottleneck.",
                    tags=["AI", "semiconductor", "美股"]),
        MemoryEntry(type="thesis", ticker=["NVDA"],
                    title="NVIDIA: Core Beneficiary of AI Infrastructure Buildout",
                    content="Inference explosion + enterprise AI + sovereign AI. Target $1200.",
                    thesis={"catalysts": ["Inference", "Enterprise AI", "Sovereign AI"],
                            "risks": ["Valuation", "Competition", "Export controls"],
                            "timeline": "12 months", "target_price": 1200.0},
                    confidence=0.80, status="correct",
                    outcome={"detail": "Correct. +41%. Inference market exploded.", "return_pct": 41.0},
                    tags=["AI", "semiconductor", "美股", "growth"]),
        MemoryEntry(type="decision", ticker=["NVDA"],
                    title="Buy NVIDIA @ $955",
                    content="50 shares, 10% position. Q2 earnings beat, DC +154% YoY.",
                    decision={"type": "buy", "price": 955.0, "quantity": 50, "mood": "confident"},
                    confidence=0.80, status="good",
                    tags=["美股", "AI", "buy"]),
        MemoryEntry(type="reflection", ticker=["NVDA"],
                    title="NVIDIA Retrospective: AI Infrastructure Success Pattern",
                    content="Supply chain verification + earnings confirmation = high-probability setup.",
                    tags=["lesson", "AI", "success_pattern"]),

        # Case 2: ZTE — correct
        MemoryEntry(type="note", ticker=["000063"],
                    title="China AI Server Market — Domestic Substitution",
                    content="Carrier AI procurement +200%, ZTE gaining share.",
                    tags=["AI", "A股", "国产替代"]),
        MemoryEntry(type="thesis", ticker=["000063"],
                    title="ZTE: AI Server as Second Growth Curve",
                    content="Carrier procurement + substitution + valuation repair. Target CNY 36.",
                    thesis={"catalysts": ["Carrier procurement", "Substitution", "Valuation"],
                            "risks": ["Huawei competition", "Margin pressure"],
                            "timeline": "6-9 months", "target_price": 36.0},
                    confidence=0.70, status="correct",
                    outcome={"detail": "Correct. +28%. Procurement surged.", "return_pct": 28.0},
                    tags=["A股", "AI", "国产替代", "growth"]),
        MemoryEntry(type="decision", ticker=["000063"],
                    title="Buy ZTE @ CNY 28.30",
                    content="5000 shares, 8% position. H1 procurement beat, 10% pullback entry.",
                    decision={"type": "buy", "price": 28.30, "quantity": 5000, "mood": "confident"},
                    confidence=0.70, status="good",
                    tags=["A股", "AI", "buy"]),
        MemoryEntry(type="reflection", ticker=["000063"],
                    title="ZTE Retrospective: Policy Research Edge",
                    content="Policy direction + industry channels = A-share advantage.",
                    tags=["lesson", "A股", "success_pattern"]),

        # Case 3: Micron — wrong
        MemoryEntry(type="note", ticker=["MU"],
                    title="Semiconductor Cycle Research — Has Memory Bottomed?",
                    content="18-month down-cycle. DRAM stabilizing. But inventories elevated.",
                    tags=["semiconductor", "cycle", "美股"]),
        MemoryEntry(type="thesis", ticker=["MU"],
                    title="Micron: Memory Cycle Bottom Opportunity",
                    content="Production cuts + HBM demand. Target $110. But demand side weak.",
                    thesis={"catalysts": ["Production cuts", "HBM demand"],
                            "risks": ["Demand weak", "HBM ramp slow"],
                            "timeline": "6-9 months", "target_price": 110.0},
                    confidence=0.65, status="wrong",
                    outcome={"detail": "Wrong. -12%. Called bottom too early.", "return_pct": -12.0},
                    tags=["semiconductor", "cycle", "美股", "value"]),
        MemoryEntry(type="decision", ticker=["MU"],
                    title="Buy Micron @ $86",
                    content="200 shares, 6% position. Price stabilization signal. Stopped at $72.",
                    decision={"type": "buy", "price": 86.0, "quantity": 200, "mood": "confident"},
                    confidence=0.65, status="bad",
                    tags=["美股", "semiconductor", "cycle"]),
        MemoryEntry(type="reflection", ticker=["MU"],
                    title="Micron Retrospective: The Perils of Cycle Timing",
                    content="Lesson: Don't do left-side entry. Wait for 2+ quarters confirmation.",
                    tags=["lesson", "cycle", "mistake"]),

        # Case 4: SMIC — pending
        MemoryEntry(type="thesis", ticker=["688981"],
                    title="SMIC: China Semiconductor Manufacturing Core Asset",
                    content="Domestic substitution + Huawei return. Target CNY 65.",
                    thesis={"catalysts": ["Utilization recovery", "Huawei", "National fund"],
                            "risks": ["Sanctions", "Yield issues"],
                            "timeline": "6-12 months", "target_price": 65.0},
                    confidence=0.55, status="pending",
                    tags=["A股", "semiconductor", "国产替代"]),

        # Principles
        MemoryEntry(type="reflection", ticker=[],
                    title="Investment Principles — 2025 Q3 Update",
                    content="1. Only trade conviction > 0.70. 2. Right-side entry. 3. Supply chain verification. 4. Position = conviction. 5. Quarterly review.",
                    tags=["lesson", "投资原则", "规则更新"]),
    ]
    repo.save_many(entries)


# ═══════════════════════════════════════════════════════════════
# Demo script
# ═══════════════════════════════════════════════════════════════

def run_demo() -> None:
    config = MemoryConfig.with_defaults()
    db = MemoryDatabase(config)
    db.initialize()
    repo = MemoryRepository(config)

    # Clear and seed
    with db.connection() as conn:
        conn.execute("DELETE FROM memory_entries")
    init_demo_data(repo)

    # ═══════════════════════════════════════════════════════
    # Part 1: Introduction
    # ═══════════════════════════════════════════════════════
    header("LXL·QuantAxis V3 — Investment Memory System")
    print(f"  {BOLD}AI-Powered Personal Investment Research Operating System{RESET}")
    print(f"  {DIM}Memory Showcase Edition{RESET}")
    print()
    print(f"  {DIM}LXL·QuantAxis is not a prediction engine.{RESET}")
    print(f"  {DIM}It does not tell you what to buy.{RESET}")
    print(f"  {DIM}It is a {BOLD}learning system{RESET}{DIM} that helps you understand{RESET}")
    print(f"  {DIM}your own investment mind.{RESET}")
    pause()

    # ═══════════════════════════════════════════════════════
    # Part 2: The Problem
    # ═══════════════════════════════════════════════════════
    header("The Research Amnesia Problem")
    print("  Every investor has experienced this:")
    print()
    print(f"  {YELLOW}Week 1:{RESET}  Deep research. Write notes. Form thesis.")
    print(f"  {YELLOW}Week 4:{RESET}  Execute trade. Record somewhere.")
    print(f"  {YELLOW}Month 3:{RESET} Earnings. Stock moves.")
    print(f"  {YELLOW}Month 6:{RESET} {RED}Can't remember why you bought it.{RESET}")
    print(f"         {RED}Don't know if your prediction was right.{RESET}")
    print(f"         {RED}Repeat the same mistakes.{RESET}")
    print()
    print(f"  {BOLD}Without memory, every decision is a first decision.{RESET}")
    pause()

    # ═══════════════════════════════════════════════════════
    # Part 3: The 4-Type Memory Model
    # ═══════════════════════════════════════════════════════
    header("Solution: 4-Type Investment Memory")
    print(f"  📝 {BOLD}Note{RESET}        — Research findings, market analysis")
    print(f"  💡 {BOLD}Thesis{RESET}      — Structured prediction + confidence score")
    print(f"  📊 {BOLD}Decision{RESET}    — Trade record + rationale + mood")
    print(f"  🧠 {BOLD}Reflection{RESET}   — Post-mortem + pattern recognition")
    print()
    print(f"  {DIM}All four types in one unified timeline.{RESET}")
    print(f"  {DIM}FTS5 full-text search across Chinese and English.{RESET}")
    print(f"  {DIM}Automatic confidence calibration.{RESET}")
    pause()

    # ═══════════════════════════════════════════════════════
    # Part 4: Case Walkthrough
    # ═══════════════════════════════════════════════════════
    header("Case 1: NVIDIA AI Infrastructure")

    nvda = repo.list_all(entry_type="thesis")[2]  # NVIDIA thesis
    step(1, "Research Note → \"AI GPU Market Analysis\"")
    info("Ticker", "NVDA")
    info("Finding", "85% market share, H100 sold out, CUDA moat")
    print()

    step(2, f"Thesis → \"{nvda.title}\"")
    info("Conviction", f"{nvda.confidence:.0%}")
    info("Catalysts", "Inference explosion, Enterprise AI, Sovereign AI")
    info("Target", f"${nvda.thesis['target_price']:.0f}")
    print()

    step(3, "Decision → Buy NVDA @ $955")
    info("Position", "10% of portfolio")
    info("Rationale", "Q2 earnings beat, DC revenue +154% YoY")
    info("Mood", "Confident")
    print()

    nvda_refl = next(e for e in repo.list_all(entry_type="reflection") if "NVDA" in e.ticker)
    step(4, f"Reflection → \"{nvda_refl.title}\"")
    success("Outcome: CORRECT | Return: +41%")
    info("Pattern", "Supply chain verification + earnings confirmation")
    pause()

    header("Case 2: ZTE AI Server")
    zte = next(e for e in repo.list_all(entry_type="thesis") if "000063" in e.ticker)
    step(5, "Research Note → China AI Server Market")
    step(6, f"Thesis → \"{zte.title}\"")
    info("Conviction", f"{zte.confidence:.0%}")
    info("Target", f"CNY {zte.thesis['target_price']:.0f}")
    step(7, "Decision → Buy ZTE @ CNY 28.30")
    step(8, "Reflection → Policy Research Edge")
    success("Outcome: CORRECT | Return: +28%")
    pause()

    header("Case 3: Micron Semiconductor Cycle")
    mu = next(e for e in repo.list_all(entry_type="thesis") if "MU" in e.ticker)
    step(9, "Research Note → Semiconductor Cycle Research")
    step(10, f"Thesis → \"{mu.title}\"")
    info("Conviction", f"{mu.confidence:.0%}")
    info("Target", f"${mu.thesis['target_price']:.0f}")
    step(11, "Decision → Buy Micron @ $86")
    step(12, "Reflection → The Perils of Cycle Timing")
    failure("Outcome: WRONG | Return: -12%")
    info("Lesson", "Don't do left-side entry on cycles")
    print()
    print(f"  {BOLD}This \"failed\" thesis generated the most value:{RESET}")
    print("  A concrete cycle-timing checklist that prevents")
    print("  repeating the same mistake.")
    pause()

    header("Case 4: SMIC — Pending Review")
    smic = next(e for e in repo.list_all(entry_type="thesis") if "688981" in e.ticker)
    step(13, f"Thesis → \"{smic.title}\"")
    info("Conviction", f"{smic.confidence:.0%}")
    info("Status", f"{YELLOW}PENDING{RESET} — awaiting outcome review")
    print()
    print(f"  {DIM}Conviction 0.55 is below the 0.70 trading threshold.{RESET}")
    print(f"  {DIM}This thesis is tracked but no trade was executed.{RESET}")
    pause()

    # ═══════════════════════════════════════════════════════
    # Part 5: Investor Profile
    # ═══════════════════════════════════════════════════════
    header("Investor Profile — Auto-Generated by MemoryAnalytics")

    analytics = MemoryAnalytics(db)
    stats = analytics.get_stats()
    cal = analytics.get_calibration()
    tag_perf = analytics.get_tag_performance()

    print(f"  {BOLD}Overall Statistics{RESET}")
    print(f"  {'─' * 40}")
    info("Total Memories", str(stats.total_entries))
    info("Notes", str(stats.notes))
    info("Theses", str(stats.theses))
    info("Decisions", str(stats.decisions))
    info("Reflections", str(stats.reflections))
    print()

    resolved = stats.thesis_correct + stats.thesis_wrong
    print(f"  {BOLD}Thesis Performance{RESET}")
    print(f"  {'─' * 40}")
    info("Hit Rate", f"{stats.thesis_hit_rate:.0%} ({stats.thesis_correct}/{resolved} resolved)")
    info("Pending Reviews", str(stats.thesis_pending))
    info("Avg Confidence", f"{stats.avg_confidence:.1%}")
    print()

    print(f"  {BOLD}Confidence Calibration{RESET}")
    print(f"  {'─' * 40}")
    for b in cal.buckets:
        bar = "█" * int(b.hit_rate * 20) if b.total > 0 else "─"
        marker = f"{GREEN}← well calibrated{RESET}" if b.hit_rate > 0.8 and b.min_conf > 0.7 else ""
        print(f"  {b.label:20s}  {b.total} theses  {bar} {b.hit_rate:.0%}  {marker}")
    print()
    print(f"  {CYAN}Insight: {cal.insight}{RESET}")
    print()
    pause()

    print(f"  {BOLD}Sector Edge Analysis{RESET}")
    print(f"  {'─' * 40}")
    for tp in tag_perf[:8]:
        icon = "🟢" if tp.hit_rate >= 0.7 else "🟡" if tp.hit_rate >= 0.4 else "🔴" if tp.total > 0 else "⚪"
        print(f"  {icon} {tp.tag:20s}  {tp.correct}/{tp.total}  {tp.hit_rate:.0%}")
    print()
    print(f"  {BOLD}Core Edge:{RESET} AI, A-share, Growth")
    print(f"  {BOLD}Weakness:{RESET}  Cycle timing, Value plays")
    pause()

    # ═══════════════════════════════════════════════════════
    # Part 6: Key Takeaways
    # ═══════════════════════════════════════════════════════
    header("Key Takeaways")

    principles = next(e for e in repo.list_all(entry_type="reflection") if "Investment Principles" in e.title)
    print(f"  {BOLD}Investment Principles Derived from Memory Analytics:{RESET}\n")
    for line in principles.content.strip().split("\n"):
        line = line.strip()
        if line.startswith("1.") or line.startswith("2.") or line.startswith("3.") or line.startswith("4.") or line.startswith("5."):
            print(f"  {BOLD}{line}{RESET}")
        elif line.startswith("   "):
            print(f"  {DIM}{line}{RESET}")
    print()
    print(f"  {DIM}These rules were not written upfront.{RESET}")
    print(f"  {DIM}They {BOLD}emerged{RESET}{DIM} from systematically tracking{RESET}")
    print(f"  {DIM}14 theses, decisions, and reflections.{RESET}")
    print()
    print(f"  {BOLD}{GREEN}This is the system working as designed.{RESET}")
    pause()

    # ═══════════════════════════════════════════════════════
    # Part 7: Next Steps
    # ═══════════════════════════════════════════════════════
    header("Explore the Full System")

    print(f"  {BOLD}Web Interface:{RESET}")
    print("    python web_modern.py")
    print("    → http://127.0.0.1:5000/journal")
    print()
    print(f"  {BOLD}Documentation:{RESET}")
    print("    docs/V3_MEMORY_SHOWCASE.md   — Full case study")
    print("    docs/V3_PRODUCT_ARCHITECTURE.md — Architecture")
    print("    docs/releases/V3_MEMORY_RELEASE.md — This release")
    print()
    print(f"  {BOLD}Coming in Phase 2:{RESET}")
    print("    Company Intelligence Engine")
    print("    — Fundamental data + industry comparison")
    print()
    print(f"  {BOLD}{CYAN}LXL·QuantAxis V3.0 — Memory Showcase Edition{RESET}")
    print(f"  {DIM}Not a prediction tool. A learning system.{RESET}")
    print()


if __name__ == "__main__":
    run_demo()
