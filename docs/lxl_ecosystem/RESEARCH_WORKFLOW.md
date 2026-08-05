# LXL Research Workflow — Buy-Side Process

A complete investment research workflow modeled after buy-side research processes.

## Workflow Overview

```
Phase 1: Idea Generation
        │
Phase 2: Fundamental Research
        │
Phase 3: Investment Thesis
        │
Phase 4: AI Structuring
        │
Phase 5: Factor Modeling
        │
Phase 6: Strategy Validation
        │
Phase 7: Research Report
        │
Phase 8: Review & Archive
```

## Phase 1: Idea Generation

**Source**: Market observation, sector screening, theme identification, news flow.

**Output**: Raw investment hypothesis (1-2 sentences).

**Example**: "AI infrastructure spending cycle may have multi-year duration unlike previous hardware cycles."

## Phase 2: Fundamental Research

**Owner**: LXL Equity Research Lab

**Activities**:
- Company business model analysis
- Industry value chain mapping
- Competitive positioning assessment
- Management track record evaluation
- Financial statement analysis (revenue drivers, margin structure, cash flow quality)
- Valuation framework (DCF, comparable, sum-of-parts)

**Output**: Detailed research notes, financial model, valuation range.

## Phase 3: Investment Thesis

**Owner**: Analyst

**Format**: Structured argument with bull case, bear case, risk factors, conviction level.

**Example**:
- **Core Argument**: Cloud CAPEX creates structural demand cycle for AI server supply chain
- **Bull Case**: Enterprise AI adoption accelerating, GPU supply constrained, order backlogs extending
- **Bear Case**: CAPEX overshoot, technology obsolescence, export controls
- **Key Risks**: Geopolitics, chip cycle, demand normalization
- **Conviction**: High (structural, not cyclical)

## Phase 4: AI Structuring

**Owner**: LXL-QuantAxis (ai_parser)

**Activity**: Natural language thesis → structured `InvestmentThesis` object.

**Output**:
```json
{
  "symbol": "AI_server",
  "core_argument": "Cloud CAPEX creates structural demand for AI servers",
  "bullish_reasons": "Enterprise AI adoption, GPU supply constraints",
  "bearish_reasons": "CAPEX overshoot, export controls",
  "key_risks": "Geopolitics, tech obsolescence",
  "style": "growth",
  "conviction": "high"
}
```

## Phase 5: Factor Modeling

**Owner**: LXL-QuantAxis (factor_mapper)

**Activity**: Thesis → weighted factor model from 28-factor registry.

**Output**:
```
Factor Model: AI Infrastructure
├── momentum_score: 0.30 (multi-period trend capture)
├── trend_strength: 0.25 (directional confirmation)
├── roc_10: 0.25 (growth acceleration)
└── volume_trend: 0.20 (institutional participation)

Rationale: Growth thesis maps to momentum+trend factors.
```

## Phase 6: Strategy Validation

**Owner**: LXL-QuantAxis (strategy_builder → validator → backtest_bridge)

**Activity**:
1. Convert factor model to safe DSL strategy
2. Validate: rule syntax, factor existence, parameter ranges
3. Compile through AST allowlist
4. Run backtest on historical data

**Output**:
```
Strategy: AI_Infrastructure_Growth
Entry: momentum_score > 0.6 AND trend_strength > 0.5
Exit: max_drawdown > 0.10
Status: Validated ✓
Backtest: Sharpe 1.25 | Return +18.5% | MaxDD -12% | Trades 24
```

## Phase 7: Research Report

**Owner**: LXL-QuantAxis (report_generator)

**Activity**: Compile all pipeline outputs into institutional research report.

**Output**: Markdown + HTML report with 8 standard sections.

## Phase 8: Review & Archive

**Owner**: Analyst

**Activities**:
- Review AI-generated analysis for accuracy
- Add qualitative commentary where needed
- Sign off on final report
- Archive to Research Notebook (immutable, searchable)

**Output**: Finalized research document in the permanent research record.

## Key Principles

1. **Human judgment at entry and exit points**: Analysts generate ideas and review outputs. AI handles the middle.
2. **Every stage is auditable**: Intermediate outputs preserved as structured data.
3. **Thesis can be revisited**: Research notebook enables searching past theses and comparing predictions to outcomes.
4. **Safety at every step**: AI output validated through schemas, compiled through AST allowlist, never directly executed.
