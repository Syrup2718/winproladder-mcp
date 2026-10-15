# 計時器資料核對（更新至2026-10-12）

[文件索引](README.md) · [功能清單](../FEATURES.md)

本文件整理普通 T 與積算型計時器的樣本、時間單位及暫停語意。檔案編碼支援、高階工具整合與執行模擬分別說明。

## 已核對的原始檔案

| 樣本 | 網路 | 內容 |
| --- | --- | --- |
| [test.ldr](../samples/test.ldr) | N003 | T1，preset 100，TUP 接 Y4 |
| [test2.ldr](../samples/test2.ldr) | N004 | T2，preset 101，TUP 接 Y0 |
| [test3.ldr](../samples/test3.ldr) | N004～N006 | T1=256、T2=1000、T3=101 |
| [test5.ldr](../samples/test5.ldr) | N003～N004 | T1=100；下一網路用 T1 接點驅動 Y1 |

[test3 原始截圖](../samples/screenshots/test3.png) 明確顯示時間基準 `.01S`。因此在此設定下，3 秒是 preset 300，5 秒是 preset 500，不需要額外的 X 時脈輸入。

T1=256 的原始 payload 為 `4fe8 fd80 0100 0392`；T2=1000 為 `4fe8 fd80 03e8 0394`。普通 T 的編碼、解碼與離線計時模型均已存在，順序產生器現在也預設使用此類 T。

## 暫停並保留已計時間

使用者提供的 《CH09.pdf》 第 9-65～9-66 頁，列出 FUN87 T.01S、FUN88 T.1S、FUN89 T1S。已核對文字與完整頁面圖示：

- 普通 T：EN=1 計時，EN=0 清除。
- 積算型：EN=1 時，TIM=1 繼續計時，TIM=0 保留 CV；EN=0 清除。
- CV 指定保存現在值的暫存器，PV 指定預設值，TUP/NUP 為到時／未到時輸出。

test19 現已提供 FUN87／88／89 原始編碼：FC41／FC42／FC43，依序是 TIM、EN、opcode、PV、CV、TUP／NUP 接線。`accumulative_timer` 支援 10／100／1000 ms 時間基準、R/D 暫存器 PV、T0..255 或 R/D CV（含手冊7-81明列的 IR）。PV 常數及其他 word bank 尚未編碼；不是 PLC 不允許。詳見 [test19](test19-functions.md)。

底層 `generate_ldr` 可生成上述積算型計時；高階 `generate_sequence_ldr` 尚未整合，仍拒絕不帶外部脈波的 pause 需求。只有需求本來就指定脈波輸入時，才可明確設定 `clock` 使用既有的完整 tick 計數模式；此模式不代表原生保持計時。

## M 網路的用途

舊 `pump_alternation.ldr` 的前五個網路把 M0/M1/M10/M11/M12 複製到 M20/M21/M30/M31/M32，作用是保存本次掃描開始時的模式與步驟，供後續網路讀取。它們不是輸入接線，但先前未附用途說明。

新版順序產生器先計算所有步驟轉移，再更新步驟狀態，已取消 M16+i → M64+i 的整批複製。保留的 M 用於啟動邊沿、執行狀態、完成／故障記憶及步驟轉移；`symbols`、`network_notes` 和高階工具的 `.ldr.design.json` 列出用途。註解尚未嵌入 `.ldr` 格式，不宣稱 WinProLadder 會顯示這些名稱。

原有泵浦檔案未覆蓋；在原生保留計時尚未完成前，不將縮減需求的範例冒充完整泵浦控制成果。
