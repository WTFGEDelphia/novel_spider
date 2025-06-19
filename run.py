import argparse
import sys
import os
import subprocess
import platform


def run_spider(spider_name, local=False):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    system = platform.system().lower()
    if system == "windows":
        venv_activate = os.path.join(base_dir, "venv", "Scripts", "activate.bat")
        scrapy_exe = os.path.join(base_dir, "venv", "Scripts", "scrapy.exe")
        if not os.path.exists(venv_activate) or not os.path.exists(scrapy_exe):
            print("虚拟环境或scrapy未找到")
            sys.exit(1)
        local_arg = " -a local=1" if local else ""
        command = f'cmd /c "{venv_activate} && cd /d {base_dir} && scrapy crawl {spider_name}{local_arg}"'
        shell_flag = True
        executable_flag = None
    else:
        venv_activate = os.path.join(base_dir, "venv", "bin", "activate")
        if not os.path.exists(venv_activate):
            print("虚拟环境未找到")
            sys.exit(1)
        local_arg = " -a local=1" if local else ""
        command = f"source {venv_activate} && cd {base_dir} && scrapy crawl {spider_name}{local_arg}"
        shell_flag = True
        executable_flag = "/bin/bash"
    print(f"运行命令: {command}")
    result = subprocess.run(command, shell=shell_flag, executable=executable_flag)
    if result.returncode == 0:
        print("爬虫运行完成。")
    else:
        print("爬虫运行失败。")


def export_ebooks(format):
    import run_export_to_ebooks

    run_export_to_ebooks.main(format=format)


def main():
    parser = argparse.ArgumentParser(description="一键运行爬虫和导出工具")
    subparsers = parser.add_subparsers(dest="command")

    crawl_parser = subparsers.add_parser("crawl", help="运行爬虫")
    crawl_parser.add_argument(
        "spider",
        choices=[
            "auto_novel_top100",
            "auto_novel_top100_postgre",
            "free_novel_top100",
            "novel_chapter_list",
            "novel_all_chapters",
        ],
    )
    crawl_parser.add_argument("--local", action="store_true", help="传递local=1参数")

    export_parser = subparsers.add_parser("export", help="导出小说")
    export_parser.add_argument("format", choices=["epub", "txt"], help="导出格式")

    args = parser.parse_args()

    if args.command == "crawl":
        run_spider(args.spider, local=args.local)
    elif args.command == "export":
        export_ebooks(args.format)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
