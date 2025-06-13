# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class SeventeenNovelsItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()

    NovelRanking = scrapy.Field()  # 小说排名
    NovelType = scrapy.Field()  # 小说类别
    NovelTypeLink = scrapy.Field()  # 小说类别
    NovelName = scrapy.Field()  # 小说名称
    NovelLink = scrapy.Field()  # 小说链接
    NewlesetChapter = scrapy.Field()  # 最新章节
    NewlesetChapterLink = scrapy.Field()  # 最新章节链接
    NovelLastUpdateTime = scrapy.Field()  # 最后更新时间
    Author = scrapy.Field()  # 小说作者
    AuthorLink = scrapy.Field()  # 小说作者链接
    NovelStatus = scrapy.Field()  # 小说状态
    RankingValues = scrapy.Field()  # 榜单数值


class NovelChaptorItem(scrapy.Item):
    NovelName = scrapy.Field()
    VolumeTitle = scrapy.Field()
    ChapterName = scrapy.Field()
    ChapterLink = scrapy.Field()
    ChapterInfo = scrapy.Field()
    ChapterContent = scrapy.Field()  # 新增字段
