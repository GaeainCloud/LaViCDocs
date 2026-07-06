"""
AIAgentData 统一日志模块
替代项目中散落的 print() 调用，提供分级日志和文件输出能力。
"""
import logging
import sys
from pathlib import Path


def get_logger(name: str, level: int = logging.INFO, log_file: Path = None) -> logging.Logger:
    """获取命名日志器。

    Args:
        name: 日志器名称（通常为模块名）
        level: 日志级别
        log_file: 可选的日志文件路径

    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(level)
    # [P2-6] 防止日志重复输出到 root logger
    logger.propagate = False

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    ))
    logger.addHandler(console_handler)

    # 可选文件输出
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(file_handler)

    return logger
