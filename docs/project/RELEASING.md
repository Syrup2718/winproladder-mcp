# v1.1.1 合併與發布

目前準備的是 v1.1.1 原始碼版本，PDW 仍標為實驗功能。這份流程不建立 wheel、sdist
或安裝程式；GitHub Release 只使用 GitHub 依標籤產生的原始碼封存。
發布說明可直接採用 [CHANGELOG](CHANGELOG.md) 的 1.1.1 條目。

## 1. 確認發布提交

在專案根目錄確認目前分支、變更內容與私人檔案：

  ```bash
  git branch --show-current
git status --short
git diff --check
git diff
git ls-files '*.pdw'
```

`git ls-files '*.pdw'` 應沒有輸出；私人 PDW 範本、產物與驗證資料不得加入 Git。
版本資訊必須在 `pyproject.toml`、`src/winproladder_mcp/__init__.py` 與 `uv.lock`
一致為 `1.1.1`。中英文 CHANGELOG 的日期目前是 2026-11-10；若實際發布日不同，
標記前同步調整。

提交前檢查暫存內容：

```bash
git add pyproject.toml uv.lock README.md src/winproladder_mcp/__init__.py tests/test_release.py docs
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "chore: prepare v1.1.1 release"
```

## 2. 完成發布檢查

```bash
uv sync --locked --python 3.12
uv run ruff check .
uv run mypy src
uv run pytest -q
uv run python scripts/verify_release.py --root .
```

`uv sync` 只準備鎖定的開發環境，不建立可散發套件。`verify_release.py` 會在
`artifacts/release-*` 建立新的離線證據目錄；檢查 manifest 為 `passed` 後，保留所需證據，
但不要將產物加入 Git。測試涵蓋 MCP 子程序傳輸、解碼輸出與離線行為模型，不等於每份
LDR／PDW 都已由 WinProLadder GUI 匯入，更不等於實體 PLC 驗證。

也要確認 GitHub 上同一提交的跨平台檢查在 Windows、macOS、Linux 全數通過。

## 3. 合併至 main

若發布準備位於分支，建立以 `main` 為 base 的 Pull Request，標題可用
`Release v1.1.1`，內容採用 CHANGELOG。檢查通過後合併並同步本機：

```bash
git switch main
git pull --ff-only origin main
```

若直接在 `main` 準備，確認提交已推送且遠端檢查通過。不要在有未提交變更或失敗檢查時
建立標籤。

## 4. 建立版本標籤與 GitHub Release

標籤必須指向已驗證的 `main` 提交。若同名標籤已存在，先確認其用途，不要覆寫或移動：

```bash
git status --short
git log -1 --oneline
git tag --list v1.1.1
git tag -a v1.1.1 -m "Release v1.1.1"
git push origin v1.1.1
```

在 GitHub Releases 選用既有 `v1.1.1` 標籤，標題填 `v1.1.1`，貼上 CHANGELOG 的
1.1.1 內容並發布。整體版本是正式 v1.1.1，但 PDW 子功能仍須明確標示為實驗性。
私人範本不在 repository 或 GitHub 原始碼封存內，本流程也沒有額外安裝包可上傳。
