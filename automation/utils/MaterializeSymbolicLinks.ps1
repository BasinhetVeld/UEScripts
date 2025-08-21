param(
  [string]$StartPath = ".",
  [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Resolve-Target {
  param([string]$Path)

  try {
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.PSObject.Properties.Name -contains "Target" -and $item.Target) {
      return $item.Target
    }
  } catch { }

  # Fallback: fsutil for junctions/symlinks
  $out = (cmd /c "fsutil reparsepoint query ""$Path""" 2>$null)
  if ($LASTEXITCODE -eq 0) {
    foreach ($line in $out) {
      if ($line -match 'Substitute Name:\s*(.+)$') {
        return $Matches[1]
      }
    }
  }
  return $null
}

function Normalize-Target {
  param([string]$Target)
  if (-not $Target) { return $null }
  # Strip Win32 NT prefix if present, e.g. "\??\C:\path..."
  if ($Target.Length -ge 4 -and $Target.Substring(0,4) -eq "\??\") {
    return $Target.Substring(4)
  }
  return $Target
}

Write-Host ("Scanning for reparse points under: {0}" -f $StartPath)

# Collect all reparse points (dirs and files)
$links = Get-ChildItem -LiteralPath $StartPath -Recurse -Force -Attributes ReparsePoint

foreach ($l in $links) {
  $item = Get-Item -LiteralPath $l.FullName -Force
  $targetRaw = Resolve-Target -Path $l.FullName
  $target = Normalize-Target $targetRaw

  if (-not $target -or -not (Test-Path -LiteralPath $target)) {
    $t = $target
    if (-not $t) { $t = "<null>" }
    Write-Warning ("Skipping {0} -- target missing or unresolvable: {1}" -f $l.FullName, $t)
    continue
  }

  if ($item.PSIsContainer) {
    # Directory link (junction/symlink dir)
    Write-Host ("Materializing DIR  {0} --> {1}" -f $l.FullName, $target)
    if ($WhatIf) { continue }

    # Remove the link; then copy the real directory into its place
    Remove-Item -LiteralPath $l.FullName -Recurse -Force -Confirm:$false
    Copy-Item -LiteralPath $target -Destination $l.FullName -Recurse -Force
  }
  else {
    # File link (mostly node_modules\.bin)
    Write-Host ("Materializing FILE {0} --> {1}" -f $l.FullName, $target)
    if ($WhatIf) { continue }

    $destDir = Split-Path -LiteralPath $l.FullName -Parent
    if (-not (Test-Path -LiteralPath $destDir)) {
      New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
    Remove-Item -LiteralPath $l.FullName -Force -Confirm:$false
    Copy-Item -LiteralPath $target -Destination $l.FullName -Force
  }
}

Write-Host "Done."
