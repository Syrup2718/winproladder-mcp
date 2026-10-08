# 驗證依據

## 原始樣本

`samples/` 保留十五份原始匯出，共 104 records；104 筆皆可語意解碼並重建，包括原生邊沿與 FUN11～14。雜湊及精確 payload 由 `tests/test_sample_integrity.py` 與編解碼測試固定。這是現有樣本覆蓋率，並不代表完整指令集。

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
