---
name: dynain-extract
description: LS-DYNA 数据提取双功能 skill：(1) 从 DYNAIN 文件（*INITIAL_STRESS_* 初始应力/应变，用于重启动/连续分析）按区段提取前 N 个定宽数据字段，输出 text/Excel；(2) 从 LS-DYNA 关键字(.k)文件解析 *NODE 与 *ELEMENT_SOLID（含 ten nodes format 两行/单元），计算每个实体单元形心坐标，输出 CSV。当用户说"提取 dynain 的应力""从 dynain 取前 N 个数据""整理 dynain 的 SOLID 段""dynain 转 excel""读取所有实体单元""求实体单元中心/形心""解析 .k 文件""ls-dyna 关键字文件提取"等时使用。
agent_created: true
---

# dynain-extract — LS-DYNA 数据提取（DYNAIN + .k 关键字）

## 这是什么
本 skill 覆盖 LS-DYNA 两类常见「大文本数据文件」的提取：
- **DYNAIN**（初始条件输入，重启动/连续分析用）：实体/壳/梁单元在某时刻的应力应变。
- **关键字 .k 文件**（前处理/求解输入 deck）：节点坐标 + 单元拓扑，用来求实体单元形心。

两类文件都是纯文本 ASCII，可能十几 MB，且都有「字段不是空格分隔」的坑，必须按特定规则解析。

---

## 功能一：DYNAIN 提取（脚本 `extract_dynain.py`）

### 文件结构
- 按 `*INITIAL_STRESS_XXX` 分段，最后 `*END`。常见顺序 SOLID→SHELL→BEAM→*END。
- 每单元记录 = 1 行 header（8 整数：EID + 7 附加）+ N 行数据。SOLID = 4 行数据。
- SOLID 一条记录共 18 个浮点（4 行：5+5+5+3）；前 6 个 = 6 应力分量(SIGXX,SIGYY,SIGZZ,SIGXY,SIGYZ,SIGXZ)。

### ⚠️ 核心坑：数据是 16 字符定宽，不是空格分隔
每个浮点固定占 16 字符，写满后直接接下一个值，中间无空格。例如：
```
-4.369666081E+04 1.030665708E+04-3.075900234E-05 3.368412746E+03 ...
```
`1.030665708E+04` 与 `-3.075900234E-05` 紧贴。**绝不能按空白 split()**。
正确：对每条数据行按 16 字符切片 `line[k:k+16].strip()`。

### 用法
```bash
python extract_dynain.py D:\桌面\dynain --section SOLID --keep 6 \
    --out D:\桌面\dynain_solid_6stress.txt \
    --xlsx D:\桌面\dynain_solid_6stress.xlsx
```
参数：`src` / `--section`(SOLID|SHELL|BEAM) / `--data-lines`(每条记录数据行数) / `--keep`(保留前 N 值) / `--out`(text) / `--xlsx`(Excel)。

### 输出约定
- text：首行写回卡片行，每条记录 header 原样 + 一行 keep 个数值(`{:.9E}`)，末尾 `*END`，仍为合法 DYNAIN 片段。
- xlsx：openpyxl，每行一记录；应力列设科学计数法 `0.000000000E+00`、列宽~150px（否则 `##########`）。

---

## 功能二：LS-DYNA .k 实体单元形心提取（脚本 `extract_k_centroids.py`）

### 文件结构
- `*NODE`：`nid x y z tc rc`（自由格式，空格分隔，取前 4 列）。
- `*ELEMENT_SOLID`：`eid pid n1..n8`（1 行/单元，8 节点六面体）。
- `*ELEMENT_SOLID (ten nodes format)`：**2 行/单元** —— 第 1 行 `eid pid`，第 2 行 10 个节点号 `n1..n10`（不足 10 时尾部为 0）；用于 10 节点四面体/高阶单元。

### ⚠️ 核心坑：ten nodes format 是「两行/单元」
若按 1 行/单元解析，会把第 2 行（节点号）误当成新单元的 `eid pid`，且把节点号当坐标，算出**错误形心 + 重复/幻影单元**（行数会 ≈ 单元数的 2 倍）。必须配对：先读 `eid pid`，下一行才是节点号。脚本已内置该逻辑。

### 形心算法
单元形心 = 该单元所有「>0 的节点号」对应坐标的算术平均（节点号 0 视为未用，跳过；不区分单元类型，六面体/四面体统一按平均）。

### 用法
```bash
python extract_k_centroids.py D:\桌面\40-0.1.k --out D:\桌面\solid_centroids.csv
# 只取某部件：
python extract_k_centroids.py D:\桌面\40-0.1.k --pid 7 --out D:\桌面\solid_pid7.csv
```
参数：`src`(必需) / `--out`(CSV 路径，默认 solid_centroids.csv) / `--pid`(可选，只输出该部件号单元)。

### 输出
CSV：`eid,pid,cx,cy,cz`（单元号、部件号、形心 x/y/z，6 位小数）。eid 唯一、含未知节点的单元会被跳过并提示。

---

## 本机环境注意（来自实测）
- **D:\桌面 会自动删除新建的 `.xlsx`**（实时防护；`.txt`/`.xlsm` 不受影响）。Excel 改存 `.xlsm` 或先存工作区再移动。
- 编辑已打开本地表格走 `tencent-docs-routing` → `tencent-local-office-edit`。
- 解析大文件用 Python（managed 运行时），无需第三方库（纯标准库即可）。
