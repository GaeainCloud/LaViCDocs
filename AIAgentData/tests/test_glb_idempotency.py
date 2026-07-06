from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from utils.glb_utils import is_rotation_applied, mark_rotation_applied


def test_rotation_marker_is_file_scoped(tmp_path):
    a = tmp_path / "a.glb"
    b = tmp_path / "b.glb"
    a.write_bytes(b"glb-a")
    b.write_bytes(b"glb-b")

    assert not is_rotation_applied(a)
    assert not is_rotation_applied(b)

    mark_rotation_applied(a)
    assert is_rotation_applied(a)
    assert not is_rotation_applied(b)
