# 自動邏輯與接圖簡化

依據使用者提供的 FB-PLC 基礎功能篇 CH01，第 1.2 節的逐網路掃描規則、
第 1.7 節（頁 1-13、1-14）的程式簡化方法實作。
手冊描述的是邏輯與簡碼規則，不是 `.ldr` 二進位格式證明。

所有生成工具及新增／替換網路會自動執行：

- 移除重複條件及無作用的 TRUE/FALSE。
- 互補律、吸收律、共同條件提取，不做指數膨脹的全量 DNF 展開。
- 並聯區塊前移、複合支路置頂，單接點後接，減少輔助 M 與網路。
- 剩餘複雜支路仍使用獨立 M 網路，維持禁止巢狀合併指令的保護。
- FALSE 使用接線完整的互斥接點，不產生 Boolean OPEN 常數；計數器 CLR
  的已採樣特殊極性編碼保留。

例如 `X0 AND (X1 OR X2)` 改為 `(X1 OR X2) AND X0`，不需輔助 M；
`(X0 AND X1) OR (X0 AND X2)` 先提取 X0，再使用相同接法。
只調整同一個純布林條件，不合併或重排原始網路、輸出、計時器、計數器，
也不跨網路快取接點狀態，因此保留自保持及順序掃描語意。

## Agent 使用方式

使用者照常描述需求即可，無需指定接圖排列或提供簡化後的 JSON。
Agent 選擇 generate_control_ldr / generate_sequence_ldr / generate_system_ldr，
或將自訂 Ladder 傳入 generate_ldr；各工具自動共用本流程。

需要先預覽時，呼叫 `validate_ladder(ladder)`，不寫檔案，回傳：

- `optimized_ladder`：實際將輸出的 IR。
- `layout.metrics`：簡化前後網路數、接點出現次數、payload 位元組數。
- `layout.helper_devices`：必須保留的輔助 M 位址。
- `layout.network_map`：有更動的原始網路對應輸出範圍。
- `layout.simplified_networks`：套用布林簡化的原始網路。

生成結果同樣帶 `layout`。不要將最佳化後的 IR 與其他程式任意拼接：
輔助 M 只避開本次整份輸入程式已使用的位址。
read/export 繼續保留原始 bytes，不會靜默改寫舊檔。

驗證包括手冊排列案例、500 組隨機邏輯樹各 16 種完整輸入組合、
所有控制配方與 16 步流程的原始元件掃描比對，以及交通燈整份程式比對。
這些是編碼及軟體模型測試，不等同實機安全驗證或 GUI 匯入測試。

## 本次結果（2026-09-12）

199 項 pytest 通過，ruff、mypy、wheel/sdist 建置及真實 stdio MCP
16 工具連線檢查通過。交通燈另外比對完整計時循環與跳步輸入。

`C:\VM_Share\artifacts\traffic_light_simplified.ldr`：18 網路、6 個輔助 M、604 bytes。
相較使用者確認成功的 connected 版本（25 網路、13 M、713 bytes）有所減少。
SHA-256：`656394d7c854f2d458fb6a38fb99f1981ab45ee9a223a520943ffdc44eafb688`。
原始未修復版本只有 12 網路，但包含有問題的巢狀合併；不能把它視為可用的
接圖基準。新檔仍待 WinProLadder GUI 匯入確認，舊成功檔沒有被覆蓋。
