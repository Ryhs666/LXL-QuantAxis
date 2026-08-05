# Interview Guide — LXL·QuantAxis

A 10-minute walkthrough for technical interviews. Practice delivering this narrative.

## 1. Why This Project?

**30-second opener**: "I built an AI-assisted quantitative research platform because I noticed that converting an investment idea into a testable strategy takes days of manual coding. The platform automates the pipeline from natural language thesis to backtested strategy, but critically — it never lets AI generate executable code. All strategies go through a safe DSL compiler."

## 2. What Problem Does It Solve?

**The friction**: A quant researcher has an idea ("cloud CAPEX will benefit AI servers") but translating that into factors (momentum? growth?), strategy rules, and a backtest takes hours of boilerplate.

**The solution**: Write the idea in natural language. The platform extracts the thesis, maps it to relevant factors from a 28-factor registry, constructs strategy rules in a safe DSL, validates them, runs a backtest, and produces an institutional report — all in one command.

## 3. What's the Technical Architecture?

**Walk through the layers**:
1. **Research Layer** — thesis notebook, AI parser, report generator
2. **AI Layer** — factor mapper, strategy builder, backtest analyst
3. **Quant Layer** — 28 factors, 16 strategies, backtest engine, portfolio analytics
4. **Data Layer** — akshare (A-share), yfinance (US/HK), SQLite persistence

**Key design decision**: V1/V2 dual architecture. Legacy code in `src/` continues to work. New code in `src/lxl_quantaxis/` follows domain-driven design. 14 V1 modules import V2, zero reverse dependencies.

## 4. Why Can't AI Generate Code Directly?

**This is the most important question.** Be ready:

"AI-generated Python code is inherently unsafe for financial applications. Even with sandboxing, the attack surface is too large. Instead, I designed a declarative DSL — strategies are expressed as rule strings like `momentum_score > 0.6 AND trend_strength > 0.5`. These pass through three safety layers:

1. **Token blocklist** — rejects `import`, `exec`, `eval`, `os`, `subprocess`, `__dunder__`
2. **AST validation** — only `Compare`, `BoolOp`, `Name`, `Constant` nodes allowed
3. **Factor whitelist** — all variable names checked against the 28-factor registry

The compiler uses Python's `ast` module with an explicit allowlist — anything not on the list is rejected. This is a deliberate architectural choice, not a short-term workaround."

## 5. How Do You Ensure Strategy Reliability?

"When AI generates a strategy, it goes through:
- Schema validation (are factor names real? do weights sum to 1?)
- AST safety check (is the rule parseable and safe?)
- Backtest on historical data (does it actually produce results?)
- AI analysis (what are the strengths/weaknesses?)
- All results saved to an immutable research notebook

The human researcher reviews the AI analysis before accepting any strategy. The platform is an assistant, not a decision maker."

## 6. Future Directions

"If I had more time:
- **Multi-step agent**: The AI could run multiple strategies, compare results, and iterate
- **Real fundamental data**: Connect to financial statement APIs for PE/PB/ROE factors
- **Live paper trading**: Connect the strategy compiler to a paper broker for forward testing
- **Collaborative research**: Multiple researchers sharing and reviewing theses in the notebook

But the current architecture is designed so each of these is a new module, not a rewrite."

## Common Follow-up Questions

**Q: How is this different from just using ChatGPT to write trading code?**
A: ChatGPT generates Python that you run at your own risk. LXL·QuantAxis extracts structured theses and compiles them through a safe DSL. No generated code ever executes. The entire pipeline is auditable.

**Q: Does it actually make money?**
A: It's a research platform, not a trading system. It helps you test ideas systematically. Whether those ideas are profitable depends on the quality of your investment thesis. The platform is paper trading only — explicitly not connected to real brokers.

**Q: What was the hardest part?**
A: The strategy DSL compiler. Designing a language expressive enough for real strategies but restrictive enough to be provably safe. The AST allowlist approach took several iterations to get right.

**Q: How many factors/strategies does it have?**
A: 28 factors (trend, momentum, volatility, volume, pattern) and 16 strategies (7 classic, 5 advanced, 4 factor-composed). But the real value isn't the quantity — it's the AI pipeline that maps arbitrary investment ideas to these factors.
