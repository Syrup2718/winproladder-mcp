# 原始 WinProLadder 樣本

共19個檔案、130筆網路記錄。保留原始 bytes、檔名與截圖，重建結果另存於 `artifacts/`，不可覆寫本目錄樣本。

| 檔案 | bytes | records | 內容 |
| --- | ---: | ---: | --- |
| [w1.ldr](w1.ldr) | 277 | 1 | 單接點、Y coil |
| [test.ldr](test.ldr) | 404 | 8 | 串並聯、多 coil、Timer、空網路 |
| [test2.ldr](test2.ldr) | 362 | 6 | NO/NC、M coil、Timer、並聯 |
| [test3.ldr](test3.ldr) | 468 | 12 | 中間空網路、較大 preset、Counter、C/M 接點 |
| [test4.ldr](test4.ldr) | 406 | 8 | Y/M 接點、反相 coil、混合支路、原生邊沿 |
| [test5.ldr](test5.ldr) | 377 | 7 | register OR、FOR/BREAK/NEXT |
| [test6.ldr](test6.ldr) | 491 | 13 | FUN33 LCNV，FBs-24MA 檔頭 |
| [test7.ldr](test7.ldr) | 371 | 5 | 原生上升沿、FUN11～14、另一 FBs-24MA metadata |
| [test8.ldr](test8.ldr) | 399 | 7 | INC／DEC、CMP、AND、SET／RESET、直接電源軌 |
| [test9.ldr](test9.ldr) | 410 | 8 | MC／MCE、DIFU／DIFD、07P.UDCTR、原生並聯 |
| [test10.ldr](test10.ldr) | 375 | 5 | XOR、XNR、ZNCMP、→BCD、→BIN、T 數值與 WX/WY |
| [test11.ldr](test11.ldr) | 461 | 7 | 比較接點170～175、浮點200～204、FBs-32MA 檔頭 |
| [test12.ldr](test12.ldr) | 388 | 4 | 浮點205～208、binary32 常數、擴充 R/D/M、FBs-40MA 檔頭 |
| [test13.ldr](test13.ldr) | 409 | 7 | 浮點209～215、單 word 角度、原地雙 word、FBs-44MN 檔頭 |
| [test14.ldr](test14.ldr) | 404 | 6 | 浮點216～220、ERR 接線、74 IMDIO、F6 常數 |
| [test15.ldr](test15.ldr) | 391 | 5 | FUN76～80、KL／WR／連續 I/O、R3999／V |
| [test16.ldr](test16.ldr) | 423 | 7 | DIV48、SUM、PID、WDT、HSC0 讀寫 |
| [test17.ldr](test17.ldr) | 420 | 8 | 整數25～29／31、DIV48新形式 |
| [test18.ldr](test18.ldr) | 400 | 6 | 類比轉換、位元存取、LBL／JMP |
| [test19.ldr](test19.ldr) | 439 | 7 | CALL、FOR/NEXT、積算計時87～89、TPCTL；function的M→M已允許；CALL僅解析 |
| [test20.ldr](test20.ldr) | 396 | 4 | ASCWR、RAMP、RAMP2、R→T；R15～R17工作區衝突 |

原始雜湊由 `tests/test_sample_integrity.py` 固定；樣本可解碼不等於符合目前生成政策，也不代表已做 GUI 或 PLC 驗證。完整邊界見 [驗證依據](../docs/verification.md)。截圖保存在 `screenshots/`。

- [test21.ldr](test21.ldr)：5網路，FBe-40MC；T→R、T→T、BT_M、T_SWP。[截圖](screenshots/test21.png)。

- [test22.ldr](test22.ldr)：481 bytes、8個function加1個空白網路，FB-28MA；[截圖](screenshots/test22.png)。

- [test23.ldr](test23.ldr)：460 bytes、8網路，HB1-32M；[截圖](screenshots/test23.png)。

- [test24.ldr](test24.ldr)：436 bytes、8網路，FBs-40MA；[截圖](screenshots/test24.png)。

- [test25.ldr](test25.ldr)：430 bytes、8網路，FBs-44MN；[截圖](screenshots/test25.png)。
