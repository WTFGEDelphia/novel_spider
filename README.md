novel_spider/README.md
# novel_spider

**novel_spider** 是一个基于 Python 的 17k 小说网爬虫与电子书导出项目，支持一键采集、断点续爬、反爬虫自动切换、数据导出为 txt/epub，推荐使用统一入口脚本 `run.py`。

## 功能说明

本项目主要包含以下功能：

1. **一键自动采集小说榜单、章节、内容**
   - 通过 `run.py` 脚本，支持如下命令：
     - `python run.py crawl auto_novel_top100`
     - `python run.py crawl auto_novel_top100_postgre`
   - 自动抓取 17k 小说网 VIP 榜单前 100 名小说的基本信息、章节列表及所有章节内容，支持断点续爬、反爬虫自动切换 Selenium。
   - 数据存入 `output/novel_data.db`（SQLite）或 PostgreSQL（自动检测 settings.py）。

2. **一键导出小说为 txt/epub**
   - 通过 `run.py` 脚本，支持如下命令：
     - `python run.py export txt`
     - `python run.py export epub`
   - 自动从数据库导出所有小说为 txt 或 epub 文件，支持章节号智能排序、中文数字识别、作者信息导出。

3. **数据库自动适配**
   - 自动检测 `seventeen_novels/settings.py`，优先用 PostgreSQL，否则用 SQLite。
   - 数据表结构自动创建，支持 upsert。

4. **章节号智能排序与中文数字识别**
   - 导出时自动识别章节号，支持"第十二章""第100章"等混合排序。
   - 支持中文数字转阿拉伯数字，章节顺序准确。

5. **环境与依赖自动管理**
   - 自动检测并激活虚拟环境。
   - ChromeDriver 自动管理，无需手动下载。

6. **反爬虫自动切换与断点续爬**
   - 遇到反爬页面自动切换 Selenium。
   - 已采集章节自动跳过，支持大规模数据采集。

7. **其它入口脚本说明**
   - 其它 `run_xxx.py` 入口脚本已被 `run.py` 整合，不再推荐单独使用。

## 目录结构

```
novel_spider/
├── seventeen_novels/           # Scrapy 爬虫主模块
│   ├── items.py
│   ├── pipelines.py
│   ├── settings.py
│   └── spiders/
├── output/                     # 所有数据输出目录
│   ├── novel_data.db           # 自动化采集的数据库
│   ├── ebooks/                 # 导出的 txt/epub 文件
├── run.py                      # 一键入口脚本（推荐）
├── requirements.txt
└── README.md
```

## 输入文件与输出目录说明

- `output/novel_data.db`：包含自动化采集的小说榜单、章节列表、章节内容等所有结构化数据，便于后续分析或二次开发。
- `output/ebooks/`：导出的 txt/epub 文件，文件名为小说名。
- 其它中间和最终数据均保存在 `output/` 目录下。该目录已加入 `.gitignore`，不会被提交到仓库。

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

   > 依赖主要包括：`scrapy`, `selenium`, `webdriver_manager`, `parsel`, `ebooklib` 等。

4. **配置 Chrome 浏览器与驱动**
   - 本项目自动使用 `webdriver_manager` 管理 ChromeDriver，无需手动下载。
   - 需本地已安装 Chrome 浏览器。

## 使用方法

### 1. 一键自动采集小说榜单与内容

```bash
python run.py crawl auto_novel_top100
# 或
python run.py crawl auto_novel_top100_postgre
```
- 自动抓取榜单、章节列表、章节内容，全部存入 `output/novel_data.db` 或 PostgreSQL。
- 支持参数 `--local`，如数据库已存在则跳过榜单采集，直接采集章节内容。

### 2. 一键导出小说为 txt/epub

```bash
python run.py export txt
python run.py export epub
```
- 自动从数据库导出所有小说为 txt 或 epub 文件，支持章节号智能排序、中文数字识别、作者信息导出。

### 3. 其它说明

- **反爬虫处理**：遇到反爬页面自动切换 Selenium。
- **断点续爬**：已采集章节自动跳过，支持大规模数据采集。
- **导出格式**：txt/epub 文件均包含小说名、作者、卷名、章节名、正文，章节顺序智能排序。
- **数据库切换**：如存在 `seventeen_novels/settings.py` 且配置了 PG_HOST 等参数，自动使用 PostgreSQL，否则用 SQLite。
- **其它入口脚本**：`run_free_novel_top100.py`、`run_novel_chapter_list.py`、`run_novel_all_chapters.py`、`run_export_to_epub.py` 等已被 `run.py` 整合，不再推荐单独使用。

## 许可证

MIT License

---

如需定制化采集或有其他问题，欢迎 issue 或联系作者。
