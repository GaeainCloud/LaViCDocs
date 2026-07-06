"""
LaViC 模型生成流水线 - 统一编排器
从自然语言描述到最终 ZIP 包的全自动化六步流水线。

CLI 用法:
    python pipeline.py --name "F-22_Raptor" --type aircraft --desc "第五代隐身战斗机"
    python pipeline.py --name "F-22_Raptor" --type aircraft --steps 1,2,3
    python pipeline.py --interactive

交互式用法:
    python pipeline.py --interactive
"""
import argparse
import copy
import json
import shutil
import uuid
from pathlib import Path

from config import (
    MODELS_DIR, DOWNLOADS_DIR, TEMPLATE_MAP, DYNAMICS_MAP,
    SCHEMA_PATH, DEFAULT_GLB_SUFFIX, DEFAULT_MIL_SUFFIX,
    resolve_agent_type, get_sidc,
)
from logger import get_logger
from utils.mil_symbol import generate_military_symbol
from utils.glb_utils import rotate_glb_to_yup
from utils.image_utils import fetch_and_select_best, scrape_images_from_page
from utils.package_utils import fix_agent_json_paths, create_flat_zip, validate_package

log = get_logger("pipeline")

STEP_NAMES = {
    1: "模型定义与 JSON 生成",
    2: "资产获取与生成",
    3: "资产标准化处理",
    4: "目录结构与配置",
    5: "最终打包",
    6: "验收检查",
}


def apply_dynamics_rule(agent: dict, agent_type: str) -> str:
    """按 agent_type 强制应用动力学插件映射。"""
    plugin = DYNAMICS_MAP.get(agent_type, "")
    if not plugin:
        return ""

    dyn_list = agent.get("missionableDynamics")
    if isinstance(dyn_list, list) and dyn_list:
        dyn = dyn_list[0]
        if isinstance(dyn, dict):
            dyn["dynPluginName"] = plugin
            dyn["dynKeyword"] = plugin
            dyn_settings = dyn.get("dynSettings")
            if isinstance(dyn_settings, dict):
                dyn_settings["pluginName"] = plugin
            return plugin

    # 模板缺失 missionableDynamics 时，生成最小可用结构
    agent["missionableDynamics"] = [{
        "dynPluginName": plugin,
        "dynKeyword": plugin,
        "dynAsDefault": True,
        "dynSettings": {
            "pluginName": plugin,
        },
    }]
    return plugin


