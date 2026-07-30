"""
金融资讯抓取模块
================
统一抓取金融资讯，Tushare 优先 → 新浪财经备用 → 东方财富兜底。
若全部不可用，返回空列表（允许上层提示"数据源暂不可用"）。

数据源优先级：
1. Tushare (major_cctv_news / news 接口) — 结构化金融资讯
2. 新浪财经 RSS — 快讯抓取
3. 东方财富 — 新闻抓取

每条资讯归一化为: {title, content, source, category, news_url, fetched_at}
"""

import os
import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError
import xml.etree.ElementTree as ET

import logging

logger = logging.getLogger(__name__)

# ============================================================
# 配置
# ============================================================

DEFAULT_DB_PATH = str(Path(__file__).parent.parent / "yihuiban_sim.db")

# 从环境变量读取 Tushare token
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")

# 新华信源关键词（用于过滤银行/理财相关）
BANK_KEYWORDS = [
    "银行", "理财", "利率", "存款", "贷款", "央行", "LPR", "MLF",
    "基金", "保险", "监管", "金融", "汇率", "债券", "股市",
    "信托", "资管", "房贷", "信用卡", "降准", "加息",
    "银保监会", "证监会", "人民银行", "逆回购",
]

# 排除关键词（噪音内容）
EXCLUDE_KEYWORDS = [
    "娱乐", "体育", "影视", "综艺", "彩票",
]


