# WinProLadder MCP 專案交接文件（給 Codex）

## 1. 專案目標

我要開發一個：

```text
WinProLadder MCP Server
```

目標是讓 ChatGPT / Codex / Claude 等 AI Agent 能夠理解、讀取、產生與修改永宏 FATEK WinProLadder 的梯形圖。

長期目標：

```text
自然語言
   ↓
AI 理解 PLC 控制需求
   ↓
Ladder IR
   ↓
WinProLadder .ldr Encoder
   ↓
產生 .ldr
   ↓
WinProLadder Import
```

反向流程：

```text
WinProLadder .ldr
   ↓
LDR Parser
   ↓
Ladder IR
   ↓
AI 分析梯形圖
```

未來可能再加入：

```text
WinProLadder GUI Automation
PLC Online Monitoring
FATEK PLC 通訊
Syntax Check
PLC Debugging
```

---

# 2. MCP 與 Skill 定位

這個專案的核心是：

```text
MCP Server
```

MCP 負責真正執行：

```text
read_ladder()
create_ladder()
modify_ladder()
export_ldr()
validate_ladder()
```

另外可以附一個：

```text
WinProLadder Skill
```

Skill 負責教 AI：

```text
FATEK PLC 元件規則
梯形圖設計方法
自保持
互鎖
Timer / Counter
如何正確使用 MCP Tools
```

兩者是獨立概念，但可以放在同一個 repository。

建議結構：

```text
winproladder-mcp/
│
├─ src/
│  ├─ mcp_server/
│  ├─ ldr/
│  │  ├─ parser.py
│  │  ├─ encoder.py
│  │  ├─ crc.py
│  │  └─ model.py
│  └─ winproladder/
│
├─ skills/
│  └─ winproladder/
│     └─ SKILL.md
│
├─ samples/
├─ tests/
├─ docs/
│  └─ ldr-format.md
├─ PROJECT_BRIEF.md
└─ README.md
```

---

# 3. 為什麼優先研究 `.ldr`

WinProLadder 可以匯出：

```text
Ladder Diagram → .ldr
```

我們希望優先直接解析與生成 `.ldr`，而不是依賴滑鼠座標操作 WinProLadder GUI。

原因：

```text
直接生成 .ldr
    ↓
速度快
穩定
容易測試
不依賴螢幕解析度
不依賴 GUI layout
```

GUI Automation 放在後續階段。

---

# 4. 已取得的樣本

`samples/` 內會放目前 WinProLadder 實際 Export 出來的 `.ldr`。

原始樣本一律視為：

```text
Ground Truth
```

不要修改原始 `.ldr`。

目前已有以下樣本：

## `w1.ldr`

最簡單梯形圖，大致為：

```text
X0 -------- (Y1)
```

主要用途：

```text
確認 .ldr 基本格式
確認 Header
確認單一 X contact
確認單一 Y coil
確認 Network record
```

---

## `test.ldr`

對應梯形圖大致包含：

```text
N000:
X0 ---------------- Y1

N001:
X1 ---------------- Y2

N002:
X2 ---------------- Y2
                   └ Y3

N003:
Timer T1
time base .01S
preset 100
------------------- Y4

N004:
T1 -- X3 -- X4 -- /X5 ------- Y5

N005:
包含：
/X6
X7 / X8 並聯
X9 / X10 並聯
---------------------------- Y6

N006:
Empty

N007:
Empty
```

主要用途：

```text
研究：
NO Contact
NC Contact
Series
Parallel
Y Coil
Timer
Empty Network
Network 順序
```

---

## `test2.ldr`

對應：

```text
N000:
X0 ---------------- Y0

N001:
/X0 --------------- Y0

N002:
/X0 --------------- M0

N003:
X0 ---------------- M0

N004:
Timer T2
.01S
101
------------------- Y0

N005:

      ┌-- X0 --┐
------|        |-------- Y0
      └-- X1 --┘
```

主要用途：

```text
研究：
X NO / NC
Y Coil
M Coil
Timer address
Timer preset
最簡單 Parallel Branch
```

如果有對應截圖，也一併放入：

```text
samples/screenshots/
```

因為 `.ldr` 告訴我們 Binary 長什麼樣子，截圖告訴我們該 Binary 實際對應哪個 Ladder。

---

# 5. 目前 `.ldr` 初步發現

