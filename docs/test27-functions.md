# test27：FUN06 BSHF 與 FUN58～64 轉換功能

[文件索引](README.md) · [功能清單](../FEATURES.md)

2026-10-15 原始碼更新，維持0.11.0，不製作安裝包。

來源：[原始檔](../samples/test27.ldr)、[截圖](../samples/screenshots/test27.png)、[IR範例](../examples/test27_functions.json)。450 bytes、8網路；加入精確FBs-40MC-test27檔頭，保留4040 metadata。

| FUN | action | 參數／控制／狀態 | opcode |
| --- | --- | --- | --- |
| 06 BSHF | `bit_shift` | destination=D；enable／input_bit／left／clear；output=OTB | F428 |
| 58 ENCOD | `encode_bits` | source=S、source_index=Ns、count=NL、destination=D；enable／high_priority；zero／error | F44D |
| 59 →7SG | `to_seven_segment` | source、count=N、destination；enable；error | F4E6 |
| 60 →ASC | `ascii_literal` | text="ABCDEF"、destination；enable | F4F0 |
| 61 →SEC | `hms_to_seconds` | source、destination；enable；zero | F4DC |
| 62 →HMS | `seconds_to_hms` | source、destination；enable；zero／overflow | F4DD |
| 63 →HEX | `ascii_to_hex` | source、count=N、destination；enable；error | F5BF |
| 64 →ASCII | `hex_to_ascii` | source、count=N、destination；enable | F5A9 |

## 手冊語意與範圍

- 基本手冊7-20：BSHF一次移動一個bit，left=1向左、0向右；INB填補，OTB輸出移出的bit。CLR=1時清除目的與OTB，優先於EN及其他輸入。四路控制獨立編解碼，沒有以普通Counter的反相CLR取代。
- 進階手冊7-46～47：ENCOD的Ns=0～15、NL=2～256 **掃描點數**，與DECOD的NL位數不同。H/L=1從高位開始找1，0從低位找1，結果是相對起點的索引，目的高byte清零。所有掃描bits為0時不執行並設D=0旗標，不等同「找到索引0」。來源跨word延伸，bank末端截取。Ns非零、NL=256時可涉及17個words；樣本R0/Ns9/NL36涉及R0～R2。
- 7-48～50：→7SG的N為0～3，代表**N+1位數**。每個nibble轉成1byte，低位數先放目的低byte；a段在B6、g段在B0、B7固定0。N=0及2時末word高byte保持原值；因此樣本R100有讀寫依賴。
- 7-51：→ASC手冊允許1～12個英文／數字字元，每2字元佔1word，第一字元在低byte。樣本ABCDEF寫R200～R202。GUI沒有ERR腳位，手冊範例卻畫ERR；此處依實際匯出不加入未確認的ERR編碼。
- 7-52～53：→SEC讀S、S+1、S+2，依序為**秒、分、時**，各為signed 16-bit，寫D、D+1合併的signed 32-bit秒數。→HMS反向讀2words、寫3words，目的亦依秒、分、時排列。HMS可表示秒數範圍為−117968399～117964799；超出時不執行並設OVR。這兩個功能的多word跨度是原生語意，不需要額外D變體。
- 7-54～57：→HEX／→ASCII的N為1～511個ASCII數碼／nibbles。HEX讀N個來源words的低byte，接受0～9／A～F，寫ceil(N/4)個words，未對應的nibbles保留。ASCII讀ceil(N/4)個words，寫N個目的低bytes，**每個高byte保留**。例N=6，HEX把123456存為低word3456、高word0012；ASCII按指定數碼由高位至低位輸出。

原樣本→HMS的(X0 OR X6) AND M1條件保留；BSHF保留X11、X12、X13、X14四路接線。→SEC來源包含R22、→HEX保留R1100部分資料等讀寫依賴均納入分析。

## 編碼與尚缺形式

ENCOD operand順序為S、D、Ns、NL−1；7SG為S、D、N；HEX／ASCII為N、S、D。HMS在opcode後保留樣本0000選擇欄位，不推定其他值。BSHF輸入依EN、INB、L/R、CLR順序編碼。

**歷史限制（已由[test28](test28-functions.md)解除）：當時→ASC只確認字串ABCDEF。** 實際字串區塊為`0007204221442246000000000000`，並非一般ASCII bytes直接排列。只有一個字串樣本，尚無足夠證據確認字元打包、長度及旗標規則；其他text會明確拒絕，不能宣稱完整1～12字元編碼已支援。仍可改動已確認形式的目的R/D、EN條件，保持ABCDEF原文字串。

其他指令為樣本非P直接位址與常數Ns／NL／N形式；動態參數、P或適用的D變體、其他word banks及間接位址待補，不代表PLC禁止。單word沿用既有R/D、T、WX0、WY0編碼；多word轉換目前限R/D。BSHF的D範圍按基本手冊7-20採D0～3071，較高D編碼／手冊版本尚未確認。

I/O契約為X0、X1、X5、X6、X11～X14，及WY0涵蓋的Y0～Y15；沒有額外創造實體I/O或中繼M。function的M控制與M狀態允許，普通無意義M複製政策保持。

## 驗證

MCP重建檔（本機：`artifacts/test27_mcp_roundtrip.ldr`）、驗證報告（本機：`artifacts/test27_verification.json`）。原始GUI匯出作獨立bytes依據，測試涵蓋四路BSHF、ENCOD高低優先、各狀態腳位、範圍與保留資料、字串／選擇欄位拒絕、完整I/O與三層政策。

未新增獨立PLC執行模型；MCP內建模擬明確拒絕新增指令。新生成檔尚未經GUI匯入或實體PLC驗證。

實際 stdio MCP 產檔、resource 與 embedded 下載均通過；450 bytes 與原始 test27 完全相同，CRC 有效。SHA256：`e6edf47845aecb35a2a8441250c61de110725a68c74143ca59368f939629e734`。

全套 pytest **1354 passed**，其中 test27 新增測試 **107 passed**；Ruff 通過、mypy **36** 個來源檔通過。目前原始樣本共 **28** 份、語意重建 **195** 個網路。未升版或建立安裝包。
