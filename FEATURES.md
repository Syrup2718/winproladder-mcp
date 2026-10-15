# WinProLadder MCP 現有功能總覽

[首頁](README.md) · [文件索引](docs/README.md)

版本：**v0.11.0**。整理日期：**2026-10-15**。

本文件描述**目前原始碼**。最後安裝包為 v0.10.0，差異記錄於[0.11.0版本紀錄](docs/release-0.11.0.md)；安裝包不隨儲存庫提供。原生指令按 FUNC 編號排列，能力與限制以此表及 MCP schema 為準。

## 1. 能完成什麼

使用者提出控制需求 → 連接 MCP 的 AI Agent 解讀需求與 I/O → MCP 編譯、檢查 → 取得真正的 **WinProLadder `.ldr` 二進位檔案**。

自然語言由 Agent 解讀；MCP 負責結構化設計、編碼、檔案與支援範圍內的模擬。產檔不需要啟動 WinProLadder 或 VM。目前支援已取樣的 FBs-20MC、FBs-24MA、FBs-32MA、FBs-40MA、FBs-44MN、FBs-60MC、FBn-26MC、FBe-20MA、FBe-40MC、FB-28MA、HB1-32M、FBs-40MC 檔頭，不代表支援全部 CPU、軟體版本或指令變體。

清單包含可生成形式、僅限原樣重建的記錄，以及僅解析項目，不能將每一列都視為完整支援。下表的限制欄是支援範圍的一部分。

| 狀態 | 定義 |
| --- | --- |
| 可生成 | 在列出的參數範圍內編碼，仍須通過政策與 I/O 檢查。 |
| 樣本限定 | 只能重建已確認記錄；不代表可任意修改標籤或程式位置。 |
| 僅解析 | 可以辨識記錄，但生成工具拒絕輸出。 |
| 未實作形式 | PLC 手冊可能允許，但本專案尚無對應編碼。 |

編碼支援不代表 D/P、所有運算元、模擬、GUI 或 PLC 執行皆已驗證。

## 2. 原生 FUNC 清單

