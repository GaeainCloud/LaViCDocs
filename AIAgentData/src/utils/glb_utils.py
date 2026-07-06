"""
GLB 3D 模型处理共享模块
合并 fix_glb_rotation.py、process_glbs.py、rotate_glbs_z180.py 的逻辑。
包含：坐标系转换、朝向修正、幂等性保障。
"""
from pathlib import Path
from typing import Optional

from logger import get_logger
from config import GLB_ROTATION_MARKER

log = get_logger(__name__)


def _rotation_marker_path(target_glb: Path) -> Path:
    """根据 GLB 文件路径生成对应的幂等性标记文件路径。"""
    target_glb = Path(target_glb)
    return target_glb.with_name(f"{target_glb.name}{GLB_ROTATION_MARKER}")


def is_rotation_applied(target_glb: Path) -> bool:
    """检查指定 GLB 是否已应用旋转变换。

    Args:
        target_glb: 目标 GLB 文件路径

    Returns:
        True 如果已存在旋转标记文件
    """
    marker = _rotation_marker_path(target_glb)
    return marker.exists()


def mark_rotation_applied(target_glb: Path):
    """写入幂等性标记文件。

    Args:
        target_glb: 目标 GLB 文件路径
    """
    marker = _rotation_marker_path(target_glb)
    marker.write_text("Rotation applied: Z-Up→Y-Up (-90°X) + Facing (180°Y)\n", encoding="utf-8")
    log.info(f"写入旋转标记: {marker}")


def rotate_glb_to_yup(
    src: Path,
    dst: Path,
    force: bool = False,
) -> bool:
    """Z-Up → Y-Up 坐标转换 + 朝向修正。

    执行两步旋转：
    1. 绕 X 轴旋转 -90°（Z-Up → Y-Up）
    2. 绕 Y 轴旋转 180°（朝向修正）

    Args:
        src: 源 GLB 文件路径
        dst: 目标 GLB 文件路径
        force: True 则忽略幂等性标记强制执行

    Returns:
        True 表示成功处理，False 表示跳过或失败
    """
    try:
        import trimesh
        import numpy as np
    except ImportError as e:
        log.error(f"缺少依赖: {e}。请运行: pip install trimesh numpy")
        return False

    src = Path(src)
    dst = Path(dst)

    if not src.exists():
        log.error(f"源文件不存在: {src}")
        return False

    # 幂等性检查
    if not force and is_rotation_applied(dst):
        log.info(f"跳过 {dst.name}: 旋转已应用（使用 force=True 强制执行）")
        return False

    log.info(f"处理 GLB: {src.name} → {dst.name}")

    try:
        scene = trimesh.load(str(src), force="scene")

        # 步骤1: Z-Up → Y-Up（绕 X 轴旋转 -90°）
        rot_x = trimesh.transformations.rotation_matrix(
            np.radians(-90), [1, 0, 0]
        )
        scene.apply_transform(rot_x)

        # 步骤2: 朝向修正（绕 Y 轴旋转 180°）
        rot_y = trimesh.transformations.rotation_matrix(
            np.radians(180), [0, 1, 0]
        )
        scene.apply_transform(rot_y)

        # 确保目标目录存在
        dst.parent.mkdir(parents=True, exist_ok=True)

        # 导出（使用非弃用 API）
        scene.export(str(dst), file_type="glb")

        # 写入幂等性标记
        mark_rotation_applied(dst)

        log.info(f"GLB 旋转完成: {dst}")
        return True

    except Exception as e:
        log.error(f"GLB 处理失败 ({src.name}): {e}")
        return False


def rotate_glb_y180(src: Path, dst: Optional[Path] = None) -> bool:
    """仅执行 Y 轴 180° 朝向修正（不做 Z-Up→Y-Up 转换）。

    Args:
        src: 源 GLB 文件路径
        dst: 目标路径，默认覆盖原文件

    Returns:
        True 表示成功
    """
    try:
        import trimesh
        import numpy as np
    except ImportError as e:
        log.error(f"缺少依赖: {e}。请运行: pip install trimesh numpy")
        return False

    src = Path(src)
    if dst is None:
        dst = src

    if not src.exists():
        log.error(f"源文件不存在: {src}")
        return False

    log.info(f"Y180 旋转: {src.name}")

    try:
        scene = trimesh.load(str(src), force="scene")

        matrix = np.eye(4)
        matrix[0, 0] = -1
        matrix[2, 2] = -1
        scene.apply_transform(matrix)

        scene.export(str(dst), file_type="glb")
        log.info(f"Y180 旋转完成: {dst}")
        return True

    except Exception as e:
        log.error(f"Y180 旋转失败 ({src.name}): {e}")
        return False
