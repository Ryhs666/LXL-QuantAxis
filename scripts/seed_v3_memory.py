#!/usr/bin/env python3
"""Seed V3 Investment Memory System with realistic research cases.

Three complete cases across all four memory types:
  1. NVIDIA AI Infrastructure  — thesis CORRECT, +41%
  2. ZTE AI Server             — thesis CORRECT, +28%
  3. Micron Semiconductor Cycle — thesis WRONG, -12%

Usage:
    python scripts/seed_v3_memory.py          # Seed into default DB
    python scripts/seed_v3_memory.py --reset  # Clear and re-seed
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.v3.memory import MemoryAnalytics, MemoryConfig, MemoryDatabase, MemoryEntry, MemoryRepository


def _days_ago(n: int) -> str:
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ═══════════════════════════════════════════════════════════════
# Case 1: NVIDIA AI Infrastructure
# ═══════════════════════════════════════════════════════════════

CASE_NVIDIA = [
    MemoryEntry(
        type="note",
        ticker=["NVDA"],
        title="AI GPU Market Analysis — NVIDIA Dominance",
        content="""## AI GPU Market Landscape

NVIDIA holds 85%+ share in data center GPUs. AMD MI300 is just ramping.

### Key Data Points
- H100 sold out, 6-8 month lead times
- Cloud CAPEX shifting massively toward AI infra
- CUDA ecosystem moat is extremely deep — switching costs are prohibitive

### Supply Chain Verification
- TSMC CoWoS packaging capacity is the bottleneck
- NVIDIA has pre-booked majority of 2025 advanced packaging capacity
- InfiniBand networking equally supply-constrained

### Risks
- Premium valuation: PE 70x+
- China export controls
- Hyperscaler custom silicon (Google TPU, AWS Trainium)""",
        tags=["AI", "semiconductor", "infrastructure", "美股"],
    ),
    MemoryEntry(
        type="thesis",
        ticker=["NVDA"],
        title="NVIDIA: Core Beneficiary of AI Infrastructure Buildout",
        content="""## Core Thesis

NVIDIA is the single largest beneficiary of AI infrastructure construction.
As GenAI moves from lab to enterprise deployment, GPU demand expands from
training to inference — the TAM is much larger than consensus.

## Three Catalysts

1. **Inference Market Explosion**: Inference demand is 10x+ training volume.
   Mid-range GPUs (L40S) benefit equally.
2. **Enterprise AI Spending Acceleration**: Fortune 500 AI budgets growing 3x in 2025.
3. **Sovereign AI**: Governments building domestic AI infrastructure creates
   incremental demand beyond commercial sector.

## Risks

- Valuation: PE 70x — any earnings miss causes sharp correction
- Competition: AMD MI300 price/performance advantage, Google TPU v5 at scale
- Geopolitical: China export controls may tighten further

## Price Target

- Target: $1200 (current $950)
- Timeline: 12 months
- Stop-loss: $750 (-20%)""",
        thesis={
            "catalysts": ["Inference market explosion", "Enterprise AI spending acceleration", "Sovereign AI buildout"],
            "risks": ["Premium valuation correction", "AMD competition", "Export controls"],
            "timeline": "12 months",
            "target_price": 1200.0,
        },
        confidence=0.80,
        status="correct",
        tags=["AI", "semiconductor", "美股", "growth"],
    ),
    MemoryEntry(
        type="decision",
        ticker=["NVDA"],
        title="Buy NVIDIA @ $955",
        content="""## Trade Decision

### Entry
- Ticker: NVDA
- Direction: Long
- Price: $955
- Shares: 50
- Position: 10% of portfolio

### Rationale
Q2 earnings beat — data center revenue +154% YoY.
Guidance raised. PEG < 1 despite high PE.

