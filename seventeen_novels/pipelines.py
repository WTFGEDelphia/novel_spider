# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import os
import sqlite3
from .items import SeventeenNovelsItem, NovelChapterItem

# useful for handling different item types with a single interface
from scrapy.exporters import CsvItemExporter
from scrapy.exceptions import NotConfigured
from psycopg2 import pool


class FreeNovelTop100Pipeline:
    def __init__(self):
        self.Top100NovelsFile = None
        self.Top100NovelsExporter = None

    def open_spider(self, spider):
        if spider.name == "free_novel_top100":
            os.makedirs("output", exist_ok=True)
            self.Top100NovelsFile = open("output/free_novel_top100.csv", "wb")
            self.Top100NovelsExporter = CsvItemExporter(self.Top100NovelsFile, encoding="utf8")  # type: ignore
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


class NovelChapterListPipeline:
    def __init__(self):
        self.exporters = {}
        self.files = {}
        self.dir = "output/novel_chapter_list"

    def open_spider(self, spider):
        if spider.name == "novel_chapter_list":
            os.makedirs(self.dir, exist_ok=True)

    def close_spider(self, spider):
        for exporter in self.exporters.values():
            exporter.finish_exporting()
        for f in self.files.values():
            f.close()
        self.exporters.clear()
        self.files.clear()

    def process_item(self, item, spider):
        if spider.name != "novel_chapter_list":
            return item
        if isinstance(item, NovelChapterItem):
            novel_name = item.get("NovelName", "unknown")
            safe_name = "".join([c if c.isalnum() else "_" for c in novel_name])
            file_path = f"{self.dir}/{safe_name}.csv"
            if novel_name not in self.exporters:
                f = open(file_path, "wb")
                exporter = CsvItemExporter(f, encoding="utf8")  # type: ignore
                exporter.start_exporting()
                self.exporters[novel_name] = exporter
                self.files[novel_name] = f
            self.exporters[novel_name].export_item(item)
        return item


