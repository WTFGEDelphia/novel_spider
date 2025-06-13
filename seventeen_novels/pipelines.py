# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from .items import SeventeenNovelsItem, NovelChaptorItem

# useful for handling different item types with a single interface
from scrapy.exporters import CsvItemExporter
import os


class FreeNovelTop100Pipeline:

    def __init__(self):
        os.makedirs("output", exist_ok=True)
        self.Top100NovelsFile = open(
            "output/free_novel_top100.csv", "wb+"
        )  # 保存为csv格式
        self.Top100NovelsExporter = CsvItemExporter(self.Top100NovelsFile, encoding="utf8")  # type: ignore
        self.Top100NovelsExporter.start_exporting()

    def process_item(self, item, spider):
        # print(type(item))

        # print(
        #     "isinstance(item, SeventeenNovelsItem):",
        #     isinstance(item, SeventeenNovelsItem),
        # )

        # print("isinstance(item, NovelListItem):", isinstance(item, NovelListItem))

        if isinstance(item, SeventeenNovelsItem):
            print(f"Processing item: {item}")  # 查看处理的 Item 类型
            if spider.name == "free_novel_top100":
                self.Top100NovelsExporter.export_item(item)
                return item


class NovelChaptorListPipeline:

    def __init__(self):
        os.makedirs("output", exist_ok=True)
        self.NovelChaptorListFile = open(
            "output/novel_chaptor_list.csv", "wb+"
        )  # 保存为csv格式
        self.NovelChaptorListExporter = CsvItemExporter(self.NovelChaptorListFile, encoding="utf8")  # type: ignore
        self.NovelChaptorListExporter.start_exporting()

    def process_item(self, item, spider):
        # print(type(item))

        # print(
        #     "isinstance(item, SeventeenNovelsItem):",
        #     isinstance(item, SeventeenNovelsItem),
        # )

        # print("isinstance(item, NovelListItem):", isinstance(item, NovelListItem))
        # print(f"Processing item: {type(item)}")  # 查看处理的 Item 类型

        if isinstance(item, NovelChaptorItem):
            if spider.name == "novel_chaptor_list":
                if not item:
                    return item
                else:
                    self.NovelChaptorListExporter.export_item(item)
                    return item


class NovelAllChaptorsPipeline:

    def __init__(self):
        os.makedirs("output", exist_ok=True)
        self.NovelAllChaptorsFile = open(
            "output/novel_all_chaptors.csv", "wb+"
        )  # 保存为csv格式
        self.NovelAllChaptorsExporter = CsvItemExporter(self.NovelAllChaptorsFile, encoding="utf8")  # type: ignore
        self.NovelAllChaptorsExporter.start_exporting()

    def process_item(self, item, spider):
        # print(type(item))

        # print(
        #     "isinstance(item, SeventeenNovelsItem):",
        #     isinstance(item, SeventeenNovelsItem),
        # )

        # print("isinstance(item, NovelListItem):", isinstance(item, NovelListItem))
        # print(f"Processing item: {type(item)}")  # 查看处理的 Item 类型

        if isinstance(item, NovelChaptorItem):
            if spider.name == "novel_all_chaptors":
                self.NovelAllChaptorsExporter.export_item(item)
                return item
