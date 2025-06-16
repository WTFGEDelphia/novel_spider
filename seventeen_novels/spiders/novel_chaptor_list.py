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

class NovelChaptorListSpider(scrapy.Spider):
    name = "novel_chaptor_list"
    allowed_domains = ["www.17k.com"]
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.abspath(os.path.join(base_dir, "..", "..", "output"))
    novel_top100_path = os.path.abspath(os.path.join(output_dir, "novel_top100_html"))
    os.makedirs(novel_top100_path, exist_ok=True)

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
        csv_path = os.path.abspath(os.path.join(self.output_dir, "free_novel_top100.csv"))
        self.logger.info(f"CSV文件路径: {csv_path}")
        if not os.path.exists(csv_path):
            self.logger.error(f"CSV文件未找到: {csv_path}")
            return

        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                self.logger.info(f"row: {row}")
                novel_link = row.get("NovelLink", "").strip()
                if not novel_link:
                    continue
                # 补全协议头
                novel_link = novel_link.replace("book", "list")
                if novel_link.startswith("//"):
                    novel_link = "https:" + novel_link
                elif novel_link.startswith("/"):
                    novel_link = "https://www.17k.com" + novel_link
                self.logger.info(f"novel_link: {novel_link}")
                novel_name = row.get("NovelName", "")
                if not novel_name:
                    continue
                html_file = os.path.abspath(os.path.join(self.novel_top100_path, novel_name + ".html"))
                if os.path.exists(html_file):
                    self.logger.warning(f"小说html已存在: {html_file}")
                    continue
                yield scrapy.Request(
                    novel_link,
                    callback=self.parse_novel,
                    meta={'novel_name': row.get("NovelName", ""), 'html_file': html_file}
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

    def parse_novel(self, response):
        novel_name = response.meta.get('novel_name', '')
        html_file = response.meta.get('html_file', '')
        self.logger.info(f"抓取小说: {novel_name}，URL: {response.url}")

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
            else:
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(html_content)

        selector = Selector(text=html_content)
        # 解析所有卷
        for volume in selector.xpath('//dl[@class="Volume"]'):
            volume_title = volume.xpath('./dt/span[@class="tit"]/text()').get(default='').strip()
            # 解析该卷下所有章节
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
                # self.logger.info(f"抓取item: {item}")
                yield item
