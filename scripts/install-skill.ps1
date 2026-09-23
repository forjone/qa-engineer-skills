[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('ClaudeCode', 'Cursor', 'Qoder', 'Custom')]
    [string]$Agent,

    [ValidateSet('Project', 'User')]
    [string]$Scope = 'Project',

    [string]$Target
)

$source = (Resolve-Path (Join-Path $PSScriptRoot '..\plugins\test-case-design\skills\test-case-design')).Path

if (-not $Target) {
    $root = switch ($Agent) {
        'ClaudeCode' {
            if ($Scope -eq 'User') { Join-Path $HOME '.claude\skills' } else { Join-Path (Get-Location) '.claude\skills' }
        }
        'Cursor' {
            if ($Scope -eq 'User') { Join-Path $HOME '.cursor\skills' } else { Join-Path (Get-Location) '.cursor\skills' }
        }
        default {
            throw "Specify -Target for $Agent because its skill directory is not standardized by this repository."
        }
    }
} else {
    $root = $Target
}

$destination = Join-Path $root 'test-case-design'
if (Test-Path -LiteralPath $destination) {
    throw "Destination already exists: $destination"
}

New-Item -ItemType Directory -Force -Path $root | Out-Null
Copy-Item -LiteralPath $source -Destination $root -Recurse -ErrorAction Stop
Write-Output "Installed test-case-design for $Agent at $destination"
