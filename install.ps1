param([string]$Workspace = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$installDir = Join-Path $PSScriptRoot '.install'
New-Item -ItemType Directory -Force -Path $installDir | Out-Null
$previousEnvironment = $env:UV_PROJECT_ENVIRONMENT
$previousUnmanaged = $env:UV_UNMANAGED_INSTALL
try {
    $uvCommand = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $localUv = Join-Path $installDir 'uv/uv.exe'
    if ($uvCommand) { $uv = $uvCommand.Source }
    elseif (Test-Path -LiteralPath $localUv) { $uv = $localUv }
    else {
        Write-Host 'Installing uv locally (no administrator rights required)...'
        $installer = Join-Path $installDir 'uv-installer.ps1'
        Invoke-WebRequest -UseBasicParsing 'https://astral.sh/uv/install.ps1' -OutFile $installer
        $env:UV_UNMANAGED_INSTALL = Join-Path $installDir 'uv'
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installer
        if ($LASTEXITCODE -ne 0) { throw 'uv installation failed. Check your network and retry.' }
        $uv = $localUv
    }
    $env:UV_PROJECT_ENVIRONMENT = Join-Path $installDir 'venv'
    & $uv sync --project $PSScriptRoot --locked --no-dev --python 3.12
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check your network and retry.' }
    $python = Join-Path $env:UV_PROJECT_ENVIRONMENT 'Scripts/python.exe'
    & $python -m winproladder_mcp.setup check
    if ($LASTEXITCODE -ne 0) { throw 'MCP self-check failed; setup is incomplete.' }
    & $python -m winproladder_mcp.setup prepare --root $Workspace --config-dir $installDir
    if ($LASTEXITCODE -ne 0) { throw 'Client configuration failed; setup is incomplete.' }
} finally {
    $env:UV_PROJECT_ENVIRONMENT = $previousEnvironment
    $env:UV_UNMANAGED_INSTALL = $previousUnmanaged
}
