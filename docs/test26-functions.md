# test26：FUN50～57 分配、移位、旋轉、格雷碼與解碼

[文件索引](README.md) · [功能清單](../FEATURES.md)

2026-10-15 原始碼更新，維持 0.11.0，不製作安裝包。

來源：[原始檔](../samples/test26.ldr)、[截圖](../samples/screenshots/test26.png)、[IR 範例](../examples/test26_functions.json)。原檔440 bytes、8網路，沿用FBs-60MC-test16檔頭。

| FUN | action | 參數／控制／狀態 | opcode |
| --- | --- | --- | --- |
| 50 BDIST | `byte_distribute` | source=S、length_register=N、destination=D；enable | F478 |
| 51 SHFL | `shift_left` | destination=D、count=N；enable／input_bit；output／error | F550 |
| 52 SHFR | `shift_right` | destination=D、length_register=N；enable／input_bit；output／error | F452 |
| 53 ROTL | `rotate_left` | destination=D、length_register=N；enable；output／error | F4A2 |
| 54 ROTR | `rotate_right` | destination=D、count=N；enable；output／error | F5AA |
| 55 B→G | `binary_to_gray` | source=S、destination=D；enable | F47A |
| 56 G→B | `gray_to_binary` | source=S、destination=D；enable | F479 |
| 57 DECOD | `decode_bits` | source=S、source_index=Ns、bit_length=NL、destination=D；enable；error | F4A8 |

enable=EN、input_bit=INB、output=OTB、error=ERR。FUN51／52的INB是獨立第二路控制，樣本為直接通電TRUE；M1控制原生SHFR且輸出M2屬使用者允許的function用途。沒有自動M中繼或額外實體I/O。

## 手冊語意

依《進階篇應用指令.pdf》7-38～45：

- BDIST的N為1～256 **bytes**。依7-38的N=9圖例，讀5個來源words、寫9個目的words；先取來源高byte，再取低byte，每個目的word的高byte清零。正文「N個資料暫存器」與N單位／圖例不一致，此處採明確的byte單位與圖例，來源為ceil(N/2) words、目的為N words。
- 範例N=R999是執行時數值，靜態分析不假定R999內容；保守涵蓋R1000～R1127來源、R999及R1500～R1755目的。不是每次都讀寫最大範圍。若最大範圍跨bank會保守拒絕，即使較小的實際N可能合法。
- SHFL／SHFR／ROTL／ROTR的16-bit N為1～16；32-bit D形式為1～32，後者編碼未接入。連續移動N次，OTB為最後移出的bit；移位每次填入INB，旋轉將移出bit繞回。目的為單word原地讀寫。N為暫存器時，執行值越界由PLC的ERR處理，靜態分析不捏造其值。
- B→G／G→B轉換一個來源word到一個目的word；本次沒有推導D/P形式。7-43～44關於「小於16／大於或等於16位元」的敘述有歧義，樣本為非D單word形式，不據此新增不存在的位數參數。
- DECOD的Ns為0～15、NL為1～8 **來源bits**；目的為2^NL個單點，最少佔1 word、最多16 words。樣本WX0的X3～X7解碼至R2、R3，不是寫5個words。7-45表格NL欄列2～256，與運算元定義及正文1～8不一致；依定義、正文與GUI樣本解讀NL，另以2^NL計算目的寬度。
- DECOD來源超過B15時延伸到下一個word；若到該運算元bank最高位元，按7-45規則截取，不把Ns+NL>16當成非法。實作支援R/D、T及WX0／WY0來源的跨度；例如R0/Ns15/NL8會讀R0與R1，D4095/Ns15/NL8只讀D4095。
- DECOD在NL<4時只明確定義2^NL個結果bits，未明載同一目的word其餘bits的處理；資源分析保守納入目的word讀寫，不宣稱已驗證其執行結果。

## 編碼範圍

BDIST順序為N暫存器、S、D；移位／旋轉為N、D；DECOD為S、D、Ns、NL。常數直接儲存，沒有減一。

本次僅樣本16-bit非P直接位址形式：BDIST／SHFR／ROTL用length_register，SHFL／ROTR用count，DECOD用常數Ns/NL。替代的常數／暫存器N、動態Ns/NL、其他word banks、D/P及間接位址是尚未實作的編碼，不代表PLC禁止。

BDIST三個operand依手冊限HR／ROR／DR；單word其他功能沿用R/D、T、WX0、WY0編碼，目的限可寫R/D、WY0；多word目的目前限R/D。word I/O採完整word保守契約。原樣本契約為X0～X15，以及Y0、Y2；這些源自WX0與原接線，沒有自行分配實體I/O。

原程式ROTL先讀D22作N，下一網路ROTR再修改D22；此跨網路依賴保留原樣，不調換順序、不改暫存器。

## 驗證

MCP重建檔（本機：`artifacts/test26_mcp_roundtrip.ldr`）、驗證報告（本機：`artifacts/test26_verification.json`）。測試以原始GUI匯出bytes為獨立編碼依據，涵蓋8個網路、每路控制、兩種狀態接線、完整資源跨度、N界線、DECOD跨word／bank末端截取、I/O與三層政策。

未新增獨立PLC執行模型；MCP內建模擬明確拒絕這些新增指令。尚未對新生成檔進行WinProLadder GUI匯入或實體PLC驗證。

實際新啟動MCP stdio的generate_ldr、resources/read與get_ldr_artifact均通過；440 bytes與原檔完全一致，CRC有效。SHA-256：`ef51137d5b53a130e99afd213b1c646166db3de14ad4a507aaafe42cbc1a80f3`。全套 **1246項測試通過**（test26新增111項），Ruff通過，mypy檢查35個原始碼檔案通過。27份原始樣本共187網路可語意解碼並逐byte重建。