| FUNC | 名稱／用途 | MCP action | 已實作範圍與主要限制 |
| --- | --- | --- | --- |
| 00 | MC 主控開始 | `mc` | EN、編號 0..127；須配對，不接受巢狀或交錯區域 |
| 01 | MCE 主控結束 | `mce` | 對應 MC 編號 |
| 04 | DIFU 上升沿微分 | `difu` | trigger 條件、Y/M 目的位址 |
| 05 | DIFD 下降沿微分 | `difd` | trigger 條件、Y/M 目的位址 |
| 06 | BSHF 位元移位 | `bit_shift` | destination；enable／input_bit／left／clear，output；CLR優先於EN |
| 07P | UDCTR 加減計數 | `udctr` | PLS、U/D、CLR；PV 為 0..32767 常數，CV 為可寫 R/D；不支援 CUP 接線 |
| 08 | MOV 搬移 | `move_word` | 16-bit word 來源，R/D、既有 T/WX0/WY0 與精確 WY8；不含常數來源、D/P |
| 09 | MOV/ 倒相搬移 | `move_inverse` | 同上；WY8 寫入 Y8～Y23 全部16點 |
| 10 | TOGG 交替開關 | `toggle_bit` | trigger 上升沿翻轉 bit_destination，Y0～255／M0～999 |
| 11 | ＋ 加法 | `arithmetic` / `add` | 16-bit；Sa 為 R/D，Sb 為 0..32767 常數，D 為可寫 R/D |
| 12 | − 減法 | `arithmetic` / `sub` | 同上 |
| 13 | × 乘法 | `arithmetic` / `mul` | 同上；目的地佔兩個連續 word |
| 14 | ÷ 除法 | `arithmetic` / `div` | 同上；商／餘數佔兩個 word，拒絕常數除零 |
| 15 | ＋1 原生加一 | `increment` | EN、R/D 目的位址 |
| 16 | −1 原生減一 | `decrement` | EN、R/D 目的位址 |
| 17 | CMP 數值比較 | `compare` | R/D Sa、Sb，EN、U/S；相等／大於／小於接普通 Y/M 線圈 |
| 18 | AND 位元且 | `bitwise` / `and` | R/D Sa、Sb、目的位址及 EN |
| 19 | OR 位元或 | `bitwise` / `or` | 同上；保留舊 `register_or` 介面 |
| 20 | →BCD 二進位轉 BCD | `word_conversion` / `to_bcd` | **目前僅接受 0..9999 常數來源**，不支援暫存器來源形式 |
| 21 | →BIN BCD 轉二進位 | `word_conversion` / `to_bin` | word 來源及可寫目的地；不接受常數來源 |
| 22 | BREAK 跳出迴圈 | `break` | EN 條件；須位於迴圈內 |
| 23 | DIV48 48-bit 除法 | `div48` | Sa／Sb／D 各3 words；two_inputs含U/S，single_input不含；D=0／ERR |
| 24 | SUM 總和 | `sum` | 16-bit 來源整段，N=1..511 常數，R/D 目的地 |
| 25 | MEAN 平均值 | `mean` | 暫存器 N，執行時2..256；來源按最大256 words檢查；ERR |
| 26 | SQRT 整數平方根 | `sqrt` | 暫存器來源、目的地各1 word；ERR |
| 27 | NEG 取負 | `neg` | 原地1 word，與浮點 FNEG 區分 |
| 28 | ABS 絕對值 | `abs` | 原地1 word，與浮點 FABS 區分 |
| 29 | EXT 符號擴展 | `ext` | 16-bit 擴展至相鄰2 words |
| 30 | PID 泛用控制 | `pid` | A/M、BUM、D/R；SR8／OR1／PR7／WR5；ERR／HAL／LAL；Ts 單位10 ms |
| 31 | CRC16 | `crc16` | 樣本 MD=1、常數 N=1..256；手冊標為保留，僅支援編碼、語意尚未確認 |
| 32 | ADCNV 類比轉換 | `adcnv` | Pl=0、N=1..64常數；EN／F/T；來源目的整段檢查 |
| 33 | LCNV 線性轉換 | `lcnv` | Md、S、Ts、D、L；Md=0..3、L=1..64；超出原樣本的參數組合屬外推 |
| 34 | MLC 多段線性轉換 | `mlc` | Sl常數1..64、Tl暫存器；EN／X/Y、OVR；表格各255個可能讀取word |
| 35 | XOR 位元互斥或 | `exclusive_logic` / `xor` | word Sa、Sb、可寫目的地；不支援 D=0 腳位接線 |
| 36 | XNR 位元互斥或反相 | `exclusive_logic` / `xnr` | 同上；支援樣本中的 T1 數值來源 |
| 37 | ZNCMP 區間比較 | `zone_compare` | R/D 來源；上下限為 -32768..32767 常數；區間內／高於上限／低於下限接普通線圈 |
| 40 | BITRD 讀取位元 | `bitrd` | R/D word、bit=0..15、OTB／ERR；EN=0受M1919影響 |
| 41 | BITWR 寫入位元 | `bitwr` | R/D word、bit=0..15、EN／INB、ERR；其他bits保持 |
| 42 | BITMV 位元搬移 | `bit_move` | source／destination、source_index／destination_index=0～15；enable、error；保留目的其他bits |
| 43 | NBMV 位數搬移 | `nibble_move` | 同上；位置0～3 |
| 44 | BYMV 位元組搬移 | `byte_move` | 同上；位置0～1 |
| 45 | XCHG 資料互換 | `word_exchange` | source=Da、destination=Db；enable；兩端均讀寫 |
| 46 | SWAP 高低byte交換 | `byte_swap` | destination；enable；原地讀寫 |
| 47 | UNIT 位數結合 | `nibble_unite` | source、count=1～4、destination；enable、error；讀N words寫1 word |
| 48 | DIST 位數分配 | `nibble_distribute` | source、count=1～4、destination；enable、error；讀1 word寫N words |
| 49 | BUNIT 位元組結合 | `byte_unite` | source、length_register=N、destination；enable；動態N 1～256 bytes，最大256來源／128目的words |
| 50 | BDIST 位元組分配 | `byte_distribute` | source、length_register=N、destination；N=1～256 bytes，最大128來源／256目的words |
| 51 | SHFL 左移 | `shift_left` | destination、count=1～16；enable／input_bit；output／error |
| 52 | SHFR 右移 | `shift_right` | destination、length_register=N；enable／input_bit；output／error |
| 53 | ROTL 左旋 | `rotate_left` | destination、length_register=N；enable；output／error |
| 54 | ROTR 右旋 | `rotate_right` | destination、count=1～16；enable；output／error |
| 55 | B→G 二進制轉格雷碼 | `binary_to_gray` | source、destination、enable；樣本16-bit非P |
| 56 | G→B 格雷碼轉二進制 | `gray_to_binary` | 同上 |
| 57 | DECOD 解碼 | `decode_bits` | source、source_index=0～15、bit_length=1～8、destination；enable／error；輸出2^NL bits |
| 58 | ENCOD 編碼 | `encode_bits` | source、source_index=0～15、count=NL=2～256點、destination；enable／high_priority，zero／error |
| 59 | →7SG 七段碼轉換 | `to_seven_segment` | source、count=N=0～3（N+1位）、destination；enable／error；保留未用高byte |
| 60 | →ASC 文字轉ASCII | `ascii_literal` | 目前僅text="ABCDEF"精確字串編碼、可改R/D目的及EN；其他字串尚未確認 |
| 61 | →SEC 時分秒轉秒 | `hms_to_seconds` | 來源3words依秒／分／時，目的2words；enable／zero |
| 62 | →HMS 秒轉時分秒 | `seconds_to_hms` | 來源2words，目的3words依秒／分／時；enable／zero／overflow |
| 63 | →HEX ASCII轉十六進制 | `ascii_to_hex` | count=1～511；讀N words寫ceil(N/4) words，保留未用nibbles；error |
| 64 | →ASCII 十六進制轉ASCII | `hex_to_ascii` | count=1～511；讀ceil(N/4) words寫N words，保留目的高bytes |
| 65 | LBL 標籤 | `lbl` | 精確標籤1記錄，尚未支援任意名稱 |
| 66 | JMP 跳躍 | `jmp` | 僅完整test18原樣重建；目標欄位未解碼，不支援重定位或改動程式 |
| 67 | CALL 副程式呼叫 | `call` | 僅解析 test19 精確記錄；目標重定位未解碼，禁止生成 |
| 70 | FOR 迴圈開始 | `for` | 次數1..16383常數，單層迴圈 |
| 71 | NEXT 迴圈結束 | `next` | 須與 FOR 配對 |
| 74 | IMDIO 即時 I/O 更新 | `imdio` | start=X/Y、count=1..36；整段 I/O 契約，限主機點位 |
| 76 | TKEY 十進位按鍵 | `tkey` | X×10、KL×10；KPR 狀態輸出 |
| 77 | HKEY 矩陣鍵盤 | `hkey` | X×4、Y×4、KL×16、WR×1；NKP／FKP |
| 78 | DSW 指撥開關 | `dsw` | X×4、Y×4、WR×2；DN／ERR |
| 79 | 7SGDL 七段掃描輸出 | `7sgdl` | Y×8、mode=0..3、WR×1；DN |
| 80 | MUXI 多工接點輸入 | `muxi` | X×8、Y×N，N=2..8；結果 ceil(N/2) words、WR×1 |
| 86 | TPCTL 溫控 | `tpctl` | EN／H/C；Sn+Zn≤32、Yn及參數各Zn、WR9；ERR／ALM；Md未編碼 |
| 87 | T.01S 積算計時 | `accumulative_timer` | unit_ms=10；TIM／EN、R/D PV、T或R/D CV、TUP／NUP |
| 88 | T.1S 積算計時 | `accumulative_timer` | 同上，unit_ms=100 |
| 89 | T1S 積算計時 | `accumulative_timer` | 同上，unit_ms=1000 |
| 90 | WDT 設定監控計時器 | `wdt` | 50、60、…120，單位10 ms；90代表900 ms |
| 91 | RSWDT 清除監控計時器 | `rswdt` | EN，無運算元 |
| 92 | HSCTR 讀取硬體計數 | `hsctr` | 目前為 HSC0 精確形式 |
| 93D | HSCTW 寫入硬體計數 | `hsctw` | 目前為 S=0、CN=HSC0、D=PV 精確形式 |
| 94P | ASCWR ASCII輸出 | `ascwr` | 樣本MD=1保留用途，僅編碼；EN／PAU／ABT、Pt8、ACT／ERR／DN；來源範圍未完全解析 |
| 95 | RAMP 緩升降 | `ramp` | Tn須10 ms且獨占、暫存器PV／SL／SU、D+1獨占；EN／PAU／U/D與三狀態 |
| 98 | RAMP2 追蹤緩升降 | `ramp2` | 暫存器Om／Ta／Td／Rt／Rc、WR4；OR區與D0..3999，Ta／Td內容為ms |
| 100 | R→T 暫存器到表格 | `reg_to_table` | 16-bit非P；暫存器Rs／Td／Pr、L=2..2048；EN／INC／CLR、END／ERR |
| 101 | T→R 表格到暫存器 | `table_to_reg` | Ts／L／Pr／Rd；L=2..2048；EN／INC／CLR、END／ERR |
| 102 | T→T 表格逐筆搬移 | `table_to_table` | Ts／Td／L／Pr；L=2..2048；EN／INC／CLR、END／ERR |
| 103 | BT_M 整表搬移 | `block_table_move` | Ts／Td／L；L=2..256；EN |
| 104 | T_SWP 整表互換 | `table_swap` | source=Ta、destination=Tb、L=2..256；兩表皆可寫 |
| 105 | R-T_S 暫存器對表格搜尋 | `register_table_search` | 常數Rs、Ts／L／Pr；FHD／D/S、FND／END／ERR |
| 106 | T-T_C 表格比較 | `table_compare` | Ta／Tb／L／Pr；FHD／D/S、FND／END／ERR |
| 107 | T_FIL 表格填入 | `table_fill` | 常數Rs、Td／L；EN |
| 108 | T_SHF 表格位移 | `table_shift` | 暫存器IW／Ts／Td／L／OW；L/R，支援原地 |
| 109 | T_ROT 表格旋轉 | `table_rotate` | Ts／Td／L；L/R，支援原地 |
| 110 | QUEUE 先進先出 | `queue` | IW／QU／L／Pr／OW；I/O、EPT／FUL／ERR |
| 111 | STACK 後進先出 | `stack` | IW／ST／L／Pr／OW；I/O、EPT／FUL／ERR |
| 112 | BKCMP 區塊比較 | `block_compare` | Rs／Ts／L／D；讀2L個限值，寫L個Y/M結果；ERR／M1975 |
| 113 | SORT 大小排序 | `table_sort` | source、destination、length=2～127；enable／ascending，error |
| 114 | Z-WR 區域寫入 | `zone_write` | R/D destination、length=N=1～511；enable／ones，error；N直接編碼 |
| 120 | MAND 矩陣AND | `matrix_and` | Ma／Mb／Md、L=2..256 words；EN |
| 121 | MOR 矩陣OR | `matrix_or` | 同上 |
| 122 | MXOR 矩陣XOR | `matrix_xor` | 同上 |
| 123 | MXNR 矩陣XNR | `matrix_xnr` | 同上 |
| 124 | MINV 矩陣反相 | `matrix_invert` | Ms／Md、暫存器L；按256 words追蹤可能範圍 |
| 125 | MCMP 矩陣比較 | `matrix_compare` | Ma／Mb／L／Pr；FHD／D/S、FND／END／ERR |
| 126 | MBRD 矩陣位元讀取 | `matrix_bit_read` | Ms／L／Pr；INC／CLR、OTB／END／ERR |
| 127 | MBWR 矩陣位元寫入 | `matrix_bit_write` | Md／L／Pr；EN／INB／INC／CLR、END／ERR |
| 128 | MBSHF 矩陣位元位移 | `matrix_bit_shift` | source、destination、length=2～256 words；enable／input_bit／left，output |
| 129 | MBROT 矩陣位元旋轉 | `matrix_bit_rotate` | source、destination、length=2～256 words；enable／left，output |
| 130 | MBCNT 矩陣位元計數 | `matrix_bit_count` | source、length=2～256 words，destination只寫1 word；enable／ones，zero |
| 170 | = 相等比較接點 | `comparison_chain` / `eq` | 首段／後續串聯皆可；位置試檔已經使用者 GUI 確認 |
| 171 | > 大於比較接點 | `comparison_chain` / `gt` | 首段／後續串聯皆可；位置試檔已經使用者 GUI 確認 |
| 172 | < 小於比較接點 | `comparison_chain` / `lt` | 首段／後續串聯皆可；位置試檔已經使用者 GUI 確認 |
| 173 | <> 不等比較接點 | `comparison_chain` / `ne` | 首段／後續串聯皆可；位置試檔已經使用者 GUI 確認 |
| 174 | >= 大於等於比較接點 | `comparison_chain` / `ge` | 首段／後續串聯皆可；位置試檔已經使用者 GUI 確認 |
| 175 | <= 小於等於比較接點 | `comparison_chain` / `le` | 首段／後續串聯皆可；位置試檔已經使用者 GUI 確認，可用常數 Sb=0..32767 |
| 200 | I→F 整數轉浮點 | `float_operation` / `i_to_f` | 來源 1 word，結果 2 words |
| 201 | F→I 浮點轉整數 | `float_operation` / `f_to_i` | 來源 2 words，結果 1 word |
| 202 | FADD 浮點加法 | `float_operation` / `add` | 各來源及結果都是 2 words |
| 203 | FSUB 浮點減法 | `float_operation` / `sub` | 同上 |
| 204 | FMUL 浮點乘法 | `float_operation` / `mul` | 同上 |
| 205 | FDIV 浮點除法 | `float_operation` / `div` | 暫存器或浮點常數來源；拒絕常數除零 |
| 206 | FCMP 浮點比較 | `float_compare` | equal／greater／less 普通 Y/M 線圈 |
| 207 | FZCP 浮點區間比較 | `float_zone_compare` | S 為暫存器，上下限可為暫存器或常數；within／above／below 線圈 |
| 208 | FSQR 浮點平方根 | `float_operation` / `sqrt` | 暫存器或常數來源，結果 2 words |
| 209～211 | FSIN／FCOS／FTAN | `float_operation` / `sin`、`cos`、`tan` | 16-bit 角度 -18000～18000，單位 0.01 度；結果為浮點雙字組 |
| 212～213 | FNEG／FABS | `float_operation` / `neg`、`abs` | destination 原地讀寫雙字組，不提供 sa／sb |
| 214～215 | FLN／FEXP | `float_operation` / `ln`、`exp` | 浮點來源／結果；這兩個指令的 D bank 上限為 D3999 |
| 216～220 | FLOG／FPOW／FASIN／FACOS／FATAN | `float_operation` / `log`、`pow`、`asin`、`acos`、`atan` | pow 的 sa 為指數、sb 為底數；反三角結果為弧度 |