> 以下內容是先前根據少量樣本做 reverse engineering 得到的結果。
>
> Codex 不可以因為本文件寫了就直接視為官方格式。
>
> 必須用現有 `.ldr` 樣本重新做 byte-by-byte differential analysis 驗證。

目前觀察 `.ldr` 不是文字格式，而是 FATEK 自訂 Binary Resource。

Header 中可以看到：

```text
Fatek Resource File Format 1

FB-RES
WinProladder
FBs-20MC
```

目前觀察：

```text
0x000 ~ 0x0FF
```

很可能主要是 Resource Header。

真正 Ladder record 約從：

```text
0x100
```

開始。

這個 Offset 需要對更多檔案驗證。

---

# 6. Network 儲存順序

目前樣本顯示 Network 在 `.ldr` 裡可能是：

```text
反向儲存
```

例如 WinProLadder 顯示：

```text
N000
N001
N002
N003
...
```

Binary 中可能是：

```text
N007
N006
...
N001
N000
```

Codex 必須重新驗證此規則，尤其是：

```text
1 Network
2 Network
多個 Empty Network
中間有 Empty Network
```

等案例。

---

# 7. Network Record 初步結構

目前推測每個 Network 類似：

```text
12 10

record_length     uint16 little endian

payload_length    uint16 little endian

payload

01 00 00

CRC / integrity
```

目前觀察：

```text
record_length = payload_length + 5
```

檔案尾端曾觀察到：

```text
FF FF 00 00 00 00
```

可能為 Resource 結束標記。

需要重新驗證。

---

# 8. 目前已觀察的 Opcode

## X Normally Open — rung 開頭

目前觀察：

```text
40 nn
```

可能代表：

```text
Rung 開頭的 Xn Normally Open Contact
```

例如：

```text
40 00 → X0
40 01 → X1
40 02 → X2
```

---

## X Normally Closed — rung 開頭

目前觀察：

```text
50 nn
```

可能代表：

```text
Rung 開頭的 Xn Normally Closed Contact
```

例如：

```text
50 00 → /X0
```

---

## X Normally Open — 串聯

目前觀察：

```text
80 nn
```

可能代表：

```text
後續串聯的 Xn Normally Open Contact
```

---

## X Normally Closed — 串聯

目前觀察：

```text
90 nn
```

可能代表：

```text
後續串聯的 Xn Normally Closed Contact
```

---

## Y Coil

目前觀察：

```text
C1 nn
```

可能代表：

```text
Yn Output Coil
```

例如：

```text
C1 00 → Y0
C1 01 → Y1
C1 02 → Y2
C1 03 → Y3
```

---

## M Coil

目前樣本中：

```text
C8 10
```

對應：

```text
M0 Coil
```

但目前只有少量 M device 樣本。

必須增加：

```text
M1
M2
M10
M100
```

來確認 address encoding。

---

## T Contact

目前曾觀察：

```text
42 nn
```

可能與：

```text
Tn Contact
```

有關。

必須增加更多 T contact 樣本。

---

# 9. Branch / Parallel 初步結果

Branch 中曾出現：

```text
A0
60
E2
```

最簡單案例：

```text
X0 OR X1 → Y0
```

曾觀察到類似：

```text
40 00 A0 01 C1 00
```

所以：

```text
A0 nn
```

高度疑似與：

```text
Parallel NO X Contact
```

有關。

但是複雜 Branch topology 尚未完全破解。

需要專門建立最小差分樣本：

```text
X0 OR X1 → Y0

(X0 OR X1) AND X2 → Y0

X0 AND (X1 OR X2) → Y0

(X0 OR X1) AND (X2 OR X3) → Y0

(X0 AND X1) OR X2 → Y0

三路 parallel：
X0 OR X1 OR X2 → Y0
```

不要直接用複雜 Ladder 猜 Branch encoding。

---

# 10. Timer 初步結果

已有樣本：

```text
T1
Preset = 100
```

以及：

```text
T2
Preset = 101
```

Binary 差分顯示：

```text
100 decimal = 0x64
101 decimal = 0x65
```

所以目前推測 preset 至少在部分情況下是直接整數儲存。

曾觀察 Timer binary 類似：

```text
T1 / 100:
4F E8 FD 80 00 64 03 92 6F FC

T2 / 101:
4F E8 FD 80 00 65 03 94 6F FC
```

其中：

```text
0x64 = 100
0x65 = 101
```

而：

```text
T1 → 0x92
T2 → 0x94
```

曾觀察到可能存在 Timer address mapping。

但不要直接假設：