class Pipeline:
    """LaViC 模型生成流水线。"""

    def __init__(self, model_name: str, agent_type: str, description: str,
                 steps: list = None, sidc_subtype: str = "default"):
        self.model_name = model_name
        self.agent_type = resolve_agent_type(agent_type)
        self.description = description
        self.steps = steps or [1, 2, 3, 4, 5, 6]
        self.sidc_subtype = sidc_subtype

        # 工作目录
        self.model_dir = MODELS_DIR / model_name
        self.assets_dir = self.model_dir / model_name
        self.json_path = self.model_dir / "agent.json"
        self.zip_path = MODELS_DIR / f"{model_name}.zip"

    def run(self):
        """执行选定的流水线步骤。"""
        log.info(f"=== 流水线启动: {self.model_name} (类型: {self.agent_type}) ===")

        step_map = {
            1: self.step1_generate_json,
            2: self.step2_acquire_assets,
            3: self.step3_standardize_assets,
            4: self.step4_structure_and_config,
            5: self.step5_package,
            6: self.step6_verify,
        }

        for step in self.steps:
            if step not in step_map:
                log.warning(f"未知步骤: {step}，跳过")
                continue

            log.info(f"\n--- 步骤 {step}: {STEP_NAMES[step]} ---")
            try:
                step_map[step]()
                log.info(f"步骤 {step} 完成")
            except Exception as e:
                log.error(f"步骤 {step} 失败: {e}")
                log.error("流水线中止。请检查错误后重试。")
                return False

        log.info(f"\n=== 流水线完成: {self.model_name} ===")
        return True

    def step1_generate_json(self):
        """模板选择 + JSON 生成 + Schema 校验。"""
        template_path = TEMPLATE_MAP.get(self.agent_type)
        if not template_path or not template_path.exists():
            raise FileNotFoundError(f"模板文件不存在: {template_path}")

        with open(template_path, "r", encoding="utf-8") as f:
            template_data = json.load(f)

        # 深拷贝模板
        agent_data = copy.deepcopy(template_data)
        if isinstance(agent_data, list):
            agent = agent_data[0]
        else:
            agent = agent_data
            agent_data = [agent]

        # 填充字段
        agent["agentKey"] = f"AGENTKEY_{uuid.uuid4().int}"
        agent["agentName"] = self.model_name
        agent["agentNameI18n"] = self.model_name
        agent["agentDesc"] = self.description

        # 动力学规则映射（降低对 LLM 选择的依赖）
        applied_plugin = apply_dynamics_rule(agent, self.agent_type)
        if applied_plugin:
            log.info(f"已应用动力学插件: {applied_plugin}")

        # 确保目录存在
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # 保存 JSON
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(agent_data, f, ensure_ascii=False, indent=2)

        log.info(f"JSON 生成: {self.json_path}")

        # [P2-4] Schema 校验 — 警告但不中止（与 skill.md 对齐）
        if SCHEMA_PATH.exists():
            try:
                from jsonschema import Draft7Validator

                with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                    schema = json.load(f)

                validator = Draft7Validator(schema)
                errors = list(validator.iter_errors(agent_data))
                if errors:
                    log.warning(f"Schema 校验发现 {len(errors)} 个问题（警告，不影响继续）:")
                    for err in errors[:3]:
                        log.warning(f"  {err.message}")
                else:
                    log.info("Schema 校验通过")
            except ImportError:
                log.warning("jsonschema 未安装，跳过校验")

    def step2_acquire_assets(self):
        """缩略图搜索 (3-5张候选→评分择优) + 军标生成 + 3D 模型获取。"""
        self.assets_dir.mkdir(parents=True, exist_ok=True)

        # 1. 缩略图（优先级：downloads 预下载 > Web 搜索 > 提示手动处理）
        png_name = f"{self.model_name}.png"
        png_path = self.assets_dir / png_name
        downloaded_png = DOWNLOADS_DIR / f"{self.model_name}.png"

        if downloaded_png.exists():
            log.info(f"使用已下载的缩略图: {downloaded_png}")
            shutil.copy(downloaded_png, png_path)
        elif not png_path.exists():
            # 尝试自动搜索：抓取 Wikipedia 页面候选图 → 评分择优
            search_query = self.model_name.replace("_", " ")
            wiki_url = f"https://en.wikipedia.org/wiki/{self.model_name}"
            log.info(f"自动搜索缩略图: {search_query} (from {wiki_url})")
            try:
                candidate_urls = scrape_images_from_page(wiki_url)
                if candidate_urls:
                    best = fetch_and_select_best(candidate_urls, query=search_query)
                    if best:
                        png_path.write_bytes(best.data)
                        log.info(f"已保存最佳缩略图: {png_path} "
                                 f"({best.width}x{best.height}, 评分: {best.score:.0f})")
                    else:
                        log.warning("候选图均不合格，请手动放入 "
                                    f"models/downloads/{self.model_name}.png 后重新运行步骤 2")
                else:
                    log.warning(f"未从 {wiki_url} 抓取到候选图片")
            except Exception as e:
                log.warning(f"缩略图搜索失败: {e}。"
                            f"请手动放入 models/downloads/{self.model_name}.png")

        # 2. 军标（优先级：assets 已存在 > downloads 预下载 > 动态生成）
        mil_name = f"{self.model_name}{DEFAULT_MIL_SUFFIX}"
        mil_path = self.assets_dir / mil_name
        downloaded_mil = DOWNLOADS_DIR / mil_name

        if mil_path.exists():
            log.info(f"军标已存在: {mil_path}")
        elif downloaded_mil.exists():
            log.info(f"使用已下载的军标: {downloaded_mil}")
            shutil.copy(downloaded_mil, mil_path)
        else:
            symbol_desc = get_sidc(self.agent_type, self.sidc_subtype)
            generate_military_symbol(self.model_name, symbol_desc, self.assets_dir)

        # 3. 3D 模型
        glb_name = f"{self.model_name}{DEFAULT_GLB_SUFFIX}"
        glb_path = self.assets_dir / glb_name
        # 优先级：带后缀的 > 不带后缀的
        downloaded_glb_full = DOWNLOADS_DIR / f"{self.model_name}{DEFAULT_GLB_SUFFIX}"
        downloaded_glb_plain = DOWNLOADS_DIR / f"{self.model_name}.glb"

        if glb_path.exists():
            log.info(f"GLB 已存在: {glb_path}")
        elif downloaded_glb_full.exists():
            log.info(f"使用已下载的 GLB: {downloaded_glb_full}")
            shutil.copy(downloaded_glb_full, glb_path)
        elif downloaded_glb_plain.exists():
            log.info(f"使用已下载的 GLB: {downloaded_glb_plain}")
            shutil.copy(downloaded_glb_plain, glb_path)
        else:
            log.info("暂无 3D 模型，需通过 Rodin/Blender 获取")

    def step3_standardize_assets(self):
        """3D 模型坐标系修正（带幂等性检查）。"""
        glb_name = f"{self.model_name}{DEFAULT_GLB_SUFFIX}"
        glb_path = self.assets_dir / glb_name

        if not glb_path.exists():
            log.warning(f"GLB 文件不存在，跳过旋转: {glb_path}")
            return

        rotate_glb_to_yup(glb_path, glb_path)

    def step4_structure_and_config(self):
        """目录结构验证 + JSON 路径修复。"""
        if not self.json_path.exists():
            raise FileNotFoundError(f"agent.json 不存在: {self.json_path}")

        fix_agent_json_paths(self.json_path, self.model_name)

    def step5_package(self):
        """UTF-8 ZIP 打包。"""
        if not self.model_dir.exists():
            raise FileNotFoundError(f"模型目录不存在: {self.model_dir}")

        create_flat_zip(self.model_dir, self.zip_path)

    def step6_verify(self):
        """端到端验收检查。验收失败将中止流水线。"""
        if not self.zip_path.exists():
            raise FileNotFoundError(f"ZIP 文件不存在: {self.zip_path}")

        passed, errors = validate_package(self.zip_path)
        if passed:
            log.info(f"验收通过: {self.zip_path.name}")
        else:
            # [P1-1] 验收失败必须抛异常以中止流水线
            msg = f"验收失败，发现 {len(errors)} 个问题:\n"
            for err in errors:
                msg += f"  - {err}\n"
            log.error(msg)
            raise RuntimeError(msg)


