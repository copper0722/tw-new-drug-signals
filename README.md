# tw-new-drug-signals

**台灣的藥品許可證上，「新藥」有三個來源，而它們量的不是同一件事。**

這個 repo 把三者的意思、失效模式、彼此的對照，以及「怎麼知道自己沒搞錯」寫下來。
公開資料人人抓得到，難的是知道抓到的欄位在說什麼。

---

## 先講結論

| 你要問的 | 用哪個訊號 | 落差 |
|---|---|---|
| 這張證有沒有被列入**新藥安全監視** | 許可證明細的 `restraintItemsCode` 含碼 `07` | **無需等另一則公告** |
| 這是不是食藥署認定的**新成分新藥** | 〈新成分新藥核准審查報告摘要〉 | 中位 **69 天**（`M-14`），且非核准順序 |
| 這個**本站正規化 moiety 字串**在許可證上是不是首次出現 | 自算 moiety 首見（基線含已註銷證） | 無 |

**ATC 不是第四個訊號，是一個反例。** 它是治療分類欄位，拿它當新舊的鍵會失敗，
而且失敗的方向剛好最糟：缺口集中在新分子上（`M-33`）。理由在
[docs/04](docs/04-moiety-first-appearance.md)。

這是縮寫版。**完整的決策表——含每個訊號最容易踩的錯——只維護一份**，在
**[docs/05 — 三個訊號對起來看](docs/05-crosswalk.md)**：三者在同一批藥上的交叉
結果、以及不一致的地方為什麼不一致，都在那一頁。那是本 repo 最有用的一頁。

三個訊號的身分不一樣，這件事比表格本身重要：

- **食藥署的公告清單，它列出來的每一筆都是權威**——那是食藥署自己審查認定並
  公告的。但**它的沉默不可用**：一個號碼不在上面，可能是還沒公告、可能是不在
  這份清單的收錄範圍內，也可能真的不是。資料分不出來，所以不要讀成否定。
- **`07` 只回答一件事**：這張證的明細裡有沒有 `07` 這個碼。食藥署沒有公開它的
  收錄準則，所以帶 `07` 不等於經審查認定為第 7 條新藥。
- **moiety 首見是純粹的候選產生器**，本 repo 自己算的，沒有任何官方地位。它量
  的是**正規化後的字串**：鹽別會被剝掉，所以「這個分子在台灣首見」不是它說的話。

而「這是不是**法定**新藥」，三個訊號都不回答。藥事法第 7 條的新藥身分來自
**中央衛生主管機關的審查認定**，不是任何一個可以從許可證讀出來的欄位。

---

## 一個立刻可以看出差別的例子

`衛部藥輸字第029062號`（耐脂德膜衣錠 / Nustendi，ezetimibe + bempedoic acid）：

- **兩個成分都不是第一次出現在許可證上**，所以 moiety 首見說「不是」。
- **它帶 `07 新藥監視`**。至於為什麼帶——食藥署沒有公開這個碼的收錄準則，
  所以誠實的答案是不知道；已知的只有「它帶著」。
- 到 2026-08-05 為止，食藥署的**新成分新藥**清單上沒有它。那份清單的沉默不構成
  否定（中位落後 69 天，`M-14`）——而「不是新成分」是一個法定判斷，只有食藥署
  作得出來；本 repo 能說的只有上面第一點那個字串事實。

三個訊號給出三個不同的答案，而三個都沒有錯——它們回答的是三個不同的問題。

順帶示範這個 repo 的規矩：上面第二點很想寫成「因為兩種已核准成分的複方在藥事法
上就是新藥」。**那句話是錯的**，而且錯得很順口。施行細則第 2 條要求該複方
「具有優於各該單一成分藥品之醫療效能」，第 7 條再要求經審查認定；兩個舊成分湊
在一起不會自動變成法定新藥。這個 repo 的前一版就是這樣寫的。

---

## 這個 repo 是什麼、不是什麼