補充限制：

- 比較接點支援六種關係的首段／後續串聯位置，位置試檔已獲 GUI 確認，其他運算元組合仍需驗證；仍不支援 OR、混合普通接點或 D 型；精確新增 WS0、WM0、C2；R5000..8071 已依手冊與編碼錨點擴充。WM0 的 M0..M15 讀取納入架構政策。
- 浮點暫存器範圍為 R0..3839、R5000..8071、D0..4095；完整雙字組不得跨界；FUN214～220 的 D bank 依個別手冊頁限定至 D3999。算術與比較支援有限 binary32 常數，轉換指令仍限暫存器。F5/F6 常數格式已取樣，F7 為推導；支援普通浮點 ERR 線圈，FLOG 已取樣，其他 ERR 形式屬推導。不支援 P／間接。詳見 [test12](docs/test12-functions.md)。

- 整數加減乘除尚不支援 Sa 常數、Sb 暫存器／負常數、狀態旗標接線、D/P 形式或間接定址。
- CMP、ZNCMP 的結果線圈目前不接受 SET／RESET／反相模式。
- ZNCMP 尚不支援暫存器上下限或 ERR 接線，lower 不得大於 upper。
- →BCD／→BIN 尚不支援 ERR 接線；LCNV 不支援 33P、間接定址、暫存器 L 或轉換表自動初始化。
- 除明列的 07P.UDCTR 外，不可將其他 D/P 變體視為已支援。
- **上表 action 目前均未提供內建執行模擬**；可產檔與可模擬是不同能力。

