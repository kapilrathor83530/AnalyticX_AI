param(
    [Parameter(Mandatory = $true)]
    [string]$Source,
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$lines = [System.IO.File]::ReadAllLines((Resolve-Path $Source))
$languages = @(
    'python', 'tsx', 'ts', 'js', 'json', 'css', 'yaml', 'yml', 'markdown', 'md',
    'text', 'ini', 'dockerfile', 'nginx', 'powershell', 'bash', 'txt', 'html',
    'sql', 'env', 'gitignore'
)

function Test-PathHeading([string]$Line) {
    $trimmed = $Line.Trim()
    return $trimmed -match '^(backend|frontend|docs|scripts|training|sample_data)(/|\\).+' -or
        $trimmed -match '^(docker-compose\.yml|README\.md|\.env\.example|\.gitignore)$'
}

function Get-CleanPath([string]$Heading) {
    return (($Heading.Trim() -replace '\s+(\(|—).*$','').Trim() -replace '/', '\\')
}

function Test-StopLine([string]$Line, [string]$Language) {
    $trimmed = $Line.Trim()
    if (Test-PathHeading $trimmed) { return $true }
    if ($Language -notin @('markdown', 'md') -and $trimmed -match '^\d+\.\s') { return $true }
    return $trimmed -match '^(Analyticx AI —|The user wants|I did not run|Note: Code|This part|This is the complete|If your|If you already|Run Docker|Run Everything|Known Limitations|Exact Next|Expected new|Reply CONTINUE|Tests were|Backend$|Frontend$|Tests$|Add to |Add the |Add a |Change every|Change the |Edit backend|Install )'
}

$entries = @()
for ($index = 0; $index -lt $lines.Length - 1; $index++) {
    $heading = $lines[$index].Trim()
    if (-not (Test-PathHeading $heading)) { continue }
    $language = $lines[$index + 1].Trim().ToLowerInvariant()
    if ($language -notin $languages) { continue }
    $entries += [PSCustomObject]@{
        Index = $index
        Heading = $heading
        RelativePath = Get-CleanPath $heading
        Language = $language
        IsAppend = $heading -match '\bappend\b'
        IsPartial = $heading -match '(add dev dependencies|add Workspace link|add navigation buttons)'
    }
}

$written = 0
$appended = 0
$skipped = 0
for ($entryIndex = 0; $entryIndex -lt $entries.Count; $entryIndex++) {
    $entry = $entries[$entryIndex]
    $nextIndex = if ($entryIndex + 1 -lt $entries.Count) { $entries[$entryIndex + 1].Index } else { $lines.Length }
    $body = New-Object System.Collections.Generic.List[string]
    for ($lineIndex = $entry.Index + 2; $lineIndex -lt $nextIndex; $lineIndex++) {
        if ($body.Count -gt 0 -and (Test-StopLine $lines[$lineIndex] $entry.Language)) { break }
        $body.Add($lines[$lineIndex])
    }
    while ($body.Count -gt 0 -and [string]::IsNullOrWhiteSpace($body[$body.Count - 1])) {
        $body.RemoveAt($body.Count - 1)
    }

    if ($entry.IsPartial -or $body.Count -eq 0) {
        $skipped++
        continue
    }

    $target = Join-Path $root $entry.RelativePath
    $content = ($body -join [Environment]::NewLine) + [Environment]::NewLine
    $action = if ($entry.IsAppend) { 'append' } else { 'write' }
    Write-Host ("{0,-6} {1} ({2} lines)" -f $action, $entry.RelativePath, $body.Count)
    if (-not $Apply) { continue }

    $parent = Split-Path -Parent $target
    [System.IO.Directory]::CreateDirectory($parent) | Out-Null
    if ($entry.IsAppend) {
        [System.IO.File]::AppendAllText($target, [Environment]::NewLine + $content)
        $appended++
    } else {
        [System.IO.File]::WriteAllText($target, $content)
        $written++
    }
}

Write-Host "Summary: $written written, $appended appended, $skipped skipped."
