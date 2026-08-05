#!/usr/bin/env python3
"""許可證號 -> licId，以及 TFDA 字別碼的封閉集合。

這個模組存在的唯一理由，是「補零」這件事有兩個會靜默出錯的地方：

1. `re.sub` / `regexp_replace` 在不匹配時「原樣回傳輸入」，不會報錯。
2. `lpad` / `str.zfill` 對超過目標長度的字串，`lpad` 會**截斷**。

兩者相加，會產出一段許可證號的 6 字元切片並當成 licId 送出去。那會連到
**別張許可證**——一個錯的連結，比沒有連結更糟。所以這裡的補零一律走
`normalize_serial()`，長度超過就丟例外，不截斷。

R 開頭的序號（放射性藥品，例如 第R00108號）本身已經是 6 字元，永遠不補零。

字別碼取自食藥署自己的碼表（封閉集合，61 筆）：

    GET https://lmspiq.fda.gov.tw/api/public/codes/search/full/codeKind/Lic.Type

快照見 `fixtures/lic_type_codes.2026-08-05.json`（含重抓指令）。

CLI:
    python3 reference/tw_permit_id.py 衛部藥輸字第R00108號
    python3 reference/tw_permit_id.py 衛署藥製字第033862號 衛部菌疫輸字第001328號
"""

from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass

__all__ = [
    "PermitIdError",
    "SERIAL_WIDTH",
    "LIC_TYPE_CODES",
    "LIC_TYPE_BY_CODE",
    "DRUG_LIC_TYPES",
    "PermitNumber",
    "normalize_text",
    "normalize_lic_type",
    "normalize_serial",
    "parse_permit_number",
    "lic_id",
    "permit_page_url",
]

SERIAL_WIDTH = 6

# --------------------------------------------------------------------------
# 字別碼表 — 食藥署 Lic.Type，2026-08-05 取得，61 筆。
# 這是一個**封閉集合**：標題裡的字別只能是這 61 個之一。
# 為什麼重要見 docs/03；簡短版是公告標題會把公司名直接接上許可證
# （…有限公司衛部藥輸字第027623號），貪婪的中文字元類會吞掉「有限公司衛部藥輸字」。
# --------------------------------------------------------------------------
LIC_TYPE_CODES: dict[str, str] = {
    "衛署藥製": "01", "衛署藥輸": "02", "衛署成製": "03", "衛署中藥輸": "04",
    "衛署醫器製": "05", "衛署醫器輸": "06", "衛署粧製": "07", "衛署粧輸": "08",
    "衛署菌疫製": "09", "衛署菌疫輸": "10", "衛署色輸": "11", "內衛藥製": "12",
    "內衛藥輸": "13", "內衛成製": "14", "內衛菌疫製": "15", "內衛菌疫輸": "16",
    "署藥兼食製": "18", "衛署成輸": "19", "衛署罕藥輸": "20", "衛署罕藥製": "21",
    "衛署罕菌疫輸": "22", "衛署罕菌疫製": "23", "衛署罕醫器輸": "24", "衛署色製": "31",
    "衛署粧陸輸": "40", "衛署藥陸輸": "41", "衛署醫器陸輸": "42", "衛署醫器製壹": "43",
    "衛署醫器輸壹": "44", "衛署醫器外製": "45", "衛署醫器陸輸壹": "46",
    "衛署醫器外製壹": "47", "衛部藥製": "51", "衛部藥輸": "52", "衛部成製": "53",
    "衛部醫器製": "55", "衛部醫器輸": "56", "衛部粧製": "57", "衛部粧輸": "58",
    "衛部菌疫製": "59", "衛部菌疫輸": "60", "部藥兼食製": "68", "衛部成輸": "69",
    "衛部罕藥輸": "70", "衛部罕藥製": "71", "衛部罕菌疫輸": "72", "衛部罕菌疫製": "73",
    "衛部罕醫器輸": "74", "衛部罕醫器製": "75", "衛部醫器製壹登": "83",
    "衛部醫器輸壹登": "84", "衛部醫器陸輸壹登": "86", "衛部粧陸輸": "90",
    "衛部藥陸輸": "91", "衛部醫器陸輸": "92", "衛部醫器製壹": "93",
    "衛部醫器輸壹": "94", "衛部醫器外製": "95", "衛部醫器陸輸壹": "96",
    "衛部醫器外製壹": "97", "衛署菌製": "99",
}

LIC_TYPE_BY_CODE: dict[str, str] = {v: k for k, v in LIC_TYPE_CODES.items()}

# 藥品類字別（排除醫器 / 粧 / 色）。這是「哪些字別可能出現在一張藥證上」的集合，
# 不是「資料裡真的出現過幾種」——後者是 26，見 fixtures/README.md。
DRUG_LIC_TYPES: frozenset[str] = frozenset(
    name for name in LIC_TYPE_CODES
    if not any(k in name for k in ("醫器", "粧", "色"))
)

_FULLWIDTH_DIGITS = {chr(0xFF10 + i): str(i) for i in range(10)}
_FULLWIDTH_LATIN = {chr(0xFF21 + i): chr(0x41 + i) for i in range(26)}
_FULLWIDTH_LATIN.update({chr(0xFF41 + i): chr(0x61 + i) for i in range(26)})
_TRANS = str.maketrans({**_FULLWIDTH_DIGITS, **_FULLWIDTH_LATIN, "　": " "})

_PERMIT_RE = re.compile(r"([一-鿿]+?)字第\s*([0-9A-Za-z]+)\s*號?")


