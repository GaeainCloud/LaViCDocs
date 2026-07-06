"""
图片搜索/评分/转换共享模块
合并 fetch_images.py、download_images.py、check_and_convert_images.py 的逻辑。
"""
import os
import time
import random
import re
from io import BytesIO
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from logger import get_logger
from config import (
    IMAGE_SEARCH_MAX_CANDIDATES,
    IMAGE_MIN_WIDTH,
    IMAGE_MIN_HEIGHT,
    IMAGE_MAX_ASPECT_RATIO,
    IMAGE_MIN_ASPECT_RATIO,
    IMAGE_BLOCKED_COPYRIGHT_DOMAINS,
    IMAGE_PREFERRED_LICENSE_DOMAINS,
    IMAGE_LOW_TRUST_DOMAINS,
)

log = get_logger(__name__)


@dataclass
class CandidateImage:
    """候选图片数据"""
    url: str
    data: bytes
    width: int
    height: int
    score: float
    format: str


def _get_http_headers() -> dict:
    """返回 HTTP 请求头（不硬编码 UA）。"""
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
    }


def _clean_wikimedia_url(url: str) -> str:
    """将 Wikimedia 缩略图 URL 转为全分辨率 URL。"""
    if "/thumb/" in url:
        try:
            base, part = url.split("/thumb/")
            parts = part.split("/")
            if len(parts) >= 2:
                full_path = "/".join(parts[:-1])
                return f"{base}/{full_path}"
        except Exception:
            pass
    return url


