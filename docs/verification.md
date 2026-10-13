# 驗證依據

## 原始樣本

`samples/` 保留二十一份原始匯出，共141 records；141筆皆可解析並在取證編碼層重建，不代表全部允許生成。雜湊及精確payload由`tests/test_sample_integrity.py`與編解碼測試固定。這是現有樣本覆蓋率，並不代表完整指令集。

| 樣本 | bytes | records | 覆蓋 |
| --- | ---: | ---: | --- |
| w1.ldr | 277 | 1 | 單接點、Y coil |
| test.ldr | 404 | 8 | 串並聯、多 coil、Timer、空網路 |
| test2.ldr | 362 | 6 | NO/NC、M coil、Timer、並聯 |
| test3.ldr | 468 | 12 | 中間空網路、較大 preset、Counter、C/M 接點 |
| test4.ldr | 406 | 8 | Y/M 接點、反相 coil、混合支路、原生邊沿 |
| test5.ldr | 377 | 7 | register OR、FOR/BREAK/NEXT |
| test6.ldr | 491 | 13 | FUN33 LCNV，FBs-24MA 檔頭 |
| test7.ldr | 371 | 5 | 原生上升沿、FUN11～14、另一 FBs-24MA metadata |
| test8.ldr | 399 | 7 | INC／DEC、CMP、AND、SET／RESET、直接電源軌 |
| test9.ldr | 410 | 8 | MC／MCE、DIFU／DIFD、07P.UDCTR、原生並聯 |
| test10.ldr | 375 | 5 | XOR、XNR、ZNCMP、→BCD、→BIN、T 數值與 WX/WY |
| test11.ldr | 461 | 7 | 比較接點170～175、浮點200～204、FBs-32MA 檔頭 |
| test12.ldr | 388 | 4 | 浮點205～208、binary32 常數、擴充 R/D/M、FBs-40MA 檔頭 |
| test13.ldr | 409 | 7 | 浮點209～215、單 word 角度、原地雙 word、FBs-44MN 檔頭 |
| test14.ldr | 404 | 6 | 浮點216～220、ERR 接線、74 IMDIO、F6 常數 |
| test15.ldr | 391 | 5 | FUN76～80、KL／WR／連續 I/O、R3999／V |
| test16.ldr | 423 | 7 | DIV48、SUM、PID、WDT、HSC0 讀寫、FBs-60MC 檔頭 |
| test17.ldr | 420 | 8 | 整數25～29／31、DIV48新形式、FBn-26MC |
| test18.ldr | 400 | 6 | ADCNV、MLC、BITRD／BITWR、精確LBL／JMP |
| test19.ldr | 439 | 7 | 積算型計時、TPCTL、精確CALL解析、FBe-20MA |
| test20.ldr | 396 | 4 | ASCWR、RAMP、RAMP2、R→T；已解析但完整樣本有工作區衝突 |

test9 是格式樣本片段，能解碼不代表符合完整程式的 MC 配對與架構政策。新增 function 的驗證邊界見 [原生 function 編碼](test8-test9-functions.md)。

對照畫面位於 `samples/screenshots/`。測試內保留完整 bytes，不在文件重複列出所有 record。

## 匯入基準

自保持模板：`(Y0 OR X0) AND NOT X1 → Y0`，281 bytes，payload `4100A0009001C100`，record CRC `0x5048`。已有人工匯入成功紀錄；`create_start_stop` 預設重建此組合。其他極性、位址或 header 不自動繼承驗證狀態。

交通燈基準保存在 `tests/fixtures/`：

| 檔案 | 用途 |
| --- | --- |
| traffic_light-dangling.ldr | 未連接支路的缺陷重現 |
| traffic_light-connected-verified.ldr | 人工匯入成功基準：25 網路、13 輔助 M、713 bytes |

Connected 基準 SHA-256：`a4694aa8db73737ada925742ebc6ba164aee52e56137bd5ae201017c203b3b94`。

簡化版為 18 網路、6 輔助 M、604 bytes，SHA-256 `656394d7c854f2d458fb6a38fb99f1981ab45ee9a223a520943ffdc44eafb688`。已通過原始元件掃描比對，尚不列為 GUI 匯入基準。

## 驗證層次