```text
Tn = 0x90 + 2*n
```

必須增加：

```text
T0
T3
T10
```

驗證。

另外要驗證：

```text
不同 time base
不同 preset 數值範圍
preset > 255
preset > 65535
```

等情況。

---

# 11. CRC / Integrity 初步結果

先前分析推測每個 Network 最後兩個 byte 是：

```text
CRC-16/MODBUS
```

可能參數：

```text
Polynomial: 0xA001
Initial:    0xFFFF
Output:     Little Endian
```

目前推測 CRC 計算範圍為：

```text
payload_length
+
payload
+
01 00 00
```

例如：

```text
04 00
40 00 C1 00
01 00 00
```

計算 CRC16-MODBUS 後，如果結果為：

```text
0xE515
```

則 Binary 內儲存：

```text
15 E5
```

但：

> Codex 第一件事情之一就是重新用所有現有 `.ldr` Network 驗證 CRC。
>
> 必須對所有 Network 逐筆計算並確認 100% match。
>
> 驗證完成後才能標示為 CONFIRMED。

---

# 12. Ladder Intermediate Representation（IR）

不要讓 MCP Tool 直接操作 raw binary。

中間必須建立：

```text
Ladder IR
```

目的：

```text
自然語言
    ↓
Ladder IR
    ↓
LDR Encoder
```

以及：

```text
.ldr
 ↓
LDR Parser
 ↓
Ladder IR
 ↓
AI
```

範例 IR：

```json
{
  "networks": [
    {
      "id": 0,
      "logic": {
        "type": "series",
        "items": [
          {
            "type": "contact",
            "device": "X",
            "address": 0,
            "normally_closed": false
          },
          {
            "type": "coil",
            "device": "Y",
            "address": 0
          }
        ]
      }
    }
  ]
}
```

架構：

```text
             ┌─ LDR Parser ─────┐
.ldr ────────┤                  │
             ▼                  │
          Ladder IR             │
             │                  │
             └─ LDR Encoder ────┘
                     │
                     ▼
                   .ldr
```

MCP 層應盡量只跟 IR 溝通。

---

# 13. Parser 設計原則

Parser 第一版至少要做到：

```text
讀 Header
辨識 Network records
解析 record length
解析 payload length
取得 raw payload
解析 CRC
保留 unknown bytes
輸出 Network 順序
```

非常重要：

> Parser 不可因為不認識某個 opcode，就把未知資料丟掉。

建議 IR 或 AST 支援：

```json
{
  "type": "unknown",
  "raw": "E2 00",
  "offset": 123
}
```

這樣：

```text
parse → encode
```

才有可能做到 lossless round-trip。

---

# 14. Encoder 設計原則

Encoder 第一階段只允許輸出：

```text
已確認支援的 instruction
```

若遇到：

```text
UNKNOWN
HYPOTHESIS
尚未 reverse engineered
```

不要猜 Binary。

應該：

```text
raise UnsupportedInstruction
```

或回傳清楚錯誤。

---

# 15. 第一版 MCP Tools

第一版可以考慮：

## `inspect_ldr(path)`

用於 reverse engineering。

回傳：

```text
File size
Header
Network count
Network order
Record offsets
Record length
Payload length
Raw payload
Footer
CRC
CRC validity
Unknown bytes
```

---

## `read_ldr(path)`

輸入：

```text
.ldr file
```

輸出：

```text
Ladder IR
```

---

## `create_ldr(output_path, ladder)`

輸入：

```text
Ladder IR
```

輸出：

```text
合法 .ldr
```

---

未來再增加：

```text
modify_network()
add_network()
delete_network()
validate_ladder()
```

---

# 16. V0.1 支援範圍

第一版不要追求完整 WinProLadder。

V0.1 優先：

```text
X Normally Open
X Normally Closed

Y Coil
M Coil

Series

簡單 Parallel

Empty Network

Timer
```

後續才增加：

```text
Counter
SET
RST
M Contact
Y Contact
T Contact
C Contact
Registers
MOV
CMP
Arithmetic
Function blocks
複雜 branch
```

---

# 17. Reverse Engineering 方法

必須使用：

```text
Differential Analysis
```

不要亂猜 Opcode。

例如：

```text
Sample A:
X0 → Y0

Sample B:
X1 → Y0
```

若 binary diff 為：

```text
40 00 C1 00

vs

40 01 C1 00
```

則可以合理推測：

```text
第二個 byte = X address
```

但是一個 hypothesis 至少要用多個樣本驗證。