### Market Context
- NASDAQ uptrend
- AI sector sentiment elevated
- VIX at 15, low vol environment""",
        decision={
            "type": "buy",
            "price": 955.0,
            "quantity": 50,
            "reason": "Q2 earnings beat, DC revenue +154% YoY, PEG<1",
            "market_context": "NASDAQ uptrend, AI sentiment elevated, VIX=15",
            "mood": "confident",
        },
        confidence=0.80,
        status="good",
        tags=["美股", "AI", "buy"],
    ),
    MemoryEntry(
        type="reflection",
        ticker=["NVDA"],
        title="NVIDIA Retrospective: AI Infrastructure Investing Pattern",
        content="""## Retrospective

### Outcome
Thesis: CORRECT
- Entry $955 → Current $1350, +41% return
- Inference market did explode, Sovereign AI orders exceeded expectations

### What Went Well
1. Supply chain verification: checked TSMC CoWoS capacity before investing
2. Entry timing: waited for earnings confirmation before entering
3. Position sizing: 10% allocation — participates without overexposure

### What Could Improve
1. Could have entered earlier — H100 shortage signal was visible sooner
2. Target price was conservative — $1200 reached in 4 months

### Pattern Recognition
AI infrastructure investment success pattern:
  Industry trend confirmation (AI demand)
  → Supply chain verification (TSMC capacity / cloud CAPEX)
  → Select monopoly leader (NVIDIA 85% share)
  → Enter after earnings confirmation""",
        tags=["lesson", "AI", "美股", "复盘", "success_pattern"],
    ),
]

# ═══════════════════════════════════════════════════════════════
# Case 2: ZTE AI Server
# ═══════════════════════════════════════════════════════════════

CASE_ZTE = [
    MemoryEntry(
        type="note",
        ticker=["000063"],
        title="China AI Server Market Research — Domestic Substitution",
        content="""## China AI Server Market

### Competitive Landscape
- Inspur: Traditional server leader, #1 in AI server market share
- ZTE: Telecom equipment transforming into AI servers, government/enterprise advantage
- Sugon: HPC traditional strength, tied to Hygon chips

### Policy Drivers
- 2025 domestic AI chip procurement ratio requirements increasing
- Carrier AI compute procurement scale surpassing expectations
- East-West Computing project entering implementation phase

### ZTE Advantages
- Deep carrier relationships (5G base station core supplier)
- Self-developed AI accelerator (ASIC-based)
- Government/enterprise channel coverage""",
        tags=["AI", "server", "A股", "国产替代"],
    ),
    MemoryEntry(
        type="thesis",
        ticker=["000063"],
        title="ZTE: AI Server as Second Growth Curve",
        content="""## Core Thesis

Beyond telecom equipment, AI servers are becoming ZTE's second growth curve.
Carrier AI compute procurement + government digital transformation
open new growth opportunities.

## Three Catalysts

1. **Carrier AI Procurement**: China Mobile/Telecom/Unicom 2025 AI server
   procurement volume up 200%+ YoY
2. **Domestic Substitution**: Government mandates increasing domestic
   chip ratios in AI compute, benefiting local supply chain
3. **Valuation Repair**: Current PE 15x vs telecom equipment industry 20x.
   AI business value not yet priced in.

## Risks

- Huawei Ascend ecosystem competition
- AI server margins lower than telecom equipment
- US-China tech tensions uncertainty

## Price Target

- Target: CNY 36 (current CNY 28)
- Timeline: 6-9 months
- Stop-loss: CNY 24 (-14%)""",
        thesis={
            "catalysts": ["Carrier AI procurement surge", "Domestic substitution policy", "Valuation repair"],
            "risks": ["Huawei competition", "Margin pressure", "US-China tensions"],
            "timeline": "6-9 months",
            "target_price": 36.0,
        },
        confidence=0.70,
        status="correct",
        tags=["A股", "AI", "server", "国产替代", "growth"],
    ),
    MemoryEntry(
        type="decision",
        ticker=["000063"],
        title="Buy ZTE @ CNY 28.30",
        content="""## Trade Decision

### Entry
- Ticker: 000063 ZTE
- Direction: Long
- Price: CNY 28.30
- Shares: 5,000
- Position: 8% of portfolio

