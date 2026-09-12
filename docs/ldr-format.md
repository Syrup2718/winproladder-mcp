# LDR 格式

適用樣本：WinProLadder v3.28 / FBs-20MC。以下為逆向格式，不是官方規格或跨版本相容性保證。

`CONFIRMED` 表示現有樣本逐 byte 驗證；`INFERRED` 表示由樣本外推的實作規則；`UNKNOWN` 表示未解明。CRC 與往返成功不能證明任意指令組合可匯入。

## 容器（CONFIRMED）

256-byte header，接續 records，最後為 `FF FF 00 00 00 00`。現有六份原始樣本 header 相同，包含 `Fatek Resource File Format 1`、`FB-RES`、`WinProladder`、`FBs-20MC`。其他 metadata 欄位語意 UNKNOWN，需原樣保留。

Records 按階梯圖顯示順序反向儲存，第一筆對應最後一個網路；空網路亦有 record，payload 為 `5F EB`。

| 相對 offset | 長度 | 內容 |
| --- | --- | --- |
| 0 | 2 | marker `12 10` |
| 2 | 2 | record_length，little endian |
| 4 | 2 | payload_length，little endian |
| 6 | payload_length | payload |
| 6 + payload_length | 3 | trailer，樣本為 `01 00 00` |
| 9 + payload_length | 2 | CRC，little endian |

`record_length = payload_length + 5`，實際 record 大小為 `payload_length + 11`。

CRC-16/MODBUS：反射多項式 `0xA001`、初值 `0xFFFF`、無 final XOR。涵蓋 payload_length 的兩個 bytes、payload、trailer，不含 marker 與 record_length。測試向量 `123456789 → 0x4B37`。

## 布林編碼（INFERRED）

元件位址：X=`0x000+n`、Y=`0x100+n`、T=`0x200+n`、C=`0x300+n`、M=`0x810+n`。實作限制 n=0..255，完整範圍為外推。

接點為兩 bytes：首 byte 是指令 base 加位址高位，次 byte 是位址低位。NC 再加 `0x10`。

| 指令 | base／編碼 |
| --- | --- |
| 起始 load | `0x40` |
| 巢狀 load | `0x60` |
| AND | `0x80` |
| OR | `0xA0` |
| 普通／反相 coil | `0xC0` / `0xD0` 加位址高位 |
| AND／OR 區塊合併 | `E2 00` / `E4 43` |
| TRUE/FALSE 偽元件 | 位址 `0xFE8`，以 NC 區分 |

Raw compiler 保留巢狀編碼以支援樣本往返；正式生成先經 [接圖簡化](logic-optimization.md)，不輸出巢狀合併或 Boolean OPEN 常數。Counter CLR 的特殊極性例外保留。

`test4` 的兩筆 `E0 00` 邊沿接點仍為 opaque；高階邊沿配方不是該原生指令的實作。

## 功能方塊（INFERRED）

| 類型 | payload 形式 |
| --- | --- |
| Timer | enable + `FD80` + preset BE16 + `(0x0390 + 2*n)` BE16 |
| Counter | pulse + nested NOT(clear) + `F940` + preset BE16 + `(0x0590 + 2*n)` BE16 |
| block 後接 coil | `6FFC` + coil bytes |
| 16-bit register OR | enable + `F4C8` + 三個 `(0x0A00 + 2*R)` BE16 |
| FOR | `F590` + count BE16 |
| NEXT | `F491` |
| BREAK | enable + `F476A7FE` |

Timer 樣本支持 T1/T2/T3 與 preset 100/101/256/1000；Counter 支持 C1/C2/C3 與 preset 10/16/17。OR 直接暫存器支持 R0/R1/R2；高位址及其他 enable 組合仍需匯入驗證。BREAK 尾碼 A7FE 的独立語意 UNKNOWN。

不支援 R 間接定址、常數運算元、D/P 修飾或輸出旗標。FOR/NEXT 只實作單層。編碼界限及模擬限制見 [功能參考](reference.md)。

## 證據與未知部分

Framing、payload 及雜湊由原始 samples 與測試固定；GUI 基準見 [驗證依據](verification.md)。未知網路可無損 export，但不可作語意生成的依據。尚未解明的 metadata、其他時間基準、指令修飾、硬體專用指令及跨型號 header 不應猜測。
