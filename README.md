# dynain-extract

LS-DYNA **DYNAIN** 初始应力/应变文件提取 skill（WorkBuddy）。

从 LS-DYNA 重启动/连续分析用的 DYNAIN 文件（`*INITIAL_STRESS_*` 关键字）中，
按区段、按前导字段数提取数据，整理为干净的 text 片段或 Excel。

## 文件
- `SKILL.md` — 用法、文件格式说明与关键坑点（⚠️ 数据是 **16 字符定宽**字段，不是空格分隔）。
- `extract_dynain.py` — 参数化提取脚本。

## 快速开始

```bash
python extract_dynain.py D:\path\to\dynain --section SOLID --keep 6 \
       --out out.txt --xlsx out.xlsx
```

参数：`src` 源文件；`--section` SOLID/SHELL/BEAM（默认 SOLID）；
`--keep` 每条记录保留前 N 个数据（默认 6=6 应力分量）；`--out`/`--xlsx` 输出路径。

详见 `SKILL.md`。