### Rationale
Carrier H1 AI server procurement exceeded expectations.
ZTE won higher share than anticipated. 10% pullback provided entry window.

### Market Context
- A-share range-bound uptrend
- TMT sector active
- Northbound capital inflow""",
        decision={
            "type": "buy",
            "price": 28.30,
            "quantity": 5000,
            "reason": "Carrier H1 AI procurement beat, ZTE share gain, 10% pullback entry",
            "market_context": "A-share uptrend, TMT active, northbound inflow",
            "mood": "confident",
        },
        confidence=0.70,
        status="good",
        tags=["A股", "AI", "buy"],
    ),
    MemoryEntry(
        type="reflection",
        ticker=["000063"],
        title="ZTE Retrospective: Domestic Substitution Thesis Validated",
        content="""## Retrospective

### Outcome
Thesis: CORRECT
- Entry CNY 28.30 → Current CNY 36.20, +28% return
- Carrier procurement did surge, domestic substitution accelerated

### What Went Well
1. Policy direction judgment accurate: substitution went from slogan to procurement
2. Industry research depth: identified carrier procurement scale early
3. Used pullback to enter: waited for 10% correction

### What Could Improve
1. Position could be larger: 8% too conservative for high-conviction opportunity
2. Huawei competition analysis needs more granularity

### Pattern Recognition
A-share AI investment success pattern:
  Policy direction confirmation → Supply chain verification →
  Select channel-advantaged player → Enter on pullback""",
        tags=["lesson", "A股", "AI", "国产替代", "复盘"],
    ),
]

# ═══════════════════════════════════════════════════════════════
# Case 3: Micron — Semiconductor Cycle
# ═══════════════════════════════════════════════════════════════

CASE_SEMICONDUCTOR = [
    MemoryEntry(
        type="note",
        ticker=["MU", "NVDA", "AMD"],
        title="Semiconductor Cycle Research — Has Memory Bottomed?",
        content="""## Semiconductor Cycle Analysis

### Cycle Theory
Semiconductor industry has 3-4 year cycles driven by supply-demand mismatch:
1. Demand rises → Capacity shortage → Prices up → Expansion
2. Overcapacity → Prices down → Production cuts → Demand recovery

### Current Assessment
- Memory prices declining for 18 months (longest down-cycle in history)
- DRAM spot prices showing stabilization signs
- Samsung/SK Hynix/Micron have announced production cuts
- But demand side still weak: PC/smartphone shipments not recovering

### Leading Indicators
- SOX index rebounded 30%+ from bottom
- TSMC monthly revenue showing sequential improvement
- But memory maker inventories remain elevated""",
        tags=["semiconductor", "cycle", "存储", "美股"],
    ),
    MemoryEntry(
        type="thesis",
        ticker=["MU"],
        title="Micron Technology: Memory Cycle Bottom Opportunity",
        content="""## Core Thesis

Memory industry after 18-month down-cycle — supply-demand dynamics improving.
Three major producers cutting production + AI-driven HBM demand explosion
= cycle inflection approaching.

## Three Catalysts

1. **Production Cut Impact**: 20-30% cuts across 3 major producers,
   inventory digestion within 2 quarters
2. **HBM Demand Explosion**: AI GPU HBM demand up 5x YoY,
   Micron is key HBM3E supplier
3. **Valuation at Historic Low**: PB 1.2x, lowest in 10 years

## Risks

- Demand recovery below expectations: PC/smartphone may stay weak
- HBM ramp may fall short of targets
- Geopolitical risk (China memory self-sufficiency policy)

## Price Target

- Target: $110 (current $85)
- Timeline: 6-9 months
- Stop-loss: $72 (-15%)""",
        thesis={
            "catalysts": ["Production cut impact", "HBM demand explosion", "Valuation at historic low"],
            "risks": ["Demand recovery weaker", "HBM ramp delay", "Geopolitical risk"],
            "timeline": "6-9 months",
            "target_price": 110.0,
        },
        confidence=0.65,
        status="wrong",
        tags=["semiconductor", "cycle", "存储", "美股", "value"],
    ),
    MemoryEntry(
        type="decision",
        ticker=["MU"],
        title="Buy Micron @ $86",
        content="""## Trade Decision

