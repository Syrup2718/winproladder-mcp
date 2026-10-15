# test28：脈波、速度與字串

[文件索引](README.md) · [功能清單](../FEATURES.md)

來源：[test28.ldr](../samples/test28.ldr)、[畫面](../samples/screenshots/test28.png)、[IR](../examples/test28_functions.json)。原檔470 bytes、8網路，FBs-40MA檔頭。

## 支援範圍

| FUNC | action | 狀態 |
| --- | --- | --- |
| 81 PLSO | `pulse_output` | MD0非D；frequency=Fr、pulse_count=PC、forward_output=UY、reverse_output=DY、destination=HO；三路控制、三路狀態 |
| 82 PWM | `pwm` | on_ms=To、period_ms=Tp、physical_output=OT；常數時間、EN／ERR |
| 83 SPD | `speed_detect` | physical_input=S、sample_ms=TI、destination=D；EN／OVF |
| 84 TDSP | `text_display` | MD1原樣解析；Ns／Nl動態跨度未確認，不能生成 |
| 60 →ASC | `ascii_literal` | 擴充1～12個ASCII英數字／空白，R/D目的及EN |
| 65／66／67 | `lbl`／`jmp`／`call` | 新增標籤8的記錄辨識；JMP改程式及CALL生成仍未支援 |

PLSO的Fr／PC／HO目前使用可寫R/D區；Fr與PC是暫存器內容，不是位址數字。其他bank、常數與D／P形式未加入。

## 手冊核對

《進階篇應用指令.pdf》：

- **7-74～75**：PLSO只可使用一次；Fr為8～2000Hz，非D的PC為0～32767，0代表連續輸出。EN上升沿重置，方向在此時擷取；PAU保留進度。UY／DY需主機電晶體輸出，實際CPU容量未驗證。
- **7-76**：PWM以ms計時，To須≤Tp；只可使用一次，OT限Y0～15。Tp標題寫32676，運算元表寫32767；編碼採表格1～32767，上界仍須對照目標版本。
- **7-77**：SPD用X0～7，TI為1～32767ms；D佔連續3個word。輸入頻率總和須小於5kHz；無硬體執行模擬。
- **7-78**：TDSP只列MD0～1，未列畫面中的Nd；來源、起始及長度皆為暫存器。本次保留完整記錄，引用分析標示不完整，生成明確拒絕。
- **7-51**：ASC每2字元佔1word，第一字元在低byte。奇數長度的末word保留情況未明，讀取引用採保守計算。
- **7-59～61**：LBL／JMP／CALL語意已知，但目標記錄的部分欄位仍未知；不能把樣本辨識當成通用流程控制。

## 新證據

ASC固定14-byte字串區塊：前2 bytes保存6組第一字元的最低bit；後12 bytes中，每組第一字元右移1bit，第二字元保持原值。空位補零。

- ABCDEF：`0007204221442246000000000000`
- SYRUP IS CAT：`0029295929552820245310432054`

兩份原始匯出支持此規則；其他英數字／空白仍是推導變體，未經GUI確認。標點、Unicode、P及ERR腳位未開放。

LBL8為`ef38000000000000`。JMP8與CALL8均帶`a7fe1c0000000000`；舊CALL1則帶`672e188000000000`。目前不能證明前段欄位的作用，因此不任意複製到新流程。

## 產檔與驗證

原樣本PWM的To=4096、Tp=100會依手冊觸發ERR；另外含未支援生成的CALL／TDSP，因此完整樣本不直接產檔。

本機 `artifacts/test28_supported_functions.ldr` 保留原N000、N001、N004、N007（PLSO、LBL8、SPD、ASC），沒有改位址或參數。370 bytes，SHA-256：`9c08c9ed9ccc1eba6b1ca3287cac7ef4db74c599f6786eddedfb5a581eb0097e`。

全套 **1416項測試通過**，Ruff與38個來源檔mypy通過。實際stdio MCP生成、兩種下載與CRC通過；四個payload與原樣本相同。新增指令無執行模擬，未經GUI匯入或實體PLC驗證。原始8個網路皆可解碼並逐byte重建。
