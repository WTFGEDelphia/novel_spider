novel_spider/README.md
# novel_spider

**novel_spider** 是一个基于 Python 的 17k 小说网爬虫项目，使用 Scrapy、Selenium 及 webdriver_manager 实现自动化抓取 17k 小说网的免费小说榜单、小说章节列表及章节内容，并将数据保存为 CSV 文件，便于后续分析和处理。

## 功能说明

本项目主要包含以下功能：

1. **抓取免费小说 TOP100 榜单**
   - 通过 `free_novel_top100` 爬虫，自动抓取 17k 小说网免费榜单前 100 名小说的基本信息，包括排名、类别、名称、作者、最新章节、状态等，并保存为 `free_novel_top100.csv`。

2. **抓取小说章节列表**
   - 通过 `novel_chaptor_list` 爬虫，读取榜单 CSV，批量抓取每本小说的所有卷及章节信息，包括卷名、章节名、章节链接等，保存为 `novel_chaptor_list.csv`。

3. **抓取小说所有章节内容**
   - 通过 `novel_all_chaptors` 爬虫，读取章节列表 CSV，批量抓取每个章节的正文内容，自动处理反爬虫机制（如遇到反爬页面自动切换 Selenium），并保存为 `novel_all_chaptors.csv` 及本地 HTML 文件。

4. **数据结构**
   - 所有抓取的数据均以 CSV 格式输出，便于后续数据分析或导入数据库。
   - 支持断点续爬、反爬虫检测与自动切换抓取方式。

## 目录结构

```
novel_spider/
├── seventen_novels/           # Scrapy 爬虫主模块
│   ├── items.py               # 定义数据结构
│   ├── pipelines.py           # 数据处理与导出
│   ├── settings.py            # Scrapy 配置
│   └── spiders/               # 各爬虫脚本
│       ├── free_novel_top100.py
│       ├── novel_chaptor_list.py
│       └── novel_all_chaptors.py
├── output/                    # 所有数据输出目录（已自动 .gitignore）
│   ├── free_novel_top100.csv              # 免费榜单数据
│   ├── novel_chaptor_list/                # 每本小说的章节列表csv
│   │   ├── 小说A.csv
│   │   ├── 小说B.csv
│   │   └── ...
│   ├── novel_all_chaptors/                # 每本小说的章节正文csv
│   │   ├── 小说A.csv
│   │   ├── 小说B.csv
│   │   └── ...
├── run_free_novel_top100.py   # 运行免费榜单爬虫的入口脚本
├── run_novel_chaptor_list.py  # 运行章节列表爬虫的入口脚本
├── run_novel_all_chaptors.py  # 运行章节内容爬虫的入口脚本
├── LICENSE
└── README.md
```

## 输入文件与输出目录说明

- `output/free_novel_top100.csv`：免费小说榜单，作为章节列表爬虫的输入。
- `output/novel_chaptor_list/`：每本小说所有章节列表 csv，作为章节内容爬虫的输入。
- `output/novel_all_chaptors/`：每本小说所有章节正文 csv，最终输出结果。

所有中间和最终数据均保存在 `output/` 目录下。该目录已加入 `.gitignore`，不会被提交到仓库。

## 安装与环境准备

1. **克隆项目**
   ```bash
   git clone git@github.com:WTFGEDelphia/novel_spider.git
   cd novel_spider
   git checkout main
   ```

2. **安装 Python 环境**

   - 推荐 Python 3.13.3 及以上版本。
   - 可从 [Python 官网](https://www.python.org/downloads/) 下载并安装适合你操作系统的版本。
   - 各操作系统安装方法如下：

   **Windows：**
   1. 访问 [Python 官网下载页面](https://www.python.org/downloads/windows/)。
   2. 下载最新的 Python 3 安装包（.exe）。
   3. 双击运行安装包，**务必勾选“Add Python to PATH”**，然后点击“Install Now”。
   4. 安装完成后，在命令行输入 `python --version` 或 `py --version` 验证安装。

   **macOS：**
   1. 推荐使用 Homebrew 安装（如未安装 Homebrew，可参考 https://brew.sh/ ）：
      ```bash
      brew install python
      ```
   2. 或前往 [Python 官网下载页面](https://www.python.org/downloads/macos/) 下载 `.pkg` 安装包并安装。
   3. 安装完成后，在终端输入 `python3 --version` 验证安装。

   **Linux（以 Ubuntu/Debian 为例）：**
   1. 系统通常自带 Python3，可通过以下命令安装/升级：
      ```bash
      sudo apt update
      sudo apt install python3 python3-venv python3-pip
      ```
   2. 验证安装：
      ```bash
      python3 --version
      ```
   3. 其他发行版可参考各自的包管理器（如 yum、dnf、pacman 等）。

   > 如需多版本管理，可考虑使用 [pyenv](https://github.com/pyenv/pyenv)。

3. **创建虚拟环境并安装依赖**

   - **Windows**
     ```cmd
     py -m venv venv
     venv\Scripts\activate
     pip install -r requirements.txt
     ```

   - **macOS / Linux**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt
     ```

   > 依赖主要包括：`scrapy`, `selenium`, `webdriver_manager`, `parsel` 等。

4. **配置 Chrome 浏览器与驱动**
   - 本项目自动使用 `webdriver_manager` 管理 ChromeDriver，无需手动下载。
   - 需本地已安装 Chrome 浏览器。

## 使用方法

### 1. 抓取免费小说 TOP100 榜单

```bash
python run_free_novel_top100.py
```
- 运行后会自动激活虚拟环境并执行爬虫，输出 `free_novel_top100.csv`。

### 2. 抓取小说章节列表

```bash
python run_novel_chaptor_list.py
```
- 依赖上一步生成的 `free_novel_top100.csv`，输出 `novel_chaptor_list.csv`。

### 3. 抓取所有章节内容

```bash
python run_novel_all_chaptors.py
```
- 依赖上一步生成的 `novel_chaptor_list.csv`，输出 `novel_all_chaptors.csv` 及各章节 HTML 文件。

### 4. 参数说明

- 各入口脚本会自动检测虚拟环境并激活，若未找到虚拟环境会报错。
- 支持本地调试模式，可通过修改爬虫参数实现。

### 5. 结果文件

- `free_novel_top100.csv`：包含小说榜单信息。
- `novel_chaptor_list.csv`：包含每本小说的所有章节信息。
- `novel_all_chaptors.csv`：包含所有章节的正文内容。
- 各章节 HTML 文件：以小说名为目录，章节名为文件名保存。

## 注意事项

- 抓取速度已做限流（`DOWNLOAD_DELAY=1`），如遇反爬虫可适当调整。
- 若遇到反爬虫页面，程序会自动切换 Selenium 进行抓取。
- 建议在稳定网络环境下运行，避免中断。

## 许可证

MIT License

---

如需定制化采集或有其他问题，欢迎 issue 或联系作者。