### Entry
- Ticker: MU
- Direction: Long
- Price: $86
- Shares: 200
- Position: 6% of portfolio

### Rationale
Memory price stabilization signals appearing. Samsung further cutting production.
HBM order visibility improving. Valuation at 10-year low — limited downside.

### Market Context
- SOX index in recovery channel
- Market optimistic on rate cuts
- Tech sector risk appetite improving""",
        decision={
            "type": "buy",
            "price": 86.0,
            "quantity": 200,
            "reason": "Memory price stabilization, Samsung cuts, HBM order visibility, 10yr low PB",
            "market_context": "SOX recovery channel, rate cut optimism, risk appetite up",
            "mood": "confident",
        },
        confidence=0.65,
        status="bad",
        tags=["美股", "semiconductor", "cycle", "buy"],
    ),
    MemoryEntry(
        type="reflection",
        ticker=["MU"],
        title="Micron Retrospective: The Perils of Cycle Timing",
        content="""## Retrospective

### Outcome
Thesis: WRONG
- Entry $86 → Stopped at $72, -16% loss
- Called the cycle bottom too early. Actual recovery delayed 2 quarters.

### What Went Wrong
1. **Premature Inflection Call**: Price stabilization != cycle bottom.
   Bottom is confirmed after the fact, not predicted beforehand.
   Should have waited for 2+ quarters of sustained price recovery + inventory drawdown.
2. **Ignored Demand-Side Signals**: PC/smartphone shipments didn't recover.
   Supply-side cuts alone insufficient to drive cycle turn.
   AI HBM demand growing but traditional DRAM/NAND still weak.
3. **Position/Stop Execution**: 6% position + strict stop-loss — this part was good.

### Improvement Checklist
Cycle judgment checklist:
   - [ ] Prices rising for 2+ consecutive quarters
   - [ ] Inventories down 20%+ at producers
   - [ ] End-demand inflection signals present
   - [ ] At least 2 independent leading indicators confirmed

For cyclical stocks:
   - Don't do left-side entry (this mistake)
   - Wait for confirmation signals then enter
   - Accept "missing first 20%" as confirmation cost

### Pattern Recognition
Cycle investment failure pattern:
  Single signal confirmation → Premature inflection call →
  Left-side entry → Stop-loss exit

Correct pattern:
  Multiple independent cross-verification → Right-side confirmation →
  Phased entry""",
        tags=["lesson", "semiconductor", "cycle", "美股", "mistake"],
    ),
]

# ═══════════════════════════════════════════════════════════════
# General Research Notes & Principles
# ═══════════════════════════════════════════════════════════════

CASE_GENERAL = [
    MemoryEntry(
        type="note",
        ticker=["NVDA", "000858", "688981"],
        title="2025H2 Investment Themes Overview",
        content="""## 2025 H2 Core Investment Themes

### 1. AI Infrastructure Buildout
- Compute: GPU/ASIC/Optical modules
- Networking: InfiniBand/800G optics
- Power: Data center electricity supply

### 2. Consumer Recovery
- Baijiu: Premium spirits structural growth
- Home Appliances: Trade-in policy boost
- Tourism: Outbound travel recovery

### 3. Domestic Substitution
- Semi Equipment: Sanctions driving localization
- AI Chips: Ascend/Cambricon ecosystem
- Industrial Software: Smart manufacturing demand

### 4. High Dividend Defense
- Banks: Low valuation + high dividend yield
- Utilities: Stable cash flows
- Coal: Supply constraints""",
        tags=["macro", "投资主题", "2025", "A股", "美股"],
    ),
    MemoryEntry(
        type="reflection",
        ticker=[],
        title="Investment Principles — 2025 Q3 Update",
        content="""## Current Investment Principles

