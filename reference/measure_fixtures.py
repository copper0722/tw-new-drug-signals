#!/usr/bin/env python3
"""重跑 `measurements.json` 裡所有「不必連網、不必私有資料」的數字。

`measurements.json` 是本 repo 每一個對外數字的登記處。裡面的項目分四種：

| `reproduce.kind` | 意思 | 這支程式 |
|---|---|---|
| `fixture` | 隨附的 `fixtures/` 就算得出來 | **會跑** |
| `repo-internal` | 數本 repo 自己的檔案就得到 | **會跑** |
| `private-data` | 需要一份本 repo 不發布的許可證全表 | 不跑，只印出 SQL |
| `public-source` | 需要向食藥署公開來源重抓 | 不跑，只印出重抓方式 |

分這四種不是分類癖。一個數字如果連「它要從哪裡才能再算一次」都說不出來，
它就不該印在一份掛在真名底下的文件上。這支程式讓前兩種**真的可以被陌生人跑**，
並且逼後兩種把「你需要什麼才能重現」寫清楚。

CLI:
    python3 reference/measure_fixtures.py            # 跑全部可跑的，逐項比對
    python3 reference/measure_fixtures.py M-04       # 只跑一項，印出值
    python3 reference/measure_fixtures.py --list     # 列出每一項與它的重跑方式
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tw_permit_id import LIC_TYPE_CODES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"
DOCS = ROOT / "docs"

#: 貪婪中文字元類——**這是反面示範**，量的是「天真作法會錯幾則」。
#: 正解是拿 61 筆碼表當封閉集合做最長匹配，見 tw_nme_titles.py。
_GREEDY_LIC_TYPE = re.compile(r"([一-鿿]+)字第")
_R_SERIAL = re.compile(r"第\s*R[0-9]")


def _json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _jsonl(name: str) -> list[dict]:
    rows = []
    for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("//"):
            rows.append(json.loads(line))
    return rows


def _titles(origin: str | None = "real") -> list[dict]:
    rows = _jsonl("nme_titles.sample.jsonl")
    return [r for r in rows if origin is None or r["origin"] == origin]


# --------------------------------------------------------------------------
# 每個 measurement id 一個函式。回傳值要與 measurements.json 的 value 相等。
# --------------------------------------------------------------------------

def m01() -> int:
    """Lic.Type 碼表筆數。"""
    return len(_json("lic_type_codes.2026-08-05.json")["codes"])


def m02() -> int:
    """字別名稱不含「器」「粧」「色」者 = 藥品類。本 repo 自訂的字串判準。"""
    codes = _json("lic_type_codes.2026-08-05.json")["codes"]
    return sum(1 for c in codes
               if not any(k in c["lic_type"] for k in ("器", "粧", "色")))


def m03() -> int:
    """Restraint.Dr 碼表筆數。"""
    return len(_json("restraint_codes.2026-08-05.json")["codes"])


def m04() -> int:
    """名稱含「監視」的限制項目碼數。"""
    codes = _json("restraint_codes.2026-08-05.json")["codes"]
    return sum(1 for c in codes if "監視" in c["name"])


def m23() -> int:
    """序號以 R 開頭的公告標題數。四則真實案例全部收在樣本裡，所以與全量相同。"""
    return sum(1 for r in _titles() if _R_SERIAL.search(r["title"]))


def m24() -> int:
    """完全沒有「號」字的公告標題數。兩則真實案例全部收在樣本裡。"""
    return sum(1 for r in _titles() if "號" not in r["title"])


def m26() -> dict:
    """標題樣本的列數與 real / synthetic 組成。"""
    rows = _jsonl("nme_titles.sample.jsonl")
    return {
        "total": len(rows),
        "real": sum(1 for r in rows if r["origin"] == "real"),
        "synthetic": sum(1 for r in rows if r["origin"] == "synthetic"),
    }


def m27() -> int:
    """樣本裡對到超過一張許可證的真實標題數。"""
    return sum(1 for r in _titles() if len(r["expected"]) > 1)


def m28() -> int:
    """樣本裡會讓貪婪比對抓到非法字別的真實標題數。"""
    n = 0
    for r in _titles():
        m = _GREEDY_LIC_TYPE.search(r["title"])
        if m and m.group(1) not in LIC_TYPE_CODES:
            n += 1
    return n


def m30() -> dict:
    """成分樣本的列數與 real / synthetic 組成。"""
    rows = _jsonl("ingredients.sample.jsonl")
    return {
        "total": len(rows),
        "real": sum(1 for r in rows if r["origin"] == "real"),
        "synthetic": sum(1 for r in rows if r["origin"] == "synthetic"),
    }


def m53() -> dict:
    """兩張流感疫苗證的正規化 moiety 集合：交集數與各自獨有數。

    docs/05 早期版本說這兩張「正規化後相同」。用本 repo 自己的正規化器跑一次
    就能推翻：三個相同、各有一個不同。這一項存在的理由，是讓那句反駁**可以
    被陌生人執行**，而不是只能被相信。
    """
    from tw_moiety import moieties  # noqa: PLC0415 - 只有這一項需要它

    rows = [r for r in _jsonl("ingredients.sample.jsonl")
            if r["active_ingredient"].startswith(("B/Austria", "A/Thailand"))]
    if len(rows) != 2:
        raise AssertionError(f"樣本裡的流感疫苗列應為 2，實得 {len(rows)}")
    a, b = (moieties(r["active_ingredient"]).moieties for r in rows)
    return {"shared": len(a & b), "only_2013": len(a - b), "only_2023": len(b - a)}


def m44() -> int:
    """本 repo 逐筆引用明細 API 結果的相異許可證數。

    清單是 measurements.json 的 `M-44.permits`；這裡驗證每一張都真的出現在
    docs/ 裡。**反方向偵測不到**：有人新增第 12 張引用而沒更新清單時，這個
    檢查不會紅。已知盲區，寫在那一項的 caveat 裡。
    """
    permits = _entry("M-44")["permits"]
    blob = "\n".join(p.read_text(encoding="utf-8") for p in sorted(DOCS.glob("*.md")))
    missing = [p for p in permits if p not in blob]
    if missing:
        raise AssertionError(f"M-44 清單裡有 docs/ 找不到的許可證：{missing}")
    return len(permits)


def m51() -> dict:
    """docs/07 驗證檢查表的項數，以及三個訊號各自的項數。"""
    text = (DOCS / "07-controls-and-pitfalls.md").read_text(encoding="utf-8")
    section = None
    counts = {"signal_1": 0, "signal_2": 0, "signal_3": 0}
    for line in text.splitlines():
        if line.startswith("### 訊號一"):
            section = "signal_1"
        elif line.startswith("### 訊號二"):
            section = "signal_2"
        elif line.startswith("### 訊號三"):
            section = "signal_3"
        elif line.startswith("## "):
            section = None
        elif section and line.lstrip().startswith("- [ ]"):
            counts[section] += 1
    counts["total"] = sum(counts.values())
    return counts


RUNNABLE = {
    "M-01": m01, "M-02": m02, "M-03": m03, "M-04": m04,
    "M-23": m23, "M-24": m24, "M-26": m26, "M-27": m27, "M-28": m28,
    "M-30": m30, "M-44": m44, "M-51": m51, "M-53": m53,
}


# --------------------------------------------------------------------------

def load() -> dict:
    return json.loads((ROOT / "measurements.json").read_text(encoding="utf-8"))


def _entry(mid: str) -> dict:
    for e in load()["measurements"]:
        if e["id"] == mid:
            return e
    raise KeyError(mid)


def expected(mid: str):
    """measurements.json 記錄的值，攤平成與 RUNNABLE 回傳值可比較的形狀。"""
    e = _entry(mid)
    if mid == "M-26":
        return {"total": e["value"], **e["breakdown"]}
    if mid == "M-30":
        return {"total": e["value"], **e["breakdown"]}
    if mid == "M-51":
        return {**e["breakdown"], "total": e["value"]}
    if mid == "M-53":
        return e["breakdown"]
    if isinstance(e["value"], str) and e["value"].endswith("%"):
        return e["value"]
    return e["value"]


def check_all() -> list[tuple[str, bool, object, object]]:
    out = []
    for mid, fn in sorted(RUNNABLE.items()):
        got = fn()
        want = expected(mid)
        out.append((mid, got == want, got, want))
    return out


def _main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="重跑 measurements.json 裡不必連網的數字")
    ap.add_argument("id", nargs="?", help="只跑這一項（例：M-04）")
    ap.add_argument("--list", action="store_true",
                    help="列出每一項與它的重跑方式")
    args = ap.parse_args(argv)

    data = load()

    if args.list:
        for e in data["measurements"]:
            kind = e["reproduce"]["kind"]
            mark = "可跑" if e["id"] in RUNNABLE else "    "
            print(f"{e['id']}  [{kind:<13}] {mark}  {e['claim'][:58]}")
        return 0

    if args.id:
        mid = args.id.upper()
        if mid not in RUNNABLE:
            e = _entry(mid)
            print(f"{mid} 無法在本機重跑（kind={e['reproduce']['kind']}）。",
                  file=sys.stderr)
            for k, v in e["reproduce"].items():
                if k != "kind":
                    print(f"  {k}: {v}", file=sys.stderr)
            return 3
        got = RUNNABLE[mid]()
        want = expected(mid)
        print(json.dumps(got, ensure_ascii=False) if isinstance(got, dict) else got)
        return 0 if got == want else 1

    bad = 0
    for mid, ok, got, want in check_all():
        flag = "OK  " if ok else "FAIL"
        print(f"{flag} {mid}  got={got!r}  measurements.json={want!r}")
        bad += 0 if ok else 1
    total = len(RUNNABLE)
    unrunnable = len(data["measurements"]) - total
    print(f"\n{total - bad}/{total} 相符。"
          f"另有 {unrunnable} 項需要本 repo 不發布的資料或向公開來源重抓——"
          f"跑 --list 看每一項的重跑方式。")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
