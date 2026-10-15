# test16：DIV48、SUM、PID、WDT 與高速計數器

> 指令研究紀錄：參數與編碼依據保留於下文。測試數及產物狀態屬當次紀錄；目前能力請以功能清單為準。本機產物不隨 Git 發布。

[首頁](../README.md) · [文件索引](README.md) · [功能清單](../FEATURES.md)

原始樣本為 `samples/test16.ldr`，7個網路、423 bytes，FBs-60MC 檔頭。截圖保存在 `samples/screenshots/test16.png`。這是未發版原始碼更新，版本仍為0.10.0。

## 已支援的形式

| FUNC | action.type | 參數與界線 |
| --- | --- | --- |
| 23 DIV48 | `div48` | sa、sb、destination 各占3個連續 R/D；enable、unsigned_when；zero／error 普通 Y/M 線圈 |
| 24 SUM | `sum` | source 起始 R/D、count=1～511、destination；目前是16-bit、常數 N 形式 |
| 30 PID | `pid` | interval=1～3000，單位10 ms；setting=SR×8、destination=OR×1、parameters=PR×7、work=WR×5 |
| 90 WDT | `wdt` | setting 只能是50、60、70、80、90、100、110、120，單位10 ms |
| 91 RSWDT | `rswdt` | enable，無運算元 |
| 92 HSCTR | `hsctr` | 目前只支援 counter=HSC0；讀出硬體 CV 到 R4096／R4097 |
| 93D HSCTW | `hsctw` | 目前只支援樣本的 source=0、counter=HSC0、target=PV；更新 R4098／R4099 與硬體 PV |

PID 的 `enable` 對應畫面上的 **A/M**，不是一般 EN；另外兩個獨立條件為 `bumpless`（BUM）及 `direction`（D/R）。三路輸出為 `error`（ERR）、`high`（HAL）、`low`（LAL）。可使用與其他指令相同的布林條件，不限定單接點或串聯首段。

WDT 的90代表900 ms，PID 的100代表1000 ms。這是這兩種指令各自的欄位單位，不改動原有 Timer 的輸入契約。手冊依據為使用者提供的《進階篇應用指令》7-3、7-4、7-10、7-83～86頁。

PID WR 的5個字組不得與本指令 SR／OR／PR 或其他網路讀寫範圍重疊。DIV48 的輸入／輸出三字組、SUM 的來源整段也會檢查 bank 邊界；不因起始位址合法就放過尾端越界。樣本既有的 DIV48／SUM 來源與目的地重疊保持原樣，未自行改位址。

## 編碼證據

| 網路 | 原始 payload |
| --- | --- |
| N000 WDT | `4000f5d1005a` |
| N001 RSWDT | `48e4f4f2` |
| N002 HSCTR | `4fe8f4e50000` |
| N003 HSCTW | `4fe8f7e7010000000000` |
| N004 PID | `481280077fe86fe8f51700640b900ba40bb80bcc6ffcc1006ffdc1016ffec102` |
| N005 DIV48 | `4fe87fe8f46c0a180a2a0a2c6ffcc815` |
| N006 SUM | `4fe8f5c000160a2c0a2e` |

DIV48、SUM、PID 的同形式位址／條件／輸出變化使用既有編碼規則，標為 `inferred_variant`；原樣本 payload 標為 `observed_export`。HSC 的零欄位不足以確認完整 CN、CV/PV、常數／暫存器選擇規則，因此未開放其他形式，未知 bytes 保持 opaque。P、SUM D、間接定址、PID 暫存器 Ts 也尚未開放。

## MCP 使用範例

```json
{
  "profile": "FBs-60MC-test16",
  "networks": [
    {"action": {"type": "wdt", "enable": "X0", "setting": 90}},
    {"action": {"type": "sum", "source": "R22", "count": 22, "destination": "R23"}}
  ]
}
```

交給 `generate_ldr`，並明列 `io_contract`，如上述例子的 inputs=[X0]、outputs=[]。完整七網路範例見 [test16 JSON](../examples/test16_functions.json)。完整樣本的實體 I/O 只有 X0、X7、Y0、Y1、Y2。

## 驗證界線

離線驗證涵蓋原始 bytes、CRC、讀寫跨度、三層 M→M 政策與 I/O 契約。七種指令目前都不支援 MCP 內建執行模擬，也未建立獨立的 PID／WDT／硬體計數執行模型。新產生的 `.ldr` 尚未經 GUI 匯入或實體 PLC 驗證；原樣本匯出證據不延伸為任意變體的執行保證。

MCP stdio 已完成讀取、產檔與 resource 二進位下載，重建423 bytes 與原檔完全相同。630項自動測試通過。輸出為 `artifacts/test16_mcp_roundtrip.ldr`，共用目錄另存相同檔案；報告為 `artifacts/test16_verification.json`。
