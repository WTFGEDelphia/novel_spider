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
        self.Top100NovelsFile = None
        self.Top100NovelsExporter = None

    def open_spider(self, spider):
        if spider.name == "free_novel_top100":
            os.makedirs("output", exist_ok=True)
            self.Top100NovelsFile = open("output/free_novel_top100.csv", "wb")
            self.Top100NovelsExporter = CsvItemExporter(self.Top100NovelsFile, encoding="utf8") # type: ignore
            self.Top100NovelsExporter.start_exporting()
        else:
            self.Top100NovelsFile = None
            self.Top100NovelsExporter = None

    def close_spider(self, spider):
        if self.Top100NovelsExporter:
            self.Top100NovelsExporter.finish_exporting()
        if self.Top100NovelsFile:
            self.Top100NovelsFile.close()

    def process_item(self, item, spider):
        if spider.name != "free_novel_top100":
            return item
        if self.Top100NovelsExporter and isinstance(item, SeventeenNovelsItem):
            self.Top100NovelsExporter.export_item(item)
            return item


class NovelChaptorListPipeline:
    def __init__(self):
            self.exporters = {}
            self.files = {}
            self.dir = "output/novel_chaptor_list"

    def open_spider(self, spider):
        if spider.name == "novel_chaptor_list":
            os.makedirs(self.dir, exist_ok=True)

    def close_spider(self, spider):
        for exporter in self.exporters.values():
            exporter.finish_exporting()
        for f in self.files.values():
            f.close()
        self.exporters.clear()
        self.files.clear()

    def process_item(self, item, spider):
        if spider.name != "novel_chaptor_list":
            return item
        if isinstance(item, NovelChaptorItem):
            novel_name = item.get("NovelName", "unknown")
            safe_name = "".join([c if c.isalnum() else "_" for c in novel_name])
            file_path = f"{self.dir}/{safe_name}.csv"
            if novel_name not in self.exporters:
                f = open(file_path, "wb")
                exporter = CsvItemExporter(f, encoding="utf8")
                exporter.start_exporting()
                self.exporters[novel_name] = exporter
                self.files[novel_name] = f
            self.exporters[novel_name].export_item(item)
        return item


class NovelAllChaptorsPipeline:
    def __init__(self):
        self.exporters = {}
        self.files = {}
        self.output_dir = "output/novel_all_chaptors"

    def open_spider(self, spider):
        if spider.name == "novel_all_chaptors":
            os.makedirs(self.output_dir, exist_ok=True)

    def close_spider(self, spider):
        for exporter in self.exporters.values():
            exporter.finish_exporting()
        for f in self.files.values():
            f.close()
        self.exporters.clear()
        self.files.clear()

    def process_item(self, item, spider):
        if spider.name != "novel_all_chaptors":
            return item
        if isinstance(item, NovelChaptorItem):
            novel_name = item.get("NovelName", "unknown")
            safe_name = "".join([c if c.isalnum() else "_" for c in novel_name])
            file_path = f"{self.output_dir}/{safe_name}.csv"
            if novel_name not in self.exporters:
                f = open(file_path, "wb")
                exporter = CsvItemExporter(f, encoding="utf8")
                exporter.start_exporting()
                self.exporters[novel_name] = exporter
                self.files[novel_name] = f
            self.exporters[novel_name].export_item(item)
        return item
