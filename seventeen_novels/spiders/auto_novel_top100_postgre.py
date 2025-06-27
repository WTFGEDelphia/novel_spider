import scrapy
import os
import time

from scrapy.selector import Selector
from ..items import SeventeenNovelsItem, NovelChapterItem

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from scrapy import signals
import psycopg2


class AutoNovelTop100PostgreSpider(scrapy.Spider):
    name = "auto_novel_top100_postgre"
    allowed_domains = ["17k.com", "www.17k.com"]

    def __init__(self, local=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local = local
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.abspath(
            os.path.join(self.base_dir, "..", "..", "output")
        )
        self.pg_conn_params = None  # 由 from_crawler 注入
        self.driver = None
        self.pg_conn = None
        self.cursor = None

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        settings = crawler.settings
        spider.pg_conn_params = {
            "host": settings.get("PG_HOST"),
            "port": settings.get("PG_PORT"),
            "user": settings.get("PG_USER"),
            "password": settings.get("PG_PASSWORD"),
            "database": settings.get("PG_DBNAME"),
        }
        crawler.signals.connect(spider.open_spider, signal=signals.spider_opened)
        crawler.signals.connect(spider.close_spider, signal=signals.spider_closed)
        return spider

    def open_spider(self, spider):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--enable-unsafe-swiftshader")
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        chrome_options.add_argument(f"user-agent={user_agent}")
        chrome_options.binary_location = os.environ.get("CHROME_BIN", "/usr/bin/google-chrome")

        # 优先从环境变量读取chromedriver路径
        chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", r"/usr/local/bin/chromedriver")
        if not os.path.exists(chromedriver_path):
            self.logger.error(f"ChromeDriver not found at {chromedriver_path}")
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), options=chrome_options
            )
        else:
            self.driver = webdriver.Chrome(
                service=Service(chromedriver_path), options=chrome_options
            )
        self.driver.implicitly_wait(15)
        self.driver.set_page_load_timeout(25)
        try:
            self.pg_conn = psycopg2.connect(
                host=self.pg_conn_params["host"],  # type: ignore
                port=self.pg_conn_params["port"],  # type: ignore
                user=self.pg_conn_params["user"],  # type: ignore
                password=self.pg_conn_params["password"],  # type: ignore
                database=self.pg_conn_params["database"],  # type: ignore
            )
            self.cursor = self.pg_conn.cursor()
        except Exception as e:
            raise Exception(f"Failed to create PostgreSQL connection: {e}")

    def close_spider(self, spider):
        if self.driver:
            self.driver.quit()
            self.driver = None
        if hasattr(self, "cursor") and self.cursor:
            self.cursor.close()
            self.cursor = None
        if hasattr(self, "pg_conn") and self.pg_conn:
            self.pg_conn.close()
            self.pg_conn = None

    def start_requests(self):
        if not self.local or not self.pg_novels_exist():
            url = "https://www.17k.com/top/refactor/top100/06_vipclick/06_click_freeBook_top_100_pc.html"
            yield scrapy.Request(url, callback=self.parse_top100)
        else:
            self.logger.info("PostgreSQL novels表已存在，跳过爬取")
            yield from self.request_chapter_list() # type: ignore

    def pg_novels_exist(self):
        exit_flag = False
        try:
            self.cursor.execute("SELECT COUNT(*) FROM novels")  # type: ignore
            count = self.cursor.fetchone()[0]  # type: ignore
            exit_flag = count > 0
        except Exception as e:
            self.logger.error(f"PostgreSQL novels表检测失败: {e}")
            exit_flag = False
        return exit_flag

    def parse_top100(self, response):
        anti_spider_keywords = [
            "setCookie",
            "reload",
            "_0x",
            "window.location",
            "检测到异常请求",
            "访问验证",
            "人机验证",
        ]
        html_content = response.text
        is_anti_spider = any(
            keyword in html_content for keyword in anti_spider_keywords
        )
        if is_anti_spider:
            self.logger.warning("检测到反爬虫页面，尝试用Selenium重新获取页面内容")
            html_content = self.get_html_with_selenium(response.url) # type: ignore
            if not html_content:
                self.logger.error("Selenium 仍然未能绕过反爬虫，终止解析")
                return
            selector = Selector(text=html_content)
        else:
            selector = response

        table_content = selector.xpath(
            '//div[contains(@class, "BOX") and contains(@style, "block")]//table'
        )
        tr_list = table_content.xpath(".//tr[not(th)]")
        items = []
        for tr in tr_list:
            if tr.xpath("./th"):
                continue
            item = SeventeenNovelsItem()
            item["NovelRanking"] = tr.xpath("./td[1]/text()").get(default="").strip()
            item["NovelType"] = tr.xpath("./td[2]/a/text()").get(default="").strip()
            item["NovelTypeLink"] = tr.xpath("./td[2]/a/@href").get(default="").strip()
            item["NovelName"] = tr.xpath("./td[3]/a/@title").get(default="").strip()
            item["NovelName"] = tr.xpath("./td[3]/a/@title").get(default="").strip()
            item["NovelLink"] = tr.xpath("./td[3]/a/@href").get(default="").strip()
            item["NewlesetChapter"] = tr.xpath("./td[4]/a/@title").get(default="").strip()
            item["NewlesetChapterLink"] = tr.xpath("./td[4]/a/@href").get(default="").strip()
            item["NovelLastUpdateTime"] = tr.xpath("./td[5]/text()").get(default="").strip()
            item["Author"] = tr.xpath("./td[6]/a/text()").get(default="").strip()
            item["AuthorLink"] = tr.xpath("./td[6]/a/@href").get(default="").strip()
            item["NovelStatus"] = tr.xpath("./td[7]/text()").get(default="").strip()
            item["RankingValues"] = tr.xpath("./td[8]/text()").get(default="").strip()
            items.append(item)

        for item in items:
            yield item

        yield from self.request_chapter_list()

    def request_chapter_list(self):
        rows = []
        try:
            self.cursor.execute("SELECT name, link FROM novels ORDER BY ranking")  # type: ignore
            rows = self.cursor.fetchall()  # type: ignore
        except Exception as e:
            self.logger.error(f"PostgreSQL novels表读取失败: {e}")

        for novel_name, novel_link in rows:
            self.logger.info(f"抓取小说: {novel_name}, URL: {novel_link}")
            if not novel_link:
                continue
            novel_link = novel_link.replace("book", "list")
            if novel_link.startswith("//"):
                novel_link = "https:" + novel_link
            elif novel_link.startswith("/"):
                novel_link = "https://www.17k.com" + novel_link
            if not novel_name:
                continue
            yield scrapy.Request(
                novel_link,
                callback=self.parse_novel_chapter_list,
                meta={"novel_name": novel_name},
            )

    def parse_novel_chapter_list(self, response):
        novel_name = response.meta.get("novel_name", "")

        html_content = response.text
        anti_spider_keywords = [
            "setCookie",
            "reload",
            "_0x",
            "window.location",
            "检测到异常请求",
            "访问验证",
            "人机验证",
        ]
        is_anti_spider = any(
            keyword in html_content for keyword in anti_spider_keywords
        )
        if is_anti_spider:
            self.logger.warning(
                f"检测到反爬虫页面，尝试用Selenium重新获取: {novel_name}"
            )
            html_content = self.get_html_with_selenium(response.url) # type: ignore
            if not html_content:
                self.logger.error(f"Selenium 仍然未能绕过反爬虫，未保存: {novel_name}")
                return

        selector = Selector(text=html_content)
        chapter_items = []
        for volume in selector.xpath('//dl[@class="Volume"]'):
            volume_title = (
                volume.xpath('./dt/span[@class="tit"]/text()').get(default="").strip()
            )
            for chapter in volume.xpath("./dd/a"):
                chapter_name = chapter.xpath(".//span/text()").get(default="").strip()
                # span 的 class 为 ellipsis vip 时 跳过该章节
                vip_chapter = chapter.xpath('.//span[@class="ellipsis vip"]')
                if vip_chapter:
                    self.logger.warning(f"跳过小说 {novel_name}: vip章节: {chapter_name}")
                    continue
                chapter_link = chapter.xpath("./@href").get(default="").strip()
                if chapter_link.startswith("/"):
                    chapter_link = response.urljoin(chapter_link)
                chapter_info = chapter.xpath("./@title").get(default="").strip()
                item = NovelChapterItem()
                item["NovelName"] = novel_name
                item["VolumeTitle"] = volume_title
                item["ChapterName"] = chapter_name
                item["ChapterLink"] = chapter_link
                item["ChapterInfo"] = chapter_info
                chapter_items.append(item)

        # 一次性查询所有已存在的章节信息
        exist_chapters = set()
        content_exist_chapters = set()
        try:
            self.cursor.execute(  # type: ignore
                """
                SELECT chapter_name,
                CASE WHEN chapter_content IS NOT NULL AND chapter_content != ''
                THEN 1 ELSE 0 END as has_content
                FROM novel_chapter
                WHERE novel_name = %s
                """,
                (novel_name,),
            )
            for row in self.cursor.fetchall():  # type: ignore
                chapter_name, has_content = row
                exist_chapters.add(chapter_name)
                if has_content:
                    content_exist_chapters.add(chapter_name)
        except Exception as e:
            self.logger.error(f"PostgreSQL novel_chapter表查询失败: {e}")

        self.logger.info(
            f"总章节数: {len(chapter_items)}, 已存在: {len(exist_chapters)}, 有内容: {len(content_exist_chapters)}"
        )

        for item in chapter_items:
            chapter_name = item["ChapterName"]
            if chapter_name not in exist_chapters:
                # 新章节，插入并抓取内容
                yield item
                yield scrapy.Request(
                    url=item["ChapterLink"],
                    callback=self.parse_chapter_content,
                    meta=item,
                )
            elif chapter_name not in content_exist_chapters:
                # 已有章节但内容为空，抓取内容
                yield scrapy.Request(
                    url=item["ChapterLink"],
                    callback=self.parse_chapter_content,
                    meta=item,
                )

    def is_ad_line(self, line):
        AD_FILTER_KEYWORDS = [
            "本书首发来自",
            "第一时间看正版内容",
            "17K小说网",
            "作者寄语",
            "banner_content",
            "二维码",
            "17K客户端",
            "签到即送VIP",
            "免费读全站",
        ]
        return any(keyword in line for keyword in AD_FILTER_KEYWORDS)

    def parse_chapter_content(self, response):
        novel_name = response.meta.get("NovelName", "").strip()
        chapter_name = response.meta.get("ChapterName", "").strip()
        chapter_link = response.meta.get("ChapterLink", "").strip()
        self.logger.info(f"抓取小说章节: {chapter_name}, URL: {chapter_link}")

        html_content = response.text
        anti_spider_keywords = [
            "setCookie",
            "reload",
            "_0x",
            "window.location",
            "检测到异常请求",
            "访问验证",
            "人机验证",
        ]
        is_anti_spider = any(
            keyword in html_content for keyword in anti_spider_keywords
        )
        if is_anti_spider:
            self.logger.warning(
                f"检测到反爬虫页面，尝试用Selenium重新获取: {novel_name}_{chapter_name}"
            )
            html_content = self.get_html_with_selenium(chapter_link)
            if not html_content:
                self.logger.error(
                    f"Selenium 仍然未能绕过反爬虫，未保存: {novel_name}_{chapter_name}"
                )
                return

        selector = Selector(text=html_content)
        content_nodes = selector.xpath(
            '//div[contains(@class,"readAreaBox")]/div[contains(@class,"content")]//text()'
            '| //div[contains(@class,"readAreaBox")]//text()'
        ).getall()
        content = [line.strip() for line in content_nodes if line.strip()]
        content = [line for line in content if not self.is_ad_line(line)]

        item = NovelChapterItem()
        item["NovelName"] = novel_name
        item["VolumeTitle"] = response.meta.get("VolumeTitle", "")
        item["ChapterName"] = chapter_name
        item["ChapterLink"] = chapter_link
        item["ChapterInfo"] = response.meta.get("ChapterInfo", "")
        item["ChapterContent"] = "\n".join(content)
        yield item

    def get_html_with_selenium(self, url, max_retry=3):
        html = ""
        for attempt in range(1, max_retry + 1):
            try:
                if not self.driver:
                    self.logger.error("Selenium driver未初始化")
                    return ""
                self.driver.get(url)
                self.driver.execute_cdp_cmd(
                    "Page.addScriptToEvaluateOnNewDocument",
                    {
                        "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    """
                    },
                )
                time.sleep(0.5)
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
                time.sleep(0.1)
                html = self.driver.page_source
                return html
            except Exception as e:
                self.logger.warning(f"Selenium 第{attempt}次抓取失败: {e}")
                time.sleep(2)
        self.logger.error(f"Selenium 多次重试仍失败: {url}")
        return html
