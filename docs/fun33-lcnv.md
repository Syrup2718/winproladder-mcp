# FUN33 LCNV：test6 的證據與外推界線

[文件索引](README.md) · [功能清單](../FEATURES.md)

## 原始資料

- [test6.ldr](../samples/test6.ldr)：SHA-256 `443500807d610cf2b459d1ea8bea00150e8dceeeae46b5750f3576b3df7d71e9`。
- [使用者截圖](../samples/screenshots/test6.png)：N000、N002、N004、N006，都是 `33.LCNV`、Md=0、L=1。
- 使用者提供的原廠 `FBe進階篇/進階篇應用指令.pdf` 第 7-14～7-18 頁：Md=0..3、L=1..64、運算元角色、轉換表大小。這是 FBs 文件；不能把早期 FBe 手冊中相同 FUN 編號當成同一指令。
- [FATEK 原廠指令型錄](https://file.fatek.com/cht/PLC/FBs/Document/FBs_PLC_Catalog_cht.pdf)：FUN33 為線性轉換，FUN34 為多段線性轉換。

本次未操作 VM。解碼／重建成功不等於新組合已通過 GUI 或 PLC 執行。

## 差分結果

| 網路 | Md | S | Ts | D | L | payload |
| --- | --- | --- | --- | --- | --- | --- |
| N000 | 0 | R3840 | R2001 | D1000 | 1 | `4fe8 f57c 0000 0100 19a2 47d0 0001` |
| N002 | 0 | R3841 | R2006 | D1001 | 1 | `4fe8 f57c 0000 0102 19ac 47d2 0001` |
| N004 | 0 | R3842 | R2011 | D1002 | 1 | `4fe8 f57c 0000 0104 19b6 47d4 0001` |
| N006 | 0 | R3843 | R2016 | D1003 | 1 | `4fe8 f57c 0000 0106 19c0 47d6 0001` |
| N008 | 0 | R3844 | R2021 | D1004 | 1 | `4fe8 f57c 0000 0108 19ca 47d8 0001` |

第五組的 bytes 存在於檔案，但未出現在截圖中；其運算元名稱由前四組規律外推。檔案共 13 個網路，另有 8 個空網路。

支援格式為 `EN + F57C + Md BE16 + S word + Ts word + D word + L BE16`。普通 EN 接點沿用既有布林編碼；33P 脈波版本尚未支援。

可推得三種直接暫存器位址公式：

| 暫存器區 | 編碼 | 依據 |
| --- | --- | --- |
| R0..3839 | `0x0A00 + 2*n` | test5 的 R0/R1/R2，加上 test6 的 R2001/R2006 等 |
| R3840..3903 | `0x0100 + 2*(n-3840)` | test6 的 R3840～R3844 |
| D0..3999 | `0x4000 + 2*n` | test6 的 D1000～D1004；範圍取 FBs LCNV 手冊 |

未實際出現的位址與跨運算元角色使用仍屬外推。R3840 起不是繼續套用 `0x0A00 + 2*n`；R5000 以上、間接定址及其他暫存器區不會猜測。

## MCP 使用

呼叫 `generate_ldr`，提供需求允許的 `io_contract` 與下列 `ladder`。此例無實體 X/Y，所以 inputs、outputs 都是空清單。

```json
{
  "profile": "FBs-24MA",
  "networks": [
    {
      "action": {
        "type": "lcnv",
        "mode": 0,
        "source": "R3840",
        "table": "R2001",
        "destination": "D1000",
        "length": 1,
        "enable": "TRUE"
      }
    }
  ]
}
```

`profile` 保存 test6 的 FBs-24MA 檔頭；既有 FBs-20MC 為預設值。僅接受兩個樣本中完全吻合的檔頭，不猜未知 metadata。

| Md | 計算方式 | 轉換表讀取範圍 |
| --- | --- | --- |
| 0 | 兩點校正，共用參數 | Ts 起 4 words |
| 1 | 兩點校正，每筆各自參數 | Ts 起 4×L words |
| 2 | 倍率與偏置，共用參數 | Ts 起 3 words |
| 3 | 倍率與偏置，每筆各自參數 | Ts 起 3×L words |

Md=1..3、L>1 是根據手冊及固定欄位排列外推，尚無獨立匯出樣本。`validation.instruction_evidence` 區分 `observed_export` 和 `inferred_variant`，不將自身編解碼往返當作外部驗證。超出 Md/L、讀寫區域或暫存器連續範圍即拒絕。交叉引用會展開全部 S、Ts、D 範圍，且不自動新增 X/Y。

目的工程必須事先有正確的轉換表數值；本工具只產生指令，沒有替 R/D 初始化校正參數。LCNV 尚不支援離線運算模擬，不能宣稱換算數值或溢位行為已驗收。

## 能否推出其他 FUN

目前能外推的是暫存器編碼與同一 LCNV 指令的參數。不能直接以 FUN 編號計算 opcode：既有 OR 是 `F4C8`、FOR 是 `F590`、NEXT 是 `F491`，新 LCNV 是 `F57C`，沒有足以跨指令建立通用編碼器的證據。

歷史紀錄（test6 當時；MLC／ADCNV 後於 test18、積算型計時後於 test19 實作）：FUN34 MLC、FUN32 ADCNV、FUN8 MOV、FUN87～89 積算型計時的用途可以從手冊確認，但各自的 opcode、參數數量、修飾位、輸入與輸出格式仍須另有編碼證據。本次沒有把猜測的 `F57D` 宣稱成 FUN34，也沒有開放輸入任意 FUN 編號就產檔。