## 3. 基本階梯圖元件

| 元件／功能 | 支援內容 |
| --- | --- |
| 接點 | X、Y、M、T、C 常開／常閉接點 |
| 條件 | AND、OR、NOT、括號、TRUE/FALSE，以及 `&`、`|`、`!` 寫法 |
| 接線 | 串聯、並聯、多輸出；支援範圍內自動化簡條件與整理接圖 |
| 線圈 | 普通、反相、SET、RESET；Y/M 位址仍受架構政策限制 |
| 原生邊沿接點 | 單一 X 上升沿／下降沿，直接接 Y/M 線圈；與 DIFU/DIFD function 分開實作 |
| Timer | 原生 T、EN、常數 preset、TUP 輸出；目前編碼模型只有 `.01S` 時基 |
| Counter | 原生 C、PLS、CLR、常數 preset、CUP 輸出 |
| 空網路 | 讀取與保留空網路 |
| 設計說明 | 回傳 symbols、network_notes；高階產檔另附設計 JSON，尚未寫入 LDR 註解區段 |

單份 IR 支援 1..1000 網路。X/Y/T/C 的編碼範圍為 0..255，一般 M 為 0..1911，這不是實際 PLC 硬體點數保證。

### Word 位址

- 既有直接 R/D：R0..3839、唯讀輸入區 R3840..3903、R5000..8071、D0..4095；多 word 結果不能跨越已支援 bank 邊界。
- XOR／XNR／→BIN 等新增 word 指令可讀 T0..255 數值；不把它解讀為 T 接點，且不開放 T 作目的地。
- 新增 word 類型目前僅確認 WX0、WY0，其他 WX/WY 編號尚未開放。比較接點另有精確 WS0、WM0、C2 支援；R5000..8071 已納入直接 R bank。
- FUN76～80 另支援精確特殊 word R3999、V；這不等同整個 SR／RTC 區已實作。
- WX0 涵蓋 X0..X15；WY0 涵蓋 Y0..Y15。I/O 檢查與寫入重疊分析會展開全部位元；WX0 不可寫入。

