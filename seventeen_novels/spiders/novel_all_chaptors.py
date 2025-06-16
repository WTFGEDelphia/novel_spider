import scrapy
import csv
import os
from ..items import NovelChaptorItem
from parsel import Selector
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
from scrapy import signals

class NovelAllChaptorsSpider(scrapy.Spider):
    name = "novel_all_chaptors"
    allowed_domains = ["17k.com"]
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.abspath(os.path.join(base_dir, "..", "..", "output"))
    novel_chaptor_list_path = os.path.abspath(os.path.join(output_dir, "novel_chaptor_list"))
    novel_all_chaptors_dir = os.path.abspath(os.path.join(output_dir, "novel_all_chaptors"))
    os.makedirs(novel_all_chaptors_dir, exist_ok=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.driver = None  # Selenium driver实例

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.open_spider, signal=signals.spider_opened)
        crawler.signals.connect(spider.close_spider, signal=signals.spider_closed)
        return spider

    def open_spider(self, spider):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--enable-unsafe-swiftshader")
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        chrome_options.add_argument(f"user-agent={user_agent}")

        chromedriver_path = r"C:\Users\wtf50\.wdm\drivers\chromedriver\win64\137.0.7151.70\chromedriver-win32\chromedriver.exe"
        if not os.path.exists(chromedriver_path):
            self.logger.error(f"ChromeDriver not found at {chromedriver_path}")
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        else:
            self.driver = webdriver.Chrome(service=Service(chromedriver_path), options=chrome_options)
        self.driver.implicitly_wait(15)
        self.driver.set_page_load_timeout(25)

    def close_spider(self, spider):
        if self.driver:
            self.driver.quit()
            self.driver = None

    async def start(self):
        if not os.path.exists(self.novel_chaptor_list_path):
            self.logger.error(f"csv目录未找到: {self.novel_chaptor_list_path}")
            return
        self.logger.info(f"章节csv目录: {self.novel_chaptor_list_path}")
        for filename in os.listdir(self.novel_chaptor_list_path):
            if not filename.endswith(".csv"):
                continue
            csv_path = os.path.join(self.novel_chaptor_list_path, filename)
            self.logger.info(f"处理csv文件: {csv_path}")
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    chapter_link = row.get("ChapterLink", "").strip()
                    if not chapter_link:
                        continue
                    novel_name = row.get("NovelName", "").strip()
                    chapter_name = row.get("ChapterName", "").strip()
                    novel_dir = os.path.abspath(os.path.join(self.novel_all_chaptors_dir, novel_name))
                    os.makedirs(novel_dir, exist_ok=True)
                    html_file = os.path.join(novel_dir, f"{novel_name}_{chapter_name}.html")
                    if os.path.exists(html_file):
                        self.logger.info(f"已存在文件: {html_file}")
                        continue
                    meta = {
                        "NovelName": novel_name,
                        "VolumeTitle": row.get("VolumeTitle", ""),
                        "ChapterName": row.get("ChapterName", ""),
                        "ChapterLink": chapter_link,
                        "ChapterInfo": row.get("ChapterInfo", ""),
                        "html_file": html_file,
                    }
                    yield scrapy.Request(
                        url=chapter_link,
                        callback=self.parse_chapter,
                        meta=meta
                    )

    def get_html_with_selenium(self, url):
        html = ""
        try:
            if not self.driver:
                self.logger.error("Selenium driver未初始化")
                return ""
            self.driver.get(url)
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                """
            })
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
            html = self.driver.page_source
        except Exception as e:
            self.logger.error(f"Selenium 抓取失败: {e}")
        return html

    def parse_chapter(self, response):
        novel_name = response.meta.get('NovelName', '').strip()
        chapter_name = response.meta.get("ChapterName", "").strip()
        chapter_link = response.meta.get("ChapterLink", "").strip()
        html_file = response.meta.get("html_file", "").strip()
        self.logger.info(f"抓取小说章节: {chapter_name}，URL: {chapter_link}")
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
            else:
                self.logger.info(f"保存: {novel_name}_{chapter_name}")
                if not os.path.exists(html_file):
                    with open(html_file, "w", encoding="utf-8") as f:
                        f.write(html_content)

        selector = Selector(text=html_content)
        content = selector.xpath('//div[contains(@class,"readAreaBox")]/div[contains(@class,"content")]/text()').getall()
        if not content:
            content = selector.xpath('//div[contains(@class,"readAreaBox")]//text()').getall()
        content = [line.strip() for line in content if line.strip()]

        item = NovelChaptorItem()
        item["NovelName"] = novel_name
        item["VolumeTitle"] = response.meta.get("VolumeTitle", "")
        item["ChapterName"] = chapter_name
        item["ChapterLink"] = chapter_link
        item["ChapterInfo"] = response.meta.get("ChapterInfo", "")
        item["ChapterContent"] = "\n".join(content)

        yield item
