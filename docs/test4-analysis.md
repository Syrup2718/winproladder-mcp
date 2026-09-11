# test4 樣本分析

來源：使用者提供 `C:/VM_Share/test4.ldr`，原樣保存於 samples。
[畫面](../samples/screenshots/test4.png)。沿用專案已提供的 WinProLadder v3.28 背景。
406 bytes、8 records，footer 0x190；header 與前四份相同，8/8 CRC 通過。
合計五份樣本 35/35 records 通過既有 framing/CRC 測試。

## 畫面對照

| N | record offset (hex) | payload | 人工辨識 |
| --- | --- | --- | --- |
| 000 | 181 | `50 00 C1 00` | /X0→Y0 |
| 001 | 172 | `51 00 C1 01` | /Y0→Y1；是常閉，不是常開 |
| 002 | 161 | `50 02 80 03 D1 02` | /X2 AND X3→反相 Y2 coil |
| 003 | 150 | `41 03 88 16 C1 05` | Y3 AND M6→Y5 |
| 004 | 13D | `58 16 91 03 81 07 C1 08` | /M6 AND /Y3 AND Y7→Y8 |
| 005 | 12C | `E0 00 40 00 C1 01` | X0 上升沿接點→Y1 |
| 006 | 11B | `E0 00 50 01 C1 03` | X1 下降沿接點→Y3 |
| 007 | 100 | `41 02 60 04 A0 05 60 06 90 07 E4 43 E2 00 C1 09` | Y2 AND (X4 OR X5 OR (X6 AND /X7))→Y9 |

具體 raw bytes 由 `test_all_observed_records` 回歸保護，畫面語意為人工核對。
不能將 N005/N006 當作普通 NO/NC；`E0 00` 的作用與狀態儲存機制尚未破解。

## 新增證據與限制

- HIGH CONFIDENCE：`41 nn` 是開頭 Y NO 候選，Y2/Y3 兩個案例支持。
  `51 00` 對應開頭 Y0 NC；`81 07` / `91 03` 對應串聯 Y7 NO / Y3 NC。
  具體案例已核對，完整位址範圍未驗證。
- HYPOTHESIS：`88 16` 為串聯 M6 NO，`58 16` 為開頭 M6 NC。
  M0/M2/M6 的 operand 支持低位址偏移規律，但不能外推全部 M 位址。
- HYPOTHESIS：`D1 02` 為圖中反相 Y2 coil，不能誤認成普通 `C1` coil。
- UNKNOWN：N007 的 `E4 43` / `E2 00` 之堆疊與分支合併語意。
  單一複雜拓樸不足以建立通用 branch encoder。

## 自保持需求仍待驗證的部分

後續更新：使用者已回報候選自保持檔匯入成功，該具體組合已驗證。
見 [匯入紀錄](start-stop-verification.md)。以下保留當時假設與需求脈絡，
額外混合並聯樣本不再是這個已驗證模板的前置條件。

需求式為 `(X0 OR Y0) AND NOT X1 → Y0`，其中 X1 採梯形圖 NC 的解讀。
test4 補到 Y NO 接點，但未提供並聯 Y NO 的直接樣本。
也可交換 OR 的次序為 `(Y0 OR X0) AND NOT X1`，以已觀測的 X 並聯形式減少未知，
但新的完整指令組合仍需要 WinProLadder 匯入驗證，不應宣稱已驗證可用。
先前提到只補單個 Y 接點就足以產生檔案並不完整：仍需處理組合編碼的證據。

最小補充案例：`(Y0 OR X0) → Y1`，Y0/X0 均為普通常開接點，附截圖及 .ldr。
這能直接驗證混合 Y/X 自保持支路，不必再新增複雜 network。
實體停止按鈕接線與邏輯 X1 極性仍未由截圖回答；生成目標沿用使用者指定的梯形圖 NC，
不將它視為已確認的實體接線。