**是**：方法。哪個介面回答哪個問題、每個標記的法源與界線、把公告標題解析成
許可證號的四個陷阱、以及一組可執行的正控與負控。

**不是**：抓取工具，也不是資料鏡像。批次下載、排程、鏡像資料表都不在這裡；
本 repo 只說明「拿到之後怎麼讀才不會讀錯」。健保給付與藥價屬於
[`nhi-rule-history`](https://github.com/copper0722/nhi-rule-history)，這裡完全不碰。

判準寫成一句話：**拿掉它會讓人「拿不到 bytes」→ 不屬於這裡；
拿掉它會讓人「對 bytes 產生錯誤信念」→ 屬於這裡。**

---

## 刻意不做

- **不鏡像任何資料。** 不放許可證全表、不放現行清單、不放那 273 列公告表。
  一份掛在執業醫師名下、卻過期的法規清單，比沒有清單更糟；而且那是食藥署要
  發布的東西，不是我的。`fixtures/` 每個檔都標了抓取日與「這是測試樣本，不是
  資料鏡像」。五個檔裡只有兩個附得出一行可執行的重抓指令；另外三個寫的是
  **缺什麼才能重建**，因為本 repo 不提供批次抓取工具。指向一頁其實沒有指令的
  文件，讀起來像已經驗證過——那比留白更糟。
- **不提供批次抓取工具。** 示範一次請求的形狀是教學；提供批次工具是把流量指向
  政府主機。`tfda_lic_query.py` 一次只吃一筆、跑完就結束，預設 30 秒間隔。
- **不做臨床判斷。** 不評藥、不排名、不談療效或該不該用。
- **不出 schema 與 migration。** [docs/08](docs/08-if-you-build-a-ledger.md) 講
  一份持續更新的清單該是什麼形狀，但只講到形狀為止，不給 DDL。文件裡出現的 SQL
  一律是**重跑某個數字的查詢**，附在 [`measurements.json`](measurements.json) 的
  登記項目旁，不含任何主機或連線資訊。
- **不對政府主機做 CI 檢查。** `make test` 完全離線。

---

## 跑跑看

只需要 Python 3.10+ 的標準函式庫（`pytest` 僅測試用，
`python3 -m pip install -r requirements-dev.txt`）。**所有指令都從 repo 根目錄
執行**；文件裡的路徑一律是 `reference/<檔名>.py`。

```console
$ python3 reference/tw_restraint.py '25 監視中學名藥'
designated      False
matched_code    None
monitoring_family       25
interpretation  本 repo 解讀：…（完整字串見 tw_restraint.py）

$ python3 reference/tw_moiety.py 'OPADRY PINK;;RIVAROXABAN'
OPADRY PINK;;RIVAROXABAN
  -> ['RIVAROXABAN']   [丟棄賦形劑: OPADRY PINK]

$ python3 reference/tw_nme_titles.py '台灣拜耳股份有限公司 衛部藥輸字第028325、26號 「可申達10、20毫克膜衣錠」'
台灣拜耳股份有限公司 衛部藥輸字第028325、26號 「可申達10、20毫克膜衣錠」
  -> 衛部藥輸字第028325號, 衛部藥輸字第028326號

$ make test          # 離線測試
$ make measurements  # 離線重跑所有算得出來的數字，與 measurements.json 比對
$ make check-live    # 一次請求，打已知正控；手動跑，不進 CI
```

`reference/` 是**參考實作**，不是套件：預期你複製其中的檔案，不是安裝它。
`tw_permit_id.py`、`tw_restraint.py`、`tw_moiety.py` 各自獨立，複製一個檔就能用；
**`tw_nme_titles.py` 需要 `tw_permit_id.py`，要複製就複製這兩個檔。**
（這件事有測試釘住，見 `test_documented_copy_set_actually_runs`。）

---

## 文件

| 檔 | 內容 |
|---|---|
| [00 — 來源、端點與欄位速查](docs/00-sources.md) | 打哪裡、拿到什麼欄位、節流與 422 |
| [01 — 「新藥」到底在說什麼](docs/01-what-counts-as-new.md) | 藥事法第 7／45／47 條、施行細則、查驗登記審查準則，以及一個很像答案的誘餌 |
| [02 — 訊號一：`07 新藥監視`](docs/02-marker-restraint-07.md) | 判定規則、三個靜默陷阱、語意的界線 |
| [03 — 訊號二：新成分新藥核准審查報告摘要](docs/03-marker-nme-report.md) | 落差、沉默的意義、四個解析陷阱與真實標題 |
| [04 — 訊號三：moiety 首見](docs/04-moiety-first-appearance.md) | 定義、正規化擋得掉的四種噪音、擋不掉的兩種、為什麼不是 ATC |
| [05 — 三個訊號對起來看](docs/05-crosswalk.md) | 交叉表、七筆不一致逐一打開 |
| [06 — 許可證身分與日期](docs/06-permit-identity-and-dates.md) | licId、兩個產生錯誤連結的細節、發證日的限制、七張不可能的發證日 |
| [07 — 驗證協議](docs/07-controls-and-pitfalls.md) | 檢查表、寫出數字前的三個檢查、活體 canary |
| [08 — 如果你要做一份持續更新的清單](docs/08-if-you-build-a-ledger.md) | 為什麼時間窗是錯的、逐筆首次觀察 |
| [`measurements.json`](measurements.json) | 每一個數字的量測時刻、母體、方法、重跑方式，以及被刪掉的數字與理由 |

---

## 數字的規矩

**任何數字都不得裸奔。** 本 repo 裡每一個百分比與計數都登記在
**[`measurements.json`](measurements.json)**，帶著量測時刻、母體、方法，以及
**重跑方式——一段指令、一段查詢，或一個來源網址**（三者擇一，與
[CONTRIBUTING §1](CONTRIBUTING.md) 同一條規則）。文中的 `M-NN` 就是登記編號。
三者都給不出來就改寫成定性敘述，或刪掉——**刪掉是合法而且常常正確的結果**。
被撤回的數字沒有被抹掉，逐筆連同理由留在 `measurements.json` 的 `deleted` 段落。

除非另外標註，所有數字量測於 **2026-08-05**，母體為 66,440 張許可證（`M-05`；
其中現行、`製劑`／`菌疫`、有發證日者 19,705 張，`M-06`）與 206 則新成分新藥公告
（`M-10`，展開後 273 張證，`M-11`）。

登記處把數字分成四種，因為它們的可重現程度不同：

| 種類 | 意思 | 你能做什麼 |
|---|---|---|
| `fixture` / `repo-internal` | 用本 repo 隨附的檔案就算得出來 | `make measurements` 當場重跑 |
| `public-source` | 需要向食藥署公開來源重抓 | 依登記處寫的網址與指令自己抓 |
| `private-data` | 需要一份完整的許可證表，**本 repo 不發布** | 登記處附 SQL，你套在自己的表上 |

第三種佔多數，這是誠實的代價：本 repo 不鏡像資料（見〈刻意不做〉），所以那些
數字你無法在這裡按一個鍵重現。**但它們至少會告訴你缺的是什麼**，而不是讓你以為
自己可以重現卻貼上去拿到錯誤。

還有兩條同樣硬的規矩：

- **數字帶的是量測，不是推論。** 一個真實的量測，配上一句順手加的概括，整句話
  就會以量測的權威傳出去。
- **自己組出來的數字要回頭查一次。** 兩個真數字相減，差值仍然可能沒有人看過。

這兩條都是本 repo 自己被抓到過的錯；收斂成可執行動作在
[docs/07 §3](docs/07-controls-and-pitfalls.md)，被撤回的數字逐筆留在
`measurements.json` 的 `deleted` 段落，沒有刪。

---

## 授權

程式碼 MIT（[LICENSE](LICENSE)）；`docs/` 的文字 CC BY 4.0（[LICENSE-docs](LICENSE-docs)），
方便被引用與翻譯。

本 repo 引用的法規以全國法規資料庫為準，資料以食藥署公開來源為準。
這裡是方法說明，不是法律意見，也不是臨床建議。

---

## English

**Taiwan marks a drug permit as "new" in three non-equivalent ways.** This repository
documents what each one means, when each is wrong, and how to check — for clinicians,
pharmacists, health-policy researchers and developers who have to pick one and be
able to defend the choice.

It does **not** give you a single reproducible answer to "is this permit a genuinely
new drug", because there isn't one: that status is conferred by review, not readable
off a record. What it gives you is the three questions that *are* answerable, and
which of them you actually meant.

| Question | Signal | Latency |
|---|---|---|
| Is this permit under **new-drug safety monitoring**? | `restraintItemsCode` contains code `07` | none — no second announcement to wait for |
| Is it a TFDA-designated **new active ingredient** drug? | TFDA 新成分新藥核准審查報告摘要 | median **69 days** (`M-14`), not in approval order |
| Is this **normalized moiety string** appearing on a permit for the first time? | Self-computed moiety first appearance | none |

ATC is not a fourth signal; it is a counter-example, listed with the others below.
Abridged; the full decision table, with each signal's most common error, is
maintained in exactly one place: [docs/05](docs/05-crosswalk.md).

The three are not the same kind of thing, and that matters more than the table:

- The **TFDA announcement list is authoritative for what it lists** — each entry
  was reviewed and designated by TFDA. Its **silence is not usable**: an absent
  permit may be not-yet-announced, outside that list's scope, or genuinely not a
  new drug, and the data cannot tell you which.
- **`07` answers exactly one question**: whether the detail record carries the
  code `07`. TFDA publishes no inclusion criteria for it, so carrying `07` does
  not mean the permit was determined to be a §7 new drug.
- **Moiety first appearance is a pure candidate generator** computed here, with
  no official standing. It is a statement about a *normalized string*: salts are
  stripped, so it does not say "this molecule is new to Taiwan".
- ATC is a classification field. **Never** key newness on it: the coverage gap
  concentrates on new molecules (`M-33`: 87.9% of 2026 first-appearance permits
  carry no ATC, against 1.8% of the whole current list).

**None of the three answers "is this a new drug in law."** Under 藥事法 §7 that status
is conferred by review and determination by the central health authority
(經中央衛生主管機關審查認定); it is not a property readable off a permit record.
§7 defines the three classes and requires that determination — it creates no marker and
no queryable field. Monitoring is authorised by **§45**, implemented by
藥品安全監視管理辦法 (made under §45 II per its §1); that regulation's **§8 then points
back at §7**, tying new-drug periodic safety reporting to §7 新藥 permits from the issue
date. State all three levels: "§7 is unrelated to monitoring" is as wrong as "§7 creates
the marker". Details, with verbatim citations, in
[docs/01](docs/01-what-counts-as-new.md).

All figures measured 2026-08-05 against 66,440 permits and 206 TFDA announcements
(273 permits after expansion). **Every figure is registered in
[`measurements.json`](measurements.json)** with its measurement timestamp,
population, method, and one of: a runnable command, a query, or a source URL. The
`M-NN` markers in the prose are its keys. Figures computable from the shipped
fixtures re-run offline via `make measurements`; the rest state exactly what data
they need, because this repository mirrors none of it. Figures that could be
neither reproduced nor honestly qualified were deleted — the `deleted` section of
that file lists each one with its reason.

Scope, non-goals and the "deliberately not doing" list are in the Chinese
sections above; the code in `reference/` is stdlib-only and commented in
Chinese, with English identifiers.

Code MIT, prose CC BY 4.0. Not legal advice, not clinical advice.
