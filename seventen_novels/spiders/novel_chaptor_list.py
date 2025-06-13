import scrapy
import csv
import os
from ..items import NovelChaptorItem

class NovelChaptorListSpider(scrapy.Spider):
    name = "novel_chaptor_list"
    allowed_domains = ["www.17k.com"]

    async def start(self):
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "seventeen_novels_top100.csv"
        )
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
                yield scrapy.Request(
                    novel_link,
                    callback=self.parse_novel,
                    meta={'novel_name': row.get("NovelName", "")}
                )

    def parse_novel(self, response):
        novel_name = response.meta.get('novel_name', '')
        self.logger.info(f"抓取小说: {novel_name}，URL: {response.url}")
        html_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            novel_name + ".html"
        )
        if not os.path.exists(html_file):
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(response.text)

        # 解析所有卷
        for volume in response.xpath('//dl[@class="Volume"]'):
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
                self.logger.info(f"抓取item: {item}")
                yield item
