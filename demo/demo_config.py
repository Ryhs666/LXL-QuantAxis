"""Demo configuration — safe defaults for showcase runs."""

DEMO_SYMBOL = "000001"
DEMO_START_DATE = "2024-01-01"
DEMO_USE_LLM = False  # Rule-based for deterministic demos
DEMO_OUTPUT_DIR = "reports"

# Example investment theses for quick demos
EXAMPLE_THESES = [
    {
        "title": "AI Server Supply Chain",
        "text": (
            "AI服务器产业链受益于云厂商资本开支持续提升。"
            "GPU算力需求增长确定性高，订单可见度达12个月以上。"
            "风险：产能过剩、技术迭代快、芯片管制。"
        ),
        "symbol": "000001",
    },
    {
        "title": "Consumer Value Recovery",
        "text": (
            "消费板块估值处于历史低位，经济复苏预期升温。"
            "龙头企业市场份额提升，现金流充裕。"
            "风险：消费复苏不及预期、渠道库存积压。"
        ),
        "symbol": "000001",
    },
    {
        "title": "Semiconductor Cycle Bottom",
        "text": (
            "全球半导体周期接近底部，库存去化进入尾声。"
            "AI驱动的需求增量将成为下一轮上行周期的催化剂。"
            "风险：地缘政治、出口管制升级、需求反弹幅度不确定。"
        ),
        "symbol": "000001",
    },
]
