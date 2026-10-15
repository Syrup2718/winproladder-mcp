# test18：類比轉換、位元存取與跳躍樣本

[文件索引](README.md) · [功能清單](../FEATURES.md)

2026-10-12未發版更新，版本維持0.11.0。原始 `samples/test18.ldr` 為6網路、400 bytes，使用既有 FBs-20MC 檔頭；截圖保存在 `samples/screenshots/test18.png`。

## 支援形式

| FUNC | action.type | 參數與驗證 |
| --- | --- | --- |
| 32 ADCNV | `adcnv` | enable=EN、selector=F/T、polarity=Pl（目前0）、source、count=1～64常數、destination；來源與目的地各 count words |
| 34 MLC | `mlc` | enable=EN、selector=X/Y、source=Rs、count=Sl（1～64常數）、x_table=Tx、y_table=Ty、table_length=Tl暫存器、destination、overflow=OVR |
| 40 BITRD | `bitrd` | enable、word=S、bit=N（0～15常數）、output=OTB、error=ERR |
| 41 BITWR | `bitwr` | enable、word=D、bit=N（0～15常數）、input_bit=INB、error=ERR |
| 65 LBL | `lbl` | 精確標籤1記錄；其他名稱的編碼尚未實作 |
| 66 JMP | `jmp` | 精確跳躍1記錄；目前只能重建完整、不變動的 test18，不能重排、修改其他網路或改檔頭 |

類比與位元指令支援相同的布林條件組合；不限定串聯首段。狀態輸出為普通 Y/M 線圈，EN及第二路輸入皆納入原始 IR、展平後程式與解碼產檔的 M→M 檢查。不自動配置 X/Y 或輔助 relay 鏈。

## 手冊與參數語意

依使用者提供的《進階篇應用指令》7-12～13、7-19～20、7-28～29、7-59～60頁：

- ADCNV F/T=0為12-bit、1為14-bit；Pl=0／1分別表示單／雙極性。Pl=1合法，但序列化尚未實作。7-12運算元表的 S／IR欄空白，但7-13範例及 test18 都使用 R3840，故依兩份實際證據支援該來源。
- MLC X/Y=0以 Tx 搜尋並轉成 Ty，1反向轉換；Tl執行時有效範圍2～255。來源超出表格範圍時 OVR=1。此指令手冊 D bank到D3999，所有跨度均檢查尾端。
- Tl=R199是執行時數值，不是表格長度199。分析保守追蹤 Tx／Ty各255個可能讀取字組，包含與 PID／周邊 WR 的衝突。這不代表每次執行都讀255個。
- BITRD／BITWR目前為16-bit形式，N=0～15。BITWR只更新指定 bit，其他15 bits保持不變，因此目的 word 同時列為讀取與寫入。BITRD EN=0時，OTB依M1919保持或清除；M1919只記為隱含設定讀取，不會生成額外接點。
- LBL合法名稱為1～6英數字且不可重複；JMP可向前或向後跳，但不能跨主／副程式區。手冊沒有解釋 `.ldr` 中跳躍目標的二進位欄位。

目前 ADCNV Pl=1／暫存器 N、MLC 暫存器 Sl／常數 Tl、D/P／間接形式，以及 BITRD／BITWR 非直接 R/D 形式尚未實作編碼。這些限制不等於 PLC 不支援。

## LBL／JMP 的精確界線

LBL 1的 payload為 `ef31000000000000`，JMP 1為 `4fe8f78ca7fe188000000000`。JMP中 `a7fe1880` 欄位不能從單一樣本證明是名稱、位址、識別碼或重定位資料，所以不把未知值任意複製到改動後的程式。

完整原樣重建可通過；缺少標籤、重複標籤、搬動網路、修改運算元、改profile及網路編輯都會阻止產檔。其餘四種指令可獨立組合。引用分析只描述結構上的裝置讀寫，不宣稱跳躍後每個網路仍會執行。

原樣本 N003為無條件往回跳 N001，可能持續迴圈直到 watchdog 觸發；N004／N005不應視為會正常掃描到的網路。因此另外提供不含跳躍的四網路試檔，保留原有M1、M2、M4及Y0，沒有新增I/O。

## 原始編碼與交付

| 網路 | payload |
| --- | --- |
| N000 | `4fe86811f55a000601000de8` |
| N001 | `ef31000000000000` |
| N002 | `4fe86812f55e011e0004286428740b8e402e` |
| N003 | `4fe8f78ca7fe188000000000` |
| N004 | `4fe8f4ba0a1400026ffcc100` |
| N005 | `4fe86814f544000f0a18` |

完整 IR：[test18 JSON](../examples/test18_functions.json)。呼叫 `generate_ldr` 時使用 inputs=[]、outputs=[Y0] 的 `io_contract`。

MCP stdio 已完成讀取、生成與 resource 下載：`artifacts/test18_mcp_roundtrip.ldr` 與原始400 bytes完全相同；`artifacts/test18_data_functions.ldr` 包含N000／N002／N004／N005。兩者在共用目錄另有相同檔案；報告為 `artifacts/test18_verification.json`。

離線驗證涵蓋 bytes、CRC、裝置跨度、動態表格長度、狀態輸出、架構政策與 I/O。沒有獨立類比／跳躍執行模型，MCP內建執行模擬會拒絕本批 action；新檔尚未經 GUI 匯入或實體 PLC 驗證。
