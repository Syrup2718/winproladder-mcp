# MCP 設定與電路範例

- `start-stop.json`：可作為 create_ldr 的 ladder 參數。
- `timer-observed.json`：已觀測 T1／256，EN 接母線、TUP 未接輸出。
- `counter-observed.json`：已觀測 C1／10，PLS/CLR 均接母線、CUP 未接輸出。
  這是重現來源樣本，不是推薦的 Counter 控制設計。兩個 block 範例均需 `allow_unverified=true`。
- `uv run winproladder-setup config --format codex`：產生本機 Codex TOML 區段。
- `uv run winproladder-setup config --format json`：產生通用 stdio MCP client JSON。

設定使用當前 Python 的完整路徑與工作目錄，不在 Git 裡固定使用某人的目錄。
輸出只列印，不會覆蓋 client 現有設定。請合併 server 區段並重新載入 client。
