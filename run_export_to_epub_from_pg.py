from ebooklib import epub
import os
import re
import psycopg2
import os
import importlib.util

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.abspath(os.path.join(BASE_DIR, "output"))
EBOOKS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "output", "ebooks"
)
os.makedirs(EBOOKS_DIR, exist_ok=True)
settings_path = os.path.join(BASE_DIR, "seventeen_novels", "settings.py")
spec = importlib.util.spec_from_file_location("settings", settings_path)
settings = importlib.util.module_from_spec(spec)  # type: ignore
spec.loader.exec_module(settings)  # type: ignore


def fetch_all_novels(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name, author FROM novels")
    return cursor.fetchall()


# 中文数字转阿拉伯数字的简单实现
def chinese_to_arabic(cn: str) -> int:
    """
    更健壮的中文数字转阿拉伯数字，支持十、十一、一百零一、两百五十六等表达
    """
    cn_num = {
        "零": 0,
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "〇": 0,
        "两": 2,
    }
    cn_unit = {
        "十": 10,
        "百": 100,
        "千": 1000,
        "点": 1000,
        "万": 10000,
        "亿": 100000000,
    }
    unit, num = 1, 0
    cn = cn.strip()
    if not cn:
        return 0
    # 特殊处理“十X”=10+X，“十一”=10+1，“二十”=2*10
    if cn.startswith("十"):
        if len(cn) == 1:
            return 10
        else:
            return 10 + chinese_to_arabic(cn[1:])
    total = 0
    unit = 1
    i = len(cn) - 1
    while i >= 0:
        c = cn[i]
        if c in cn_num:
            num = cn_num[c]
            total += num * unit
            i -= 1
        elif c in cn_unit:
            unit = cn_unit[c]
            if unit in (10000, 100000000):
                if total == 0:
                    total = 1
                total = total * unit
            i -= 1
        else:
            i -= 1
    return total


def clean_chapter_name(name):
    # 把“七百七百四十二”变成“七百四十二”
    # 连续重复的“百”“千”等只保留一个
    return re.sub(r"([一二三四五六七八九十百千万亿〇两点])\1+", r"\1", name)


def extract_chapter_number(chapter_name):
    """
    提取章节号，只取“第xxx章”中的xxx部分，忽略后续内容（如括号、空格等）
    """
    m = re.search(
        r"第\s*([一二三四五六七八九零十百千万亿〇两点]+)\s*(?:章|回|节|卷|更)",
        chapter_name,
    )
    if m:
        clean_num = clean_chapter_name(m.group(1))
        return chinese_to_arabic(clean_num)
    return float("inf")  # 提取不到数字的章节排在最后


def fetch_chapters_for_novel(conn, novel_name):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT volume_title, chapter_name, chapter_content FROM novel_chapter JOIN novels ON novels.name = novel_chapter.novel_name
        WHERE novel_name = %s AND chapter_content is not null ORDER BY chapter_name ASC
        """,
        (novel_name,),
    )
    chapters = cursor.fetchall()
    # 只保留章节名中包含“第XX章/回/节/卷/更”的项
    filtered_chapters = [
        x
        for x in chapters
        if x[1]
        and (
            ("第" in x[1])
            and (
                ("章" in x[1])
                or ("回" in x[1])
                or ("节" in x[1])
                or ("卷" in x[1])
                or ("更" in x[1])
            )
        )
    ]
    # 提取章节编号并排序
    filtered_chapters.sort(key=lambda x: extract_chapter_number(x[1]))
    # 打印调试信息
    # for ch in filtered_chapters:
    #     print(
    #         f"Chapter Name: {ch[1]}, Extracted Number: {extract_chapter_number(ch[1])}"
    #     )
    return filtered_chapters


def export_novel_to_epub(novel_name, author="未知", chapters=[]):
    output_epub = os.path.join(EBOOKS_DIR, f"{novel_name}.epub")

    # 创建EPUB电子书
    book = epub.EpubBook()
    book.set_identifier("id123456")
    book.set_title(novel_name)
    book.set_language("zh")
    book.add_author(author)

    epub_chapters = []
    for idx, (volume_title, chapter_name, chapter_content) in enumerate(chapters):
        c = epub.EpubHtml(
            title=chapter_name, file_name=f"chap_{idx+1}.xhtml", lang="zh"
        )
        # 章节内容转为HTML，换行转为<br/>
        safe_content = chapter_content.replace("\n", "<br/>") if chapter_content else ""
        c.content = (
            f"<h1>{chapter_name}</h1><h2>{volume_title}</h2><p>{safe_content}</p>"
        )
        book.add_item(c)
        epub_chapters.append(c)

    # 设置目录和spine
    book.toc = tuple(epub_chapters)  # type: ignore
    book.spine = ["nav"] + epub_chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # 写入EPUB文件
    epub.write_epub(output_epub, book, {})
    print(f"已生成EPUB电子书：{output_epub}")


def main():
    pg_conn_params = {
        "host": getattr(settings, "PG_HOST"),
        "port": getattr(settings, "PG_PORT"),
        "user": getattr(settings, "PG_USER"),
        "password": getattr(settings, "PG_PASSWORD"),
        "database": getattr(settings, "PG_DBNAME"),
    }
    conn = psycopg2.connect(
        host=pg_conn_params["host"],
        port=pg_conn_params["port"],
        user=pg_conn_params["user"],
        password=pg_conn_params["password"],
        database=pg_conn_params["database"],
    )
    novels = fetch_all_novels(conn)
    if not novels:
        print("未找到任何小说数据。")
        return
    for novel_name, author in novels:
        print(f"导出小说：{novel_name} 作者：{author}")
        chapters = fetch_chapters_for_novel(conn, novel_name)
        if chapters:
            export_novel_to_epub(novel_name, author, chapters)
    conn.close()
    print("全部小说导出完成。")


if __name__ == "__main__":
    main()
