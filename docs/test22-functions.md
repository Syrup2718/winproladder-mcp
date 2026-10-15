# test22：FUN105～112 表格指令

> 指令研究紀錄：參數與編碼依據保留於下文。測試數及產物狀態屬當次紀錄；目前能力請以功能清單為準。本機產物不隨 Git 發布。

[首頁](../README.md) · [文件索引](README.md) · [功能清單](../FEATURES.md)

2026-10-14原始碼更新，維持0.11.0，不製作安裝包。

來源：[原始檔](../samples/test22.ldr)、[截圖](../samples/screenshots/test22.png)、[IR範例](../examples/test22_functions.json)。原檔481 bytes，包含8個function網路與末尾1個空白網路。新增精確 `FB-28MA-test22` 檔頭，保留1020 metadata。

| FUN | action | 運算元對應 | 控制及狀態 |
| --- | --- | --- | --- |
| 105 R-T_S | `register_table_search` | value=Rs、source=Ts、length=L、pointer=Pr | enable／from_head／different；found／done／error |
| 106 T-T_C | `table_compare` | source=Ta、destination=Tb、length=L、pointer=Pr | 同上；Tb是讀取表格 |
| 107 T_FIL | `table_fill` | value=Rs、destination=Td、length=L | enable |
| 108 T_SHF | `table_shift` | input_word=IW、source=Ts、destination=Td、length=L、output_word=OW | enable／left |
| 109 T_ROT | `table_rotate` | source=Ts、destination=Td、length=L | enable／left |
| 110 QUEUE | `queue` | input_word=IW、destination=QU、length=L、pointer=Pr、output_word=OW | enable／push；empty_flag／full／error |
| 111 STACK | `stack` | input_word=IW、destination=ST、length=L、pointer=Pr、output_word=OW | 同上 |
| 112 BKCMP | `block_compare` | input_word=Rs、source=Ts、length=L、bit_destination=D | enable；error；另寫入L個連續結果位元 |

## 手冊與範圍

依使用者提供的《進階篇應用指令.pdf》7-100～109頁：

- 105／106：FHD=1或Pr=L−1時從表頭開始；否則從Pr+1開始。D/S=1找不同，0找相同。Pr範圍0～L−1，抵達最後時END成立，找到目標時FND成立。
- 107：把Rs填入整張表。
- 108／109：L/R=1左移／左旋，0右移／右旋；108用IW補空位、OW接收移出資料。Ts和Td可相同，原地操作保留。
- 110／111：I/O=1存入，0取出；QUEUE先進先出、STACK後進先出。Pr範圍0～L，0為空、L為滿。第一個儲存位置就是QU/ST起點，沒有額外跳過一個word。N005的R2、L10涵蓋R2～R11；N006涵蓋R102～R111。
- 112：讀取2×L個上下限word，每組低位址為下限、高位址為上限，寫入L個連續結果位元。N007的L10讀R200～R219，寫Y5～Y14。M1975會改變跨零區間的比較行為，已列為隱含讀取；M1975=0且上限小於下限時，該組輸出0並設ERR。

105～111的L為2～256；112的L為1～256。現在序列化實作為16-bit非P、直接R/D暫存器、常數L；105／107的Rs採樣本常數形式，支援有號16-bit數值，未採樣的值屬外推。108／110／111／112目前為暫存器IW／Rs。來源R3840～3903可讀，寫入目的不可使用輸入bank。一般已編碼bank為R0～3839、R5000～8071、D0～4095，整段不得跨bank。

BKCMP結果支援Y0～255／M0～999，必須檢查整段，而非只檢查起點。S結果、其他word bank、動態L、D/P與間接定址是尚未編碼的形式，不代表手冊禁止。M1975是系統語意參照，不是新增接點或中繼M。

## 編碼與政策

常數105為F50C，106為F410，常數107為F5F8，108為F446，109為F458，110為F448，111為F44A，112為F4D8。L均以L−1儲存；不從功能編號猜測D/P或其他運算元形式的opcode。

保留X0／X2／X3／X5／X7、M1／M5／M6／M7及所有暫存器地址。來源、lowered IR及decoded bytes均檢查政策；native function的M控制／狀態與BKCMP隱含M結果允許，普通M複製仍禁止。I/O契約需包含BKCMP整段Y5～Y14。

此檔是指令樣本，網路共享R0～R20等資料：QUEUE、STACK寫入R20會影響搜尋指標及位移輸入，T_FIL只填入R200～R203而BKCMP會讀到R219。沒有為消除這些互動而擅自改址；格式重建不代表這些網路共同構成已驗證的控制流程。

## 驗證

MCP重建檔（本機產物：`artifacts/test22_mcp_roundtrip.ldr`）、驗證報告（本機產物：`artifacts/test22_verification.json`）。實際stdio MCP生成並resource下載後，481 bytes與原檔完全一致，包含空白網路。SHA-256：`6eff04db1f6734fbb1592fb082d26388df243284b05d3a42acefae9d1503826d`。

離線檢查涵蓋CRC、完整bytes、資源範圍、政策、I/O、常數與邊界。未建立獨立PLC執行模型；MCP內建模擬明確拒絕這些新指令；未進行WinProLadder GUI匯入或實體PLC驗證。

完整測試 **882項通過**；Ruff與31個原始碼檔案的mypy通過。23份原始樣本、155個網路可語意解碼並逐byte重建；本機資料夾檢查未發現內容結構、文件連結或LDR CRC錯誤。
