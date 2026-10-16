# WinProLadder 離線驗證與取樣交接（2026-10-16）

[文件索引](README.md) · [修復說明](repair-2026-10-15.md)

## 工作範圍

接手 WinProLadder GUI 匯入、檢查、重新匯出及新形式取樣。原始碼修復與離線測試由原工作繼續處理；請不要同時修改 src/tests 或既有 samples，避免覆蓋工作。

本次尚未取得任何新檔案的 GUI 匯入成功證據。VM 視窗已可見 WinProLadder 空白工程，但自動化輸入結果未確認，因此不算驗證。使用者已同意操作 VM。只做離線工程，不連線、下載、啟停 PLC 或驅動實體輸出。

## 檔案位置

- 主機交付資料夾：`C:\VM_Share\mcp-repair-20261015`
- VM 共用資料夾：`\\vmware-host\Shared Folders\VM_Share\mcp-repair-20261015`
- 原始產物與驗收：`C:\Fatek\winproladder-mcp\artifacts\release-20261015T133100Z-f08ce625\manifest.json`
- 共用資料夾內 `offline-manifest.json` 是同一份離線紀錄；每個 case 含輸入、期望、I/O 契約、實際檔案 hash。
- GUI 結果請另存共用資料夾的 `gui-results`，不得覆寫待測 `.ldr`。`gui-results-template.json` 列出精確 hash 與待填欄位。

## A. 優先匯入本次修復產物

所有 17 份高階產物使用 FBs-20MC 樣本檔頭。請使用相符的離線空白工程，一份檔案一個獨立工程，不要連續匯入造成地址重複或網路混合。使用 **Import Ladder Diagram**，不要將 `.ldr` 當成完整專案直接 Open。

建議順序：

1. `17_native_pause_resume.ldr`：R 狀態、FUN87 TIM/EN、PV/CV、M 比較狀態；核對接線沒有變成 M 自保持或中繼複製。
2. `16_native_timer_sequence.ldr`、`13_pause_resume_sequence.ldr`：普通 T 流程與使用者明確指定外部脈波的流程；時間、步驟與輸出符合 manifest。
3. `03_toggle.ldr`、`07_off_delay.ldr`、`08_pulse.ldr`、`11_star_delta.ldr`：原生微分、TOGG、數值狀態及計時接線。
4. 其餘 `01`、`02`、`04`、`05`、`06`、`09`、`10`、`12`、`14`、`15`：完成全部 17 份匯入及梯形圖語法檢查。

每份都需要：

- 記錄 WinProLadder 版本、工程 CPU/機型、普通 T 時間基準（T0～49=.01s）、待測檔名與 SHA-256。
- 匯入是否成功、程式檢查是否有錯誤；保留錯誤完整文字與所在網路號。不要為了通過而改掉原始檔。
- 截圖保留 FUN 名稱、操作數、EN/TIM/狀態接線及關鍵網路。特別檢查 XOR 清零、加法賦值、ZNCMP、DIFU、TOGG 和 FUN87。
- 原樣重新 Export Ladder Diagram 至 `gui-results/<原檔名>_reexport.ldr`，並保存工程副本。記錄匯入過程有無自動轉換；原工作會比對 bytes 與語意。
- 只完成匯入時填 `gui_import=passed`；沒有實際執行時，不填 runtime/PLC passed。

### 顯示槽的額外測試

`display_99.ldr`、`display_00.ldr`、`display_98.ldr` 是同一個測試程式（hash 相同），差別是模型的初始值，並非三份含不同初始資料的 LDR。匯入一份即可檢查格式；測試初始化 R0=0、R1=1000、R10=99／0／98，其他用到的 R/M 為零。

測試 I/O：Y0=秒位使能，Y1=十分位使能，R13=選中數字；R10 以十分之一秒為單位。這些僅是測試 fixture 的地址，不是客戶機台的 I/O 指派。只驗證前 300 ms 的顯示槽，不是完整倒數器或無限循環顯示設計。

每槽 50 ms：秒位先，40 ms ON/10 ms OFF，再十分位 40 ms ON/10 ms OFF；9.9 與0.0也必須保留空白。若 WinProLadder 沒有適合的離線數值/時間模擬，記為未執行；不要拿 GUI 動畫或手動快速點擊宣稱 10 ms 已量測。

## B. 補齊編碼證據：一次只改一個因素

以下是 MCP 真正還缺的 `.ldr` 原始 GUI exports。手冊的合法模式不等於 binary 格式已確認，請保留每份原始匯出、完整工程與對應截圖；檔名描述唯一變動。不要改既有 samples。

### B1. JMP／CALL 目標與重定位（最高優先）

依進階手冊 7-59～61 建立合法可檢查的完整離線程式：前向條件 JMP 至存在的 LBL；另有 CALL 至完整副程式及 RTS。避免無條件向後跳造成無限迴圈。

從同一份基準工程各自另存變體：

- 不變動，連續匯出兩次；關閉重開後再匯出，確認不穩定欄位。
- 只將目標名稱 `1` 改 `8`（引用與定義一致），再做 `A`、`B1` 等名稱變體。
- 名稱不變，只在目標前插入一個無關網路。
- 名稱不變，只將目標移動到另一網路位置。
- CALL 與 JMP 分開取樣，記錄所有網路的顯示順序。

目的：判定目標 metadata 是名稱、位置、識別碼或重定位資料。現在 CALL1/8 與 JMP1 的精確樣本不足以證明任意搬動安全。

### B2. FUN87／88／89 的 PV 常數

進階手冊 7-81～82：同一指令、相同 CV 與接線，分別匯出 PV=`R100`、常數 `0`、`1`、`10`、`255`、`256`、`32767`。三種 unit 各自建立基準，不同時改 CV 或狀態接線。再單獨比較 R/D CV、其他手冊允許 bank 的形式。

### B3. MOV 與算術常見缺口

基本手冊 7-23～34：從既有支援形式建立對照，分別取 MOV 常數來源（0、1、-1、32767）、算術 register Sb、constant Sa、D、P、DP，以及間接定址。每種只改一項，記錄實際 UI 接受的機型及完整操作數，不假設所有 CPU 都相同。

### B4. 無 helper 的複雜連接分支

用一般接點和線圈建立以下圖，保留真實連線並匯出，不自行加 M helper：

- `(X0 OR X1) AND (X2 OR X3) -> Y0`
- `(X0 AND X1) OR (X2 AND X3) -> Y0`
- 多層混合及相同條件接到原生 function EN 的版本。

這些是取樣 fixture 地址。MCP 現在會拒絕需要自動 helper 的設計，不能用放寬政策替代格式研究。

## 回報格式

先交 A 的匯入結果及 reexports，再交 B 的差分樣本。每筆回報至少：檔名、原檔 hash、工程/軟體版本、成功或失敗、錯誤網路、截圖名稱、reexport 檔名、唯一改動。GUI、離線模型與實體 PLC 結果分開記錄。
