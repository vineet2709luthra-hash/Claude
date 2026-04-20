# Claude Code Installer for Windows
# Usage: irm https://claude.ai/install.ps1 | iex

$ErrorActionPreference = 'Stop'

function Write-Status($msg) { Write-Host $msg -ForegroundColor Cyan }
function Write-Success($msg) { Write-Host $msg -ForegroundColor Green }
function Write-Fail($msg) { Write-Host $msg -ForegroundColor Red }

Write-Status "Installing Claude Code..."

# Check for Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Fail "Node.js is required but not found."
    Write-Host "Download and install Node.js from https://nodejs.org (v18 or later), then re-run this script."
    exit 1
}

$nodeVersion = node --version
$nodeMajor = [int]($nodeVersion -replace 'v(\d+)\..*', '$1')
if ($nodeMajor -lt 18) {
    Write-Fail "Node.js v18 or later is required (found $nodeVersion)."
    Write-Host "Update Node.js at https://nodejs.org, then re-run this script."
    exit 1
}

# Check for npm
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Fail "npm is required but not found. Reinstall Node.js from https://nodejs.org."
    exit 1
}

# Install Claude Code
Write-Status "Running: npm install -g @anthropic-ai/claude-code"
try {
    npm install -g @anthropic-ai/claude-code
} catch {
    Write-Fail "Installation failed: $_"
    exit 1
}

# Verify installation
if (Get-Command claude -ErrorAction SilentlyContinue) {
    $claudeVersion = claude --version
    Write-Success "Claude Code $claudeVersion installed successfully!"
    Write-Host ""
    Write-Host "Get started: claude"
    Write-Host "Documentation: https://docs.anthropic.com/en/docs/claude-code"
} else {
    Write-Fail "Installation may have succeeded but 'claude' was not found in PATH."
    Write-Host "Try restarting your terminal, then run: claude"
}