class NovelAllChaptersPipeline:
    def __init__(self):
        self.exporters = {}
        self.files = {}
        self.output_dir = "output/novel_all_chapters"

    def open_spider(self, spider):
        if spider.name == "novel_all_chapters":
            os.makedirs(self.output_dir, exist_ok=True)

    def close_spider(self, spider):
        for exporter in self.exporters.values():
            exporter.finish_exporting()
        for f in self.files.values():
            f.close()
        self.exporters.clear()
        self.files.clear()

    def process_item(self, item, spider):
        if spider.name != "novel_all_chapters":
            return item
        if isinstance(item, NovelChapterItem):
            novel_name = item.get("NovelName", "unknown")
            safe_name = "".join([c if c.isalnum() else "_" for c in novel_name])
            file_path = f"{self.output_dir}/{safe_name}.csv"
            if novel_name not in self.exporters:
                f = open(file_path, "wb")
                exporter = CsvItemExporter(f, encoding="utf8")  # type: ignore
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
        self.cursor.execute(
            """
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
        """
        )
        self.cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_novels_name ON novels(name)
        """
        )
        # 章节列表表
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS novel_chapter (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_name TEXT,
                volume_title TEXT,
                chapter_name TEXT,
                chapter_link TEXT,
                chapter_info TEXT,
                chapter_content TEXT
            )
        """
        )
        self.cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_chapter_name ON novel_chapter(novel_name, chapter_name)
        """
        )
        self.conn.commit()

    def close_spider(self, spider):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def process_item(self, item, spider):
        if spider.name != "auto_novel_top100":
            return item
        # Top100榜单
        if isinstance(item, SeventeenNovelsItem):
            self.cursor.execute(  # type: ignore
                """
                INSERT OR REPLACE INTO novels (
                    id, ranking, type, type_link, name, link,
                    latest_chapter, latest_chapter_link, update_time,
                    author, author_link, status, ranking_values
                ) VALUES (
                    (SELECT id FROM novels WHERE name = ?),
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """,
                (
                    item.get("NovelName"),
                    item.get("NovelRanking"),
                    item.get("NovelType"),
                    item.get("NovelTypeLink"),
                    item.get("NovelName"),
                    item.get("NovelLink"),
                    item.get("NewlesetChapter"),
                    item.get("NewlesetChapterLink"),
                    item.get("NovelLastUpdateTime"),
                    item.get("Author"),
                    item.get("AuthorLink"),
                    item.get("NovelStatus"),
                    item.get("RankingValues"),
                ),
            )
            self.conn.commit()  # type: ignore
            return item

        # 章节内容
        if isinstance(item, NovelChapterItem) and item.get("ChapterContent"):
            self.cursor.execute(  # type: ignore
                """
                INSERT OR REPLACE INTO novel_chapter (
                    id, novel_name, volume_title, chapter_name,
                    chapter_link, chapter_info, chapter_content
                ) VALUES (
                    (SELECT id FROM novel_chapter WHERE novel_name = ? AND chapter_name = ?),
                    ?, ?, ?, ?, ?, ?
                )
            """,
                (
                    item.get("NovelName"),
                    item.get("ChapterName"),
                    item.get("NovelName"),
                    item.get("VolumeTitle"),
                    item.get("ChapterName"),
                    item.get("ChapterLink"),
                    item.get("ChapterInfo"),
                    item.get("ChapterContent"),
                ),
            )
            self.conn.commit()  # type: ignore
            return item

        # 章节列表（无正文）
        if isinstance(item, NovelChapterItem):
            self.cursor.execute(  # type: ignore
                """
                INSERT OR REPLACE INTO novel_chapter (
                    id, novel_name, volume_title, chapter_name,
                    chapter_link, chapter_info
                ) VALUES (
                    (SELECT id FROM novel_chapter WHERE novel_name = ? AND chapter_name = ?),
                    ?, ?, ?, ?, ?
                )
            """,
                (
                    item.get("NovelName"),
                    item.get("ChapterName"),
                    item.get("NovelName"),
                    item.get("VolumeTitle"),
                    item.get("ChapterName"),
                    item.get("ChapterLink"),
                    item.get("ChapterInfo"),
                ),
            )
            self.conn.commit()  # type: ignore
            return item

        return item


class AutoNovelsTop100PostgrePipeline:
    def __init__(self, host, port, user, password, dbname, minconn, maxconn):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.dbname = dbname
        self.minconn = minconn
        self.maxconn = maxconn
        self.connection_pool = None

    @classmethod
    def from_crawler(cls, crawler):
        # 从 settings 中获取数据库配置
        settings = crawler.settings
        host = settings.get("PG_HOST")
        port = settings.get("PG_PORT")
        user = settings.get("PG_USER")
        password = settings.get("PG_PASSWORD")
        dbname = settings.get("PG_DBNAME")
        minconn = settings.get("PG_MINCONN", 1)  # 最小连接数
        maxconn = settings.get("PG_MAXCONN", 10)  # 最大连接数

        # 检查是否配置了数据库信息
        if not all([host, port, user, password, dbname]):
            raise NotConfigured("PostgreSQL settings not configured")

        return cls(host, port, user, password, dbname, minconn, maxconn)

    def open_spider(self, spider):
        if spider.name != "auto_novel_top100_postgre":
            return
        # 在爬虫开始时创建连接池
        self.connection_pool = pool.SimpleConnectionPool(
            self.minconn,
            self.maxconn,
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            dbname=self.dbname,
        )
        if not self.connection_pool:
            raise Exception("Failed to create PostgreSQL connection pool")
        # 从连接池中获取连接
        conn = self.connection_pool.getconn()
        if not conn:
            spider.logger.error("Failed to get connection from pool")
            return
        try:
            cursor = conn.cursor()
            # Top100榜单表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS novels (
                    id SERIAL PRIMARY KEY,
                    ranking INTEGER,
                    type TEXT,
                    type_link TEXT,
                    name TEXT UNIQUE,
                    link TEXT,
                    latest_chapter TEXT,
                    latest_chapter_link TEXT,
                    update_time TEXT,
                    author TEXT,
                    author_link TEXT,
                    status TEXT,
                    ranking_values TEXT
                )
            """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_novels_name ON novels(name)
            """
            )
            # 章节列表表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS novel_chapter (
                    id SERIAL PRIMARY KEY,
                    novel_name TEXT,
                    volume_title TEXT,
                    chapter_name TEXT,
                    chapter_link TEXT,
                    chapter_info TEXT,
                    chapter_content TEXT,
                    UNIQUE(novel_name, chapter_name)
                )
            """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_chapter_name ON novel_chapter(novel_name, chapter_name)
            """
            )
            conn.commit()
        except Exception as e:
            # 如果发生错误，回滚事务
            conn.rollback()
            spider.logger.error(f"Error inserting data into PostgreSQL: {e}")
        finally:
            # 将连接返回到连接池
            self.connection_pool.putconn(conn)

    def close_spider(self, spider):
        # 在爬虫结束时关闭连接池
        if self.connection_pool:
            self.connection_pool.closeall()

    def process_item(self, item, spider):
        if spider.name != "auto_novel_top100_postgre":
            return item
        if not self.connection_pool:
            return item
        if isinstance(item, SeventeenNovelsItem):
            return self._process_novel_item(item, spider)
        elif isinstance(item, NovelChapterItem) and item.get("ChapterContent"):
            return self._process_chapter_content_item(item, spider)
        elif isinstance(item, NovelChapterItem):
            return self._process_chapter_list_item(item, spider)
        return item

    def _process_novel_item(self, item, spider):
        conn = self.connection_pool.getconn()  # type: ignore
        if not conn:
            spider.logger.error("Failed to get connection from pool")
            return item
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO novels (
                    ranking, type, type_link, name, link,
                    latest_chapter, latest_chapter_link, update_time,
                    author, author_link, status, ranking_values
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (name) DO UPDATE SET
                    ranking=EXCLUDED.ranking,
                    type=EXCLUDED.type,
                    type_link=EXCLUDED.type_link,
                    link=EXCLUDED.link,
                    latest_chapter=EXCLUDED.latest_chapter,
                    latest_chapter_link=EXCLUDED.latest_chapter_link,
                    update_time=EXCLUDED.update_time,
                    author=EXCLUDED.author,
                    author_link=EXCLUDED.author_link,
                    status=EXCLUDED.status,
                    ranking_values=EXCLUDED.ranking_values
            """,
                (
                    item.get("NovelRanking"),
                    item.get("NovelType"),
                    item.get("NovelTypeLink"),
                    item.get("NovelName"),
                    item.get("NovelLink"),
                    item.get("NewlesetChapter"),
                    item.get("NewlesetChapterLink"),
                    item.get("NovelLastUpdateTime"),
                    item.get("Author"),
                    item.get("AuthorLink"),
                    item.get("NovelStatus"),
                    item.get("RankingValues"),
                ),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            spider.logger.error(f"Error inserting data into PostgreSQL: {e}")
        finally:
            self.connection_pool.putconn(conn)  # type: ignore
        return item

    def _process_chapter_content_item(self, item, spider):
        conn = self.connection_pool.getconn()  # type: ignore
        if not conn:
            spider.logger.error("Failed to get connection from pool")
            return item
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO novel_chapter (
                    novel_name, volume_title, chapter_name,
                    chapter_link, chapter_info, chapter_content
                ) VALUES (
                    %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (novel_name, chapter_name) DO UPDATE SET
                    volume_title=EXCLUDED.volume_title,
                    chapter_link=EXCLUDED.chapter_link,
                    chapter_info=EXCLUDED.chapter_info,
                    chapter_content=EXCLUDED.chapter_content
            """,
                (
                    item.get("NovelName"),
                    item.get("VolumeTitle"),
                    item.get("ChapterName"),
                    item.get("ChapterLink"),
                    item.get("ChapterInfo"),
                    item.get("ChapterContent"),
                ),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            spider.logger.error(f"Error inserting data into PostgreSQL: {e}")
        finally:
            self.connection_pool.putconn(conn)  # type: ignore
        return item

    def _process_chapter_list_item(self, item, spider):
        conn = self.connection_pool.getconn()  # type: ignore
        if not conn:
            spider.logger.error("Failed to get connection from pool")
            return item
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO novel_chapter (
                    novel_name, volume_title, chapter_name,
                    chapter_link, chapter_info
                ) VALUES (
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT (novel_name, chapter_name) DO UPDATE SET
                    volume_title=EXCLUDED.volume_title,
                    chapter_link=EXCLUDED.chapter_link,
                    chapter_info=EXCLUDED.chapter_info
            """,
                (
                    item.get("NovelName"),
                    item.get("VolumeTitle"),
                    item.get("ChapterName"),
                    item.get("ChapterLink"),
                    item.get("ChapterInfo"),
                ),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            spider.logger.error(f"Error inserting data into PostgreSQL: {e}")
        finally:
            self.connection_pool.putconn(conn)  # type: ignore
        return item
