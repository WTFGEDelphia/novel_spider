import scrapy
import os
import sqlite3
import time

from scrapy.selector import Selector
from ..items import SeventeenNovelsItem, NovelChaptorItem

# Selenium相关
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

class AutoNovelTop100Spider(scrapy.Spider):
    name = "auto_novel_top100"
    allowed_domains = ["17k.com", "www.17k.com"]

    def __init__(self, local=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local = local
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.abspath(os.path.join(self.base_dir, "..", "..", "output"))
        self.db_path = os.path.join(self.output_dir, "novel_data.db")

    def start_requests(self):
        # Step 1: 抓取Top100榜单
        if not os.path.exists(self.db_path) or not self.local:
            url = "https://www.17k.com/top/refactor/top100/06_vipclick/06_click_freeBook_top_100_pc.html"
            yield scrapy.Request(url, callback=self.parse_top100)
        else:
            # 已有榜单，直接进入下一步
            yield from self.request_chaptor_list()

    def parse_top100(self, response):
        anti_spider_keywords = [
            "setCookie", "reload", "_0x", "window.location", "检测到异常请求", "访问验证", "人机验证"
        ]
        html_content = response.text
        is_anti_spider = any(keyword in html_content for keyword in anti_spider_keywords)
        if is_anti_spider:
            self.logger.warning("检测到反爬虫页面，尝试用Selenium重新获取页面内容")
            html_content = self.get_html_with_selenium(response.url)
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
            item["NovelRanking"] = tr.xpath("./td[1]/text()").get()
            item["NovelType"] = tr.xpath("./td[2]/a/text()").get()
            item["NovelTypeLink"] = tr.xpath("./td[2]/a/@href").get()
            item["NovelName"] = tr.xpath("./td[3]/a/@title").get()
            item["NovelLink"] = tr.xpath("./td[3]/a/@href").get()
            item["NewlesetChapter"] = tr.xpath("./td[4]/a/@title").get()
            item["NewlesetChapterLink"] = tr.xpath("./td[4]/a/@href").get()
            item["NovelLastUpdateTime"] = tr.xpath("./td[5]/text()").get()
            item["Author"] = tr.xpath("./td[6]/a/text()").get()
            item["AuthorLink"] = tr.xpath("./td[6]/a/@href").get()
            item["NovelStatus"] = tr.xpath("./td[7]/text()").get()
            item["RankingValues"] = tr.xpath("./td[8]/text()").get()
            items.append(item)

        # 只 yield item，写入交由 pipeline
        for item in items:
            yield item

        # 进入下一步
        yield from self.request_chaptor_list()

    def request_chaptor_list(self):
        # Step 2: 直接从pipeline写入的sqlite读取榜单
        if not os.path.exists(self.db_path):
            self.logger.error(f"sqlite文件未找到: {self.db_path}")
            return
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, link FROM novels order by ranking")
        rows = cursor.fetchall()
        conn.close()
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
                callback=self.parse_novel_chaptor_list,
                meta={'novel_name': novel_name}
            )

    def parse_novel_chaptor_list(self, response):
        novel_name = response.meta.get('novel_name', '')
        self.logger.info(f"抓取小说: {novel_name}, URL: {response.url}")

        html_content = response.text
        anti_spider_keywords = [
            "setCookie", "reload", "_0x", "window.location", "检测到异常请求", "访问验证", "人机验证"
        ]
        is_anti_spider = any(keyword in html_content for keyword in anti_spider_keywords)
        if is_anti_spider:
            self.logger.warning(f"检测到反爬虫页面，尝试用Selenium重新获取: {novel_name}")
            html_content = self.get_html_with_selenium(response.url)
            if not html_content:
                self.logger.error(f"Selenium 仍然未能绕过反爬虫，未保存: {novel_name}")
                return

        selector = Selector(text=html_content)
        chaptor_items = []
        for volume in selector.xpath('//dl[@class="Volume"]'):
            volume_title = volume.xpath('./dt/span[@class="tit"]/text()').get(default='').strip()
            for chapter in volume.xpath('./dd/a'):
                chapter_name = chapter.xpath('.//span/text()').get(default='').strip()
                chapter_link = chapter.xpath('./@href').get(default='').strip()
                if chapter_link.startswith('/'):
                    chapter_link = response.urljoin(chapter_link)
                chapter_info = chapter.xpath('./@title').get(default='').strip()
                item = NovelChaptorItem()
                item["NovelName"] = novel_name
                item["VolumeTitle"] = volume_title
                item["ChapterName"] = chapter_name
                item["ChapterLink"] = chapter_link
                item["ChapterInfo"] = chapter_info
                chaptor_items.append(item)

        # 只 yield item，写入交由 pipeline
        for item in chaptor_items:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
            SELECT count(*) FROM novel_chaptor
            WHERE novel_name = ? AND chapter_name = ? AND chapter_content IS NOT NULL
            ''',
            (item["NovelName"], item["ChapterName"]))
            count = cursor.fetchone()[0]
            conn.close()
            if count == 1:
                self.logger.info(f"小说{item['NovelName']}章节内容已存在: {item['ChapterName']}")
                continue
            yield item
            # 进入下一步：抓取章节内容
            yield scrapy.Request(
                url=item["ChapterLink"],
                callback=self.parse_chaptor_content,
                meta=item
            )

    def parse_chaptor_content(self, response):
        novel_name = response.meta.get('NovelName', '').strip()
        chapter_name = response.meta.get("ChapterName", "").strip()
        chapter_link = response.meta.get("ChapterLink", "").strip()
        self.logger.info(f"抓取小说章节: {chapter_name}, URL: {chapter_link}")

        html_content = response.text
        anti_spider_keywords = [
            "setCookie", "reload", "_0x", "window.location", "检测到异常请求", "访问验证", "人机验证"
        ]
        is_anti_spider = any(keyword in html_content for keyword in anti_spider_keywords)
        if is_anti_spider:
            self.logger.warning(f"检测到反爬虫页面，尝试用Selenium重新获取: {novel_name}_{chapter_name}")
            html_content = self.get_html_with_selenium(chapter_link)
            if not html_content:
                self.logger.error(f"Selenium 仍然未能绕过反爬虫，未保存: {novel_name}_{chapter_name}")
                return

        selector = Selector(text=html_content)
        content = selector.xpath('//div[contains(@class,"readAreaBox")]/div[contains(@class,"content")]/text()').getall()
        if not content:
            content = selector.xpath('//div[contains(@class,"readAreaBox")]//text()').getall()
        content = [line.strip() for line in content if line.strip()]

        # 只 yield item，写入交由 pipeline
        item = NovelChaptorItem()
        item["NovelName"] = novel_name
        item["VolumeTitle"] = response.meta.get("VolumeTitle", "")
        item["ChapterName"] = chapter_name
        item["ChapterLink"] = chapter_link
        item["ChapterInfo"] = response.meta.get("ChapterInfo", "")
        item["ChapterContent"] = "\n".join(content)
        yield item

    def get_html_with_selenium(self, url):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--enable-unsafe-swiftshader")
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        chrome_options.add_argument(f"user-agent={user_agent}")

        driver = None
        html = ""
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            driver.implicitly_wait(15)
            driver.set_page_load_timeout(25)
            driver.get(url)
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                """
            })
            time.sleep(3)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            html = driver.page_source
        except Exception as e:
            self.logger.error(f"Selenium 获取页面失败: {e}")
        finally:
            if driver:
                driver.quit()
        return html
