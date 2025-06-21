#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小说爬虫和导出工具
支持运行爬虫和导出小说为不同格式
"""

import argparse
import sys
import os
import subprocess
import platform
import logging
from pathlib import Path
from typing import Optional, Tuple


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class VenvManager:
    """虚拟环境管理器"""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.system = platform.system().lower()
        self.is_windows = self.system == "windows"
        
    def get_venv_paths(self) -> Tuple[Path, Path]:
        """获取虚拟环境路径"""
        if self.is_windows:
            venv_activate = self.base_dir / "venv" / "Scripts" / "activate.bat"
            python_exe = self.base_dir / "venv" / "Scripts" / "python.exe"
        else:
            venv_activate = self.base_dir / "venv" / "bin" / "activate"
            python_exe = self.base_dir / "venv" / "bin" / "python"
        
        return venv_activate, python_exe
    
    def check_venv(self, check_python: bool = True) -> bool:
        """检查虚拟环境是否存在"""
        venv_activate, python_exe = self.get_venv_paths()
        
        if not venv_activate.exists():
            logger.error(f"虚拟环境未找到: {venv_activate}")
            return False
            
        if check_python and not python_exe.exists():
            logger.error(f"Python可执行文件未找到: {python_exe}")
            return False
            
        return True
    
    def build_command(self, command: str, check_python: bool = True) -> Tuple[str, bool, Optional[str]]:
        """构建执行命令"""
        if not self.check_venv(check_python):
            return "", False, None
            
        venv_activate, _ = self.get_venv_paths()
        
        if self.is_windows:
            full_command = f'cmd /c "{venv_activate} && cd /d {self.base_dir} && {command}"'
            shell_flag = True
            executable = None
        else:
            full_command = f"source {venv_activate} && cd {self.base_dir} && {command}"
            shell_flag = True
            executable = "/bin/bash"
            
        return full_command, shell_flag, executable


class SpiderRunner:
    """爬虫运行器"""
    
    def __init__(self, base_dir: str):
        self.venv_manager = VenvManager(base_dir)
        
    def run_spider(self, spider_name: str, local: bool = False) -> bool:
        """运行爬虫"""
        logger.info(f"开始运行爬虫: {spider_name}")
        
        # 验证爬虫名称
        valid_spiders = [
            "auto_novel_top100",
            "auto_novel_top100_postgre",
            # "free_novel_top100",
            # "novel_chapter_list", 
            # "novel_all_chapters",
        ]
        
        if spider_name not in valid_spiders:
            logger.error(f"无效的爬虫名称: {spider_name}")
            logger.info(f"可用的爬虫: {', '.join(valid_spiders)}")
            return False
        
        # 构建命令
        local_arg = " -a local=1" if local else ""
        command = f"scrapy crawl {spider_name}{local_arg}"
        
        full_command, shell_flag, executable = self.venv_manager.build_command(command, check_python=False)
        if not full_command:
            return False
            
        return CommandExecutor._execute_command(full_command, shell_flag, executable, "爬虫")


class EbookExporter:
    """电子书导出器"""
    
    def __init__(self, base_dir: str):
        self.venv_manager = VenvManager(base_dir)
        
    def export_ebooks(self, format_type: str) -> bool:
        """导出电子书"""
        logger.info(f"开始导出电子书，格式: {format_type}")
        
        # 验证格式
        valid_formats = ["epub", "txt"]
        if format_type not in valid_formats:
            logger.error(f"无效的导出格式: {format_type}")
            logger.info(f"支持的格式: {', '.join(valid_formats)}")
            return False
        
        # 检查导出脚本是否存在
        export_script = self.venv_manager.base_dir / "run_export_to_ebooks.py"
        if not export_script.exists():
            logger.error(f"导出脚本未找到: {export_script}")
            return False
        
        # 构建命令
        command = f"python run_export_to_ebooks.py --format {format_type}"
        
        full_command, shell_flag, executable = self.venv_manager.build_command(command)
        if not full_command:
            return False
            
        return CommandExecutor._execute_command(full_command, shell_flag, executable, "导出")


class CommandExecutor:
    """命令执行器"""
    
    @staticmethod
    def _execute_command(command: str, shell: bool, executable: Optional[str], operation_name: str) -> bool:
        """执行命令"""
        logger.info(f"执行命令: {command}")
        
        try:
            result = subprocess.run(
                command,
                shell=shell,
                executable=executable,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            # 输出命令结果
            if result.stdout:
                logger.info(f"{operation_name}输出:\n{result.stdout}")
            if result.stderr:
                logger.warning(f"{operation_name}警告:\n{result.stderr}")
            
            if result.returncode == 0:
                logger.info(f"{operation_name}完成。")
                return True
            else:
                logger.error(f"{operation_name}失败，返回码: {result.returncode}")
                return False
                
        except Exception as e:
            logger.error(f"执行{operation_name}时发生错误: {e}")
            return False


class NovelTool:
    """小说工具主类"""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.spider_runner = SpiderRunner(self.base_dir)
        self.ebook_exporter = EbookExporter(self.base_dir)
        
    def run_spider(self, spider_name: str, local: bool = False) -> bool:
        """运行爬虫"""
        return self.spider_runner.run_spider(spider_name, local)
        
    def export_ebooks(self, format_type: str) -> bool:
        """导出电子书"""
        return self.ebook_exporter.export_ebooks(format_type)
        
    def show_help(self):
        """显示帮助信息"""
        print("""
小说爬虫和导出工具

使用方法:
  python run.py crawl <spider_name> [--local]    运行爬虫
  python run.py export <format>                  导出小说

爬虫选项:
  auto_novel_top100              - 自动爬取小说TOP100
  auto_novel_top100_postgre      - 自动爬取小说TOP100 (PostgreSQL)

导出格式:
  txt                           - 导出为TXT文本文件
  epub                          - 导出为EPUB电子书

示例:
  python run.py crawl auto_novel_top100
  python run.py crawl auto_novel_top100_postgre --local
  python run.py export txt
  python run.py export epub
        """)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="小说爬虫和导出工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s crawl auto_novel_top100
  %(prog)s crawl auto_novel_top100_postgre --local
  %(prog)s export txt
  %(prog)s export epub
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 爬虫命令
    crawl_parser = subparsers.add_parser("crawl", help="运行爬虫")
    crawl_parser.add_argument(
        "spider",
        choices=[
            "auto_novel_top100",
            "auto_novel_top100_postgre",
        ],
        help="爬虫名称"
    )
    crawl_parser.add_argument(
        "--local", 
        action="store_true", 
        help="传递local=1参数"
    )
    
    # 导出命令
    export_parser = subparsers.add_parser("export", help="导出小说")
    export_parser.add_argument(
        "format", 
        choices=["epub", "txt"], 
        help="导出格式"
    )
    
    args = parser.parse_args()
    
    # 创建工具实例
    tool = NovelTool()
    
    # 执行命令
    success = False
    if args.command == "crawl":
        success = tool.run_spider(args.spider, local=args.local)
    elif args.command == "export":
        success = tool.export_ebooks(args.format)
    else:
        tool.show_help()
        return
    
    # 退出状态
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
