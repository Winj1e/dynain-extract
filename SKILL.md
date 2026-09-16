---
name: dynain-extract
description: 从 LS-DYNA 的 DYNAIN 文件（*INITIAL_STRESS_* 初始应力/应变输入，常用于重启动/连续分析）中提取指定区段、指定数量的前导数据字段，输出为整理后的 text 文件或 Excel。当用户说"提取 dynain 的应力""从 dynain 取前 N 个数据""整理 dynain 的 SOLID 段""dynain 转 excel"等时使用。
agent_created: true
---

# dynain-extract — LS-DYNA DYNAIN 数据提取

## 这是什么
DYNAIN 是 LS-DYNA 在一步分析结束后导出的**初始条件输入文件**，可被下一步分析用
`*INITIAL_STRESS_*` 关键字读回，实现重启动/连续分析。典型内容是实体(SOLID)/壳(SHELL)/
梁(BEAM) 单元在某时刻的应力、应变等状态。文件是**纯文本 ASCII**，可能很大（十几 MB）。

## 文件结构（务必先理解，否则会解析错）
- 文件按**关键字卡片**分段，每段以 `*INITIAL_STRESS_XXX` 开头，最后 `*END` 结束。
  常见顺序：`*INITIAL_STRESS_SOLID` → `*INITIAL_STRESS_SHELL` → `*INITIAL_STRESS_BEAM` → `*END`。
- 每个单元记录 = **1 行 header + N 行数据行**：
  - SOLID 段（最常见）：每记录 = 1 行 header（8 个整数：EID + 7 个附加整数）+ **4 行数据**。
  - 数据行里的浮点数 = **本条记录的全部数值**；SOLID 一条记录共 **18 个浮点**
    （4 行分别有 5+5+5+3 个值）。
  - 前 6 个数据值 = **6 个应力分量**（顺序 SIGXX, SIGYY, SIGZZ, SIGXY, SIGYZ, SIGXZ）。

### ⚠️ 最关键的一个坑：数据是「16 字符定宽」字段，不是空格分隔
DYNAIN 数据行每个浮点固定占 **16 个字符**（含符号、小数点、E±阶码），写满 16 列后
**直接接下一个值，中间没有空格**。例如：
```
-4.369666081E+04 1.030665708E+04-3.075900234E+05 3.368412746E+03 ...
```
`1.030665708E+04` 与 `-3.075900234E+05` 之间是**紧贴**的（前者 16 列正好结束于负号前）。
因此 **绝对不能按空白 split() 来解析**——那样会把两个数黏成一个坏字符串。
正确做法：对每条数据行按 **16 字符为步长切片** (`line[k:k+16].strip()`)。
header 行的整数也是定宽的（约 10 字符/个），但可直接整行保留、无需拆解。

## 提取流程（通用套路）
1. 读全文件，找目标区段卡片行（`*INITIAL_STRESS_<SECTION>`，默认 SOLID）。
2. 从该卡片下一行开始，到下一个 `*...` 卡片行为止，即为本段 body。
3. body 内按「1 行 header + `data_lines` 行数据」循环切每条记录。
4. 每条记录的 4 行数据按 16 字符定宽切片，得到该记录的全部浮点值列表。
5. 取前 `keep` 个浮点（默认 6 = 6 应力分量），与 header 一起输出。
6. 输出 text（整理成干净 DYNAIN 片段）和/或 Excel。

## 输出约定
- **text**：首行写回 `*INITIAL_STRESS_<SECTION>` 卡片，随后每条记录两行——
  header 原样 + 一行 `keep` 个数值（空格分隔，用 `{:.9E}` 保持精度），末尾补 `*END`。
  这样产物仍是合法、可被 LS-DYNA 读回的输入片段。
- **Excel**：用 openpyxl。建议结构 = 每行一个记录：
  第 1 列 EID（header 第 1 个整数）+ 后续列 `keep` 个数值。表头写字段名
  （EID, H2…H8, SIGXX, SIGYY, SIGZZ, SIGXY, SIGYZ, SIGXZ…）。
  应力列务必设置**科学计数法数字格式** `0.000000000E+00`，并把列宽设到 ~150px，
  否则单元格会显示成 `##########`。

## Excel 在本机环境的两点注意（来自实测）
- **D:\桌面 会自动删除新建的 `.xlsx` 文件**（疑似实时防护，`.txt`/`.xlsm` 不受影响）。
  把 Excel 放到桌面时改存 `.xlsm`，或先存到工作区再由用户自行移动。
- 编辑已打开的本地表格请走 `tencent-docs-routing` → `tencent-local-office-edit`：
  设科学计数法用 `sheet_set_cell_style` 的 `format.number_format_pattern`；
  设列宽用 `sheet_set_dimension_size`（`dimension_type=col`, `size` 单位像素）；
  改完务必 `save_file`。

## 脚本
本 skill 目录附带 `extract_dynain.py`（参数化，无需记忆格式细节），典型用法：
```bash
python extract_dynain.py D:\桌面\dynain --section SOLID --keep 6 \
       --out D:\桌面\dynain_solid_6stress.txt \
       --xlsx D:\桌面\dynain_solid_6stress.xlsx
```
参数：
- `src`：DYNAIN 源文件
- `--section`：SOLID / SHELL / BEAM（默认 SOLID）
- `--data-lines`：每条记录数据行数（SOLID=4，其它段按需）
- `--keep`：每条记录保留前 N 个数据值（默认 6）
- `--out`：输出 text 路径
- `--xlsx`：同时输出 xlsx 路径（可选）

> 若用户还要求按材料号/应力阈值筛选、或只留 EID+数值，在脚本基础上加过滤即可，
> 但核心的「16 字符定宽解析」不要动。
