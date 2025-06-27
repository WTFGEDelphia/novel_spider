import os
import re
import sqlite3
import importlib.util
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.abspath(os.path.join(BASE_DIR, "output"))
DB_FILE = os.path.join(OUTPUT_DIR, "novel_data.db")
EBOOKS_DIR = os.path.join(BASE_DIR, "output", "ebooks")
os.makedirs(EBOOKS_DIR, exist_ok=True)

settings_path = os.path.join(BASE_DIR, "seventeen_novels", "settings.py")
use_pg = os.path.exists(settings_path)
if use_pg:
    import psycopg2

    spec = importlib.util.spec_from_file_location("settings", settings_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 settings.py")
    settings = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(settings)

try:
    from ebooklib import epub

    has_epub = True
except ImportError:
    has_epub = False


def fetch_all_novels(conn, use_pg=False):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name, author FROM novels")
        return cursor.fetchall()
    except Exception:
        cursor.execute("SELECT DISTINCT novel_name FROM novel_chapter")
        return [(row[0], "未知") for row in cursor.fetchall()]


# 中文数字转阿拉伯数字
def chinese_to_arabic(cn: str) -> int:
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
    return re.sub(r"([一二三四五六七八九十百千万亿〇两点])\1+", r"\1", name)


def extract_chapter_number(chapter_name):
    # 先匹配阿拉伯数字
    m = re.search(r"第\s*0*([0-9]+)\s*(?:章|回|节|卷|更)", chapter_name)
    if m:
        return int(m.group(1))
    # 再匹配中文数字
    m = re.search(
        r"第\s*([一二三四五六七八九零十百千万亿〇两点]+)\s*(?:章|回|节|卷|更)",
        chapter_name,
    )
    if m:
        clean_num = clean_chapter_name(m.group(1))
        return chinese_to_arabic(clean_num)
    return float("inf")


def fetch_chapters_for_novel(conn, novel_name, use_pg=False):
    cursor = conn.cursor()
    if use_pg:
        cursor.execute(
            """
            SELECT volume_title, chapter_name, chapter_content FROM novel_chapter JOIN novels ON novels.name = novel_chapter.novel_name
            WHERE novel_name = %s AND chapter_content is not null ORDER BY chapter_name ASC
            """,
            (novel_name,),
        )
    else:
        cursor.execute(
            """
            SELECT volume_title, chapter_name, chapter_content FROM novel_chapter JOIN novels ON novels.name = novel_chapter.novel_name
            WHERE novel_name = ? and chapter_content is not null ORDER BY chapter_name ASC
            """,
            (novel_name,),
        )
    chapters = cursor.fetchall()
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
    filtered_chapters.sort(key=lambda x: extract_chapter_number(x[1]))
    return filtered_chapters


def export_novel_to_txt(novel_name, author, chapters):
    safe_name = "".join(
        c for c in novel_name if c.isalnum() or c in (" ", "_", "-")
    ).rstrip()
    txt_path = os.path.join(EBOOKS_DIR, f"{safe_name}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"{novel_name} 作者：{author}\n\n")
        last_volume = None
        for volume, chapter, content in chapters:
            if volume and volume != last_volume:
                f.write(f"\n【{volume}】\n")
                last_volume = volume
            if chapter:
                f.write(f"\n{chapter}\n")
            if content:
                f.write(f"{content}\n")
    print(f"已导出: {txt_path}")


def export_novel_to_epub(novel_name, author, chapters):
    if not has_epub:
        print("未安装 ebooklib，无法导出 epub。请先 pip install ebooklib")
        return
    output_epub = os.path.join(EBOOKS_DIR, f"{novel_name}.epub")
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
        safe_content = chapter_content.replace("\n", "<br/>") if chapter_content else ""
        c.content = (
            f"<h1>{chapter_name}</h1><h2>{volume_title}</h2><p>{safe_content}</p>"
        )
        book.add_item(c)
        epub_chapters.append(c)
    book.toc = tuple(epub_chapters)  # type: ignore
    book.spine = ["nav"] + epub_chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(output_epub, book, {})
    print(f"已生成EPUB电子书：{output_epub}")


def main(format="txt"):
    if use_pg:
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
    else:
        if not os.path.exists(DB_FILE):
            print(f"数据库未找到: {DB_FILE}")
            return
        conn = sqlite3.connect(DB_FILE)
    novels = fetch_all_novels(conn, use_pg=use_pg)
    if not novels:
        print("未找到任何小说数据。")
        return
    for novel_name, author in novels:
        chapters = fetch_chapters_for_novel(conn, novel_name, use_pg=use_pg)
        if chapters:
            if format == "epub":
                export_novel_to_epub(novel_name, author, chapters)
            else:
                export_novel_to_txt(novel_name, author, chapters)
    conn.close()
    print("全部小说导出完成。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="导出小说为txt或epub")
    parser.add_argument(
        "--format", choices=["txt", "epub"], default="txt", help="导出格式"
    )
    args = parser.parse_args()
    main(format=args.format)
