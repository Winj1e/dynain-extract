#!/usr/bin/env python3
"""LS-DYNA .k 实体单元形心提取。

从 LS-DYNA 关键字文件中解析 *NODE 与 *ELEMENT_SOLID（含 ten nodes format 两行/单元），
计算每个实体单元形心 = 其全部有效节点(>0)坐标的算术平均。

⚠️ 关键：*ELEMENT_SOLID (ten nodes format) 是「2 行/单元」——
     第 1 行 `eid pid`，第 2 行 10 个节点号。必须配对，不能按 1 行/单元解析。

用法示例：
    python extract_k_centroids.py D:\\桌面\\40-0.1.k --out D:\\桌面\\solid_centroids.csv
    python extract_k_centroids.py D:\\桌面\\40-0.1.k --pid 7 --out D:\\桌面\\solid_pid7.csv
"""
import argparse


def main():
    ap = argparse.ArgumentParser(
        description="Compute centroid of every solid element in a LS-DYNA .k keyword file")
    ap.add_argument("src", help="LS-DYNA .k 关键字文件路径")
    ap.add_argument("--out", default="solid_centroids.csv",
                    help="输出 CSV 路径（默认 solid_centroids.csv）")
    ap.add_argument("--pid", type=int, default=None,
                    help="只输出指定部件号(pid)的单元（可选）")
    args = ap.parse_args()

    nodes = {}          # nid -> (x, y, z)
    elems = []          # (eid, pid, cx, cy, cz)
    skipped = 0
    mode = None         # 'node' | 'elem' | 'elem10'
    pending = None      # (eid, pid) for ten-nodes 2-line format

    with open(args.src, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if s.startswith("*"):
                mode = None
                pending = None
                if s == "*NODE":
                    mode = "node"
                elif s.startswith("*ELEMENT_SOLID"):
                    mode = "elem10" if "ten nodes" in s else "elem"
                continue
            if not s or s.startswith("$"):
                continue
            toks = s.split()
            if mode == "node":
                nid = int(toks[0])
                nodes[nid] = (float(toks[1]), float(toks[2]), float(toks[3]))
            elif mode == "elem":
                eid = int(toks[0]); pid = int(toks[1])
                cx, cy, cz, cnt, ok = _avg(nodes, toks[2:])
                if ok and cnt > 0:
                    elems.append((eid, pid, cx, cy, cz))
                else:
                    skipped += 1
            elif mode == "elem10":
                # line1: eid pid (<=2 tokens)；line2: n1..n10 (>=8 tokens)
                if pending is None or len(toks) <= 2:
                    pending = (int(toks[0]), int(toks[1]))
                else:
                    eid, pid = pending
                    cx, cy, cz, cnt, ok = _avg(nodes, toks)
                    if ok and cnt > 0:
                        elems.append((eid, pid, cx, cy, cz))
                    else:
                        skipped += 1
                    pending = None

    if args.pid is not None:
        elems = [e for e in elems if e[1] == args.pid]

    with open(args.out, "w", encoding="utf-8", newline="\n") as g:
        g.write("eid,pid,cx,cy,cz\n")
        for eid, pid, cx, cy, cz in elems:
            g.write(f"{eid},{pid},{cx:.6f},{cy:.6f},{cz:.6f}\n")

    print(f"[ok] {len(elems)} solid elements -> {args.out}")
    if skipped:
        print(f"[warn] {skipped} elements skipped (unknown node id)")


def _avg(nodes, nid_tokens):
    """对节点号列表求坐标平均。返回 (cx, cy, cz, cnt, ok)。ok=False 表示有未知节点。"""
    cx = cy = cz = 0.0
    cnt = 0
    ok = True
    for t in nid_tokens:
        if t == "":
            continue
        nid = int(t)
        if nid <= 0:
            continue
        p = nodes.get(nid)
        if p is None:
            ok = False
            continue
        cx += p[0]; cy += p[1]; cz += p[2]
        cnt += 1
    if cnt > 0:
        cx /= cnt; cy /= cnt; cz /= cnt
    return cx, cy, cz, cnt, ok


if __name__ == "__main__":
    main()
