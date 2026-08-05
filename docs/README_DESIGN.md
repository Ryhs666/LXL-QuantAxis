# README Design Notes — LXL·QuantAxis V2.0

## Design Principles

### 1. Lead with Value, Not Features
Open with the core transformation: human thesis → validated research.
Avoid "We support X, Y, Z" lists at the top.

### 2. Show the Pipeline
The 6-stage pipeline is the product. Make it visible immediately.
Use ASCII art in code blocks for clarity.

### 3. Prove with Demo Output
Include real CLI output from `demo_ai_research.py`. Not mocked.

### 4. Be Honest About Limitations
Explicitly state what the platform is NOT: no live trading, no market data vendor, AI output requires human review.

### 5. Target Audience
- Quantitative researchers evaluating AI-assisted workflows
- Individual investors wanting systematic research
- Students learning quant research methodology
- Open-source contributors

## Structure Rationale

| Section | Purpose |
|---------|---------|
| Overview | Problem/solution elevator pitch |
| Core Innovation | Differentiators from traditional quant systems |
| Architecture | Visual hierarchy of system layers |
| Pipeline | The hero feature — step-by-step with CLI output |
| Features | Drill-down into each subsystem |
| Quick Start | 3 commands to get running |
| Tech Stack | Transparency about dependencies |
| Philosophy | What we believe about research process |
| What It's Not | Honest limitations |

## Tone

- Professional but accessible
- No marketing hyperbole ("revolutionary", "best-in-class")
- No absolute claims ("guaranteed returns", "optimal strategies")
- Attribution for data sources
- Clear about paper trading only
