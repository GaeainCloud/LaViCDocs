from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from utils.image_utils import score_image


def test_score_image_blocks_high_copyright_risk_domains():
    s = score_image(
        width=1200,
        height=800,
        data_size=100000,
        url="https://www.shutterstock.com/some-image.jpg",
        query="fighter aircraft",
    )
    assert s == -1


def test_score_image_prefers_permissive_sources():
    preferred = score_image(
        width=1200,
        height=800,
        data_size=100000,
        url="https://upload.wikimedia.org/wikipedia/commons/a/a1/test.jpg",
        query="fighter aircraft",
    )
    neutral = score_image(
        width=1200,
        height=800,
        data_size=100000,
        url="https://example.com/images/test.jpg",
        query="fighter aircraft",
    )
    assert preferred > neutral


def test_score_image_query_relevance_bonus():
    with_hit = score_image(
        width=1200,
        height=800,
        data_size=100000,
        url="https://example.com/images/f22_raptor_fighter.jpg",
        query="F22 fighter",
    )
    without_hit = score_image(
        width=1200,
        height=800,
        data_size=100000,
        url="https://example.com/images/random_vehicle.jpg",
        query="F22 fighter",
    )
    assert with_hit > without_hit