---

# 18. 建議新增差分樣本

下一批最希望取得：

```text
M0 → Y0

M1 → Y0

T0 → Y0

T3 → Y0

T10 → Y0

(X0 OR X1) AND X2 → Y0

X0 AND (X1 OR X2) → Y0

X0 OR X1 OR X2 → Y0

X0 → M1

X0 → M10
```

Timer：

```text
T0 .01S 100 → Y0
T1 .01S 101 → Y0
T2 .01S 200 → Y0
T3 .01S 300 → Y0
```

這些檔案要：

```text
一次只改一個變數
```

以便做 binary diff。

---

# 19. 建議建立 Reverse Engineering Tests

建立：

```text
tests/
└─ reverse_engineering/
   ├─ test_header.py
   ├─ test_records.py
   ├─ test_crc.py
   ├─ test_contacts.py
   ├─ test_coils.py
   ├─ test_branches.py
   ├─ test_timers.py
   └─ test_roundtrip.py
```

所有已知 `.ldr` 必須能：

```text
decode
  ↓
IR
  ↓
encode
```

再做：

```text
original.ldr
      ↓
parser
      ↓
IR
      ↓
encoder
      ↓
generated.ldr
```

最後：

```text
byte-by-byte comparison
```

理想結果：

```text
original == generated
```

---

# 20. Specification 文件

建立：

```text
docs/ldr-format.md
```

建議包含：

```text
WinProLadder LDR Format

1. File Header
2. Resource Metadata
3. Network Record
4. Record Length
5. Payload
6. Footer
7. CRC
8. Instructions / Opcode
9. Device Encoding
10. Branch Encoding
11. Timer Encoding
12. Empty Network
13. End Marker
14. Unknown Fields
```

每項規則標示：

```text
CONFIRMED
HIGH CONFIDENCE
HYPOTHESIS
UNKNOWN
```

例如：

```markdown
### 0x40 — X Normally Open

Status: HIGH CONFIDENCE

Observed:
- `40 00` → X0
- `40 01` → X1
- `40 02` → X2

Hypothesis:
`0x40` represents a normally-open X contact when located at the beginning of a rung.
```

不要把 hypothesis 寫成確定事實。

---

# 21. 專案的重要原則

1. 不修改原始 `.ldr` 樣本。

2. 每項 Binary 規則都必須有測試支持。

3. 不確定的 opcode 標成 `UNKNOWN`，不要猜。

4. Reverse engineering specification 與實作分離。

5. Parser 必須盡量保留未知資料，避免 round-trip 時資訊消失。

6. Encoder 第一階段只輸出已確認支援的 instruction。

7. 所有寫入操作先作用於 copy。

8. 暫時不要對實體 PLC 做任何寫入。

9. 暫時不要優先做 GUI Automation。

10. 不要為了快速完成 MCP 而跳過 `.ldr` reverse engineering。

11. 所有 inference 都必須能追溯到實際 sample。

12. 每新增一種 WinProLadder instruction，都新增對應 sample 和 regression test。

---

# 22. 第一階段優先級

```text
★★★★★ LDR Reverse Engineering
★★★★★ Parser
★★★★★ Encoder
★★★★★ Ladder IR

★★★★☆ Tests
★★★★☆ Documentation

★★☆☆☆ MCP Server

★☆☆☆☆ GUI Automation
★☆☆☆☆ PLC Online Communication
```

先把 `.ldr` 搞懂。

---

# 23. Codex 接手後第一個任務

請先：

```text
1. 閱讀 PROJECT_BRIEF.md

2. 掃描 samples/ 內所有 .ldr

3. 對全部 .ldr 做 hexdump

4. 建立自動 binary diff 工具

5. 找共同 Header

6. 找 0x12 0x10 Network records

7. 驗證 record_length / payload_length

8. 驗證 Network 儲存順序

9. 驗證 CRC-16/MODBUS hypothesis

10. 比較 w1.ldr、test.ldr、test2.ldr 的 opcode 差異

11. 建立 docs/ldr-format.md

12. 每個 reverse engineering 結論標：
    CONFIRMED
    HIGH CONFIDENCE
    HYPOTHESIS
    UNKNOWN

13. 實作最小 Parser

14. Parser 先至少能列出：
    Network index
    raw payload
    CRC
    offsets

15. 實作最小 Encoder

16. 建立：
    parse → encode → byte-for-byte equality test

17. 在 reverse engineering 結果穩定之前，
    不要優先做 GUI automation 或 PLC 寫入。
```

