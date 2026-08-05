#!/usr/bin/env python3
"""新成分新藥核准審查報告摘要的公告標題 -> 許可證號集合。

**這個模組需要 `tw_permit_id.py`。要複製就複製這兩個檔。**（其餘三個模組各自獨立。）

## 為什麼要寫成程式

因為一個「看起來對」的正則會靜默地少抓，而少抓的東西沒有任何徵兆——你得到
一份比較短的清單，不會得到錯誤。在 2026-08-05 量測的 206 則真實公告標題
（`M-10`；展開後 273 張證，`M-11`）上——每個數字的母體、方法與重跑方式見
repo 根目錄的 `measurements.json`：

| 陷阱 | 一個天真的作法 | 量測到的損失 | 登記 |
|---|---|---|---|
| 一則公告帶多張證 | 只取第一張 | 273 張證裡少 67 張（24.5%） | `M-19` |
| 字別用貪婪中文字元類 | `[一-鿿]+字第` | 20 則標題的字別被吃進公司名 | `M-22` |
| 序號錨定 `[0-9]` | 漏掉 R 開頭 | 4 則放射性藥品公告 | `M-23` |
| 假設一定有「號」 | 以「號」為終止符 | 2 則標題根本沒有「號」 | `M-24` |

反過來，這個模組跑過全部 206 則之後，205 則的結果與許可證資料裡實際登錄的
證號集合完全一致（`M-25`）；唯一不一致的是一則來源錯字，本模組依設計回報
無法解析而不是猜一個。

## 設計上的兩個決定

1. **字別取自封閉集合，用最長匹配。** 標題會把公司名直接接上許可證
   （`…有限公司衛部藥輸字第027623號`），所以不能貪婪地吃中文字。
2. **展開是假設，不是結論。** 這裡把 `第029081-82號` 展開成兩張證，那只是
   一個候選集合。真正的檢定是「它存在於許可證表裡嗎」。無法通過的展開一律不收。
   本模組不連網也不查表，所以它回傳的是候選，呼叫端負責檢定。

CLI:
    python3 reference/tw_nme_titles.py '台灣禮來股份有限公司  衛部藥輸字第027640-027643號「捷癌寧膜衣錠」'
    python3 reference/tw_nme_titles.py --json --file fixtures/nme_titles.sample.jsonl

退出碼：**0 = 全部解析完，1 = 至少一則有無法解析的片段**（2 = 用法錯誤）。
第二個範例**會回 1，而那是正確的**：隨附樣本刻意收了一則來源錯字
（`衛部藥字第027731號`，字別不合法）與四則合成負控，本模組依設計回報「無法解析」
而不是猜一個。把這個指令包進 script 或 CI 之前先讀這一段——不然你會把一個
刻意的拒絕當成故障。
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tw_permit_id import (  # noqa: E402
    LIC_TYPE_CODES,
    SERIAL_WIDTH,
    PermitIdError,
    normalize_serial,
    normalize_text,
)

__all__ = [
    "RANGE_SEPARATORS",
    "LIST_SEPARATORS",
    "TitleParse",
    "PermitGroup",
    "extract_permits",
    "parse_title",
]

#: 量測到的範圍符號（`M-20`，2026-08-05，206 則標題）。`-` 26 則、`~` 1 則。
#: 這是**已量測到的形態，不是保證的完整集合**。
RANGE_SEPARATORS = "-~‐‑‒–—－～"
#: 量測到的列舉符號（同 `M-20`）。`、` 7 則、`/` 2 則。全形變體一併收，成本為零。
LIST_SEPARATORS = "、､/／,，"

# 序號酬載：「第」之後的一段英數與分隔符，**不含空白**。
#
# 兩個決定，各自對應一個真實形態：
#  * `\s*` 放在群組外，所以「第 027864/027865號」開頭的空白會被吃掉；
#    「第059019 號」結尾的空白則自然落在群組外。真實標題裡沒有任何一則
#    在序號**之間**放空白。
#  * 群組內不允許空白，所以「第 027864 Testdrug 100mg」只會取到 027864。
#    如果允許空白，產品名會被整段吃成序號。
#
# 產品名裡有數字、「、」和「/」（例如「可申達10、20毫克膜衣錠」、
# 「百穩益注射劑20毫克/毫升」），但那些都在「號」或「「」之後，碰不到。
_PAYLOAD_RE = re.compile(
    r"字第\s*([0-9A-Za-z][0-9A-Za-z"
    + re.escape(RANGE_SEPARATORS + LIST_SEPARATORS)
    + r"]*)"
)
_SPLIT_RE = re.compile("[" + re.escape(LIST_SEPARATORS) + "]")


@dataclass(frozen=True)
class PermitGroup:
    """標題裡的一段『<字別>字第<酬載>』。"""

    lic_type: str | None
    raw_prefix: str
    payload: str
    permits: tuple[str, ...] = field(default=())
    note: str | None = None


@dataclass(frozen=True)
class TitleParse:
    title: str
    groups: tuple[PermitGroup, ...]

    @property
    def permits(self) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for g in self.groups:
            for p in g.permits:
                seen.setdefault(p, None)
        return tuple(seen)

    @property
    def unresolved(self) -> tuple[str, ...]:
        return tuple(g.note for g in self.groups if g.note)

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "permits": list(self.permits),
            "unresolved": list(self.unresolved),
        }


def _longest_lic_type(prefix: str) -> str | None:
    """從右往左取碼表裡最長的合法字別。公司名不會被吃進來。"""
    for length in range(min(len(prefix), 10), 0, -1):
        cand = prefix[-length:]
        if cand in LIC_TYPE_CODES:
            return cand
    return None


def _apply_short_tail(anchor: str, tail: str) -> str:
    """`('029081', '82')` -> `'029082'`；`('001160', '64')` -> `'001164'`。

    短尾寫法只給尾巴，前綴沿用前一個序號。尾巴不短於錨點時，視為完整序號。
    """
    if len(tail) >= len(anchor):
        return normalize_serial(tail)
    return anchor[: len(anchor) - len(tail)] + tail


def _expand_range(anchor: str, tail: str) -> list[str]:
    end = _apply_short_tail(anchor, tail)
    if not (anchor.isdigit() and end.isdigit()):
        # R 開頭的序號不做範圍展開：字母序號的遞增規則未經量測，猜會出錯。
        raise PermitIdError(f"拒絕展開含字母的序號範圍：{anchor}-{tail}")
    lo, hi = int(anchor), int(end)
    if hi < lo:
        raise PermitIdError(f"範圍終點小於起點：{anchor}-{end}")
    if hi - lo > 50:
        raise PermitIdError(f"範圍過大（{hi - lo + 1} 張），視為解析錯誤：{anchor}-{end}")
    return [str(n).rjust(SERIAL_WIDTH, "0") for n in range(lo, hi + 1)]


def _serials_from_payload(payload: str) -> list[str]:
    """酬載字串 -> 序號清單。處理列舉、範圍、短尾與空白。"""
    serials: list[str] = []
    for chunk in _SPLIT_RE.split(payload):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = [p.strip() for p in re.split("[" + re.escape(RANGE_SEPARATORS) + "]", chunk)]
        parts = [p for p in parts if p]
        if not parts:
            continue
        anchor = normalize_serial(parts[0]) if not serials else (
            _apply_short_tail(serials[-1], parts[0]) if len(parts[0]) < SERIAL_WIDTH
            else normalize_serial(parts[0])
        )
        if len(parts) == 1:
            serials.append(anchor)
            continue
        for tail in parts[1:]:
            expanded = _expand_range(anchor, tail)
            serials.extend(s for s in expanded if s not in serials)
            anchor = expanded[-1]
    # 去重但保留順序
    out: list[str] = []
    for s in serials:
        if s not in out:
            out.append(s)
    return out


def parse_title(title: str) -> TitleParse:
    """公告標題 -> TitleParse（含每一段的字別、序號與未解析註記）。"""
    text = normalize_text(title)
    groups: list[PermitGroup] = []
    for m in _PAYLOAD_RE.finditer(text):
        prefix = text[: m.start()]
        lic_type = _longest_lic_type(prefix)
        payload = m.group(1).strip()
        if lic_type is None:
            tail = prefix[-8:]
            groups.append(PermitGroup(
                None, tail, payload,
                note=(f"字別無法對到碼表：…{tail}字第{payload}。"
                      "這可能是來源錯字（已知一例：衛部藥字第027731號，"
                      "正確為衛部藥輸字）。用許可證表反查，不要猜。"),
            ))
            continue
        try:
            serials = _serials_from_payload(payload)
        except PermitIdError as exc:
            groups.append(PermitGroup(lic_type, lic_type, payload, note=str(exc)))
            continue
        groups.append(PermitGroup(
            lic_type, lic_type, payload,
            permits=tuple(f"{lic_type}字第{s}號" for s in serials),
        ))
    return TitleParse(title=title, groups=tuple(groups))


def extract_permits(title: str) -> list[str]:
    """公告標題 -> 候選許可證號清單（正規化）。"""
    return list(parse_title(title).permits)


def _main(argv: list[str]) -> int:
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    titles: list[str] = []
    if argv and argv[0] == "--file":
        if len(argv) < 2:
            print("usage: reference/tw_nme_titles.py [--json] --file <jsonl>", file=sys.stderr)
            return 2
        for line in Path(argv[1]).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("//"):
                titles.append(json.loads(line)["title"])
    else:
        titles = argv
    if not titles:
        print("usage: reference/tw_nme_titles.py [--json] <標題> [...] | --file <jsonl>", file=sys.stderr)
        return 2
    rc = 0
    for t in titles:
        parsed = parse_title(t)
        if as_json:
            print(json.dumps(parsed.as_dict(), ensure_ascii=False))
        else:
            print(f"{t}\n  -> {', '.join(parsed.permits) or '(none)'}")
            for n in parsed.unresolved:
                print(f"  !! {n}")
        if parsed.unresolved:
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