def interactive_mode():
    """交互式模式：逐步提示用户确认。[P3-4] 同时写入日志文件。"""
    print("=" * 50)
    print("  LaViC 模型生成流水线 (交互模式)")
    print("=" * 50)
    print()

    name = input("模型名称 (英文，用下划线连接): ").strip()
    if not name:
        print("错误：模型名称不能为空")
        return

    print(f"\n可用类型: {', '.join(TEMPLATE_MAP.keys())}")
    agent_type = input("Agent 类型: ").strip()

    desc = input("模型描述: ").strip()

    try:
        pipeline = Pipeline(name, agent_type, desc)
    except ValueError as e:
        print(f"错误: {e}")
        return

    log.info(f"交互模式启动: name={name}, type={agent_type}, desc={desc}")

    print(f"\n将执行以下步骤:")
    for step in pipeline.steps:
        print(f"  {step}. {STEP_NAMES[step]}")

    for step in pipeline.steps:
        print(f"\n--- 步骤 {step}: {STEP_NAMES[step]} ---")
        resp = input("按回车执行，输入 's' 跳过，输入 'q' 退出: ").strip().lower()

        if resp == "q":
            log.info("用户退出交互模式")
            print("已退出流水线")
            return
        if resp == "s":
            log.info(f"用户跳过步骤 {step}")
            print(f"跳过步骤 {step}")
            continue

        try:
            step_map = {
                1: pipeline.step1_generate_json,
                2: pipeline.step2_acquire_assets,
                3: pipeline.step3_standardize_assets,
                4: pipeline.step4_structure_and_config,
                5: pipeline.step5_package,
                6: pipeline.step6_verify,
            }
            step_map[step]()
            print(f"步骤 {step} 完成")
        except Exception as e:
            log.error(f"交互模式步骤 {step} 失败: {e}")
            print(f"步骤 {step} 失败: {e}")
            resp = input("继续下一步？(y/n): ").strip().lower()
            if resp != "y":
                return

    print("\n流水线执行完毕!")


def main():
    parser = argparse.ArgumentParser(
        description="LaViC 模型生成流水线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python pipeline.py --name F-22_Raptor --type aircraft --desc "第五代隐身战斗机"
  python pipeline.py --name TestVehicle --type vehicle --steps 1,2 --desc "测试车辆"
  python pipeline.py --interactive
        """,
    )
    parser.add_argument("--name", help="模型名称（英文，用下划线连接）")
    parser.add_argument("--type", help=f"Agent 类型: {', '.join(TEMPLATE_MAP.keys())}")
    parser.add_argument("--desc", help="模型描述", default="")
    parser.add_argument("--steps", help="执行步骤（逗号分隔，如 '1,2,3'）")
    parser.add_argument("--sidc", help="SIDC 子类型（默认 default）", default="default")
    parser.add_argument("--interactive", action="store_true", help="交互模式")

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
    elif args.name and args.type:
        steps = [int(s) for s in args.steps.split(",")] if args.steps else None
        pipeline = Pipeline(args.name, args.type, args.desc, steps, args.sidc)
        pipeline.run()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