### Based on 2025 H1 Retrospectives

1. **Only High-Conviction Deserves Heavy Weight**
   High-confidence (>0.7) thesis accuracy: 100% (2/2)
   Medium-low confidence thesis accuracy: 0% (0/1)
   → Rule: Conviction < 0.7 → track only, no actual trading

2. **Right-Side Entry, Not Left-Side**
   Cycle timing lesson: wait for confirmation, not prediction
   NVIDIA success case: entered after earnings confirmation

3. **Supply Chain Verification > Macro Judgment**
   NVIDIA case: TSMC CoWoS capacity research → accurate thesis
   Micron case: only looked at memory prices → wrong thesis
   → Rule: Every thesis must include supply chain verification data

4. **Position Size Matches Conviction**
   High conviction (>0.7): 10-15% position
   Medium conviction (0.5-0.7): 5-8% position
   Low conviction (<0.5): track only, no trade

5. **Quarterly Review of All Theses**
   Regardless of status, systematically review every thesis quarterly""",
        tags=["lesson", "投资原则", "复盘", "规则更新"],
    ),
]

ALL_CASES = CASE_NVIDIA + CASE_ZTE + CASE_SEMICONDUCTOR + CASE_GENERAL


def backdate_created_at(repo: MemoryRepository, entry_ids: list[int], days_ago_values: list[int]) -> None:
    """Set historical created_at dates for demo entries."""
    with repo._db.connection() as conn:
        for eid, days in zip(entry_ids, days_ago_values, strict=True):
            ts = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("UPDATE memory_entries SET created_at = ? WHERE id = ?", (ts, eid))


def seed(clear_first: bool = False) -> None:
    config = MemoryConfig.with_defaults()
    db = MemoryDatabase(config)
    db.initialize()
    repo = MemoryRepository(config)

    if clear_first:
        with db.connection() as conn:
            conn.execute("DELETE FROM memory_entries")
        print("Cleared existing data.\n")

    existing = repo.count()
    if existing > 0 and not clear_first:
        print(f"Database already has {existing} entries. Use --reset to clear first.")
        return

    # Each entry's "days ago" for backdating
    days_ago = [90, 85, 80, 20,  75, 70, 65, 15,  60, 55, 50, 10,  30, 5]
    ids = repo.save_many(ALL_CASES)
    backdate_created_at(repo, ids, days_ago)
    print(f"Seeded {len(ids)} entries across {len(ALL_CASES)} records.\n")

    analytics = MemoryAnalytics(db)
    stats = analytics.get_stats()

    print("═══ V3 Memory System Seeded ═══")
    print(f"  Total:       {stats.total_entries} entries")
    print(f"  Notes:       {stats.notes}")
    print(f"  Theses:      {stats.theses}")
    print(f"  Decisions:   {stats.decisions}")
    print(f"  Reflections: {stats.reflections}")
    print(f"  Thesis hit rate: {stats.thesis_hit_rate:.0%} ({stats.thesis_correct}/{stats.thesis_correct + stats.thesis_wrong})")
    print(f"  Decision win rate: {stats.decision_win_rate:.0%}")
    print(f"  Avg confidence: {stats.avg_confidence:.1%}")
    print(f"  Streak: {stats.streak_days} days")
    print()
    print("Cases:")
    print("  1. NVIDIA AI Infrastructure   (NVDA)   — thesis CORRECT, +41%")
    print("  2. ZTE AI Server              (000063) — thesis CORRECT, +28%")
    print("  3. Micron Semiconductor Cycle (MU)     — thesis WRONG, -12%")
    print()
    print("Run: python web_modern.py → /journal")


def main():
    parser = argparse.ArgumentParser(description="Seed V3 Memory System with demo data")
    parser.add_argument("--reset", action="store_true", help="Clear existing data before seeding")
    args = parser.parse_args()
    seed(clear_first=args.reset)


if __name__ == "__main__":
    main()