- 容器測試：長度、CRC、未知資料保存、byte-for-byte 往返。
- 邏輯測試：完整真值表、隨機樹、最佳化等價性與無巢狀合併。
- 時序測試：配方、暫停續跑、交通燈循環與跳步。
- MCP 測試：schema、工具呼叫、驗收失敗不寫檔、實際輸出與設計報告。
- GUI 匯入：僅適用已確認的具體檔案，不由前述測試推定。

沒有實體 PLC 運行或機械安全驗證保證。測試通過不提高未知指令或任意新組合的匯入狀態。

## 比較接點位置人工確認

2026-10-07 使用者確認 `FUN170_175_all_positions_probe.ldr` 全部正確，涵蓋6種比較的首段／串聯位置。完整hash與驗證範圍見 [test11 使用者 GUI 確認](test11-functions.md)。這是指定試檔的 GUI 回報，不是實機驗證，也不是所有後續生成檔的匯入保證。

## test12 未發版驗證

四筆 payload 與完整 388 bytes 經目前原始碼 MCP stdio 讀取、生成、resource 下載後與原檔相同。包含 CRC、雙字組、I/O 與三層 M→M 政策檢查；483 項自動測試通過。浮點 PLC 執行模型、內建執行模擬、新檔 GUI 匯入與實體 PLC 均未驗證。詳見 [test12](test12-functions.md)。

## test13 未發版驗證

完整 409 bytes 經 MCP 生成／下載後與原檔相同；新增單字組角度來源、原地讀寫及個別指令 bank 邊界檢查。531 項測試通過；詳見 [test13](test13-functions.md)。未經浮點執行模型、內建執行模擬、GUI 或實機驗證。

## test14 未發版驗證

MCP stdio 產檔下載與原檔 404 bytes 相同；559 項測試通過。包含 ERR 的 M→M 拒絕與 IMDIO X0～X9 完整契約。沒有數學／I/O 執行模型、GUI 或實機驗證。詳見 [test14](test14-functions.md)。

## test15 未發版驗證

MCP stdio 產檔下載與原檔 391 bytes 相同；592 項測試通過。KL 隱含 M 輸出參與三層政策檢查，WR 不可重複使用。未做掃描硬體執行模型、內建模擬、GUI 或 PLC 驗證。詳見 [test15](test15-functions.md)。

## test16 未發版驗證

完整423 bytes 經 MCP stdio 讀取、生成、resource 下載後與原始 test16 相同；630項測試通過。新增 DIV48 三字組、SUM 整段、PID WR 獨占、三路輸入／輸出政策檢查及 FBs-60MC 檔頭。未做獨立執行模型、MCP 內建執行模擬、GUI 或實機驗證。詳見 [test16](test16-functions.md)。

## test17 未發版驗證

MCP stdio 產檔、下載後420 bytes 與原檔完全相同，663項測試通過。包含 MEAN 暫存器 N 的最大可能跨度、EXT 雙字組、DIV48 兩種輸入形式與三層 M→M 檢查。CRC16 MD=1 的引用分析明列不完整；無獨立執行模型、內建模擬、GUI 或實機驗證。詳見 [test17](test17-functions.md)。

## test18 未發版驗證

MCP stdio 重建、下載後400 bytes與原檔完全相同；701項測試通過。另生成四個資料處理網路，不含無條件向後跳躍。新指令無獨立執行模型、內建模擬、GUI或PLC驗證；[LBL／JMP重定位限制](test18-functions.md)保持明列。

## test19 未發版驗證

新啟動的MCP stdio生成330 bytes試檔，包含原N004與N006，兩個payload及FBe-20MA檔頭與原樣本相同。二進位資源下載、CRC、完整I/O範圍、當時嚴格模式的M→M拒絕、CALL生成拒絕均經實際工具呼叫確認。使用者後續澄清允許function所需M→M；更新試檔包含原N001～N006，完整CALL仍拒絕。新增功能沒有執行模型、GUI或PLC驗證；詳見[test19](test19-functions.md)。

## test20 未發版驗證

MCP stdio已生成並讀回原N000～N002、N003兩份候選檔，payload與原樣本一致。完整樣本R15～R17工作區衝突被正確拒絕；function的M→M通過。沒有新指令執行模型、GUI或實體PLC驗證；見[test20](test20-functions.md)。