def _extract_domain(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _domain_matches(domain: str, patterns: tuple) -> bool:
    if not domain:
        return False
    for pattern in patterns:
        p = pattern.lower().strip()
        if not p:
            continue
        if p.startswith("."):
            if domain.endswith(p):
                return True
        elif domain == p or domain.endswith(f".{p}"):
            return True
    return False


def _query_tokens(query: str) -> List[str]:
    if not query:
        return []
    return [t for t in re.split(r"[^a-z0-9]+", query.lower()) if len(t) >= 3]


def _query_relevance_multiplier(url: str, query: str) -> float:
    tokens = _query_tokens(query)
    if not tokens:
        return 1.0

    url_lower = url.lower()
    hits = sum(1 for t in tokens if t in url_lower)
    if hits == 0:
        return 1.0
    return 1.0 + min(0.25, hits * 0.05)


def _copyright_source_multiplier(url: str) -> float:
    domain = _extract_domain(url)
    if _domain_matches(domain, IMAGE_BLOCKED_COPYRIGHT_DOMAINS):
        return -1.0
    if _domain_matches(domain, IMAGE_PREFERRED_LICENSE_DOMAINS):
        return 1.15
    if _domain_matches(domain, IMAGE_LOW_TRUST_DOMAINS):
        return 0.7
    return 1.0


def scrape_images_from_page(url: str) -> List[str]:
    """从网页抓取候选图片 URL。

    Args:
        url: 网页 URL

    Returns:
        去重后的图片 URL 列表
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as e:
        log.error(f"缺少依赖: {e}")
        return []

    # 直接图片 URL
    lower_url = url.lower()
    if any(lower_url.endswith(ext) for ext in [".jpg", ".png", ".jpeg", ".webp"]):
        return [url]

    candidates = []
    try:
        log.info(f"抓取页面: {url}")
        time.sleep(random.uniform(2.0, 4.0))
        resp = requests.get(url, headers=_get_http_headers(), timeout=15)

        if resp.status_code == 429:
            log.warning("被限速，等待 10 秒后重试...")
            time.sleep(10)
            resp = requests.get(url, headers=_get_http_headers(), timeout=15)

        if resp.status_code != 200:
            log.warning(f"请求失败 ({resp.status_code}): {url}")
            return []

        soup = BeautifulSoup(resp.content, "html.parser")

        # og:image
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            candidates.append(og["content"])

        # 所有 <img>
        for img in soup.find_all("img"):
            src = img.get("src")
            if not src:
                continue

            full_url = urljoin(url, src)
            fl = full_url.lower()

            if any(x in fl for x in ["logo", "icon", "button", "sprite", "flag"]):
                continue
            if not any(fl.endswith(ext) for ext in [".jpg", ".png", ".jpeg", ".webp"]):
                continue

            if "wikimedia.org" in full_url and "/thumb/" in full_url:
                cleaned = _clean_wikimedia_url(full_url)
                if cleaned != full_url:
                    candidates.append(cleaned)

            candidates.append(full_url)

    except Exception as e:
        log.error(f"抓取页面出错 ({url}): {e}")

    return list(set(candidates))


def score_image(width: int, height: int, data_size: int, url: str = "", query: str = "") -> float:
    """对候选图片评分。

    评分算法：分辨率 × 宽高比平衡系数。

    Args:
        width: 图片宽度
        height: 图片高度
        data_size: 文件大小（字节）

    Returns:
        评分值
    """
    if width < IMAGE_MIN_WIDTH or height < IMAGE_MIN_HEIGHT:
        return -1

    aspect = width / height
    resolution = width * height
    score = float(resolution)

    # 极端宽高比惩罚
    if aspect > IMAGE_MAX_ASPECT_RATIO or aspect < IMAGE_MIN_ASPECT_RATIO:
        score *= 0.5

    # 来源可靠性与版权风险
    src_mul = _copyright_source_multiplier(url)
    if src_mul < 0:
        return -1
    score *= src_mul

    # 与检索词相关性（按 URL token 粗略匹配）
    score *= _query_relevance_multiplier(url, query)

    return score


def fetch_and_select_best(
    urls: List[str],
    max_candidates: int = IMAGE_SEARCH_MAX_CANDIDATES,
    query: str = "",
) -> Optional[CandidateImage]:
    """从 URL 列表中下载并择优选择最佳图片。

    Args:
        urls: 候选图片 URL 列表
        max_candidates: 最多评估的图片数量

    Returns:
        最佳候选图片，或 None
    """
    try:
        import requests
        from PIL import Image
    except ImportError as e:
        log.error(f"缺少依赖: {e}")
        return None

    log.info(f"评估 {len(urls)} 张候选图片（最多评分 {max_candidates} 张）...")
    best: Optional[CandidateImage] = None
    scored_count = 0       # 成功评分的图片数量
    download_attempts = 0  # 总下载尝试次数
    max_download_attempts = max_candidates * 5  # 下载失败重试上限

    # 优先直接图片 URL
    urls.sort(
        key=lambda x: 0 if any(x.lower().endswith(ext) for ext in [".jpg", ".png", ".jpeg"]) else 1
    )

    for url in urls:
        # [P1-4] 分离两个退出条件：够多评分图 或 够多下载尝试
        if scored_count >= max_candidates:
            break
        if download_attempts >= max_download_attempts:
            break

        try:
            time.sleep(random.uniform(1.0, 2.0))
            if _copyright_source_multiplier(url) < 0:
                log.warning(f"跳过高版权风险来源: {url}")
                continue

            resp = requests.get(url, headers=_get_http_headers(), timeout=10)

            if resp.status_code == 429:
                log.warning("限速，等待 10 秒...")
                time.sleep(10)
                resp = requests.get(url, headers=_get_http_headers(), timeout=10)

                if resp.status_code != 200:
                    continue

            download_attempts += 1
            img_data = resp.content

            try:
                img = Image.open(BytesIO(img_data))
                width, height = img.size
                s = score_image(width, height, len(img_data), url=url, query=query)

                if s < 0:
                    continue

                log.info(f"  {width}x{height}, {len(img_data)/1024:.1f}KB, 评分: {s:.0f}")

                scored_count += 1

                if best is None or s > best.score:
                    best = CandidateImage(
                        url=url,
                        data=img_data,
                        width=width,
                        height=height,
                        score=s,
                        format="png" if img.format == "PNG" else "jpg",
                    )

            except Exception:
                continue

        except Exception as e:
            log.warning(f"下载失败 ({url}): {e}")

    return best


def convert_to_rgb_png(src: Path, dst: Path):
    """将图片转换为 RGB PNG 格式。

    Args:
        src: 源图片路径
        dst: 目标 PNG 路径
    """
    try:
        from PIL import Image
    except ImportError:
        log.error("缺少 Pillow 依赖")
        return

    src = Path(src)
    dst = Path(dst)

    try:
        img = Image.open(str(src))
        log.info(f"转换图片: {src.name} (格式={img.format}, 模式={img.mode})")

        if img.mode != "RGB":
            img = img.convert("RGB")

        dst.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(dst), "PNG")
        log.info(f"已保存: {dst}")

    except Exception as e:
        log.error(f"图片转换失败 ({src.name}): {e}")
