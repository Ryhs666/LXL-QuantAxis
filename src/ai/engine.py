"""
AI 引擎 — LLM 客户端

支持:
  - OpenAI 兼容 API (ChatGPT / DeepSeek / 通义千问 / 本地Ollama等)
  - 多轮对话
  - 流式输出
  - 量化专用 System Prompt

配置方式:
  设置环境变量:
    AI_API_KEY=your_key
    AI_BASE_URL=https://api.openai.com/v1   (或其他兼容端点)
    AI_MODEL=gpt-4o

  或新建 D:/trading_data/ai_config.json:
    {"api_key":"...", "base_url":"...", "model":"..."}
"""

import os, sys, json, time
from typing import Optional, Generator
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.config import config as cfg
from src.lxl_quantaxis.ai import CompletionResponse


# ============================================================
# 配置
# ============================================================

def _load_ai_config() -> dict:
    """加载 AI 配置"""
    ai_cfg = {
        "api_key": os.environ.get("AI_API_KEY", ""),
        "base_url": os.environ.get("AI_BASE_URL", "https://api.openai.com/v1"),
        "model": os.environ.get("AI_MODEL", "gpt-4o"),
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    # 尝试从文件加载
    config_file = os.path.join(cfg.data_dir, "ai_config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
                ai_cfg.update(file_cfg)
        except Exception:
            pass

    return ai_cfg


class LLMClient:
    """通用 LLM 客户端"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        ai_cfg = _load_ai_config()
        self.api_key = api_key or ai_cfg["api_key"]
        self.base_url = base_url or ai_cfg["base_url"]
        self.model = model or ai_cfg["model"]
        self.temperature = ai_cfg.get("temperature", 0.3)
        self.max_tokens = ai_cfg.get("max_tokens", 2048)
        self.system_prompt = ai_cfg.get("system_prompt", "")

    def _endpoint(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"

    def chat(self, messages: list, temperature: float = None,
             max_tokens: int = None, stream: bool = False) -> str:
        """发送对话，返回回复文本"""
        import urllib.request
        import urllib.error

        if not self.api_key:
            return "❌ 请先设置 AI_API_KEY 环境变量或配置 D:/trading_data/ai_config.json"

        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": stream,
        }

        try:
            req = urllib.request.Request(
                self._endpoint(),
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            return f"❌ API 错误 ({e.code}): {error_body[:200]}"
        except Exception as e:
            return f"❌ 连接失败: {e}"

    def chat_stream(self, messages: list, temperature: float = None) -> Generator[str, None, None]:
        """流式对话，逐字返回"""
        import urllib.request
        import urllib.error

        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "stream": True,
        }

        try:
            req = urllib.request.Request(
                self._endpoint(),
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=120) as resp:
                for line in resp:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            yield f"\n❌ {e}"

    def ask(self, user_message: str, system: str = None,
            temperature: float = None) -> str:
        """单轮对话快捷方法"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        elif self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": user_message})
        return self.chat(messages, temperature=temperature)

    def ask_stream(self, user_message: str, system: str = None):
        """流式快捷方法"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_message})
        return self.chat_stream(messages)


class LegacyLLMPort:
    """Compatibility adapter exposing the legacy client through the V2 LLM port."""

    def __init__(self, client: LLMClient):
        self.client = client

    def complete(self, *, prompt: str) -> CompletionResponse:
        content = self.client.ask(prompt)
        if content.startswith("❌"):
            raise RuntimeError(content)
        return CompletionResponse(
            content=content,
            model=self.client.model,
            input_tokens=0,
            output_tokens=0,
        )


# 全局客户端
llm = LLMClient()


# ============================================================
# 量化专用 System Prompts
# ============================================================

QUANT_SYSTEM = """你是一位资深量化交易策略师，拥有10年以上的A股、美股投资经验。
你的职责是帮助交易者分析交易记录、优化策略参数、解读市场信号。

核心原则:
1. 所有建议基于数据，不凭空猜测
2. 强调风险管理，不建议all-in
3. 用简洁中文回复，核心观点加粗
4. 涉及具体代码/标的时，声明"仅供参考，不构成投资建议"
5. 优先从行为金融学角度分析交易者的决策偏差"""

TRADE_REVIEW_SYSTEM = """你是交易复盘教练。分析交易记录时关注:
1. 行为偏差: 追涨杀跌、过度交易、锚定效应、处置效应
2. 模式识别: 哪些类型的交易在赚钱？哪些在亏钱？
3. 改进建议: 具体的、可操作的建议
4. 盈亏归因: 是选股问题？择时问题？还是仓位问题？

用数据说话，给出直白的评价。"""

STRATEGY_ADVISOR_SYSTEM = """你是量化策略顾问。在分析策略时:
1. 先看风险指标（最大回撤、夏普比率）再看收益
2. 判断过拟合风险（参数是否过于敏感？样本外是否稳健？）
3. 给出参数调整方向建议
4. 结合当前市场环境判断策略适用性"""

MARKET_WRITER_SYSTEM = """你是财经市场分析师。写作风格:
- 简洁有力，一针见血
- 用数据说话
- 给出明确的多空判断，不模棱两可
- 每个判断附支撑逻辑
- 标注风险提示"""
