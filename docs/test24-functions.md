# test24：MOV、MOV/、TOGG、SORT、Z-WR、矩陣位元功能

[文件索引](README.md) · [功能清單](../FEATURES.md)

2026-10-14 原始碼更新，維持 0.11.0，不製作安裝包。

來源：[原始檔](../samples/test24.ldr)、[截圖](../samples/screenshots/test24.png)、[IR 範例](../examples/test24_functions.json)。原檔 436 bytes、8 網路，沿用已知 FBs-40MA-test12 檔頭。原始 SHA-256：`01690fde5c181da0ad3b1eb1958fec73264d25dfbadc887e78dec4b1f78b95b9`。

| FUN | action | 參數與腳位 | opcode |
| --- | --- | --- | --- |
| 08 MOV | `move_word` | source=S、destination=D；enable=EN | F4AC |
| 09 MOV/ | `move_inverse` | 同上，將位元倒相後搬移 | F4AE |
| 10 TOGG | `toggle_bit` | bit_destination=D；trigger=TGU，上升沿翻轉 | F8E4 |
| 113 SORT | `table_sort` | source=S、destination=D、length=L；enable、ascending=A/D；error | F456 |
| 114 Z-WR | `zone_write` | destination=D、length=N；enable、ones=1/0；error | F75C |
| 128 MBSHF | `matrix_bit_shift` | source=Ms、destination=Md、length=L；enable、input_bit=INB、left=L/R；output=OTB | F402 |
| 129 MBROT | `matrix_bit_rotate` | source=Ms、destination=Md、length=L；enable、left=L/R；output=OTB | F44E |
| 130 MBCNT | `matrix_bit_count` | source=Ms、length=L、destination=D；enable、ones=1/0；zero=D=0 | F44C |

## 手冊語意與編碼

- 基本手冊 7-23～25：MOV 搬移 word；MOV/ 逐 bit 倒相。TOGG 每次觸發由 0→1 才翻轉一次，並非輸入維持 ON 時每掃描翻轉。
- 進階手冊 7-111：SORT 的 L 為 2～127 個資料，A/D=1 升冪、0 降冪。本次為 16-bit 形式，來源／目的各佔 L words。
- 7-112：Z-WR 的 N 為 1～511，1/0=1 填入全 1、0 清除。本次僅 R/D word 區域；N 在檔案內直接儲存，**不是 N−1**。
- 7-122～124：矩陣 L 為 2～256 words，含 16L bits。MBSHF、MBROT 每次移動一個 bit，L/R=1 向左、0 向右；移出 bit 送 OTB。MBSHF 以 INB 填補，MBROT 以移出 bit 回填。允許來源與目的相同。
- MBCNT 的 1/0 選擇統計 1 或 0；讀取 L words，但結果只寫一個 word。D=0 是統計結果為零的旗標。樣本 R100 同時作為來源與結果，保持原樣，不替換位址。
- SORT 與矩陣常數 L 儲存 L−1。Z-WR operand 順序為 N、D；MBCNT 為 Ms、L−1、D。

## I/O 與政策

MOV/ 的 WY8 編碼是 `0821`，代表 Y8～Y23 的 16 個位元，並非單一 Y8，也不是只含 Y8～Y15。分析、I/O 契約與產檔均涵蓋完整範圍。原檔的明確契約為 X0、X2、X6、X9、X11，以及 Y8～Y23；這些輸出來自使用者指定的 WY8，沒有額外創造實體 I/O。

TOGG 會讀取並寫回目的位元；原生 function 的 M 控制與 M 結果依既有政策允許。普通無意義 M→M 複製仍禁止，不合成中繼接點或替代 function。檢查來源、lowered 與 decoded 三層。

## 尚未完成的形式

目前八個 FUNC 支援樣本形式：16-bit、非 P、直接位址、常數長度。未把手冊允許的 D/P、間接定址、暫存器 L/N、Z-WR 位元區域或 MOV 常數來源冒充為已實作。

矩陣／SORT／Z-WR 此次支援既有 R/D banks，並檢查完整跨度。MOV 支援既有 word 編碼 R/D、T、WX0、WY0，另外加入精確 WY8；目的限可寫 R/D、WY0、WY8。其他 WY 起點仍需編碼證據。TOGG 此次限 Y0～255、M0～999，其餘合法家族尚未接入。

基本手冊 7-23～24 的 MOV 類 D 上限為 D3071；7-24 的 MOV/ IR 上限為 R3847。進階手冊其他功能的表格可到 D4095、R3903，但不直接證明 MOV 相同形式，因此本次 MOV 採基本手冊的界線；這是手冊版本／編碼待確認事項，不宣稱所有 CPU 都禁止較高位址。

## 驗證邊界

MCP 重建檔（本機：`artifacts/test24_mcp_roundtrip.ldr`）、驗證報告（本機：`artifacts/test24_verification.json`）。測試使用原始 GUI 匯出 bytes 作獨立編碼依據，另測每路控制、狀態輸出、完整跨度、長度上下限、I/O 缺漏及錯誤形式拒絕。

這是編碼與靜態檢查；沒有新增獨立 PLC 執行模型，MCP 內建模擬明確拒絕這些新指令。未進行新生成檔的 WinProLadder GUI 匯入或實體 PLC 驗證。

實際新啟動 MCP stdio 的 generate_ldr、resources/read 與 get_ldr_artifact 均通過；重建檔 436 bytes 與原檔完全一致，CRC有效。全套 **1037 項測試通過**（新增功能測試90項），Ruff通過，mypy檢查33個原始碼檔案通過。25份原始樣本共171網路可語意解碼並逐byte重建。
