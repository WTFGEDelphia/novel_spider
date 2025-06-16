# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import os
import sqlite3
from .items import SeventeenNovelsItem, NovelChaptorItem
# useful for handling different item types with a single interface
from scrapy.exporters import CsvItemExporter

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


class AutoNovelsTop100Pipeline:
    def __init__(self):
        self.db_path = "output/novel_data.db"
        self.conn = None
        self.cursor = None

    def open_spider(self, spider):
        if spider.name != "auto_novel_top100":
            return
        os.makedirs("output", exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        # Top100榜单表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS novels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ranking INTEGER,
                type TEXT,
                type_link TEXT,
                name TEXT,
                link TEXT,
                latest_chapter TEXT,
                latest_chapter_link TEXT,
                update_time TEXT,
                author TEXT,
                author_link TEXT,
                status TEXT,
                ranking_values TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_novels_name ON novels(name)
        ''')
        # 章节列表表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS novel_chaptor (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_name TEXT,
                volume_title TEXT,
                chapter_name TEXT,
                chapter_link TEXT,
                chapter_info TEXT,
                chapter_content TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_chaptor_name ON novel_chaptor(novel_name, chapter_name)
        ''')

    def close_spider(self, spider):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def process_item(self, item, spider):
        if spider.name != "auto_novel_top100":
            return
        # Top100榜单
        if isinstance(item, SeventeenNovelsItem):
            self.cursor.execute('''
                INSERT OR REPLACE INTO novels (
                    id, ranking, type, type_link, name, link,
                    latest_chapter, latest_chapter_link, update_time,
                    author, author_link, status, ranking_values
                ) VALUES (
                    (SELECT id FROM novels WHERE name = ?),
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            ''', (
                item.get('NovelName'),
                item.get('NovelRanking'),
                item.get('NovelType'),
                item.get('NovelTypeLink'),
                item.get('NovelName'),
                item.get('NovelLink'),
                item.get('NewlesetChapter'),
                item.get('NewlesetChapterLink'),
                item.get('NovelLastUpdateTime'),
                item.get('Author'),
                item.get('AuthorLink'),
                item.get('NovelStatus'),
                item.get('RankingValues')
            ))
            self.conn.commit()
            return item

        # 章节内容
        if isinstance(item, NovelChaptorItem) and item.get("ChapterContent"):
            self.cursor.execute('''
                INSERT OR REPLACE INTO novel_chaptor (
                    id, novel_name, volume_title, chapter_name,
                    chapter_link, chapter_info, chapter_content
                ) VALUES (
                    (SELECT id FROM novel_chaptor WHERE novel_name = ? AND chapter_name = ?),
                    ?, ?, ?, ?, ?, ?
                )
            ''', (
                item.get('NovelName'),
                item.get('ChapterName'),
                item.get('NovelName'),
                item.get('VolumeTitle'),
                item.get('ChapterName'),
                item.get('ChapterLink'),
                item.get('ChapterInfo'),
                item.get('ChapterContent'),
            ))
            self.conn.commit()
            return item

        # 章节列表（无正文）
        if isinstance(item, NovelChaptorItem):
            self.cursor.execute('''
                INSERT OR REPLACE INTO novel_chaptor (
                    id, novel_name, volume_title, chapter_name,
                    chapter_link, chapter_info
                ) VALUES (
                    (SELECT id FROM novel_chaptor WHERE novel_name = ? AND chapter_name = ?),
                    ?, ?, ?, ?, ?
                )
            ''', (
                item.get('NovelName'),
                item.get('ChapterName'),
                item.get('NovelName'),
                item.get('VolumeTitle'),
                item.get('ChapterName'),
                item.get('ChapterLink'),
                item.get('ChapterInfo'),
            ))
            self.conn.commit()
            return item

        return item
