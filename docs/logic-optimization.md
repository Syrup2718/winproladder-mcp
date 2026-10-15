# 邏輯與接圖簡化

[文件索引](README.md) · [功能清單](../FEATURES.md)

所有生成工具與新增／替換網路共用最佳化流程：

1. 去除重複條件、常數無作用項，套用互補律與吸收律。
2. 提取共同條件，不做可能指數膨脹的完整 DNF 展開。
3. 複合支路置頂、並聯區塊前移，減少 LD 合併與輔助 M。
4. 底層相容模式可將剩餘複雜支路展開為 M 網路；本儲存庫政策禁止自動 relay helpers，因此需要此展開的需求會被拒絕，不能藉最佳化繞過。禁止輸出巢狀合併指令 E200/E443。
5. FALSE 以完整接線的互斥接點表示，避免 Boolean OPEN 常數；保留 Counter CLR 的特殊極性編碼。

例如 `X0 AND (X1 OR X2)` 改為 `(X1 OR X2) AND X0`，不需輔助 M。排列規則參考 FB-PLC 基礎功能篇 CH01 §1.7；簡碼規則不等於 `.ldr` 二進位格式規格。

最佳化只作用於同一純布林條件，不重排原始網路、輸出或功能方塊，也不跨網路快取狀態。原始 read/export 維持無損，不靜默修復檔案。

## 預覽與資源

`validate_ladder` 不寫檔，回傳 `optimized_ladder` 及 `layout`。生成工具亦回傳 layout：

- `metrics`：前後網路數、接點出現次數、payload bytes。
- `helper_devices`：新增且必須保留的 M。
- `network_map`：有修改的原始網路對應生成範圍。
- `simplified_networks`：套用布林簡化的網路。

輔助 M 僅避開本次輸入程式的已用位址；合併工程前需重新核對。資源不足或超過網路上限時拒絕生成。

迴歸測試涵蓋隨機邏輯樹完整真值表、所有控制配方、16 步流程及交通燈完整時序。驗證基準見 [verification.md](verification.md)。
