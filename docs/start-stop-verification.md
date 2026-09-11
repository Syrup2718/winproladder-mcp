# 自保持匯入驗證紀錄

使用者在本對話回報 `artifacts/start_stop_candidate.ldr` 能夠順利匯入成功。
該檔 281 bytes，使用 samples 共用 256-byte header，單一 record：

```text
12 10 0D 00 08 00 41 00 A0 00 90 01 C1 00 01 00 00 48 50
```

尾端 `FF FF 00 00 00 00`。CRC 為 0x5048。
邏輯 `(Y0 OR X0) AND NOT X1 → Y0`，X1 採梯形圖 NC，輸入 1 時停止。

這份具體組合提升為「使用者回報匯入成功」。尚未收到 PLC runtime 測試結果，
也未據此將其他位址、其他組合、其他 header 或 X1-NO 變體標成匯入驗證通過。
MCP 的 `create_start_stop` 預設重建相同檔案 bytes。
