param(
    [Parameter(Mandatory = $true)]
    [string]$Labels,

    [Parameter(Mandatory = $true)]
    [string]$Output,

    [int]$Seed = 7
)

function Get-NormalizedValue {
    param([object]$Value)

    if ($null -eq $Value) {
        return ''
    }

    return ([string]$Value).Trim()
}

function Get-PreferredTextValue {
    param([object[]]$Candidates)

    foreach ($candidate in $Candidates) {
        $value = Get-NormalizedValue $candidate
        if ($value) {
            return $value
        }
    }

    return ''
}

function Resolve-GoldRoute {
    param([psobject]$Row)

    foreach ($key in @('gold_route', 'seed_route', 'Route')) {
        $value = Get-NormalizedValue $Row.$key
        if ($value) {
            return $value
        }
    }

    throw 'Could not resolve a route from the labels file.'
}

function Resolve-GoldShortCircuit {
    param([psobject]$Row, [string]$GoldRoute)

    $explicit = Get-NormalizedValue $Row.gold_short_circuit
    switch ($explicit.ToLowerInvariant()) {
        'true' { return $true }
        '1' { return $true }
        'yes' { return $true }
        'y' { return $true }
        'false' { return $false }
        '0' { return $false }
        'no' { return $false }
        'n' { return $false }
    }

    $complexity = Get-PreferredTextValue @($Row.seed_complexity, $Row.Complexity)
    if ($complexity) {
        return $complexity -eq 'short_circuit'
    }

    return $GoldRoute -eq 'short_circuit'
}

function Get-AccuracyForRow {
    param([psobject]$Row)

    $complexity = Get-PreferredTextValue @($Row.seed_complexity, $Row.Complexity)
    switch ($complexity) {
        'short_circuit' { return 0.96 }
        'medium' { return 0.90 }
        'complex' { return 0.82 }
        'llm_needed' { return 0.74 }
        default { return 0.88 }
    }
}

if (-not (Test-Path -LiteralPath $Labels)) {
    throw "Labels CSV not found: $Labels"
}

$rows = Import-Csv -LiteralPath $Labels
if (-not $rows) {
    throw 'Labels CSV contains no data rows.'
}

$routes = @($rows | ForEach-Object { Resolve-GoldRoute $_ } | Sort-Object -Unique)
$random = [System.Random]::new($Seed)

$outputDirectory = Split-Path -Parent $Output
if ($outputDirectory) {
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
}

$predictions = foreach ($row in $rows) {
    $goldRoute = Resolve-GoldRoute $row
    $goldShortCircuit = Resolve-GoldShortCircuit -Row $row -GoldRoute $goldRoute
    $useGold = $random.NextDouble() -lt (Get-AccuracyForRow $row)
    $alternativeRoutes = @($routes | Where-Object { $_ -ne $goldRoute })

    if ($useGold -or $alternativeRoutes.Count -eq 0) {
        $predictedRoute = $goldRoute
    }
    else {
        $predictedRoute = $alternativeRoutes[$random.Next(0, $alternativeRoutes.Count)]
    }

    if ($goldShortCircuit) {
        $predictedShortCircuit = $random.NextDouble() -lt 0.92
    }
    else {
        $predictedShortCircuit = $random.NextDouble() -lt 0.04
    }

    if ($predictedShortCircuit) {
        $latencyMs = 80 + $random.Next(0, 181)
        $promptTokens = 18 + $random.Next(0, 28)
        $completionTokens = 2 + $random.Next(0, 17)
        $model = 'heuristic-router'
        $routingPath = 'short_circuit'
    }
    else {
        $latencyMs = 550 + $random.Next(0, 1351)
        $promptTokens = 140 + $random.Next(0, 281)
        $completionTokens = 20 + $random.Next(0, 101)
        $model = 'gpt-4.1-mini'
        $routingPath = "llm:$predictedRoute"
    }

    $totalTokens = $promptTokens + $completionTokens
    $estimatedCost = [math]::Round(($promptTokens * 0.000001) + ($completionTokens * 0.000002), 6)

    [pscustomobject]@{
        row_id                  = Get-NormalizedValue $row.row_id
        query                   = Get-PreferredTextValue @($row.query, $row.Query)
        predicted_route         = $predictedRoute
        predicted_short_circuit = $predictedShortCircuit.ToString().ToLowerInvariant()
        latency_ms              = $latencyMs
        prompt_tokens           = $promptTokens
        completion_tokens       = $completionTokens
        total_tokens            = $totalTokens
        estimated_cost_usd      = ('{0:F6}' -f $estimatedCost)
        routing_path            = $routingPath
        model                   = $model
    }
}

$predictions | Export-Csv -LiteralPath $Output -NoTypeInformation -Encoding utf8
Write-Host "Wrote $($predictions.Count) mock predictions to $Output"