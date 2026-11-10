# PDW 產生器（v1.1.0 實驗功能）

此功能納入 v1.1.0 原始碼；舊的 v1.0.0 安裝包不包含此功能，需更新並重新啟動 MCP server。

`generate_project_pdw` 使用本機專案範本，共用既有 Ladder IR、接圖簡化及指令編譯器，
封裝成可變長度的 PDW。舊的 `generate_pdw` 保留一／兩列等長替換介面。
這不是任意型號的通用專案序列化器，也不以 `.ldr` 改副檔名代替。

## 已實作範圍

- 樣本對應的 FBs-20MC、FBs-32MC、FBs-40MC、FBs-60MC 專案格式；主機型號從範本保留。
- 新工具接受 Ladder IR，經既有編譯器產生布林、計時器及可往返解碼的指令形式。
  這不表示所有 LDR 組合已通過 PDW 的 GUI 驗證；流程控制另行拒絕。
- 程式長度上限 4094 bytes，保護用於還原遮罩的未使用區，並非 PLC 容量上限。
- 支援主程式分區名稱與註解、Network.comment、元件註解與說明。
  區域／網路文字採 CP950，保留 CR/LF；元件文字仍依 ComponentComment 限制。
- 分區的 network_index 是來源網路索引；來源到 lowered 網路數改變時拒絕分區配置。
- 保留範本型號、未知設定與原遮罩，更新字數、長度相依位置及已知加總校驗。
- 解析器檢查設定區／程式區校驗、文字紀錄校驗、單元位置及元件名稱的兩份資料。
- 重新解碼實際輸出 bytes、檢查 I/O 宣告、工作區政策與重複輸出。
- 選填 acceptance cases，使用既有 MCP 離線模型檢查來源和輸出指令。
- 僅另存新檔；可透過 MCP resource 或 `get_pdw_artifact` 取得原始 bytes。

新工具可使用空白或含程式／註解的範本，明確以請求的程式、分區與註解取代既有內容。
副程式必須為已知的空白配置；未知紀錄型別、額外次記憶體資料及未取樣型號會被拒絕。
FUNC199 目前只標示候選資料位置，不解釋模式、不生成、不模擬。
JMP/CALL、FOR/NEXT/BREAK、LBL、MC/MCE 等流程控制尚未完成 PDW 專屬驗證，會拒絕輸出。
這些是序列化實作範圍，不是 PLC 指令限制。不得把未知指令當成沒有作用。

`embed_comment=true` 可額外寫入觀察到的 `SECT:` 程式區文字；目前只接受偶數個
CP950 bytes、最多 510 bytes 的完整文字，其他長度拒絕，不猜測填充規則。
現有 SECT 樣本的文字長度相同；其他偶數長度是長度欄位的外推，必須另做 GUI 驗證。
預設僅使用區域文字紀錄，如未嵌入 SECT 的 GUI 分區樣本。
未知設定原樣保留，新增結構仍需 GUI 檢查；不要自行猜測並改寫未知旗標。

## 使用方式與私密資料

範本必須位於 MCP 的 `--root` 之內。可把 root 設為專用的私人資料夾，
例如 `C:/PrivateProjects`，輸出則預設在該資料夾的 `artifacts/`。
不需要把私人範本複製到原始碼 repository，也不需要放寬路徑檢查。

`generate_project_pdw` 參數範例：

```json
{
  "output_name": "example.pdw",
  "template_path": "one-rung-template.pdw",
  "ladder": {
    "profile": "FBs-60MC-test16",
    "networks": [
      {"condition": "X0", "coils": [{"address": 1}], "comment": "控制紅燈"}
    ]
  },
  "sections": [
    {"network_index": 0, "name": "MAIN", "comment": "主控制區"}
  ],
  "comments": [
    {"ref": "Y1", "comment": "RED", "description": "輸出說明"}
  ],
  "io_contract": {"inputs": ["X0"], "outputs": ["Y1"]}
}
```

`inspect_pdw` 回傳型號、分區、各類註解、已知校驗範圍、大小與 SHA-256；
簡單一／兩列另保留 rungs 欄位，其餘為 null，不輸出整份原始記憶體。
`get_capabilities`（含 compact 模式）的 `pdw` 與 `pdw_project` 分別列出兩種介面限制。
新增工具需要重新啟動使用此原始碼的 MCP server 才會出現。

