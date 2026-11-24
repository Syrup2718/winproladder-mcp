# 公開發布與私人資料隔離

[文件索引](README.md) · [開發指南](development.md) · [發布流程](project/RELEASING.md)

公開版本只能從獨立的 public checkout 發布。私人研究 repository 用於保存研究證據與開發，
必須維持 GitHub fetch-only；原生匯出、GUI 截圖、手冊、反編譯資料、研究腳本與客戶檔案
不得進入 public checkout。

## 目前本機角色

| 角色 | 用途 | GitHub push |
| --- | --- | --- |
| 私人開發 Repo | Production 開發與私有證據整合 | 必須由 push URL 與 `pre-push` hook 雙重封鎖 |
| 隔離公開 Repo | 只包含經審核的 Production、合成測試與公開文件 | 只有發布閘門成功及人工複核後允許普通 push |
| 私人封存 | 原始歷史 bundle、原生樣本、截圖與研究資料 | 不是 Git repository，也不得作為發布來源 |

不要用舊 public checkout 的名稱判斷它是否可發布。以 `git rev-parse HEAD` 對照 GitHub
`refs/heads/main`，並確認本機設定 `release.publicWorktree=true`；兩項都符合才是目前的公開同步
基線。

## 安全同步流程

1. 在私人 Repo 完成 Production 修改與完整驗證；私有資料留在 repository 外的封存。
2. 在隔離公開 Repo 從 GitHub `main` 建立更新基線，不 merge 私人 Git 歷史，也不複製 `.git`。
3. 只移植人工審核的 Production 原始碼、合成測試、必要設定與公開文件。不得使用
   `git add -A` 取代 staged-files 複核。
4. 檢查 `git diff --cached --name-status`、`git diff --cached` 與 `git status --short`。
5. 在 public checkout 執行 `pwsh -File scripts/check_public_release.ps1`。閘門必須在乾淨
   工作樹通過；`-AllowDirty` 只供開發閘門本身，不能作為發布結果。
6. 只有人工確認 staged tree、閘門與 GitHub refs 未變後，才從 public checkout 以普通
   `git push origin HEAD:refs/heads/main` 發布。不得從私人 Repo push，不得使用 `--mirror`，
   也不得使用未帶 lease 的 force push。

## 閘門檢查

`scripts/check_public_release.ps1` 會確認：

- 受限制的二進位格式預設不得出現在候選檔案或歷史中；唯一例外是以路徑、
  SHA-256 與 Git object ID 三重固定的公開 `assets/banner.png`。任何內容變更都會使
  發布閘門失敗，必須重新人工審核。

- checkout 已標記為隔離公開工作樹且預設為乾淨；
- tracked files 與所有可達歷史不含受限制路徑或副檔名；
- HEAD 內容沒有常見 token、private key 或個人絕對路徑；
- Ruff format/lint、strict mypy、pytest、coverage、24 個 MCP tools、Common FUN、
  LDR 生成／回讀及 workspace audit 全部通過。

本機 hook 不是安全邊界的唯一來源；複製 repository、使用 `--no-verify` 或直接指定 URL 都可能
繞過 hook，因此私人 Repo 的 push URL 也必須保持不可用。每次發布前均重新執行閘門與人工
staged-tree 複核。

## GitHub 殘留資料

一般 push 無法修改 GitHub 管理的 `refs/pull/*`，也無法立即清除舊頁面快取或不可達 objects。
若舊 PR 曾含私人資料，應使用既有清理記錄中的 repository、PR 編號、舊／新 SHA、受影響路徑、
First Changed Commit 與清理日期向 GitHub Support 申請 purge。不得直接修改 PR refs，也不得
把含私人資料的舊歷史推回作為一般回復方式。
