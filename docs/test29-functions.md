# test29：ASCII 與數字標籤

[文件索引](README.md) · [功能清單](../FEATURES.md)

來源：[test29.ldr](../samples/test29.ldr)、[畫面](../samples/screenshots/test29.png)、[IR](../examples/test29_functions.json)。438 bytes、8網路，新增精確檔頭 `FBs-32MN-test29`。

## 更新

- ASC兩組12字元字串與既有打包規則一致：`1234567890GH` → R5555～R5560，`IJKLMNOUTWXZ` → D111～D116。
- LBL擴充單一數字 `0`～`9`；0～6、8有原始匯出，7／9由同一規則推導，尚未GUI確認。
- 多字元／英文字母標籤未實作。JMP／CALL未知欄位與生成限制不變。

LBL為 `EF`、一個ASCII數字、6個零。重複標籤會拒絕；多字元、Unicode及非數字不得誤套此格式。手冊7-59允許1～6英數字，那是PLC語意範圍，並不代表本次已實作所有名稱編碼。

## 驗證

1444項測試通過，Ruff及38個來源檔mypy通過。實際MCP產檔與兩種下載皆成功，438 bytes與原檔完全一致，CRC有效。

本機產物：`artifacts/test29_mcp_roundtrip.ldr`。SHA-256：`38f6d589d9244e9cd798d593ae7b24df40dd11272be89955382223c9d9425035`。

未新增執行模擬；未經GUI匯入或實體PLC驗證。未升版、未打包。