### 時間參數

高階配方的 `delay_ms`／`gap_ms` 使用毫秒；目前要求 10 ms 倍數。低階 Timer IR 的 `preset` 則是目前編碼模型採用的時基刻度，不能與毫秒參數混用。回應會列出刻度、假設時基及名義時間，但 **LDR 解碼尚不能確認目的工程的時基配置**，`configuration_verified=false`；不把名義時間宣稱為 GUI／PLC 實測時間。

普通 T 停用即清零。目前沒有原生保持型計時，也不會擅自新增 X 當外部時脈。

## 4. 高階控制配方與順序控制

`generate_control_ldr` 提供以下 11 種配方：

| 配方 | 用途 |
| --- | --- |
| `start_stop` | 啟動／停止與自保持 |
| `set_reset` | 設定／復歸控制 |
| `toggle` | 輸入觸發切換 |
| `rising_edge` | 上升沿脈波 |
| `falling_edge` | 下降沿脈波 |
| `on_delay` | 延遲啟動 |
| `off_delay` | 延遲停止 |
| `pulse` | 定時脈波 |
| `counter` | 脈波計數與復歸 |
| `forward_reverse` | 正反轉互鎖 |
| `star_delta` | 星三角順序 |

這是配方介面清單，**不保證每個參數組合都能在目前政策下產檔**。部分配方會合成內部 M 網路，若構成無意義的 M→M 複製或中繼仍會被拒絕；原生 function 的 M 結果／狀態允許。配方也不必然採用同名原生 FUNC。