Repository 忽略 `.pdw`；自動測試只使用人工建立的結構與遮罩，
不包含機密樣本、私人註解或樣本的完整二進位內容。
輸出保留範本設定，因此分享生成檔案時也會分享其保留的專案資料。

## 主機與擴充模組

主機與 Ladder profile 必須一致；不會只改檔頭文字來轉換主機。

| 範本主機 | ladder.profile |
| --- | --- |
| FBs-20MC | FBs-20MC |
| FBs-32MC | FBs-32MC-test30 |
| FBs-40MC | FBs-40MC-test27 |
| FBs-60MC | FBs-60MC-test16 |

32MC 使用使用者提供的回存樣本版面，已於 v1.1.1 整合至 PDW 型號白名單與產生流程。
24MC 樣本尚未整合，其他推算模組（例如 24YJ）
也不列為已驗證支援。

`inspect_pdw` 的 `modules` 列出模組名稱與零起算的紀錄順序；該 index 不是實體槽號、
I/O 起始位址或硬體參數。觀察到的 `0x1040` 模組區每筆 76 bytes，名稱位於前 16 bytes；
其餘欄位和 zero trailer 的完整語意未解明，原始內容只從本機範本複製，不隨套件提供。

`generate_project_pdw` 新增：

- 不提供 `module_order`：原模組清單及參數逐 byte 保留。
- `module_order: []`：明確移除模組清單。
- 指定名稱清單：依順序複製本機現有紀錄，允許重複模組。
- `module_template_paths`：額外提供工作區內的 `.pdw` 作為本機模組紀錄來源；
  必須搭配明確的 module_order。只取模組紀錄，不切換其主機或帶入其程式。

例如本機範本或額外來源已含這兩種模組時，可加入：

```json
{
  "module_order": ["FBs-2DA", "FBs-4DA", "FBs-4DA"],
  "module_template_paths": ["local-module-catalog.pdw"]
}
```

未提供的型號會拒絕；同一型號若有不同參數紀錄，也拒絕自行選擇。
不建立未知模組的預設參數，不編輯未知欄位，不依名稱自行配置 X/Y 或暫存器。
最多 256 筆只是目前序列化防護，不是 PLC 槽數或擴充容量。
模組相容性、供電容量、I/O 容量、接線及參數效果尚未驗證；新輸出仍需 GUI 與目標硬體確認。
舊的 `generate_pdw` 等長工具仍限定原先的 60MC／無擴充表配置；模組功能使用新工具。

## 格式研究與驗證邊界

目前觀察到 256-byte 檔頭、兩個轉換後的記憶體區與尾端 records。
第一個區域的遮罩以 1,280 bytes 為週期；解析器從已知 FF 填充區還原遮罩，
再檢查程式識別、長度、metadata、未使用區與支援的尾端結構。
不會掃描未知區域並猜測指令。

此方法依賴本次取樣的固定配置。程式區與設定區的加總校驗、文字紀錄的
有號 CP950 bytes 加總及位址關聯已交叉驗證；未知欄位與其他區域的校驗尚未全面解明。
解析成功不代表整份專案完整性已被證明。

先前的常開、常閉、不同位址、兩列及六網路計時循環／元件註解案例，
已由使用者回報可在 WinProLadder 開啟且無問題。新封裝器能重建該計時案例的相同 bytes。
主程式分區、區域註解、網路註解與不透明區段，也已用額外 GUI 匯出檔交叉檢查格式。
另以 20MC／40MC 模組樣本確認模組紀錄邊界；20MC 程式／模組專案能重建相同 bytes。
40MC 輸出已核對主機檔頭與模組資料不變。使用者另回報單個 24YT 的編號與 I/O 範圍正常；
雙 24YT 的 GUI 回存樣本與畫面也顯示正確順序及 I/O 範圍。未進行實體 PLC 驗證。
這是特定檔案的證據；新產生的每份輸出仍需
個別 GUI 開啟、顯示及語法檢查，不能自動繼承該驗證。

人工測試資料驗證編解碼、拒絕未知格式、作用範圍及 MCP 二進位傳遞，
不證明 WinProLadder 相容性。Acceptance 是 MCP 內建離線模型；
沒有獨立 PLC 模擬器、GUI 自動化或實體 PLC 驗證，也不會連線 PLC。
