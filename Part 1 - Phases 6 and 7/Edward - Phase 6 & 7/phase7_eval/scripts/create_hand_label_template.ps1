param(
    [Parameter(Mandatory = $true)]
    [string]$Source,

    [Parameter(Mandatory = $true)]
    [string]$Output
)

$requiredColumns = @('Query', 'Persona', 'Intent', 'Complexity', 'Entities', 'Route', 'Notes')

if (-not (Test-Path -LiteralPath $Source)) {
    throw "Source CSV not found: $Source"
}

$rows = Import-Csv -LiteralPath $Source
if (-not $rows) {
    throw 'Source CSV contains no data rows.'
}

$availableColumns = @($rows[0].PSObject.Properties.Name)
$missingColumns = $requiredColumns | Where-Object { $_ -notin $availableColumns }
if ($missingColumns.Count -gt 0) {
    throw "Source CSV is missing required columns: $($missingColumns -join ', ')"
}

$outputDirectory = Split-Path -Parent $Output
if ($outputDirectory) {
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
}

$counter = 0
$outputRows = foreach ($row in $rows) {
    $counter += 1
    [pscustomobject]@{
        row_id              = $counter
        query               = ($row.Query | Out-String).Trim()
        persona             = ($row.Persona | Out-String).Trim()
        seed_intent         = ($row.Intent | Out-String).Trim()
        seed_complexity     = ($row.Complexity | Out-String).Trim()
        seed_entities       = ($row.Entities | Out-String).Trim()
        seed_route          = ($row.Route | Out-String).Trim()
        seed_notes          = ($row.Notes | Out-String).Trim()
        gold_route          = ''
        gold_short_circuit  = ''
        label_status        = 'todo'
        reviewer_notes      = ''
    }
}

$outputRows | Export-Csv -LiteralPath $Output -NoTypeInformation -Encoding utf8
Write-Host "Wrote $($outputRows.Count) rows to $Output"