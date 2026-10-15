# test19：積算型計時器與溫控

[文件索引](README.md) · [功能清單](../FEATURES.md)

版本維持0.11.0，屬未發版原始碼更新，未製作安裝包。

來源：[test19.ldr](../samples/test19.ldr)、[原始畫面](../samples/screenshots/test19.png)。439 bytes，FBe-20MA檔頭，7個網路。原始檔案保持不變；[完整解析IR](../examples/test19_functions.json)供研究，不可直接作為可生成的完整程式。

## 指令與編碼

| FUNC | action | 編碼與支援形式 |
| --- | --- | --- |
| 67 CALL | `call` | 精確N000記錄，僅解析；目標欄位未釐清，生成拒絕 |
| 70 FOR | `for` | 既有F590，次數2，與NEXT配對 |
| 71 NEXT | `next` | 既有F491 |
| 86 TPCTL | `tpctl` | F454，EN／H/C、Yn、Sn、Zn、SV／OS／PR／IR／DR／OR／WR、ERR／ALM |
| 87 T.01S | `accumulative_timer` | FC41，unit_ms=10 |
| 88 T.1S | `accumulative_timer` | FC42，unit_ms=100 |
| 89 T1S | `accumulative_timer` | FC43，unit_ms=1000 |

計時器欄位順序為TIM、EN、opcode、**PV、CV**、TUP／NUP。`timing`對應TIM，`enable`對應EN；`done`／`not_done`對應狀態輸出。PV目前為直接R/D暫存器，其內容是計數值；CV支援T0..255或R/D，包含手冊明列的IR區。一般暫存器寫入規則未因此放寬。

FUN88的R253不是253 ms，也不是253個ticks的常數，而是從R253讀取PV；名義時間為其內容乘100 ms。EN=1時，TIM=0保留CV、TIM=1繼續計時；EN=0清除CV。這些是手冊語意，尚無新指令的執行模擬器。既有普通T編碼與高階時長換算未改動。

TPCTL的Sn／Zn各佔一byte。以《進階篇應用指令.pdf》7-79檢查：Sn=0..31、Zn=1..32、Sn+Zn≤32、Yn=Y0..255且整段不越界；SV／OS／PR／IR／DR／OR各Zn words，WR固定9 words且不得與自身參數或其他網路讀寫重疊。參數採HR、ROR、D區，完整跨度皆檢查。ERR／ALM及TUP／NUP目前接普通線圈。

所有新增控制輸入和狀態輸出均加入來源、降低後程式、發出位元組解碼後的M→M檢查。TPCTL的Yn整段加入I/O契約：test19的Y2、Zn=3代表Y2～Y4，並非新增外部接點。

## 手冊與版本差異

- 《進階篇應用指令.pdf》7-81～82：FUN87～89語意、時間單位、CV/PV範圍。手冊允許PV常數0..32767及更多word bank；目前未建立其序列化，不能說PLC不允許。
- 同書7-79：TPCTL有Md=0／1、32區、D0..4095。test19畫面沒有Md，不能推定預設值或自行插入Md欄位。
- 同書7-80：溫度來源由規劃表或R4003/R4004選定；R4003=A55AH時，R4004=10000..13839對應R0..3839、20000..23999對應D0..3999。未提供PLC規劃和執行值，實際溫度來源標為引用不完整。
- 《CH20_FB-PLC溫度量測及溫度PID控制.pdf》20-44～47是較舊的FB-4AJ(K)形式：24區、D0..3071，沒有Md，並有FUN85前提。20-45說明H/C=1加熱、0冷卻；20-46～47列出WR9及R4005～4008、R4012～4013等隱含控制。引用分析保守列出這些可能讀取值，但不把舊版硬體前提直接套用至新版CPU。
- 同書與新版7-79的範圍差異尚未經FBe-20MA實機確認；超出樣本的參數組合標為外推，不能稱為GUI驗證。
- 《進階篇應用指令.pdf》7-61：CALL呼叫LBL定義的副程式，以RTS返回，最多5層（含中斷）。N000中`672e188000000000`的目標metadata尚未解碼，原樣本也沒有LBL1/RTS。只保留解析與底層取證重建，不允許對外生成無法重定位的CALL。

## 交付與驗證

試匯入檔（本機：`artifacts/test19_timer88_tpctl.ldr`）只包含原N004及N006，參數、接線與位元組保持原樣，使用原FBe-20MA檔頭。這是兩個指令的匯入候選檔，不是含初始化、溫度規劃的完整溫控製程。

使用者已澄清：N002的M0→計時器→M250/M251，以及N005的M2→計時器→M22/M1，均屬有意義的function結果，允許生成。工作區新增 `allow_function_m_to_m=true`，保留無意義複製與中繼的禁止規則。完整原檔目前僅因CALL目標未解碼而不能生成。

更新試檔（本機：`artifacts/test19_functions_no_call.ldr`）保留原N001～N006，共6網路，包含FOR／NEXT、三種積算計時及TPCTL；所有原接線與參數不變。只排除尚未支援生成的CALL，不是完整副程式測試。

離線檢查包括7個網路編解碼逐位元組一致、檔頭、CRC、原始雜湊、上下限、WR衝突、雙輸入／狀態政策、完整Y範圍；另由新啟動的MCP stdio程序實際呼叫生成工具並讀回二進位資源。驗證報告見test19_verification.json（本機：`artifacts/test19_verification.json`）。

初次新增功能時完整測試743項通過，Ruff檢查／格式檢查及29個來源檔案的Mypy檢查通過；setup check確認19個MCP工具及既有需求到LDR流程正常。政策澄清後的MCP產檔紀錄另見test19_function_policy_verification.json（本機：`artifacts/test19_function_policy_verification.json`），新試檔416 bytes、6網路、無中繼helpers，接線與原樣本逐位元組一致。

沒有獨立PLC執行模型、MCP內建新指令執行模擬、GUI匯入或實體PLC驗證。高階sequence尚未整合積算型計時；新功能透過底層`generate_ldr`使用。