class PermitIdError(ValueError):
    """許可證號無法安全地轉成 licId。永遠丟例外，不回傳猜測值。"""


@dataclass(frozen=True)
class PermitNumber:
    """一張許可證的結構化身分。"""

    lic_type: str      # 字別，例如 '衛部藥輸'
    code: str          # 2 位字別碼，例如 '52'
    serial: str        # 正規化後的序號，例如 '027899' / 'R00108'
    canonical: str     # 正規化後的完整許可證號

    @property
    def lic_id(self) -> str:
        return self.code + self.serial

    @property
    def page_url(self) -> str:
        return permit_page_url(self.lic_id)


def normalize_text(s: str) -> str:
    """全形數字/英文 -> 半形，全形空白 -> 半形，收斂連續空白。

    不使用 NFKC 全量正規化：那會把「（）」等中文標點一起改掉，
    而標題裡的括號是我們要保留的原文。
    """
    if s is None:
        raise PermitIdError("輸入為 None")
    out = unicodedata.normalize("NFC", s).translate(_TRANS)
    return re.sub(r"[ \t]+", " ", out).strip()


def normalize_lic_type(s: str) -> str:
    """驗證字別屬於封閉集合，回傳字別名。不在集合內就丟例外。"""
    key = normalize_text(s).replace("字", "") if s.endswith("字") else normalize_text(s)
    if key in LIC_TYPE_CODES:
        return key
    raise PermitIdError(
        f"字別 {key!r} 不在食藥署 Lic.Type 碼表（61 筆）內。"
        "如果它看起來像公司名被吃進來了，用最長匹配重抓；"
        "如果它是來源錯字，用許可證表反查，不要猜。"
    )


def normalize_serial(serial: str) -> str:
    """序號正規化：不足 SERIAL_WIDTH 才補零；超過就丟例外，**絕不截斷**。

    >>> normalize_serial('1082')
    '001082'
    >>> normalize_serial('R00108')
    'R00108'
    >>> normalize_serial('0271234')
    Traceback (most recent call last):
    PermitIdError: ...
    """
    s = normalize_text(serial)
    if not s:
        raise PermitIdError("序號為空")
    if not re.fullmatch(r"[0-9A-Za-z]+", s):
        raise PermitIdError(f"序號 {s!r} 含非英數字元")
    if len(s) > SERIAL_WIDTH:
        # 這裡是本模組的存在理由。lpad 會在這裡靜默截斷成 6 字元，
        # 產出一個指向別張證的 licId。
        raise PermitIdError(
            f"序號 {s!r} 長度 {len(s)} 超過 {SERIAL_WIDTH}；"
            "截斷會產生指向另一張許可證的 licId，因此拒絕處理。"
        )
    return s.rjust(SERIAL_WIDTH, "0")


def parse_permit_number(permit_number: str) -> PermitNumber:
    """'衛部藥輸字第027899號' -> PermitNumber。

    字別以**最長匹配**取自封閉集合，所以公司名前綴不會被吃進來。
    """
    text = normalize_text(permit_number)
    m = _PERMIT_RE.search(text)
    if not m:
        raise PermitIdError(f"{permit_number!r} 不含『…字第…號』結構")
    raw_type, raw_serial = m.group(1), m.group(2)

    # 最長匹配：從右邊往左試，取碼表裡最長的合法字別。
    lic_type = None
    for length in range(len(raw_type), 0, -1):
        cand = raw_type[-length:]
        if cand in LIC_TYPE_CODES:
            lic_type = cand
            break
    if lic_type is None:
        raise PermitIdError(
            f"{raw_type!r} 的任何後綴都不在 Lic.Type 碼表內：{permit_number!r}"
        )

    serial = normalize_serial(raw_serial)
    return PermitNumber(
        lic_type=lic_type,
        code=LIC_TYPE_CODES[lic_type],
        serial=serial,
        canonical=f"{lic_type}字第{serial}號",
    )


def lic_id(permit_number: str) -> str:
    """'衛部藥輸字第027899號' -> '52027899'。"""
    return parse_permit_number(permit_number).lic_id


def permit_page_url(lic_id_value: str) -> str:
    """許可證查詢頁。

    警告：抓這個網址並讀 HTTP 狀態碼**證明不了任何事**。它是 client-side
    SPA 路由，連食藥署自家資料裡的 licId 也會回 404。要驗證存在性只能走
    licSearch API，見 reference/tfda_lic_query.py。
    """
    return f"https://lmspiq.fda.gov.tw/web/DRPIQ/DRPIQ1000Result?licId={lic_id_value}"


def _main(argv: list[str]) -> int:
    if not argv:
        # 早期版本印的是 `__doc__` 的倒數第三行，以為那是一個範例；實際上它落在
        # 字面上的 `CLI:` 那一行，所以無參數執行只會印出 `CLI:`。從 docstring
        # 的相對位置取字串，會在 docstring 改動時安靜地指向別的東西。
        print("usage: reference/tw_permit_id.py <許可證號> [...]", file=sys.stderr)
        print("example: reference/tw_permit_id.py 衛部藥輸字第R00108號", file=sys.stderr)
        return 2
    rc = 0
    for raw in argv:
        try:
            p = parse_permit_number(raw)
        except PermitIdError as exc:
            print(f"{raw}\tERROR\t{exc}", file=sys.stderr)
            rc = 1
            continue
        print(f"{p.canonical}\t{p.lic_id}\t{p.page_url}")
    return rc


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
