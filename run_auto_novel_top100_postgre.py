import os
import platform
import subprocess
import sys

def main():

    # 获取当前脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    spider_dir = base_dir

    # 判断操作系统
    system = platform.system().lower()

    if system == "windows":
        # Windows 下虚拟环境激活脚本路径
        venv_activate = os.path.abspath(os.path.join(base_dir, "venv", "Scripts", "activate.bat"))
        scrapy_exe = os.path.abspath(os.path.join(base_dir, "venv", "Scripts", "scrapy.exe"))
        if not os.path.exists(venv_activate):
            print(f"虚拟环境激活脚本未找到: {venv_activate}")
            sys.exit(1)
        if not os.path.exists(scrapy_exe):
            print(f"未找到 scrapy.exe: {scrapy_exe}，请确保已在虚拟环境中安装 scrapy。")
            sys.exit(1)
        # 构建 Windows 命令
        shell_flag = True
        # command = f'cmd /c "{venv_activate} && cd /d {spider_dir} && scrapy crawl auto_novel_top100_postgre"'
        command = f'cmd /c "{venv_activate} && cd /d {spider_dir} && scrapy crawl auto_novel_top100_postgre -a local=1"'
        executable_flag = None
    else:
        # 类Unix系统
        venv_activate = os.path.abspath(os.path.join(base_dir, "venv", "bin", "activate"))
        if not os.path.exists(venv_activate):
            print(f"虚拟环境激活脚本未找到: {venv_activate}")
            sys.exit(1)
        # 构建 shell 命令
        # command = f"source {venv_activate} && cd {spider_dir} && scrapy crawl auto_novel_top100_postgre"
        command = f"source {venv_activate} && cd {spider_dir} && scrapy crawl auto_novel_top100_postgre -a local=1"
        shell_flag = True
        executable_flag = "/bin/bash"

    print("正在激活虚拟环境并运行爬虫，请稍候...")
    result = subprocess.run(command, shell=shell_flag, executable=executable_flag)
    if result.returncode == 0:
        print("爬虫运行完成。")
    else:
        print("爬虫运行失败，请检查输出信息。")

if __name__ == "__main__":
    main()
