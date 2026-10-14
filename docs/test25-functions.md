# test25：FUN42～49 位元搬移、交換與資料組合

2026-10-14 原始碼更新，維持 0.11.0，不製作安裝包。

來源：[原始檔](../samples/test25.ldr)、[截圖](../samples/screenshots/test25.png)、[IR 範例](../examples/test25_functions.json)。430 bytes、8 網路，沿用 FBs-44MN-test13 檔頭。

| FUN | action | 參數 | opcode |
| --- | --- | --- | --- |
| 42 BITMV | `bit_move` | source=S、source_index=Ns、destination=D、destination_index=Nd；位置0～15 | F4B0 |
| 43 NBMV | `nibble_move` | 同上；位置0～3 | F4B2 |
| 44 BYMV | `byte_move` | 同上；位置0～1 | F4B4 |
| 45 XCHG | `word_exchange` | source=Da、destination=Db；兩者均讀寫 | F4B6 |
| 46 SWAP | `byte_swap` | destination=D；原地交換高低byte | F4B8 |
| 47 UNIT | `nibble_unite` | source=S、count=N（1～4）、destination=D | F5BC |
| 48 DIST | `nibble_distribute` | source=S、count=N（1～4）、destination=D | F6BD |
| 49 BUNIT | `byte_unite` | source=S、length_register=N、destination=D | F477 |

全部使用 enable=EN。42／43／44／47／48 可接 error=ERR 的普通 Y/M 線圈；45／46／49 沒有狀態腳位。樣本沒有接出的 ERR 接線形式沿用已知狀態編碼，屬推導變體，未取得新的 GUI 匯入證據。

## 手冊語意與範圍

依《進階篇應用指令.pdf》7-30～37：

- 42～44 只搬移一個指定 bit／nibble／byte，目的 word 的其他部分保持原值。因此目的參與讀寫分析，不能當成整 word 覆寫。16-bit 位置上限分別為15、3、1；手冊D形式的較大範圍不是此次codec支援範圍。
- XCHG 對兩個 word 讀寫；SWAP 對一個 word 讀寫。
- UNIT 取連續 N 個 words 的最低 nibble，依序放入一個目的 word 的低位至高位，沒有填到的 nibble 清零。樣本讀R22～R24、寫WY0全部16個bits，包括被清零的Y12～Y15。
- DIST 取一個來源 word 的低位起 N 個 nibbles，寫進連續 N 個目的 words，各 word 的上12bits清零。樣本讀WX0，寫R100～R101。
- BUNIT 的 N 合法值為1～256 **bytes**，來源需要N個words，目的需要ceil(N/2)個words。手冊7-37圖示第一筆來源低byte放到目的高byte，第二筆放到低byte；不是UNIT的nibble順序直接放大。奇數N時末word未填byte的處理未明載，不假定清零或保留。

樣本BUNIT的N=R999是暫存器地址，並未提供執行時數值。靜態分析保守涵蓋R2000～R2255來源、R999、R5000～R5127目的，並保守包含目的讀取以涵蓋奇數末byte可能保留原值。這不是宣稱每次都搬256 bytes；較小執行時N可能合法，但最大跨度跨bank時目前仍拒絕。

## 編碼與尚缺形式

42～44順序為S、D、Ns、Nd，與畫面欄位排列不同；UNIT為N、S、D；DIST為S、N、D；BUNIT為N暫存器、S、D。所有常數位置／count直接儲存，沒有減一。

目前為16-bit、非P、直接位址形式。42～44僅常數Ns/Nd；UNIT／DIST僅常數N；BUNIT僅暫存器N。常數BUNIT N、暫存器UNIT／DIST N、動態Ns/Nd、常數來源、其他合法bank、D/P與間接位址屬待補的編碼，不代表PLC禁止。

單word使用既有R/D、T、WX0、WY0編碼，目的限可寫R/D／WY0；多word跨度限R/D。BUNIT的S／N／D依7-37限HR／ROR／DR，不能使用IR來源或IR長度暫存器。其餘R/D bank範圍按既有手冊驗證；此處不套用MOV舊版手冊的D3071界線。

WX0／WY0採整word資源契約，包含X0～X15、Y0～Y15；這些來自使用者的word操作數，沒有額外分配實體I/O。function控制M與ERR輸出M符合政策，未產生M中繼複製。樣本原有R22、R100等跨網路共用資源保留原樣，不改變使用者位址或順序。

## 驗證

[MCP重建檔](../artifacts/test25_mcp_roundtrip.ldr)、[驗證報告](../artifacts/test25_verification.json)。原始匯出作為獨立bytes依據，測試涵蓋每個網路、控制與狀態變體、完整範圍、錯誤位置／count、動態最大跨度、I/O契約和政策。

沒有新增獨立PLC執行模型；MCP內建模擬明確拒絕新指令。未對新生成檔進行GUI匯入或實體PLC驗證。

實際新啟動MCP stdio的generate_ldr、resources/read與get_ldr_artifact均通過；430 bytes與原檔完全一致，CRC有效。SHA-256：`ee988f7f2c051931529f306a89119399c4885112fe30c4c1fb866fe4d92eaf11`。全套 **1134項測試通過**（test25新增96項），Ruff通過，mypy檢查34個原始碼檔案通過。26份原始樣本共179網路可語意解碼並逐byte重建。
