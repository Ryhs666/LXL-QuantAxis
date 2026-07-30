"""
LXL·QuantAxis — 量化游戏化系统 数据库迁移脚本

创建成就/积分/关卡/徽章/连胜等表，并初始化默认数据。

运行: python migrate_game.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from src.database import engine, Base, SessionLocal
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ═══════════════════════════════════════════════════════════
# 游戏化模型
# ═══════════════════════════════════════════════════════════

class UserGameProfile(Base):
    """用户游戏档案 — 积分/等级/连胜"""
    __tablename__ = "user_game_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    total_points = Column(Integer, default=0)           # 总积分
    current_level = Column(Integer, default=1)           # 当前等级 (1-100)
    current_streak = Column(Integer, default=0)          # 连续登录天数
    max_streak = Column(Integer, default=0)              # 历史最长连胜
    total_trades = Column(Integer, default=0)            # 总交易次数
    winning_trades = Column(Integer, default=0)          # 盈利交易次数
    total_profit = Column(Float, default=0.0)            # 累计盈利
    backtests_run = Column(Integer, default=0)           # 回测次数
    strategies_created = Column(Integer, default=0)      # 创建策略数
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User")
    achievements = relationship("UserAchievement", back_populates="profile", cascade="all, delete-orphan")


class Achievement(Base):
    """成就定义表"""
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(32), unique=True, nullable=False)       # 成就标识: first_blood, streak_7 等
    name = Column(String(64), nullable=False)                    # 中文名
    description = Column(String(256), default="")                # 描述
    icon = Column(String(8), default="[!]")                       # emoji 图标
    category = Column(String(16), default="general")             # 分类: trading/backtest/strategy/streak
    points_reward = Column(Integer, default=50)                  # 达成奖励积分
    requirement_desc = Column(String(128), default="")           # 达成条件说明
    tier = Column(Integer, default=1)                            # 成就段位: 1=铜 2=银 3=金 4=钻石
    hidden = Column(Boolean, default=False)                       # 是否隐藏


class UserAchievement(Base):
    """用户已解锁成就"""
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("user_game_profiles.id"), nullable=False, index=True)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    unlocked_at = Column(DateTime, default=_utcnow)

    profile = relationship("UserGameProfile", back_populates="achievements")
    achievement = relationship("Achievement")


class DailyCheckin(Base):
    """每日签到记录"""
    __tablename__ = "daily_checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    checkin_date = Column(String(10), nullable=False)            # YYYY-MM-DD
    points_earned = Column(Integer, default=10)
    streak_bonus = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "checkin_date", name="uq_user_checkin_date"),
    )


class Leaderboard(Base):
    """排行榜快照"""
    __tablename__ = "leaderboard"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    username = Column(String(64))
    rank = Column(Integer)
    total_points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    win_rate = Column(Float, default=0.0)
    category = Column(String(16), default="weekly")              # weekly/monthly/alltime
    snapshot_at = Column(DateTime, default=_utcnow)


# ═══════════════════════════════════════════════════════════
# 默认成就数据
# ═══════════════════════════════════════════════════════════

DEFAULT_ACHIEVEMENTS = [
    # ── 交易类 ──
    {"key": "first_trade",  "name": "初次交易",   "description": "完成第一笔模拟交易",          "icon": "[!]", "category": "trading",   "points_reward": 10,  "requirement_desc": "完成1笔交易",       "tier": 1},
    {"key": "trader_10",    "name": "交易学徒",   "description": "累计完成10笔交易",             "icon": "[!]", "category": "trading",   "points_reward": 50,  "requirement_desc": "完成10笔交易",      "tier": 1},
    {"key": "trader_100",   "name": "交易大师",   "description": "累计完成100笔交易",            "icon": "[!]", "category": "trading",   "points_reward": 200, "requirement_desc": "完成100笔交易",     "tier": 2},
    {"key": "trader_1000",  "name": "交易传奇",   "description": "累计完成1000笔交易",           "icon": "[!]", "category": "trading",   "points_reward": 1000,"requirement_desc": "完成1000笔交易",    "tier": 4},
    {"key": "win_rate_60",  "name": "六成胜率",   "description": "胜率达到60%以上",              "icon": "[!]", "category": "trading",   "points_reward": 100, "requirement_desc": "胜率≥60%",         "tier": 2},
    {"key": "win_rate_80",  "name": "八成胜率",   "description": "胜率达到80%以上",              "icon": "[!]", "category": "trading",   "points_reward": 500, "requirement_desc": "胜率≥80%",         "tier": 3},
    # ── 回测类 ──
    {"key": "first_backtest","name": "初次回测",  "description": "完成第一次策略回测",           "icon": "[!]", "category": "backtest", "points_reward": 10,  "requirement_desc": "完成1次回测",       "tier": 1},
    {"key": "backtest_50",  "name": "回测狂热",   "description": "累计完成50次回测",             "icon": "[!]", "category": "backtest", "points_reward": 100, "requirement_desc": "完成50次回测",      "tier": 2},
    {"key": "sharpe_2",     "name": "夏普猎手",   "description": "某次回测夏普比率超过2.0",      "icon": "[!]", "category": "backtest", "points_reward": 200, "requirement_desc": "夏普比率≥2.0",     "tier": 3},
    {"key": "sharpe_5",     "name": "夏普之神",   "description": "某次回测夏普比率超过5.0",      "icon": "[!]", "category": "backtest", "points_reward": 500, "requirement_desc": "夏普比率≥5.0",     "tier": 4},
    # ── 策略类 ──
    {"key": "first_strategy","name": "策略新手",  "description": "创建第一个自定义策略",         "icon": "[!]️", "category": "strategy","points_reward": 20,  "requirement_desc": "创建1个策略",       "tier": 1},
    {"key": "strategy_5",   "name": "策略工匠",   "description": "创建5个自定义策略",            "icon": "⚙️", "category": "strategy","points_reward": 100, "requirement_desc": "创建5个策略",       "tier": 2},
    {"key": "all_strategies","name": "策略博览",  "description": "使用过所有内置策略进行回测",    "icon": "[!]", "category": "strategy","points_reward": 300, "requirement_desc": "使用全部11个策略",   "tier": 3},
    # ── 连胜类 ──
    {"key": "streak_3",     "name": "三日连胜",   "description": "连续3天登录",                   "icon": "[!]", "category": "streak",   "points_reward": 30,  "requirement_desc": "连续登录3天",       "tier": 1},
    {"key": "streak_7",     "name": "七日之约",   "description": "连续7天登录",                   "icon": "[!]", "category": "streak",   "points_reward": 100, "requirement_desc": "连续登录7天",       "tier": 2},
    {"key": "streak_30",    "name": "月之契约",   "description": "连续30天登录",                   "icon": "[!]", "category": "streak",   "points_reward": 500, "requirement_desc": "连续登录30天",      "tier": 3},
    {"key": "streak_100",   "name": "百折不挠",   "description": "连续100天登录",                  "icon": "[!]", "category": "streak",   "points_reward": 2000,"requirement_desc": "连续登录100天",     "tier": 4},
    # ── 因子类 ──
    {"key": "factor_master", "name": "因子大师",  "description": "使用自定义因子策略盈利超过20%", "icon": "[!]", "category": "strategy","points_reward": 300, "requirement_desc": "因子策略盈利≥20%",  "tier": 3},
    {"key": "daily_scan_10","name": "每日警觉",   "description": "累计运行10次每日扫描",          "icon": "[!]", "category": "general",  "points_reward": 50,  "requirement_desc": "运行10次每日扫描",   "tier": 1},
    {"key": "profit_100k",  "name": "十万盈利",   "description": "模拟账户累计盈利超过10万",      "icon": "[!]", "category": "trading",  "points_reward": 500, "requirement_desc": "累计盈利≥10万元",   "tier": 3},
]


# ═══════════════════════════════════════════════════════════
# 迁移入口
# ═══════════════════════════════════════════════════════════

def migrate():
    """创建游戏化相关表 + 初始化默认成就"""
    print("=" * 56)
    print("  LXL·QuantAxis — 游戏化系统 数据库迁移")
    print("=" * 56)

    # 1. 创建新表
    print("\n[1/3] 创建游戏化表...")
    Base.metadata.create_all(bind=engine)
    print(f"  [OK] user_game_profiles")
    print(f"  [OK] achievements")
    print(f"  [OK] user_achievements")
    print(f"  [OK] daily_checkins")
    print(f"  [OK] leaderboard")

    # 2. 初始化默认成就
    print(f"\n[2/3] 初始化成就数据 ({len(DEFAULT_ACHIEVEMENTS)} 个)...")
    db = SessionLocal()
    try:
        created = 0
        skipped = 0
        for ach in DEFAULT_ACHIEVEMENTS:
            existing = db.query(Achievement).filter_by(key=ach["key"]).first()
            if existing:
                skipped += 1
                continue
            db.add(Achievement(**ach))
            created += 1
        db.commit()
        print(f"  [OK] 新增 {created} 个, 跳过 {skipped} 个 (已存在)")
    except Exception as e:
        db.rollback()
        print(f"  ❌ 失败: {e}")
        raise
    finally:
        db.close()

    # 3. 为已有用户创建游戏档案
    print(f"\n[3/3] 为已有用户创建游戏档案...")
    db = SessionLocal()
    try:
        from src.database.models import User
        users = db.query(User).all()
        created = 0
        for u in users:
            profile = db.query(UserGameProfile).filter_by(user_id=u.id).first()
            if not profile:
                db.add(UserGameProfile(user_id=u.id))
                created += 1
        db.commit()
        print(f"  [OK] 为 {created} 位用户创建游戏档案")
    except Exception as e:
        db.rollback()
        print(f"  ❌ 失败: {e}")
        raise
    finally:
        db.close()

    print(f"\n{'=' * 56}")
    print(f"  [!] 游戏化系统迁移完成!")
    print(f"  [!] 成就数: {len(DEFAULT_ACHIEVEMENTS)}")
    print(f"  [!] 等级体系: 1-100 级")
    print(f"  [!] 连胜系统: 已激活")
    print(f"  [!] 排行榜: 已就绪")
    print(f"{'=' * 56}\n")


if __name__ == "__main__":
    from src.database import init_db
    init_db()  # 确保基础表存在
    migrate()