- `generate_system_ldr`：最多組合 24 個獨立控制配方，自動分配內部 M/T/C，允許共用輸入、拒絕資源衝突；不是跨配方製程協調器。
- `generate_sequence_ldr`：1..16 步，可設定各步輸出、計時、完成條件、逾時、reset、abort；每掃描最多轉移一步，同樣受架構政策檢查。
- 順序控制預設使用原生 T。高階順序控制尚未整合原生累積計時器的暫停續跑；只有需求明確指定外部 clock 時，才能使用外部脈波模式，不自動補一個 X。

## 5. MCP 工具清單（19 個）

| 工具 | 用途 |
| --- | --- |
| `get_capabilities` | 查詢版本、功能、限制、政策與輸出位置 |
| `get_manual_reference` | 查閱手冊範圍、版本差異與 RTC 操作程序 |
| `inspect_rtc_snapshot` | 檢查提供的 RTC 數值，不連線或操作 PLC |
| `get_design_guide` | 取得需求轉設計流程、範例與 Ladder schema |
| `generate_ldr` | 自訂條件／原生指令產生 .ldr，主要產檔入口 |
| `generate_control_ldr` | 使用單一控制配方產檔 |
| `generate_system_ldr` | 組合多個獨立控制配方 |
| `generate_sequence_ldr` | 順序流程產檔 |
| `create_ldr` | 從低階 IR 建立新檔；未驗證形式須明確標示 |
| `create_start_stop` | 固定 X0 啟動、X1 停止、Y0 自保持模板，僅用於符合此 I/O 的需求 |
| `get_ldr_artifact` | 取得 .ldr 原始 bytes、SHA-256 與下載資源 |
| `inspect_ldr` | 查看容器、bytes、位移與 CRC |
| `read_ldr` | 按畫面順序讀取網路，未知指令保留為 opaque |
| `analyze_ldr` | 解釋網路、列出元件讀寫與重複寫入 |
| `compare_ldr` | 比較兩份檔案的新增／刪除／修改網路 |
| `validate_ladder` | 預覽結構、接圖簡化、資源用量與架構政策結果 |
| `simulate_ladder` | 在支援的布林／T/C 範圍內執行掃描模型 |
| `export_ldr` | 匯出新檔並保留原始內容；嚴格政策下仍可能拒絕未知或違規網路 |
| `modify_network` | 插入、替換或刪除網路，另存新檔，索引 0 對應 N000 |

