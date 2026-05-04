import os
import sys
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Union, List, Dict, Any
from loguru import logger
from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv())


class FileUtils:
    """
    全能文件与路径处理工具类
    支持工程根目录自动识别、智能拼接、安全读写与截图管理
    """

    # --- 1. 路径核心定位 (支持 PYTHONPATH 与 Main 启动路径) ---

    @staticmethod
    def get_project_root() -> Path:
        """
        获取工程根目录：
        1. 优先从环境变量 PYTHONPATH 中获取 (支持 .env 注入)
        2. 备选：获取当前启动文件 (Main) 所在的目录
        """
        # 尝试从环境变量获取
        python_path = os.getenv("PYTHONPATH")
        if python_path:
            root = python_path.split(os.pathsep)[0]
            if os.path.exists(root):
                return Path(root).resolve()

        # 自动识别启动入口路径 (sys.path[0] 通常是启动脚本所在的目录)
        main_dir = sys.path[0] if (sys.path and sys.path[0]) else os.getcwd()
        return Path(main_dir).resolve()

    @staticmethod
    def get_path(*path_parts: str, ensure_dir: bool = False) -> str:
        """
        基于工程根目录生成完整路径 (不创建文件)
        示例: get_path("images", "screenshots", "1.jpg") -> E:/root/images/screenshots/1.jpg
        """
        root = FileUtils.get_project_root()
        # 处理掉每段路径首尾的斜杠，确保拼接安全
        clean_parts = [p.strip("\\/") for p in path_parts]
        full_path = root.joinpath(*clean_parts)
        if ensure_dir:
            FileUtils.ensure_dir(full_path)
        return str(full_path)

    # --- 2. 目录与文件状态 ---

    @staticmethod
    def ensure_dir(path_str: str) -> str:
        """确保目录存在，如果是文件路径则创建其父目录"""
        path = Path(path_str)
        if path.suffix:  # 看起来像文件 (有后缀)
            path.parent.mkdir(parents=True, exist_ok=True)
        else:            # 看起来像目录
            path.mkdir(parents=True, exist_ok=True)
        return str(path.resolve())

    @staticmethod
    def exists(path_str: str) -> bool:
        """判断文件或目录是否存在"""
        return Path(path_str).exists()

    @staticmethod
    def get_unique_path(path_str: str) -> str:
        """如果文件已存在，自动重命名防止覆盖 (如 test_1.png, test_2.png)"""
        path = Path(path_str)
        if not path.exists():
            return str(path)
        
        parent = path.parent
        stem = path.stem
        suffix = path.suffix
        counter = 1
        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return str(new_path)
            counter += 1

    # --- 3. 针对截图与下载的增强功能 ---

    @staticmethod
    def get_timestamp_file(dir_name: str, prefix: str = "file", ext: str = ".png") -> str:
        """
        生成带时间戳的路径（自动创建目录）
        结果: E:/root/dir_name/prefix_20231027_120001.png
        """
        target_dir = FileUtils.get_path(dir_name)
        FileUtils.ensure_dir(target_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return str(Path(target_dir) / f"{prefix}_{timestamp}{ext}")

    # --- 4. 文件读写与 IO ---

    @staticmethod
    def read_text(path: str, encoding: str = 'utf-8') -> str:
        """读取文本文件"""
        return Path(path).read_text(encoding=encoding)

    @staticmethod
    def write_text(path: str, content: str, append: bool = False, encoding: str = 'utf-8'):
        """写入文本文件"""
        FileUtils.ensure_dir(path)
        mode = 'a' if append else 'w'
        with open(path, mode, encoding=encoding) as f:
            f.write(content)

    @staticmethod
    def read_json(path: str) -> Union[Dict, List]:
        """读取 JSON 文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"文件 {path} 不存在")
            return None
        except json.JSONDecodeError:
            logger.error(f"文件 {path} 内容不是有效的 JSON 格式")
            return None

    @staticmethod
    def write_json(path: str, data: Any, indent: int = 4):
        """写入 JSON 文件"""
        try:
            FileUtils.ensure_dir(path)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
        except IOError as e:
            logger.error(f"写入文件 {path} 时发生错误: {e}")

    # --- 5. 文件操作 (移动/复制/删除) ---

    @staticmethod
    def delete(path_str: str):
        """安全删除文件或目录"""
        path = Path(path_str)
        if not path.exists():
            return
        if path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path_str)

    @staticmethod
    def get_md5(path_str: str) -> str:
        """计算文件的 MD5 值 (用于校验下载是否完整)"""
        hash_md5 = hashlib.md5()
        with open(path_str, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

# --- 测试用例 (仅在直接运行此文件时执行) ---
if __name__ == "__main__":
    # 模拟在工程中生成截图路径
    shot_path = FileUtils.get_path("images", "new_img.jpg")
    print(f"生成的完整路径: {shot_path}")
    
    # 自动生成不重复的名称
    unique = FileUtils.get_unique_path(shot_path)
    print(f"唯一路径建议: {unique}")
    
    # 时间戳截图路径
    ts_path = FileUtils.get_timestamp_file("screenshots", prefix="login_page")
    print(f"时间戳路径: {ts_path}")
