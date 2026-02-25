import os
import shutil
import zipfile
import json
from pathlib import Path
from typing import Optional, Dict, Any
from config.settings import settings

class FileHandler:
    @staticmethod
    def extract_zip(zip_path: str) -> str:
        """
        解压 Zip 文件到临时目录
        :param zip_path: Zip 文件路径
        :return: 解压后的临时目录路径
        """
        zip_path_obj = Path(zip_path)
        if not zip_path_obj.exists():
            raise FileNotFoundError(f"Zip file not found: {zip_path}")

        # 创建唯一的临时目录 (使用文件名 + 时间戳 或者 简单点直接用 settings 定义的)
        # 这里为了演示简单，使用 settings.TEMP_DIR 下的子目录
        temp_dir = Path(settings.TEMP_DIR) / zip_path_obj.stem
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        return str(temp_dir)

    @staticmethod
    def find_main_json(directory: str) -> str:
        """
        在目录中查找主要的想定 JSON 文件
        :param directory: 目录路径
        :return: JSON 文件路径
        """
        # 假设根目录下有一个 json 文件，或者根据具体规则查找
        # 这里简单策略：查找根目录下第一个 .json 文件
        dir_path = Path(directory)
        json_files = list(dir_path.glob("*.json"))
        
        if not json_files:
            # 尝试递归查找
            json_files = list(dir_path.rglob("*.json"))
            
        if not json_files:
            raise FileNotFoundError(f"No JSON file found in {directory}")
            
        # 优先返回根目录下的
        # 实际逻辑可能需要更复杂的匹配，比如文件名包含 "想定"
        return str(json_files[0])

    @staticmethod
    def load_json(json_path: str) -> Dict[str, Any]:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def cleanup(directory: str):
        """清理临时目录"""
        path = Path(directory)
        if path.exists():
            shutil.rmtree(path)

    @staticmethod
    def check_files_exist(directory: str, filenames: list[str]) -> list[str]:
        """检查文件是否存在，返回缺失的文件列表"""
        missing = []
        dir_path = Path(directory)
        for fname in filenames:
            # 简单检查：假设文件就在根目录，或者是相对路径
            # 如果资源在子目录，这里需要更复杂的逻辑
            if not (dir_path / fname).exists():
                # 尝试递归查找
                found = list(dir_path.rglob(fname))
                if not found:
                    missing.append(fname)
        return missing
