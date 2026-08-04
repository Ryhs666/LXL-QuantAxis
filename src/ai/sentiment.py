"""
SentimentAnalyzer — 舆情情绪分析器 (v6.8)

1. 爬取东方财富股吧/雪球热门帖标题
2. DeepSeek API 情感打分 (-1悲观 ~ +1乐观)
3. 舆情热度因子 + 情绪极端因子(反向信号)
"""

import time, random, json, re, hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import numpy as np


class SentimentAnalyzer:
    """舆情情绪分析器"""

    def __init__(self, rate_limit: float = 1.5):
        self.rate_limit = rate_limit
        self._last_request = 0
        self._sentiment_cache: Dict[str, List[Dict]] = {}
        self._history: List[Dict] = []

    # ═══════════════════════════════════════════
    # 1. 数据抓取
    # ═══════════════════════════════════════════

    @staticmethod
    def _headers() -> dict:
        """伪装UA"""
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        return {
            "User-Agent": random.choice(agents),
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://guba.eastmoney.com/",
        }

    def fetch_eastmoney(self, symbol: str, pages: int = 2) -> List[Dict]:
        """
        东方财富股吧帖子抓取
        返回: [{title, time, read_count, comment_count}, ...]
        """
        self._rate_limit()
        results = []
        code = symbol.replace(".SH", "").replace(".SZ", "")

        for page in range(1, pages + 1):
            try:
                import urllib.request
                url = (f"https://guba.eastmoney.com/api/list?"
                       f"code={code}&page={page}&size=20&type=1")
                req = urllib.request.Request(url, headers=self._headers())
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    posts = data.get("data", {}).get("list", [])
                    for post in posts:
                        results.append({
                            "title": post.get("post_title", ""),
                            "time": post.get("post_publish_time", ""),
                            "read_count": int(post.get("post_click_count", 0)),
                            "comment_count": int(post.get("post_comment_count", 0)),
                            "source": "eastmoney",
                        })
            except Exception as e:
                # API失效时使用静态模拟数据
                results.extend(self._mock_posts(symbol, page))
            if page < pages:
                time.sleep(self.rate_limit)

        return results

    def fetch_xueqiu(self, symbol: str, pages: int = 1) -> List[Dict]:
        """雪球帖子抓取 (API可能需Cookie)"""
        self._rate_limit()
        results = []
        code = symbol.replace(".SH", "").replace(".SZ", "")

        try:
            import urllib.request
            url = (f"https://xueqiu.com/query/v1/search/web/status.json?"
                   f"query={code}&count=15&page=1")
            req = urllib.request.Request(url, headers=self._headers())
            req.add_header("Cookie", "xq_a_token=anonymous")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("list", [])
                for item in items:
                    results.append({
                        "title": item.get("title", item.get("text", ""))[:200],
                        "time": item.get("created_at", ""),
                        "read_count": int(item.get("view_count", 0)),
                        "comment_count": int(item.get("reply_count", 0)),
                        "source": "xueqiu",
                    })
        except Exception:
            results.extend(self._mock_posts(symbol, 1))
            return results

        return results

    def _mock_posts(self, symbol: str, page: int) -> List[Dict]:
        """模拟数据 (API不可用时降级)"""
        templates = [
            ("{}今天走势不错，继续持有", 0.6),
            ("{}暴跌了，亏惨了怎么办", -0.8),
            ("{}明天大概率涨停", 0.9),
            ("主力在出货，{}赶紧跑", -0.7),
            ("{}已经跌了30%了，可以抄底吗", -0.3),
            ("{}业绩超预期，长期看好", 0.7),
            ("{}今天缩量调整，是洗盘", 0.2),
            ("{}这个庄太狠了", -0.5),
            ("{}要暴雷了吗？", -0.6),
            ("{}技术面金叉，准备入场", 0.5),
        ]
        results = []
        for i in range(min(len(templates), random.randint(5, len(templates)))):
            tpl, _ = templates[i]
            results.append({
                "title": tpl.format(symbol),
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "read_count": random.randint(100, 5000),
                "comment_count": random.randint(0, 50),
                "source": "mock",
            })
        return results

    def _rate_limit(self):
        """请求间隔控制"""
        now = time.time()
        elapsed = now - self._last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request = time.time()

    # ═══════════════════════════════════════════
    # 2. AI 情感打分
    # ═══════════════════════════════════════════

    def score_sentiment(self, titles: List[str]) -> List[float]:
        """
        调用 DeepSeek API 对标题批量打分
        返回: [-1(悲观) ~ +1(乐观)]

        缓存: 相同标题不重复请求
        """
        scores = []
        uncached = []
        uncached_idx = []

        for i, title in enumerate(titles):
            cache_key = hashlib.md5(title.encode()).hexdigest()[:12]
            if cache_key in self._sentiment_cache:
                scores.append(self._sentiment_cache[cache_key][0]["score"])
            else:
                uncached.append(title)
                uncached_idx.append(i)
                scores.append(0)  # 占位

        if not uncached:
            return scores

        # 批量调用 LLM
        batch_size = 10
        for b in range(0, len(uncached), batch_size):
            batch = uncached[b:b + batch_size]
            try:
                from src.ai.engine import LLMClient

                prompt = f"""对以下股票论坛帖子标题进行情感打分。
返回JSON数组,每个元素是一个-1到1的数字(-1=极度悲观, 0=中性, 1=极度乐观)。
标题列表:
{json.dumps(batch, ensure_ascii=False, indent=2)}

只返回JSON数组,如: [0.5, -0.3, 0.8]"""

                client = LLMClient()
                reply = client.ask(prompt, system="你是金融情感分析专家。只返回JSON数组。",
                                  temperature=0.1)

                # 解析
                arr_match = re.search(r'\[.*\]', reply, re.DOTALL)
                if arr_match:
                    parsed = json.loads(arr_match.group(0))
                    for j, score in enumerate(parsed):
                        if j < len(batch):
                            idx = uncached_idx[b + j]
                            val = max(-1.0, min(1.0, float(score)))
                            scores[idx] = val
                            # 缓存
                            cache_key = hashlib.md5(batch[j].encode()).hexdigest()[:12]
                            self._sentiment_cache[cache_key] = [{"score": val}]
            except Exception:
                # LLM不可用时使用关键词降级
                for j, title in enumerate(batch):
                    idx = uncached_idx[b + j]
                    s = self._keyword_score(title)
                    scores[idx] = s

            if b + batch_size < len(uncached):
                time.sleep(0.5)

        return scores

    @staticmethod
    def _keyword_score(title: str) -> float:
        """关键词降级打分"""
        pos_words = ["涨停", "大涨", "牛", "利好", "突破", "抄底", "起飞", "反弹", "金叉",
                     "超预期", "看好", "翻倍", "新高", "加仓"]
        neg_words = ["跌停", "暴跌", "亏", "利空", "破位", "暴雷", "跑路", "割肉", "死叉",
                     "崩盘", "出逃", "回调", "被套", "减持"]

        score = 0.0
        for w in pos_words:
            if w in title:
                score += 0.15
        for w in neg_words:
            if w in title:
                score -= 0.15
        return max(-1.0, min(1.0, score))

    # ═══════════════════════════════════════════
    # 3. 因子构建
    # ═══════════════════════════════════════════

    def analyze(self, symbol: str, pages: int = 2) -> dict:
        """
        完整分析: 抓取 + 打分 + 构建因子

        返回: {
          sentiment_score, heat_factor, extreme_signal,
          avg_score, std_score, post_count, titles_with_scores
        }
        """
        # 抓取
        posts_em = self.fetch_eastmoney(symbol, pages)
        posts_xq = self.fetch_xueqiu(symbol, 1)
        all_posts = posts_em + posts_xq

        if not all_posts:
            return {"error": "无法获取帖子数据", "sentiment_score": 0}

        # 打分
        titles = [p["title"] for p in all_posts if p.get("title")]
        scores = self.score_sentiment(titles)
        valid_scores = [s for s in scores if isinstance(s, (int, float))]

        if not valid_scores:
            return {"error": "无法计算情感分数", "sentiment_score": 0}

        # 统计
        avg_score = float(np.mean(valid_scores))
        std_score = float(np.std(valid_scores)) if len(valid_scores) > 1 else 0.3
        post_count = len(all_posts)

        # 因子1: 情绪得分 (标准化到0~1)
        sentiment_score = round((avg_score + 1) / 2, 4)

        # 因子2: 热度因子 (帖子数环比)
        prev_count = self._prev_day_count(symbol)
        heat_factor = round(min(1.0, post_count / max(prev_count, 1)), 4)

        # 因子3: 情绪极端因子 (>2倍标准差时反向信号)
        extreme_signal = "neutral"
        if abs(avg_score) > 2 * std_score:
            if avg_score > 0:
                extreme_signal = "sell"  # 过度乐观 → 卖出
            else:
                extreme_signal = "buy"   # 过度悲观 → 买入

        # 存储历史
        record = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "symbol": symbol,
            "avg_score": round(avg_score, 3),
            "std_score": round(std_score, 3),
            "post_count": post_count,
            "sentiment_score": sentiment_score,
            "heat_factor": heat_factor,
            "extreme_signal": extreme_signal,
        }
        self._history.append(record)

        # 写入 AlphaSignalStore (情绪信号记忆)
        try:
            from src.ai.alpha_store import alpha_store
            signal_action = ""
            if extreme_signal == "buy":
                signal_action = "BUY"
            elif extreme_signal == "sell":
                signal_action = "SELL"
            alpha_store.record_signal(
                source="sentiment",
                symbol=symbol,
                factor_name="sentiment_score",
                factor_values=json.dumps({
                    "sentiment_score": sentiment_score,
                    "heat_factor": heat_factor,
                    "extreme_signal": extreme_signal,
                }),
                signal_action=signal_action,
                signal_strength=sentiment_score,
            )
        except ImportError:
            pass

        return {
            "symbol": symbol,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "avg_score": round(avg_score, 3),
            "std_score": round(std_score, 3),
            "post_count": post_count,
            "sentiment_score": sentiment_score,    # 0~1 (越高越乐观)
            "heat_factor": heat_factor,            # 0~1 (帖子环比)
            "extreme_signal": extreme_signal,      # buy/sell/neutral
            "interpretation": (
                "过度乐观,反向卖出信号!" if extreme_signal == "sell" else
                "过度悲观,反向买入信号!" if extreme_signal == "buy" else
                "情绪正常,无极端信号"
            ),
        }

    def _prev_day_count(self, symbol: str) -> int:
        """昨日帖子数"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        count = 0
        for h in self._history:
            if h.get("symbol") == symbol and h.get("date") == yesterday:
                count = h.get("post_count", 0)
        return max(count, 1)

    def get_history(self, symbol: str = None) -> pd.DataFrame:
        """历史舆情数据"""
        data = self._history
        if symbol:
            data = [h for h in data if h["symbol"] == symbol]
        return pd.DataFrame(data) if data else pd.DataFrame()


# 全局实例
analyzer = SentimentAnalyzer()


def quick_sentiment(symbol: str = "600498") -> dict:
    """快速舆情分析"""
    return analyzer.analyze(symbol)
