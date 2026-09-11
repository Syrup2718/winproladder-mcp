# 下一批最小样本

已於 2026-09-11 收到並核對 `test.ldr`、`test2.ldr` 的梯形圖截圖，
保存在 `samples/screenshots/`。使用者已確認 WinProLadder 版本為 v3.28。

所有新增案例請使用新的檔名，保留原始三個檔案。下面每列是一個獨立匯出檔；
同組保持 PLC 型號、專案設定與其他條件相同，附同名截圖。若 GUI 不接受某 preset，記錄訊息即可。

## 優先 1：順序和空 network

已收到 test3.ldr，包含 N001/N003 中間空 network，這項需求已滿足。
test3 的 N008–N011 補充截圖已收到，12 個 network 的畫面對照完整。
以下順序案例可作額外回歸證據，不再是結構 Parser/Encoder 的前置需求。

| 建議檔名 | 從上到下內容 |
| --- | --- |
| order_two.ldr | N000 X0→Y0；N001 X1→Y1 |
| order_middle_empty.ldr | N000 X0→Y0；N001 empty；N002 X1→Y1 |
| empty_only.ldr | 單獨一個 empty network（若能匯出） |

## 優先 2：Timer 每次只改一個變數

每個檔案只有一個 Timer network，輸出固定 Y0，time base 固定 .01S。

| 建議檔名 | Timer | preset |
| --- | --- | ---: |
| timer_t1_p100.ldr | T1 | 100 |
| timer_t1_p101.ldr | T1 | 101 |
| timer_t1_p255.ldr | T1 | 255 |
| timer_t1_p256.ldr | T1 | 256 |
| timer_t0_p100.ldr | T0 | 100 |
| timer_t2_p100.ldr | T2 | 100 |
| timer_t3_p100.ldr | T3 | 100 |
| timer_t10_p100.ldr | T10 | 100 |

第一批先做 T1/100、T1/101、T1/256、T2/100 即可，之後補齊。
另一 time base 的樣本再另存，T1/preset100/Y0 都不變，檔名註明 time base。

## 後續：Device 與 branch

- X0→M0、X0→M1、X0→M10、X0→M100，各自獨立檔。
- T0→Y0、T3→Y0、T10→Y0；M0→Y0、M1→Y0，各自獨立檔。
- X0 AND X1→Y0；X0 AND /X1→Y0。
- (X0 OR X1)→Y0。
- (X0 OR X1) AND X2→Y0。
- X0 AND (X1 OR X2)→Y0。
- (X0 AND X1) OR X2→Y0。
- X0 OR X1 OR X2→Y0。

新增檔案後需更新完整性測試的 SHA-256 清單。尚未驗證的樣本不會自動變成生成規則。
