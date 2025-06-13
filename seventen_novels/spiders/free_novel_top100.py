import scrapy
from scrapy.selector import Selector
from ..items import SeventeenNovelsItem

class FreeNovelTop100Spider(scrapy.Spider):
    name = "free_novel_top100"
    allowed_domains = ["www.17k.com"]
    start_urls = [
        "https://www.17k.com/top/refactor/top100/06_vipclick/06_click_freeBook_top_100_pc.html"
    ]

    def __init__(self, local=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local = local

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
        # 正常网络请求解析
        with open("response.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        yield from self.parse_table(response)

    def parse_local_file(self):
        # 本地文件解析
        with open("response.html", "r", encoding="utf-8") as f:
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
