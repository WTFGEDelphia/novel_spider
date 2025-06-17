import os
import re
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.abspath(os.path.join(BASE_DIR, "output"))
DB_FILE = os.path.join(OUTPUT_DIR, "novel_data.db")
EBOOKS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "ebooks")
os.makedirs(EBOOKS_DIR, exist_ok=True)

def fetch_all_novels(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT novel_name FROM novel_chapter")
    return [row[0] for row in cursor.fetchall()]

# 定义一个函数，将中文数字转换为阿拉伯数字
def chinese_to_arabic(cn_num_str):
    CN_NUM = {
        '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100, '千': 1000, '万': 10000
    }
    result = 0  # 最终结果
    current = 0  # 当前数值
    unit = 1  # 当前单位

    for char in cn_num_str:
        if char in CN_NUM:
            value = CN_NUM[char]
            if value >= 10:  # 如果是单位（十、百、千、万）
                if current == 0:  # 如果当前数值为0，表示直接进位
                    current = 1
                current *= value
                unit = value
            else:  # 如果是个位数
                if unit > 10:  # 如果当前单位大于10，需要将当前数值累加到结果
                    result += current
                    current = 0
                current += value
        else:
            return None  # 如果包含非数字字符，返回 None

    result += current  # 将最后的当前数值累加到结果
    return result

def extract_chapter_number(chapter_name):
    # 使用正则表达式提取章节编号
        match = re.search(r'第\s*([零一两点二三四五六七八九十百千万\d]+)\s*[章回节卷更]', chapter_name)
        if match:
            chapter_num_str = match.group(1)
            # 替换“点”为“千”或“百”（根据上下文）
            chapter_num_str = chapter_num_str.replace("点", "千")
            # 尝试直接提取阿拉伯数字
            if chapter_num_str.isdigit():
                return int(chapter_num_str)
            else:
                # 尝试将中文数字转换为阿拉伯数字
                chapter_num = chinese_to_arabic(chapter_num_str)
                # print(f"{chapter_num_str} -> {chapter_num}")
                return chapter_num
        return float('inf')  # 如果无法提取数字，返回无穷大

def fetch_chapters_for_novel(conn, novel_name):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT volume_title, chapter_name, chapter_content
        FROM novel_chapter
        WHERE novel_name=?
    """, (novel_name,))
    chapters = cursor.fetchall()
    # 只保留章节名中包含“第XX章/回/节/卷/更”的项
    filtered_chapters = [
        x for x in chapters
        if x[1] and (
            ("第" in x[1]) and (
                ("章" in x[1]) or ("回" in x[1]) or ("节" in x[1]) or ("卷" in x[1]) or ("更" in x[1])
            )
        )
    ]
    # 提取章节编号并排序
    filtered_chapters.sort(key=lambda x: extract_chapter_number(x[1]))
    # 打印调试信息
    # for ch in filtered_chapters:
    #     print(f"Chapter Name: {ch[1]}, Extracted Number: {extract_chapter_number(ch[1])}")
    return filtered_chapters

def export_novel_to_txt(novel_name, chapters):
    # 处理文件名中的非法字符
    safe_name = "".join(c for c in novel_name if c.isalnum() or c in (' ', '_', '-')).rstrip()
    txt_path = os.path.join(EBOOKS_DIR, f"{safe_name}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"{novel_name}\n\n")
        last_volume = None
        for volume, chapter, content in chapters:
            print(f"导出: {volume}-{chapter}")
            if volume and volume != last_volume:
                f.write(f"\n【{volume}】\n")
                last_volume = volume
            # if chapter:
            #     f.write(f"\n{chapter}\n")
            if content:
                f.write(f"{content}\n")
    print(f"已导出: {txt_path}")

def main():
    if not os.path.exists(DB_FILE):
        print(f"数据库未找到: {DB_FILE}")
        return
    conn = sqlite3.connect(DB_FILE)
    novels = fetch_all_novels(conn)
    if not novels:
        print("未找到任何小说数据。")
        return
    for novel_name in novels:
        chapters = fetch_chapters_for_novel(conn, novel_name)
        if chapters:
            export_novel_to_txt(novel_name, chapters)
    conn.close()
    print("全部小说导出完成。")

if __name__ == "__main__":
    main()