def _load_env():
    """加载 .env 文件中的环境变量"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    val = val.strip().strip('"').strip("'")
                    if key not in os.environ:
                        os.environ[key] = val


_load_env()
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")


# ============================================================
# 数据源 1: Tushare
# ============================================================

def _fetch_tushare_news(today: date) -> list[dict]:
    """
    通过 Tushare 获取新闻资讯。

    使用 news 接口（普通新闻），需要 ≥2000 积分权限。
    若无权限（40203），直接跳过不重试 HTTP fallback。
    """
    if not TUSHARE_TOKEN:
        logger.warning("Tushare token not configured, skip")
        return []

    try:
        import tushare as ts
    except ImportError:
        logger.warning("tushare not installed, skip. Install: pip install tushare")
        return _fetch_tushare_http(today)

    try:
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()

        today_str = today.isoformat().replace("-", "")

        # 先尝试 news 接口
        try:
            df = pro.news(start_date=today_str, end_date=today_str, limit=200)
        except Exception as api_err:
            err_str = str(api_err).lower()
            if "40203" in err_str or "权限" in err_str or "permission" in err_str:
                logger.warning("Tushare news API requires permission (40203), skip Tushare")
                return []
            # 其他错误尝试 HTTP fallback
            return _fetch_tushare_http(today)

        if df is None or len(df) == 0:
            logger.info("Tushare news: no results for %s", today_str)
            return []

        results = []
        for _, row in df.iterrows():
            title = str(row.get("title", "") or "")
            content = str(row.get("content", "") or "")
            if not title:
                continue

            source = str(row.get("source", "tushare"))
            news_url = str(row.get("url", "") or "")

            # 关键词过滤
            if not _match_bank_keyword(title) and not _match_bank_keyword(content[:200]):
                continue

            results.append({
                "title": title[:300],
                "content": content[:2000] if content else "",
                "source": source[:50] if source else "tushare",
                "category": _classify_news(title, content),
                "news_url": news_url[:500] if news_url else "",
                "fetched_at": today.isoformat(),
                "created_at": datetime.now().isoformat(),
            })

        logger.info("Tushare news: fetched %d items", len(results))
        return results

    except Exception as e:
        logger.error("Tushare news fetch error: %s", e)
        return []


def _fetch_tushare_http(today: date) -> list[dict]:
    """
    Tushare HTTP API 直接调用（无需 tushare SDK）。
    """
    if not TUSHARE_TOKEN:
        return []

    try:
        today_str = today.isoformat().replace("-", "")
        url = "https://api.tushare.pro"
        payload = json.dumps({
            "api_name": "news",
            "token": TUSHARE_TOKEN,
            "params": {"limit": 100},
            "fields": "title,content,source,url",
        }).encode("utf-8")

        req = Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("code") != 0:
            logger.error("Tushare HTTP error: %s", data.get("msg", "unknown"))
            return []

        rows = data.get("data", {}).get("items", [])
        results = []
        for row in rows:
            title = (row[0] or "") if len(row) > 0 else ""
            if not title:
                continue
            content = (row[1] or "") if len(row) > 1 else ""
            source = (row[2] or "tushare") if len(row) > 2 else "tushare"
            news_url = (row[3] or "") if len(row) > 3 else ""

            if not _match_bank_keyword(title) and not _match_bank_keyword(content[:200]):
                continue

            results.append({
                "title": title[:300],
                "content": content[:2000] if content else "",
                "source": source[:50],
                "category": _classify_news(title, content),
                "news_url": news_url[:500],
                "fetched_at": today.isoformat(),
                "created_at": datetime.now().isoformat(),
            })

        logger.info("Tushare HTTP: fetched %d items", len(results))
        return results

    except Exception as e:
        logger.error("Tushare HTTP fetch error: %s", e)
        return []


# ============================================================
# 数据源 2: 新浪财经
# ============================================================

def _fetch_sina_finance(today: date) -> list[dict]:
    """
    通过新浪财经 API 获取金融快讯。

    接口：https://feed.mix.sina.com.cn/api/roll/get
    """
    today_str = today.isoformat()
    results = []

    try:
        # 获取最新财经快讯（不加 ctime 参数以获取当日最新）
        url = (
            "https://feed.mix.sina.com.cn/api/roll/get?"
            "pageid=153&lid=2516&num=50&versionNumber=1.2.4&encode=utf-8"
        )
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)

        items = data.get("result", {}).get("data", [])
        for item in items:
            title = item.get("title", "")
            if not title:
                continue

            intro = item.get("intro", "") or item.get("summary", "") or ""
            ctime_str = item.get("ctime", "")

            # 时间过滤：只要当天的
            if ctime_str and not ctime_str.startswith(today_str):
                try:
                    t = datetime.fromtimestamp(int(ctime_str))
                    if t.date() != today:
                        continue
                except (ValueError, TypeError):
                    pass

            if not _match_bank_keyword(title):
                continue

            results.append({
                "title": title[:300],
                "content": _strip_html(intro)[:2000] if intro else "",
                "source": "sina",
                "category": _classify_news(title, intro),
                "news_url": item.get("url", "")[:500],
                "fetched_at": today.isoformat(),
                "created_at": datetime.now().isoformat(),
            })

        logger.info("Sina finance: fetched %d items", len(results))
    except Exception as e:
        logger.error("Sina finance fetch error: %s", e)

    return results


# ============================================================
# 数据源 3: 东方财富
# ============================================================

def _fetch_eastmoney(today: date) -> list[dict]:
    """
    通过东方财富获取财经新闻（简易抓取版）。

    由于东方财富 API 需额外鉴权参数，此函数作为轻量备用。
    当前用新浪财经已足够覆盖日常资讯需求。
    """
    # 东方财富 API 当前需要额外鉴权参数（fastColumn, req_trace 等），
    # 且多数公开接口返回 404。保留此函数框架供将来配置后启用。
    logger.info("EastMoney: API requires authentication, skipped (using Sina as primary)")
    return []


# ============================================================
# 工具函数
# ============================================================

def _match_bank_keyword(text: str) -> bool:
    """检查文本是否匹配银行/理财关键词"""
    if not text:
        return False
    # 先排除噪音
    for kw in EXCLUDE_KEYWORDS:
        if kw in text:
            return False
    # 再匹配
    for kw in BANK_KEYWORDS:
        if kw in text:
            return True
    return False


def _classify_news(title: str, content: str) -> str:
    """新闻分类"""
    text = f"{title} {content[:200]}"

    policy_kw = ["央行", "银保监", "证监会", "LPR", "MLF", "降准", "加息", "逆回购",
                  "监管", "法规", "条例", "行政", "处罚"]
    product_kw = ["理财", "基金", "保险", "存款", "收益率", "利率调整"]
    bank_kw = ["银行发", "商业银行", "分行", "网点"]

    if any(kw in text for kw in policy_kw):
        return "policy"
    if any(kw in text for kw in product_kw):
        return "product"
    if any(kw in text for kw in bank_kw):
        return "bank"
    return "finance"


def _strip_html(text: str) -> str:
    """去除 HTML 标签"""
    import re
    return re.sub(r"<[^>]+>", "", text).strip()


# ============================================================
# 统一入口
# ============================================================

def fetch_daily_news(
    target_date: Optional[date] = None,
    db_path: Optional[str] = None,
) -> dict:
    """
    每日金融资讯抓取主函数。

    优先级：Tushare → 新浪财经 → 东方财富。
    结果存入 daily_news 表。

    Args:
        target_date: 目标日期，默认今天
        db_path: 数据库路径

    Returns:
        {"status": "ok|partial|empty",
         "count": N,
         "sources": {"tushare": N, "sina": N, "eastmoney": N}}
    """
    today = target_date or date.today()
    db = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    sources = {"tushare": 0, "sina": 0, "eastmoney": 0}
    total = 0

    try:
        # ---- 确保表存在 ----
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS daily_news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                source TEXT NOT NULL DEFAULT 'tushare',
                category TEXT NOT NULL DEFAULT 'finance',
                news_url TEXT,
                fetched_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_dn_date ON daily_news(fetched_at);
            CREATE INDEX IF NOT EXISTS idx_dn_category ON daily_news(category);
        """)

        # ---- 去重检查 ----
        existing = conn.execute(
            "SELECT COUNT(*) as cnt FROM daily_news WHERE fetched_at = ?",
            (today.isoformat(),),
        ).fetchone()
        if existing and existing["cnt"] > 0:
            logger.info("News for %s already fetched (%d items)", today.isoformat(), existing["cnt"])
            return {"status": "ok", "count": existing["cnt"], "sources": {"tushare": 0, "sina": 0, "eastmoney": 0}}

        all_news: list[dict] = []
        seen_titles = set()

        # ---- 1. Tushare ----
        tushare_items = _fetch_tushare_news(today)
        sources["tushare"] = len(tushare_items)
        for item in tushare_items:
            if item["title"] not in seen_titles:
                seen_titles.add(item["title"])
                all_news.append(item)

        # ---- 2. 新浪财经（仅当 Tushare 返回不足 5 条时启用） ----
        if len(all_news) < 5:
            sina_items = _fetch_sina_finance(today)
            sources["sina"] = len(sina_items)
            for item in sina_items:
                if item["title"] not in seen_titles:
                    seen_titles.add(item["title"])
                    all_news.append(item)

        # ---- 3. 东方财富（仅当总数不足 5 条时启用） ----
        if len(all_news) < 5:
            em_items = _fetch_eastmoney(today)
            sources["eastmoney"] = len(em_items)
            for item in em_items:
                if item["title"] not in seen_titles:
                    seen_titles.add(item["title"])
                    all_news.append(item)

        # ---- 写入数据库 ----
        for n in all_news:
            conn.execute(
                """INSERT OR IGNORE INTO daily_news
                   (title, content, source, category, news_url, fetched_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    n["title"], n["content"], n["source"],
                    n["category"], n["news_url"], n["fetched_at"],
                    n["created_at"],
                ),
            )
            total += 1

        conn.commit()

        if total > 0:
            status = "ok"
        elif any(v > 0 for v in sources.values()):
            status = "partial"
        else:
            status = "empty"

        return {"status": status, "count": total, "sources": sources}

    except Exception as e:
        conn.rollback()
        logger.exception("fetch_daily_news error")
        return {"status": "error", "count": 0, "sources": sources, "message": str(e)}
    finally:
        conn.close()


# ============================================================
# 便利函数：获取今日资讯摘要
# ============================================================

def get_today_news_summary(db_path: Optional[str] = None) -> str:
    """
    获取今日资讯的简短摘要（供 ContentAgent gen_digest 使用）。

    Returns:
        今日资讯摘要文本，若无数据则返回提示信息。
    """
    db = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    today_str = date.today().isoformat()
    rows = conn.execute(
        "SELECT title, content, source, category FROM daily_news"
        " WHERE fetched_at = ? ORDER BY id",
        (today_str,),
    ).fetchall()
    conn.close()

    if not rows:
        return "今日暂无金融资讯数据。"

    lines = [f"📰 今日金融资讯 {today_str} ({len(rows)}条)\n"]
    categories = {}
    for r in rows:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)

    for cat, items in categories.items():
        label = {"finance": "财经", "policy": "政策", "product": "产品", "bank": "银行"}.get(cat, cat)
        lines.append(f"\n## {label}")
        for item in items[:6]:  # 每类最多 6 条
            src = item["source"]
            content_preview = (item["content"] or "")[:80]
            lines.append(f"- [{src}] {item['title']}")
            if content_preview:
                lines.append(f"  {content_preview}")

    return "\n".join(lines)


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    result = fetch_daily_news()
    print(f"fetch_daily_news: status={result['status']}, count={result['count']}")
    print(f"  sources: {result['sources']}")

    summary = get_today_news_summary()
    print("\n" + summary)
