import os
import subprocess
import sys

def main():
    # 获取当前脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.abspath(os.path.join(base_dir, "venv", "bin", "activate"))
    spider_dir = base_dir

    # 检查虚拟环境激活脚本是否存在
    if not os.path.exists(venv_dir):
        print(f"虚拟环境激活脚本未找到: {venv_dir}")
        sys.exit(1)

    # 构建shell命令
    # 注意：source 只能在shell中使用，不能直接用subprocess.run激活当前Python进程的虚拟环境
    # 所以我们用shell方式运行整个命令
    command = f"source {venv_dir} && cd {spider_dir} && scrapy crawl free_novel_top100"

    print("正在激活虚拟环境并运行爬虫，请稍候...")
    result = subprocess.run(command, shell=True, executable="/bin/bash")
    if result.returncode == 0:
        print("爬虫运行完成。")
    else:
        print("爬虫运行失败，请检查输出信息。")

if __name__ == "__main__":
    main()
