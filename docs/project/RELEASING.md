# v1.1.0 合併與發布

目前準備的是 v1.1.0 原始碼版本，PDW 標為實驗功能。這份流程不建立 wheel、sdist 或安裝包。
發布內容可直接採用 [CHANGELOG](CHANGELOG.md) 的 1.1.0 條目。

## 1. 在功能分支確認並提交

以下命令可在專案目錄的 Git Bash 執行。先確認分支為 `feature/generate-pdw`：

```bash
git branch --show-current
git status --short
git diff
```

版本資訊、鎖定檔、文件與能力回報已同步整理。私人 `.pdw` 範本不應加入 Git。
以下命令應沒有輸出；若列出檔案，先處理私人資料，再繼續：

```bash
git ls-files '*.pdw'
```

中英文 CHANGELOG 已按本次準備日期 2026-11-05 填寫；若改天才發布，再同步調整日期。
檢查完成後提交：

```bash
git add pyproject.toml uv.lock README.md src/winproladder_mcp/__init__.py src/winproladder_mcp/capabilities.py docs
git diff --cached --stat
git diff --cached
git commit -m "chore: prepare v1.1.0 release"
git push -u origin feature/generate-pdw
```

## 2. 完成檢查

```bash
uv sync --locked --python 3.12
uv run ruff check .
uv run mypy src
uv run pytest -q
```

`uv sync` 會準備開發環境，不會建立可散發的發布包。也要確認 GitHub 上該提交的
Cross-platform checks 在 Windows、macOS、Linux 全數通過，才合併。
測試包括 MCP 子程序傳輸及離線驗證，不代表每份 PDW 已完成 GUI 或實體 PLC 驗證。

## 3. 合併至 main

選擇下列一種方式即可。

### GitHub Pull Request

在 GitHub 以 `main` 為 base、`feature/generate-pdw` 為 compare 建立 PR。
標題可用 `Release v1.1.0: experimental PDW generation`，內容參考 CHANGELOG。
檢查通過後合併，再同步本機：

```bash
git switch main
git pull --ff-only origin main
```

### 本機合併

若 main 有分支保護，請使用 PR 方式。

```bash
git switch main
git pull --ff-only origin main
git merge --no-ff feature/generate-pdw -m "Merge feature/generate-pdw for v1.1.0"
```

若有衝突，先解決衝突並重新檢查，完成 merge commit；不要直接繼續發布。
合併後重跑第 2 節的檢查，通過再推送：

```bash
git push origin main
```

## 4. 建立版本標籤與 GitHub Release

確認 main 的工作目錄乾淨、版本為 1.1.0，且合併後提交的 GitHub 檢查通過。
標籤應指向已驗證的 main 提交；若同名標籤已存在，先確認其用途，不覆寫。

```bash
git status --short
git log -1 --oneline
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
```

在 GitHub 的 Releases 選擇建立發布，選用既有 `v1.1.0` 標籤，
標題填 `v1.1.0`，貼上 CHANGELOG 的版本內容並發布。
整體版本可以是正式 v1.1.0，同時明確標示 PDW 子功能為實驗性。
GitHub 提供的原始碼下載不包含私人範本；本流程沒有額外安裝包可上傳。

發布後，再開新分支繼續開發；舊的功能分支可等確認 main 內容完整後再清理。
