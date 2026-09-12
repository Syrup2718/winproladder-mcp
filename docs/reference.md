# 功能與參數

## 控制配方

`generate_control_ldr` 支援：

- `start_stop`、`set_reset`、`toggle`
- `rising_edge`、`falling_edge`
- `on_delay`、`off_delay`、`pulse`、`counter`
- `forward_reverse`、`star_delta`

SET/RST 與邊沿配方由布林網路實作，不代表原生指令編碼已支援。脈衝動作期間不重觸發，結束後有一個復歸掃描；正反轉同時啟動時正轉優先。星三角依序使用連續三個 Y 位址作主接觸器、星形、三角形，仍需外部電氣／機械互鎖。

預設值、I/O 分配及假設會回傳於 `design`。`generate_system_ldr` 最多組合 24 個獨立配方，先保留明確指定的 Y/M/T/C 範圍，再分配其餘資源；拒絕重疊，允許共用輸入。它不是跨配方製程協調器。

## 順序控制

`generate_sequence_ldr` 支援 1..16 步，每步可設定輸出、tick 數、完成條件及 timeout。每掃描最多轉移一步。

預設 X0 啟動、X1 暫停、X2 復歸、X3 中止，均為 active-high；X4 為外部時脈，每 100ms 一個上升沿。高、低狀態都必須被掃描到。完成條件可參考其他 X 輸入。

暫停關閉輸出，保留完整 tick 計數並忽略暫停期間脈衝；恢復時時脈已高不會多算一個 tick。這不是原生保持型 Timer，不保留不足一個 tick 的時間，也不保證斷電保持。

省略 timeout 時使用 `max(100, 3*ticks)`，上限 32767。timeout 隨暫停凍結；同一 tick 完成與逾時並存時完成優先。中止／逾時故障 M6 保持到復歸。

## 自訂 Ladder IR

```json
{"networks": [{"condition": "(Y0 OR X0) AND NOT X1", "coils": [{"device": "Y", "address": 0}]}]}
```

`condition` 支援 AND/OR/NOT、`&`/`|`/`!`、括號與 TRUE/FALSE；AND 優先於 OR。X/Y/M/T/C 編碼範圍為 0..255，普通及反相 Y/M coil 可用 `inverted` 指定。此範圍不是實體 PLC 容量保證。

限制：1..1000 網路，條件最多 4096 字元、256 AST nodes、深度 32。Legacy `steps` 按左摺疊執行，不能與 condition 混用。工具 schema 列出完整欄位及互斥條件。

Timer 範例：

```json
{"networks": [{"block": {"type": "timer", "address": 0, "preset": 300, "enable": "X0"}, "coils": [{"address": 0}]}]}
```

Counter 範例：

```json
{"networks": [{"block": {"type": "counter", "address": 0, "preset": 10, "pulse": "X0", "clear": "X1"}, "coils": [{"address": 0}]}]}
```

Timer/Counter 編碼接受位址 0..255、preset 0..65535；Timer 的 time_base 僅 `0.01s`。執行限制與編碼範圍不同：一般時序模型只接受 T0..49、preset 0..32767，且需符合專案時間基準設定。

`action` 支援 16-bit `register_or`（sa/sb/destination 為 R0..255，enable 為布林條件）、`for`（count 1..16383）、`next`、`break`（enable）。Action 獨占網路，FOR/NEXT 無接點或線圈；只接受匹配的單層迴圈，BREAK 必須位於迴圈內。長迴圈可能觸發 PLC watchdog。

## 模擬與驗收

`simulate_ladder` 最多 256 次掃描，initial 最多 128 個元件。每次 inputs 是 X 輸入快照，省略的 X=false；Y/M 狀態逐掃描保留，網路按顯示順序更新。

未指定 scan_ms 時只模擬布林邏輯。指定 1..60000ms 的 scan_ms 後啟用 Timer/Counter 模型：Timer 停用歸零，Counter 計上升沿且 clear 優先。拒絕重複 T/C 寫入、block 初始狀態及不支援的時間設定。模型不模擬 PLC 非同步時脈相位。

`generate_ldr` 可附 1..32 個 acceptance cases，每個 case 含 name、initial、scans（inputs/expected），時序案例另附 scan_ms。每個 case 獨立起始；任何斷言失敗會在寫檔前拒絕生成。省略 acceptance 可編譯，但不會得到驗收結果。

暫存器動作與迴圈不可模擬。模型驗收不等於 WinProLadder syntax check、GUI 匯入或實機執行驗證。

## 未支援範圍

MOV、一般算術／比較、間接定址、其他 Timer time base、原生保持型計時、通訊、定位及多數硬體專用指令尚未支援。未知原生指令保持 opaque，無損 export 不丟棄原始資料。完整支援狀態以 `get_capabilities` 為準。