---

# 24. Codex 開始工作時的要求

不要立刻大量寫程式。

先：

```text
分析現有專案
   ↓
分析 samples
   ↓
驗證我們之前的 hypothesis
   ↓
整理格式 spec
   ↓
建立 tests
   ↓
再實作 parser / encoder
```

每得到一個新的 reverse engineering 結論，都要回答：

```text
Evidence 是什麼？
哪些 sample 支持？
是否有 counterexample？
confidence 是什麼？
有沒有 automated test？
```

---

# 25. MCP 最終方向

完成 Parser / Encoder / IR 後，再建立 MCP Server。

例如：

```text
@mcp.tool()
read_ldr(path)

@mcp.tool()
inspect_ldr(path)

@mcp.tool()
create_ldr(output_path, ladder)

@mcp.tool()
validate_ladder(ladder)
```

未來再擴充：

```text
modify_network()
add_network()
delete_network()
import_to_winproladder()
syntax_check()
read_plc_status()
monitor_device()
```

---

# 26. Skill 最終方向

這個 MCP 可以另外附一個 companion Skill。

例如：

```text
skills/
└─ winproladder/
   ├─ SKILL.md
   └─ references/
      ├─ fatek-devices.md
      ├─ ladder-design.md
      └─ examples.md
```

Skill 負責：

```text
FATEK PLC device 基礎知識
Ladder 設計規則
互鎖
自保持
Timer
Counter
如何正確使用 WinProLadder MCP
```

概念上：

```text
Skill = 教 AI 怎麼做
MCP   = 給 AI 真正可呼叫的工具
```

兩者可以放在同一個 repository，但不要把兩者混成同一層。

---

# 27. 最終願景

希望使用者最後可以直接說：

```text
幫我做一個馬達正反轉控制。

X0 正轉
X1 反轉
X2 停止

Y0 正轉
Y1 反轉

需要：
自保持
正反轉互鎖
```

AI：

```text
理解需求
 ↓
設計 Ladder
 ↓
產生 Ladder IR
 ↓
呼叫 WinProLadder MCP
 ↓
create_ldr()
 ↓
motor.ldr
```

然後：

```text
WinProLadder
 ↓
Import Ladder Diagram
 ↓
看到 AI 生成的梯形圖
```

未來才繼續延伸：

```text
AI
 ↓
WinProLadder MCP
 ↓
Syntax Check
 ↓
PLC Online Monitor
 ↓
Debug
```

---

# 28. 給 Codex 的第一段指令

開啟專案後，請依照下面指令開始：

```text
請接手目前的 WinProLadder MCP 專案。

先完整閱讀專案根目錄的 PROJECT_BRIEF.md，並檢查 samples/ 內所有 .ldr 樣本與對應截圖。

這個專案目前最重要的核心目標，是逆向 WinProLadder 的 .ldr binary 格式，建立可靠的 Parser、Ladder IR 與 Encoder，最後再包成 MCP Server。

PROJECT_BRIEF.md 中記錄了一些先前根據樣本得到的 binary hypothesis，但不要直接相信這些推論。請先使用實際 .ldr 樣本重新做 byte-by-byte differential analysis 並用程式驗證。

原始 samples 不得修改。

你的第一階段工作：

1. 掃描並分析所有 .ldr。
2. 建立 hexdump / binary diff 工具。
3. 驗證 Header、Network Record、record length、payload length、Network 順序、CRC、opcode 等假設。
4. 建立 docs/ldr-format.md。
5. 對每項規則標示 CONFIRMED / HIGH CONFIDENCE / HYPOTHESIS / UNKNOWN。
6. 實作最小 Parser。
7. 實作最小 Encoder。
8. 建立 parse → encode → byte-for-byte equality tests。
9. Parser 必須盡量保留 UNKNOWN raw data。
10. Encoder 不得猜測尚未確認的 opcode。
11. 暫時不要操作實體 PLC。
12. 暫時不要優先開發 GUI automation。
13. 每完成一項 reverse engineering 結論，都必須有實際 sample evidence 與 automated test 支持。

請先分析現有專案與 samples，向我報告：
- 已確認的 .ldr 結構
- 還不確定的欄位
- 現有 hypothesis 驗證結果
- 建議再建立哪些最小 WinProLadder sample
- Parser / Encoder / IR 的實作計畫

完成這份報告後，再開始大規模實作。
```
