#!/usr/bin/env python3
"""DYNAIN 提取工具 — 从 LS-DYNA DYNAIN 文件中提取指定区段、前 N 个数据字段。

关键：数据行是 16 字符定宽字段（不是空格分隔），必须按 16 字符切片解析。
用法示例：
    python extract_dynain.py D:\\桌面\\dynain --section SOLID --keep 6 \
        --out D:\\桌面\\dynain_solid_6stress.txt \
        --xlsx D:\\桌面\\dynain_solid_6stress.xlsx
"""
import argparse
import os

WIDTH = 16  # 每个浮点字段固定 16 字符


def parse_data_lines(lines, data_lines):
    """把 data_lines 条数据行按 16 字符定宽切片，返回浮点值列表。"""
    vals = []
    for ln in lines[:data_lines]:
        s = ln.rstrip("\n")
        for k in range(0, len(s), WIDTH):
            chunk = s[k:k + WIDTH].strip()
            if chunk:
                vals.append(chunk)
    return vals


def main():
    ap = argparse.ArgumentParser(description="Extract leading fields from a LS-DYNA DYNAIN file")
    ap.add_argument("src", help="DYNAIN 源文件路径")
    ap.add_argument("--section", default="SOLID",
                    choices=["SOLID", "SHELL", "BEAM"],
                    help="要提取的区段（不含 *INITIAL_STRESS_ 前缀），默认 SOLID")
    ap.add_argument("--data-lines", type=int, default=4,
                    help="每条记录的数据行数（SOLID=4），其它段按需调整")
    ap.add_argument("--keep", type=int, default=6,
                    help="每条记录只保留前 N 个数据值（默认 6 = 6 应力分量）")
    ap.add_argument("--out", default=None, help="输出整理后 text 的路径")
    ap.add_argument("--xlsx", default=None, help="同时输出 xlsx 的路径（可选）")
    args = ap.parse_args()

    card = f"*INITIAL_STRESS_{args.section.upper()}"

    with open(args.src, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    # 1) 定位区段卡片行
    start = None
    for i, ln in enumerate(lines):
        if ln.strip().upper().startswith(card.upper()):
            start = i
            break
    if start is None:
        raise SystemExit(f"未找到卡片 {card}，可用区段见文件内 *INITIAL_STRESS_* 行")

    # 2) 区段 body = 卡片下一行到下一个 *卡片行之间
    body = []
    for ln in lines[start + 1:]:
        if ln.lstrip().startswith("*"):
            break
        body.append(ln)

    # 3) 按 1 行 header + data_lines 行数据 切记录
    records = []  # 每条 = (header原始行, [前 keep 个浮点字符串])
    i = 0
    while i + args.data_lines <= len(body):
        header = body[i]
        if not header.split() or header.lstrip().startswith("*"):
            break
        vals = parse_data_lines(body[i + 1:i + 1 + args.data_lines], args.data_lines)
        if not vals:
            break
        records.append((header.rstrip("\n"), vals[:args.keep]))
        i += 1 + args.data_lines

    if not records:
        raise SystemExit("未解析出任何记录，请检查 --data-lines 是否正确")

    # 4a) 输出 text（干净 DYNAIN 片段）
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as g:
            g.write(lines[start].rstrip("\n") + "\n")  # 卡片行
            for header, vals in records:
                g.write(header + "\n")
                g.write(" ".join(f"{float(v):.9E}" for v in vals) + "\n")
            g.write("*END\n")
        print(f"[text] {len(records)} 条记录 -> {args.out}")

    # 4b) 输出 xlsx
    if args.xlsx:
        try:
            import openpyxl
        except ImportError:
            raise SystemExit("需要 openpyxl：pip install openpyxl")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = args.section.upper()
        headers = ["EID"] + [f"H{n}" for n in range(2, 9)] + \
                  ["SIGXX", "SIGYY", "SIGZZ", "SIGXY", "SIGYZ", "SIGXZ"][:args.keep]
        # 仅保留实际列数（header 8 整数 + keep 数值）
        coln = 8 + args.keep
        for c, name in enumerate(headers[:coln], start=1):
            cell = ws.cell(row=1, column=c, value=name)
            cell.font = openpyxl.styles.Font(bold=True)
        for r, (header, vals) in enumerate(records, start=2):
            ints = [int(x) for x in header.split()]
            for c, v in enumerate(ints[:8], start=1):
                ws.cell(row=r, column=c, value=v)
            for c, v in enumerate(vals, start=9):
                ws.cell(row=r, column=c, value=float(v))
        # 应力列设科学计数法 + 列宽
        from openpyxl.styles import Font
        for c in range(9, 9 + args.keep):
            for r in range(2, len(records) + 2):
                ws.cell(row=r, column=c).number_format = "0.000000000E+00"
            ws.column_dimensions[openpyxl.utils.get_column_letter(c)].width = 19.5
        ws.freeze_panes = "A2"
        wb.save(args.xlsx)
        print(f"[xlsx] {len(records)} 条记录 -> {args.xlsx}")

    if not args.out and not args.xlsx:
        # 默认打印前几条到控制台
        for header, vals in records[:3]:
            print(header)
            print(" ".join(f"{float(v):.9E}" for v in vals))


if __name__ == "__main__":
    main()