傳輸方式為本機 stdio。除工具外，提供 `winproladder://capabilities` 與 `winproladder://artifacts/{name}` 資源；後者是 MCP 二進位檔案資源，不是 HTTP 網址。

## 6. 產檔與架構規則

- 主要生成工具必填 `io_contract`，只使用需求指定的 X/Y。原始設計和生成 bytes 的 I/O 都會檢查，超出即拒絕。
- 本工作區啟用 `forbid_m_to_m=true`、`allow_function_m_to_m=true`：禁止無意義的 M→M 複製、中繼及自動 helpers；允許 M 控制原生 function，並由其輸出 M 結果／狀態（含計時、計數、比較、DIFU／DIFD）。MC 區域內的普通 M 複製仍禁止，不能用假 function 包裝複製。
- 數值與狀態設計應使用原生暫存器；不以改名或偽裝的繼電器鏈繞過政策。
- 寫出前檢查來源、接圖轉換後程式及實際 bytes 解碼结果。無法符合要求時回報限制，不自行增加 I/O。
- 新檔採不覆寫方式建立；操作限於指定工作目錄，預設輸出至 `artifacts/`。
- 提供的 acceptance 案例若失敗即不產檔；沒有提供驗收案例不代表已驗證行為。
- 未知格式可保留作讀取研究，但無法證明符合嚴格架構政策時不能直接輸出。

## 7. 模擬、測試與驗證程度

