[CmdletBinding()]
param(
    [switch]$AllowDirty
)

$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    $output = & git @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed:`n$output"
    }
    return $output
}

$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $root

$gitRoot = (Invoke-Git rev-parse --show-toplevel | Select-Object -First 1).Trim()
if ((Resolve-Path -LiteralPath $gitRoot).Path -ne $root) {
    throw "The release gate must live under the root of its public Git worktree."
}

$publicWorktree = & git config --bool --get release.publicWorktree 2>$null
if (($LASTEXITCODE -notin 0, 1) -or $publicWorktree -ne "true") {
    throw "This checkout is not marked as an isolated public release worktree."
}

$status = @(Invoke-Git status --porcelain=v1)
if ($status.Count -gt 0 -and -not $AllowDirty) {
    throw "The public release worktree is dirty. Commit or intentionally remove its changes first."
}
if ($AllowDirty) {
    Write-Warning "Dirty-worktree override is for gate development only; do not publish this run."
}

$restrictedPath = '(?i)(^|/)(docs/research|samples|research|ghidra|ida)(/|$)|\.(ldr|exe|dll|pdf|png|jpe?g|ghidra)$'
$candidate = @(Invoke-Git ls-files --cached --others --exclude-standard)
$candidateFiles = @($candidate | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })
$badCandidate = @($candidateFiles | Where-Object { $_ -match $restrictedPath })
if ($badCandidate.Count -gt 0) {
    throw "Restricted candidate paths found:`n$($badCandidate -join "`n")"
}

$objects = @(Invoke-Git rev-list --objects --all)
$badHistory = @($objects | Where-Object { $_ -match $restrictedPath })
if ($badHistory.Count -gt 0) {
    throw "Restricted paths remain in reachable history:`n$($badHistory -join "`n")"
}

$sensitivePattern = 'C:\\Users\\|C:/Users/|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|AKIA[0-9A-Z]{16}'
$contentHits = @(& git grep --no-index -I -n -E $sensitivePattern -- @candidateFiles 2>$null)
if ($LASTEXITCODE -notin 0, 1) {
    throw "Public content scan failed."
}
$unexpectedHits = @(
    $contentHits | Where-Object {
        $_ -notmatch '^(tests/test_validate_script\.py|scripts/check_public_release\.ps1):'
    }
)
if ($unexpectedHits.Count -gt 0) {
    throw "Potential sensitive content found:`n$($unexpectedHits -join "`n")"
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    & uv run python scripts/validate.py --full
} elseif (Test-Path -LiteralPath ".venv/Scripts/python.exe") {
    & .venv/Scripts/python.exe scripts/validate.py --full
} else {
    & python scripts/validate.py --full
}
if ($LASTEXITCODE -ne 0) {
    throw "Full validation failed."
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    $commonCount = & uv run python -c "from winproladder_mcp.common_functions import COMMON_FUN_EVIDENCE; print(len(COMMON_FUN_EVIDENCE))"
} elseif (Test-Path -LiteralPath ".venv/Scripts/python.exe") {
    $commonCount = & .venv/Scripts/python.exe -c "from winproladder_mcp.common_functions import COMMON_FUN_EVIDENCE; print(len(COMMON_FUN_EVIDENCE))"
} else {
    $commonCount = & python -c "from winproladder_mcp.common_functions import COMMON_FUN_EVIDENCE; print(len(COMMON_FUN_EVIDENCE))"
}
if ($LASTEXITCODE -ne 0 -or $commonCount -ne "131") {
    throw "Expected 131 Common FUN evidence keys; got '$commonCount'."
}
Write-Output "131 Common FUN evidence keys; MCP self-check confirmed 24 tools."

if ($AllowDirty) {
    Write-Output "DEVELOPMENT GATE PASSED; NOT READY TO PUBLISH WHILE DIRTY."
} else {
    Write-Output "PUBLIC RELEASE GATE PASSED."
    Write-Output "After human review, publish only from this checkout with:"
    Write-Output "  git push origin HEAD:refs/heads/main"
}
