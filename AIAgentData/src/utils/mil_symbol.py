"""
军标生成共享模块
从 gen_mil_symbols.py 和 generate_vehicle_packages.py 中提取的重复逻辑。
生成 NATO APP-6(D) 标准军标 PNG 文件。
"""
from pathlib import Path
from typing import Optional

from logger import get_logger

log = get_logger(__name__)


def generate_military_symbol(
    name: str,
    symbol_desc: str,
    output_dir: Path,
    fallback_desc: str = "Friendly Unmanned Aerial Vehicle",
) -> Optional[str]:
    """生成 NATO APP-6(D) 军标 PNG。

    Args:
        name: 模型名称（用于文件命名）
        symbol_desc: NATO 符号描述（如 "Friendly Fighter"）
        output_dir: PNG 输出目录
        fallback_desc: 当 symbol_desc 无法生成时的回退描述

    Returns:
        生成的 PNG 文件名（如 "ModelName_mil.png"），失败返回 None
    """
    try:
        import military_symbol
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
    except ImportError as e:
        log.error(f"缺少依赖: {e}。请运行: pip install military-symbol svglib reportlab")
        return None

    log.info(f"生成军标: {name} ({symbol_desc})")

    try:
        svg_string = military_symbol.get_symbol_svg_string_from_name(
            symbol_desc, style="light", bounding_padding=4, use_variants=True
        )

        if svg_string is None:
            log.warning(f"无法生成 '{symbol_desc}' 的军标，回退到 '{fallback_desc}'")
            svg_string = military_symbol.get_symbol_svg_string_from_name(
                fallback_desc, style="light", bounding_padding=4, use_variants=True
            )

        if svg_string is None:
            log.error(f"回退描述 '{fallback_desc}' 也无法生成军标")
            return None

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存临时 SVG
        svg_filename = f"{name}_mil.svg"
        svg_path = output_dir / svg_filename
        svg_path.write_text(svg_string, encoding="utf-8")

        # SVG → PNG 转换
        png_filename = f"{name}_mil.png"
        png_path = output_dir / png_filename

        drawing = svg2rlg(str(svg_path))
        renderPM.drawToFile(drawing, str(png_path), fmt="PNG")

        # 清理临时 SVG
        svg_path.unlink(missing_ok=True)

        log.info(f"军标已保存: {png_path}")
        return png_filename

    except Exception as e:
        log.error(f"军标生成失败 ({name}): {e}")
        return None
