#!/usr/bin/env python3
"""單筆許可證明細查詢 — 示範請求的形狀，**刻意不做批次**。

    POST https://lmspiq.fda.gov.tw/api/public/sh/piq/1000/licSearch
    Content-Type: application/json
    {"data": {"licBaseId": "<8 字元 licId>"}}

本工具一次只吃**一個** licId，跑完就結束。沒有 `--input-file`、沒有迴圈、
沒有併發。理由寫在 README 的〈刻意不做〉：示範一次請求的形狀是教學，提供
批次工具是把流量指向政府主機。要跑多筆是你的決定，也是你的責任——請自己
加節流，並先讀下面這段。

## 節流與 422

這台主機在負載下會回 `422`，訊息是「連接次數過於頻繁」。那是**我方 IP 被
限流**，不是「這張證不存在」，也不是「這個標記消失了」。把 422 當成資料訊號
會得到一份假的空清單。本工具遇到 422 會明講。

預設最小間隔 30 秒（`--min-interval`）。本 repo 逐筆引用明細結果的許可證共
11 張（`M-44`，見 repo 根目錄的 `measurements.json`），2026-08-05 以此節奏取得，
未觸發 422。**那個 11 說的是本 repo 引用了幾張證，不是你可以送幾次請求。**

## 為什麼不能改用抓網頁來驗證

`https://lmspiq.fda.gov.tw/web/DRPIQ/DRPIQ1000Result?licId=<licId>` 是
client-side SPA 路由。抓它並讀 HTTP 狀態碼**證明不了任何事**：連食藥署自家
資料裡的合法 licId 也會回 404。要確認一張證存在，只能走這支 API。

CLI:
    python3 reference/tfda_lic_query.py 60001328
    python3 reference/tfda_lic_query.py --raw 衛署藥製字第033862號
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request

API = "https://lmspiq.fda.gov.tw/api/public/sh/piq/1000/licSearch"
DEFAULT_MIN_INTERVAL = 30.0
_UA = "tw-new-drug-signals/1.0 (single-permit reference query; see repo README)"

#: 回應中與「新／舊」判讀有關的欄位。完整欄位清單見 docs/00-sources.md。
FIELDS_OF_INTEREST = (
    "certNo", "prodNameC", "restraintItemsCode",
    "issueDate", "oriIssueDate", "validDate", "licStatus",
    "ingredientsDesc", "atcList", "monitorDate",
)


class LicQueryError(RuntimeError):
    pass


def _to_lic_id(value: str) -> str:
    """接受 8 字元 licId，或一個完整許可證號（需要 tw_permit_id.py）。"""
    v = value.strip()
    if re.fullmatch(r"[0-9]{2}[0-9A-Za-z]{6}", v):
        return v
    try:
        from tw_permit_id import lic_id  # 只有走這條路才需要兄弟模組
    except ImportError as exc:  # pragma: no cover
        raise LicQueryError(
            f"{v!r} 不是 8 字元 licId。要用許可證號查詢，請把 tw_permit_id.py "
            "放在同一個目錄。"
        ) from exc
    return lic_id(v)


def query(lic_id_value: str, timeout: float = 45.0) -> dict:
    """送出一次 licSearch。回傳明細 dict。"""
    body = json.dumps({"data": {"licBaseId": lic_id_value}}).encode("utf-8")
    req = urllib.request.Request(
        API, data=body,
        headers={"Content-Type": "application/json",
                 "Accept": "application/json",
                 "User-Agent": _UA},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 422:
            raise LicQueryError(
                "HTTP 422：主機回「連接次數過於頻繁」。這是我方 IP 被限流，"
                "不是這張證不存在、也不是標記消失。請拉長間隔後重試，"
                "不要把它記錄成資料。"
            ) from exc
        raise LicQueryError(f"HTTP {exc.code}：{exc.reason}") from exc

    data = payload.get("data")
    if isinstance(data, list):
        data = data[0] if data else None
    if not data:
        raise LicQueryError(
            f"licId {lic_id_value} 查無明細。在下結論前先確認 licId 的組成："
            "字別碼 2 位 + 序號（不足 6 位才補零，R 開頭序號不補）。"
        )
    return data


def _main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="單筆 TFDA 許可證明細查詢（不支援批次，這是刻意的）")
    ap.add_argument("permit", help="8 字元 licId，或完整許可證號")
    ap.add_argument("--raw", action="store_true", help="輸出完整 JSON 回應")
    ap.add_argument("--min-interval", type=float, default=DEFAULT_MIN_INTERVAL,
                    help="送出前先等待的秒數（預設 %(default)s，善待政府主機）")
    ap.add_argument("--no-wait", action="store_true",
                    help="跳過等待。只在你確定這是這一輪唯一一次請求時使用。")
    args = ap.parse_args(argv)

    try:
        lic = _to_lic_id(args.permit)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not args.no_wait and args.min_interval > 0:
        print(f"# 等待 {args.min_interval:.0f}s 後查詢 {lic}", file=sys.stderr)
        time.sleep(args.min_interval)

    try:
        data = query(lic)
    except LicQueryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.raw:
        print(json.dumps(data, ensure_ascii=False, indent=1))
        return 0
    for key in FIELDS_OF_INTEREST:
        print(f"{key}\t{data.get(key)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
