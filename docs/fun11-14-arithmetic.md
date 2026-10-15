# FUN11～14、原生邊沿與後續推理

[文件索引](README.md) · [功能清單](../FEATURES.md)

## 已接入 MCP

`read_ldr`、`generate_ldr`、`analyze_ldr`、`modify_network` 現在可處理 `test7.ldr` 的全部五個網路。原檔 SHA-256 為 `cb7085f33a059f0eda2034ae9a18974249a49617b879b224cce0ab28057aed3c`。重建時保留五個網路、X0、Y1 及原有 R/D，不增加 X/Y 或 M。

| 網路 | 截圖內容 | 原始 payload |
| --- | --- | --- |
| N000 | X0 上升沿 → Y1 | `E000 4000 C101` |
| N001 | FUN11：R3840 + 5 → D100 | `4FE8 7FE8 F662 0100 0005 40C8` |
| N002 | FUN12：D100 − 1 → D101 | `4FE8 7FE8 F664 40C8 0001 40CA` |
| N003 | FUN13：D102 × 2 → D103 | `4FE8 7FE8 F666 40CC 0002 40CE` |
| N004 | FUN14：R3841 ÷ 20 → D105 | `4FE8 7FE8 F668 0102 0014 40D2` |

`test4` N006 的 `E000 5001 C103` 配合原截圖確認為 X1 下降沿 → Y3。目前原生邊沿限單一 X 接點加 Y/M 線圈，不宣稱支援其他接點種類或複合邊沿支路。簡單的 `rising_edge`／`falling_edge` 高階配方（單一正向 X、無 reset）也會直接產生原生接點，不再配置輔助 M；複合或帶 reset 條件仍使用有用途說明的布林配方。

## 算術參數

```json
{
  "profile": "FBs-24MA-test7",
  "networks": [
    {
      "action": {
        "type": "arithmetic",
        "operation": "add",
        "sa": "R3840",
        "sb": 5,
        "destination": "D100",
        "enable": "TRUE",
        "unsigned_when": "FALSE"
      }
    }
  ]
}
```

`operation` 可為 `add`、`sub`、`mul`、`div`。Sa 為直接 R/D 暫存器；Sb 必須是 0～32767 的整數常數，不能用字串暫存器、負數或布林值。範圍和條件變化屬樣本外推，回應標為 `inferred_variant`。固定除數 0 直接拒絕。

`enable` 是 EN，`unsigned_when` 是 U/S。樣本 EN=TRUE、U/S=FALSE；U/S=FALSE 是有號，TRUE 是無號。U/S 條件接線屬外推，並非另一份已匯入樣本。這些語意參考 [FATEK FBs FUN11～14 手冊](https://www.esea.cz/support/fatek/doc/FBs-Manual_Web_English/FUN11-12-13-14-ADD-SUB-MUL-DIV-EN.pdf)。

加減各寫一個 word。16-bit 乘法寫兩個連續 word（低／高乘積）；除法寫兩個連續 word（商／餘數）。因此樣本也會寫 D104、D106；交叉引用及跨界檢查會列入它們，重疊寫入亦能檢出。這是指令本身的結果範圍，並非額外配置輸出。輸入暫存器 R3840～3903 不可作目的地。D 的實作範圍仍保守限制為 D0～3999。

不支援寄存器 Sb、常數 Sa、32-bit D 修飾、P 修飾、間接定址或連接 F0 狀態輸出。算術目前只做編碼、資源與檔案驗證，模擬工具會明確拒絕執行，不會回傳假的通過結果。邊沿掃描模型則以 `initial` 的 X 值或 FALSE 作前一掃描狀態，屬離線模型，並未確認 PLC 開機語意。

## 可以繼續推出的功能

| 功能 | 實作方式 | 邊界 |
| --- | --- | --- |
| 暫存器加一／減一 | FUN11／12，Sa=D、Sb=1、destination=D | 已提供可產檔範例；EN 每次掃描成立都執行；沿用 FUN11／12 狀態及溢位語意，不能宣稱等同原生 FUN15／16 |
| 固定偏移 | ADD／SUB 常數 | 沿用 16-bit 算術限制 |
| 整數倍縮放 | MUL 常數 | 必須保留兩個結果 word |
| 商與餘數 | DIV 常數 | D 為商，D+1 為餘數 |

上述組合已放入 `get_design_guide` 的 `derived_increment_decrement`、`arithmetic_offset_scale_quotient` 範例，可直接交給 `generate_ldr`。範例位址是示意，不應自動套入使用者的專案；需按需求配置並說明用途。

test8 已確認原生 FUN15=`F496`、FUN16=`F498`、CMP=`F46A`、AND=`F4C6`；MCP v0.8.0 已支援。原生加一／減一優先使用 `increment`／`decrement`，上述 ADD／SUB 組合保留其自身語意。舊 F46A／F46C 猜測已被推翻，詳見 [test8／test9 原生 function](test8-test9-functions.md)。

`F6xx` 的 Sb 常數標記能否換成 `F4xx` 暫存器形式，仍需同指令的獨立匯出證據；MOV 等尚未啟用；XOR／XNR 已由 test10 確認並加入 v0.9.0，詳見 [test10](test10-functions.md)。

## 檔頭與驗證

`test6` 與 `test7` 都是 FBs-24MA，但檔頭 176～177 分別為 `10 45`、`10 40`。尚不清楚這個欄位的意義，故使用 `FBs-24MA` 與 `FBs-24MA-test7` 兩個精確樣本 profile，不把後者說成另一個 CPU 型號。未知 metadata 仍不允許語意編輯。

測試涵蓋原樣重建、CRC、暫存器佔用、跨界拒絕、型別歧義、未知 opcode、邊沿脈波、I/O 契約，以及真正的 stdio MCP 讀取→產檔→下載。沒有操作 VM，亦未驗證新檔的 GUI 匯入或實體 PLC 執行。
