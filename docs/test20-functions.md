# test20：ASCWR、RAMP、RAMP2、R→T

2026-10-13原始碼更新，版本維持0.11.0，沒有打包。

來源：[原始test20](../samples/test20.ldr)、[原始截圖](../samples/screenshots/test20.png)、[解析IR](../examples/test20_functions.json)。四個網路均可解碼並逐位元組重建；原始檔案保持不變。IR描述樣本，不代表整份樣本可直接通過資源衝突檢查。

## 已實作形式（FUNC排序）

| FUNC | action | 控制／運算元 | 狀態 |
| --- | --- | --- | --- |
| 94P ASCWR | `ascwr` | `enable`、`pause`、`abort`；mode=1、pulse=true、source=S、work=Pt | active=ACT、error=ERR、done=DN |
| 95 RAMP | `ramp` | `enable`、`pause`、`up`；timer=Tn、preset=PV、lower=SL、upper=SU、destination=D | error=ERR、at_lower=ASL、at_upper=ASU |
| 98 RAMP2 | `ramp2` | `enable`；maximum=Om、rise_ms=Ta、fall_ms=Td、target=Rt、destination=Rc、work=WR | accelerating=ACC、decelerating=DEC |
| 100 R→T | `reg_to_table` | `enable`、`increment`、`clear`；source=Rs、destination=Td、length=L、pointer=Pr | done=END、error=ERR |

前三路輸入各自保留，不額外新增X／Y或relay helpers。function的M控制與M結果依現行政策允許；普通無意義M複製仍禁止。狀態接線目前為普通Y/M線圈。

## 編碼證據與手冊

手冊為使用者提供的 `C:/Fatek/FBe進階篇/進階篇應用指令.pdf`；頁碼採頁面印刷編號。

- **7-87，94P ASCWR**：樣本F103，後接S、Pt。MD=1被手冊列為保留用途，不能把MD=0的Port1印表機行為直接當成MD=1執行語意。目前支援該樣本形式的參數化編碼，未推測MD=0或非P opcode。Pt保守按8個獨占暫存器檢查；ASCII資料直到END，且可能內嵌其他運算元，因此S只追蹤起點，引用報告明列不完整。不宣稱能生成ASCII資料檔或已驗證通訊。
- **7-88～89，95 RAMP**：樣本F816、固定0000形式欄位，後接PV、Tn、SL、SU、D。Tn必須使用設定為10 ms的計時器，且不能重複使用；接受T0..255並標示仍需目的PLC設定確認。PV在M1974=0時是10 ms計時設定，在M1974=1時是每10 ms的增減量。U/D=1升、0降，在EN上升時決定；PAU暫停。SU須大於SL是執行值條件，不能比較暫存器位址大小來判斷。D+1獨占，連同Tn列入跨網路衝突檢查。
- **7-90～93，98 RAMP2**：樣本F47E、固定0000形式欄位，後接Om、Ta、Td、Rt、Rc、WR。Ta/Td內容是0..65000 **ms**，Om/Rt內容是0..65535；目前僅編碼暫存器形式，不把D0、D1、D10的位址數字當設定值。EN=0立即令Rc=0；Rt至少保持兩次掃描；需PLC OS V4.60以上。HR、OR、ROR、D0..3999，WR佔4個word且獨占。R3904→0180有原樣本證據，其餘OR位址由間距規則外推；此bank僅開放於RAMP2，不擅自擴大其他指令能力。
- **7-94～95，100 R→T**：樣本F406、Rs、Td、L−1、Pr；畫面L=8對應0007。支援16-bit非P形式，R/D來源／目的／指標，常數L=2..2048；其他長度與位址組合屬外推。檢查整段目的表格而非只有起點。CLR在搬移前清Pr，且可獨立於EN執行；搬移後Pr=L−1時END=1，否則INC=1才遞增。test21 的 X5→CLR 對照修正了先前反相推論：CLR 使用一般布林極性，7FE8 解讀為 FALSE；本樣本 INC=TRUE、CLR=FALSE。歷史 LDR bytes 不變，舊驗證報告中的 IR 解讀以此更正為準。

手冊允許的常數資料、其他word bank、register L、D/P與間接定址，目前未建立對應序列化；這是編碼範圍，不是PLC禁止使用。

## 本樣本的資源重疊

N002的RAMP2 WR=R15，佔用**R15～R18**；N003的R→T目的表格從R10開始、長度8，會寫**R10～R17**。因此R15、R16、R17重疊。依7-90工作區不得重複使用，生成工具會明確拒絕整份樣本；不修改原始檔或偷偷搬移使用者位址。

分開產出兩份候選檔，原參數與接線不變：

- [ASCWR／RAMP／RAMP2](../artifacts/test20_process_functions.ldr)：原N000～N002。
- [R→T](../artifacts/test20_register_to_table.ldr)：原N003。

這兩份檔案是**分開匯入的指令試檔**，不能重新合併使用而忽略同一工作區衝突。沒有補入暫存器初始化、ASCII資料或PLC環境設定。

## 驗證層級

測試包含精確payload、CRC、原始雜湊、完整word跨度、表格L−1、CLR極性、Tn／WR重複使用、三路輸入、狀態腳位、M→M新舊政策、未知形式拒絕及缺失模擬的明確拒絕。

完整測試 **788項通過**；Ruff／格式檢查、30個來源檔案的Mypy檢查通過。setup check確認19個MCP工具及既有需求到LDR流程正常。

另以新啟動的MCP stdio呼叫生成與二進位resource回讀，核對候選檔與原樣本對應網路位元組一致；[驗證報告](../artifacts/test20_verification.json)記錄結果。沒有新指令的獨立執行模型或MCP內建執行模擬，未做GUI匯入、通訊或實體PLC驗證。
