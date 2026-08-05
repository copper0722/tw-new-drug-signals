"""許可證號 -> licId。重點在**拒絕**，不在轉換。"""

from __future__ import annotations

import pytest

from tw_permit_id import (
    LIC_TYPE_CODES,
    SERIAL_WIDTH,
    PermitIdError,
    lic_id,
    normalize_serial,
    parse_permit_number,
    permit_page_url,
)


def test_code_table_matches_authority_snapshot(lic_type_codes):
    """嵌在模組裡的碼表必須和 fixtures 的權威快照一致。"""
    snapshot = {c["lic_type"]: c["code"] for c in lic_type_codes["codes"]}
    assert LIC_TYPE_CODES == snapshot
    assert len(snapshot) == 61


def test_basic_lic_id(controls):
    pos = controls["permit_id"]["positive"]
    assert lic_id(pos["permit_number"]) == pos["lic_id"]


def test_short_serial_is_padded():
    assert normalize_serial("1082") == "001082"
    assert lic_id("衛部菌疫輸字第1082號") == "60001082"


def test_letter_serial_is_never_padded(controls):
    """負控：R 序號已是 6 字元。補零會產生 7 字元的錯誤 licId。"""
    case = controls["permit_id"]["negative_letter_serial"]
    assert normalize_serial("R00108") == "R00108"
    assert lic_id(case["permit_number"]) == case["lic_id"]
    assert len(case["lic_id"]) == 2 + SERIAL_WIDTH


def test_overlong_serial_raises_instead_of_truncating(controls):
    """本模組的存在理由。

    lpad('0271234', 6) 會回傳 '027123'，那是**另一張真實存在的許可證**。
    一個錯的連結比沒有連結更糟，所以這裡必須丟例外。
    """
    case = controls["permit_id"]["negative_overlong"]
    with pytest.raises(PermitIdError) as exc:
        normalize_serial(case["serial"])
    assert "截斷" in str(exc.value)
    with pytest.raises(PermitIdError):
        lic_id("衛部藥輸字第0271234號")


def test_company_name_prefix_does_not_become_lic_type():
    """公司名直接接上字別時，最長匹配只吃掉合法的字別。"""
    p = parse_permit_number("台灣武田藥品工業股份有限公司衛部藥輸字第027623號")
    assert p.lic_type == "衛部藥輸"
    assert p.code == "52"
    assert p.canonical == "衛部藥輸字第027623號"


def test_lic_type_outside_closed_set_raises():
    """來源錯字（衛部藥字）不在碼表內，必須拒絕而不是猜成衛部藥輸。"""
    with pytest.raises(PermitIdError):
        parse_permit_number("衛部藥字第027731號")


def test_fullwidth_digits_are_normalized():
    assert lic_id("衛部藥輸字第０２７８９９號") == "52027899"


def test_page_url_is_documented_as_unverifiable():
    url = permit_page_url("52027899")
    assert url.endswith("licId=52027899")
    assert "SPA" in permit_page_url.__doc__
