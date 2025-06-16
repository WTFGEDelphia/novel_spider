import scrapy
from scrapy.selector import Selector
from ..items import SeventeenNovelsItem
import os

# 反爬虫检测与Selenium相关
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
from scrapy import signals

class FreeNovelTop100Spider(scrapy.Spider):
    name = "free_novel_top100"
    allowed_domains = ["www.17k.com"]
    start_urls = [
        "https://www.17k.com/top/refactor/top100/06_vipclick/06_click_freeBook_top_100_pc.html"
    ]

    def __init__(self, local=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local = local
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

        # 你可以根据实际情况修改 chromedriver 路径
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

    def start_requests(self):
        if self.local:
            # 本地模式
            print("本地模式")
            yield from self.parse_local_file()
        else:
            # 正常网络模式
            print("正常网络模式")
            for url in self.start_urls:
                yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        # 反爬虫关键字
        anti_spider_keywords = [
            "setCookie", "reload", "_0x", "window.location", "检测到异常请求", "访问验证", "人机验证"
        ]
        html_content = response.text
        # 检查是否触发反爬虫
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

        os.makedirs("output", exist_ok=True)
        with open("output/response.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        yield from self.parse_table(selector)

    def parse_local_file(self):
        # 本地文件解析
        with open("output/response.html", "r", encoding="utf-8") as f:
            html = f.read()
        selector = Selector(text=html)
        yield from self.parse_table(selector)

    def parse_table(self, selector):
        """
        解析表格数据并生成 Item
        :param selector: Scrapy Selector 对象
        """
        table_content = selector.xpath(
            '//div[contains(@class, "BOX") and contains(@style, "block")]//table'
        )
        print("table_content:", table_content)
        # 跳过表头行
        tr_list = table_content.xpath(".//tr[not(th)]")
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
            yield item

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
            self.logger.error(f"Selenium 获取页面失败: {e}")
        return html
