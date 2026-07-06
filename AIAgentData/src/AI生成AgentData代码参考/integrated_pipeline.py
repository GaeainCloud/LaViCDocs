"""
AI 参考代码到主流水线的桥接入口。
避免 LangGraph 节点流与 src/pipeline.py 两套体系分离。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import Pipeline


def main():
    parser = argparse.ArgumentParser(description="Bridge to unified LaViC pipeline")
    parser.add_argument("--name", required=True, help="模型名称")
    parser.add_argument("--type", required=True, help="类型关键词（支持中文/英文）")
    parser.add_argument("--desc", default="", help="描述")
    parser.add_argument("--steps", help="步骤列表（如 1,2,3,4,5,6）")
    parser.add_argument("--sidc", default="default", help="SIDC 子类型")
    args = parser.parse_args()

    steps = [int(s) for s in args.steps.split(",")] if args.steps else None
    pipeline = Pipeline(args.name, args.type, args.desc, steps=steps, sidc_subtype=args.sidc)
    ok = pipeline.run()
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