| 層次 | 目前狀態 |
| --- | --- |
| 獨立離線核對 | 原始樣本 bytes、CRC、逐 byte 往返、I/O 引用、政策、負數與邊界檢查；不等同 PLC 行為 |
| MCP 內建模擬 | 布林接點／線圈、SET／RESET、單一 X 邊沿；指定 scan_ms 時支援有限的非保持 T/C 掃描模型 |
| MCP 真實呼叫 | 已測試 stdio 連線、需求產檔、資源下載與 SHA-256 核對 |
| WinProLadder GUI | 僅部分歷史檔案有人工匯入紀錄；test8～test27 新生成檔未因此自動取得 GUI 驗證 |
| 實體 PLC | 未執行實機驗證 |

內建模擬每次最多 256 scans；有時間模型時 scan_ms 為 1..60000 ms。T 時間模型限預設 `.01S` 的 T0..49 及支援的 preset 範圍，不模擬 PLC 非同步時脈相位。數值比較接點、原生 action、暫存器運算、MC/MCE、DIFU/DIFD、UDCTR 與迴圈均未提供執行模型。

v0.10.0 打包時為 **443 項通過**；0.11.0升版時為 **663 項通過**，目前含test27的原始碼測試結果見 [test27驗證紀錄](docs/test27-functions.md)。原始樣本目前 **28 份、195 networks** 可語意解碼與重建。這是現有樣本覆蓋，不代表所有程式都符合政策或所有指令變體皆有效。test11 的比較接點與浮點指令同樣區分離線、MCP 模擬、GUI 與實機驗證。

## 8. 仍未支援

- MOV 等尚未取得可靠編碼的原生 FUNC。
- FUN87～89 的常數 PV、其他 word bank、高階順序產生器整合與執行模擬。
- 未明列的 32-bit／P 形式、間接定址、運算元種類與狀態接線。
- 多數硬體專用指令、通訊與定位功能。
- 全指令 PLC 執行模擬、自動 GUI 匯入驗證、實體 PLC 連線／下載。
- 從 .ldr 完整確認目的工程時間基準與所有 CPU 設定。

## 9. 使用方式與檔案位置

對已連接 MCP 的 Agent 提出需求，例如：

> 使用 WinProLadder MCP，X0 啟動 Y0 並自保持，X1 為 ON 時停止，停止優先。請產生 .ldr 並驗證啟動、保持、停止的行為。

Agent 應先核對需求 I/O 與目前功能，再選擇生成工具，最後交付 .ldr 和驗證狀態。使用者不需要手寫 JSON。

| 資料 | 位置 |
| --- | --- |
| 原始程式 | `src/winproladder_mcp/` |
| 原始樣本與截圖 | `samples/`、`samples/screenshots/` |
| 生成檔與驗證紀錄 | `artifacts/` |
| 目前版安裝包 | `dist/`，目前為 v0.10.0 |
| 歷史安裝包 | `dist/archive/<版本>/` |
| 本機 VM 共享目錄 | `C:/VM_Share` |

相關文件：[入門流程](docs/quickstart.md)、[資料夾導覽](docs/folders.md)、[FUNC test8/test9](docs/test8-test9-functions.md)、[FUNC test10](docs/test10-functions.md)、[詳細參數](docs/reference.md)。

功能與欄位若有後續變更，以實際連線 MCP 回傳的 `get_capabilities`、`get_design_guide` 及工作區政策為準。

最新未發版指令與限制見 [test27](docs/test27-functions.md)。

- [test24：FUN08／09／10、113／114、128～130](docs/test24-functions.md)：樣本形式、WY8完整輸出契約與手冊差異。

- [test25：FUN42～49](docs/test25-functions.md)：部分word搬移、互換、UNIT／DIST及BUNIT動態N。

- [test26：FUN50～57](docs/test26-functions.md)：BDIST動態N、移位／旋轉雙輸入、格雷碼及DECOD跨word範圍。

- [test27：FUN06及58～64](docs/test27-functions.md)：ENCOD、7SG、ASCII、時間轉換與四路BSHF；ASC文字編碼仍限ABCDEF。
