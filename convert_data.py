"""
将 C_memorize 目录下所有 350实词-*.xlsx 文件转换为统一的 words.json。
每个 xlsx 文件包含一个词的多义项数据。

Excel 结构：
  第1行: "序号．汉字（拼音）"
  第2行: 空
  第3行: 词性 | 词义 | 例句 | 篇名
  第4行起: 数据行（词性列有纵向合并单元格）

转换规则：
  - 词性合并单元格 → 向下填充
  - 词义为 None 但例句有值 → 沿用上一个非空词义
  - 输出 JSON 结构: [{word, pinyin, index, senses: [{meaning, example, source}]}]
"""

import json
import re
import os
from glob import glob

import openpyxl


def parse_title(title):
    """从 '1．哀（āi）' 解析出序号、字、拼音"""
    m = re.match(r'(\d+)．(.+?)（(.+?)）', title.strip())
    if m:
        return int(m.group(1)), m.group(2), m.group(3)
    return None, title, ""


def convert_xlsx(filepath):
    """转换单个 xlsx 文件，返回一个词条 dict"""
    wb = openpyxl.load_workbook(filepath)
    ws = wb.active

    # 获取所有行数据（去掉 None 行）
    rows = []
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True):
        cells = list(row)
        if any(c is not None for c in cells):
            rows.append(cells)

    if len(rows) < 4:
        return None

    # 解析标题
    title = str(rows[0][0]) if rows[0][0] else ""
    index, word, pinyin = parse_title(title)

    # 跳过标题行和表头行，数据从 rows[2] 开始
    senses = []
    current_cixing = ""
    current_ciyi = ""

    for row in rows[2:]:
        cixing = str(row[0]).strip() if row[0] else ""
        ciyi = str(row[1]).strip() if row[1] else ""
        liju = str(row[2]).strip() if row[2] else ""
        pianming = str(row[3]).strip() if row[3] else ""

        if cixing:
            current_cixing = cixing
        if ciyi:
            current_ciyi = ciyi

        if liju:
            # 例句中高亮目标字（用 <b> 包裹）
            liju_highlighted = liju.replace(word, f"<b>{word}</b>")
            senses.append({
                "meaning": current_ciyi,
                "example": liju_highlighted,
                "source": pianming
            })

    return {
        "word": word,
        "pinyin": pinyin,
        "index": index,
        "senses": senses
    }


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pattern = os.path.join(base_dir, "350实词-*.xlsx")
    files = sorted(glob(pattern))

    if not files:
        print("未找到 350实词-*.xlsx 文件！")
        return

    words = []
    for f in files:
        entry = convert_xlsx(f)
        if entry:
            words.append(entry)
            print(f"已转换: {os.path.basename(f)} → {entry['word']}（{entry['pinyin']}），{len(entry['senses'])}个义项")

    # 按 index 排序
    words.sort(key=lambda w: w["index"])

    output_path = os.path.join(base_dir, "words.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

    print(f"\n共转换 {len(words)} 个词，输出至 {output_path}")


if __name__ == "__main__":
    main()
