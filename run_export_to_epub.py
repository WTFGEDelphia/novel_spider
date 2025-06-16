import sqlite3
import re
from ebooklib import epub

# 中文数字转阿拉伯数字的简单实现
def chinese_to_arabic(cn: str) -> int:
    """
    更健壮的中文数字转阿拉伯数字，支持十、十一、一百零一、两百五十六等表达
    """
    cn_num = {'零':0, '一':1, '二':2, '三':3, '四':4, '五':5, '六':6, '七':7, '八':8, '九':9, '〇':0, '两':2}
    cn_unit = {'十':10, '百':100, '千':1000, '万':10000, '亿':100000000}
    result, unit, num = 0, 1, 0
    cn = cn.strip()
    if not cn:
        return 0
    # 特殊处理“十X”=10+X，“十一”=10+1，“二十”=2*10
    if cn.startswith('十'):
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
    return re.sub(r'([一二三四五六七八九十百千万亿〇两])\1+', r'\1', name)

def extract_chapter_number(chapter_name):
    """
    提取章节号，只取“第xxx章”中的xxx部分，忽略后续内容（如括号、空格等）
    """
    m = re.search(r'第\s*([一二三四五六七八九零十百千万亿〇两]+)\s*(?:章|更)', chapter_name)
    if m:
        clean_num = clean_chapter_name(m.group(1))
        return chinese_to_arabic(clean_num)
    return float('inf')  # 提取不到数字的章节排在最后

novel_name = '修罗武神'
db_path = 'output/novel_data.db'
output_epub = f'{novel_name}.epub'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute(
    '''SELECT chapter_name, volume_title, chapter_content FROM novel_chapter
    WHERE novel_name = ? and chapter_content is not null ORDER BY chapter_name ASC'''
    , (novel_name,))
rows = cursor.fetchall()
# 只保留带“第...章”的章节
rows = [row for row in rows if re.search(r'第\s*(?:[一二三四五六七八九零十百千万亿〇两]+|[\d]+)\s*(?:章|更)', row[0])]
# 按章节号排序
rows.sort(key=lambda x: extract_chapter_number(x[0]))

for chapter_name, volume_title, chapter_content in rows:
    print(chapter_name)

# 创建EPUB电子书
book = epub.EpubBook()
book.set_identifier('id123456')
book.set_title(novel_name)
book.set_language('zh')
book.add_author('未知')

epub_chapters = []
for idx, (chapter_name, volume_title, chapter_content) in enumerate(rows):
    c = epub.EpubHtml(title=chapter_name, file_name=f'chap_{idx+1}.xhtml', lang='zh')
    # 章节内容转为HTML，换行转为<br/>
    safe_content = chapter_content.replace('\n', '<br/>') if chapter_content else ''
    c.content = f'<h1>{chapter_name}</h1><h2>{volume_title}</h2><p>{safe_content}</p>'
    book.add_item(c)
    epub_chapters.append(c)

# 设置目录和spine
book.toc = tuple(epub_chapters)
book.spine = ['nav'] + epub_chapters
book.add_item(epub.EpubNcx())
book.add_item(epub.EpubNav())

# 写入EPUB文件
epub.write_epub(output_epub, book, {})

print(f'已生成EPUB电子书：{output_epub}')
