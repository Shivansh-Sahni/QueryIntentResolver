param(
    [Parameter(Mandatory = $true)]
    [string]$Labels,

    [Parameter(Mandatory = $true)]
    [string]$Predictions,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir
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

function Get-HashtableValueOrDefault {
    param(
        [hashtable]$Table,
        [string]$Key,
        [int]$Default = 0
    )

    if ($Table.ContainsKey($Key)) {
        return $Table[$Key]
    }

    return $Default
}

function Get-JoinKey {
    param([psobject]$Row)

    $rowId = Get-NormalizedValue $Row.row_id
    if ($rowId) {
        return "row_id:$rowId"
    }

    $query = Get-PreferredTextValue @($Row.query, $Row.Query)
    if ($query) {
        return "query:$($query.ToLowerInvariant())"
    }

    throw 'Each row must include either row_id or query.'
}

function Resolve-GoldRoute {
    param([psobject]$Row)

    foreach ($key in @('gold_route', 'seed_route', 'Route')) {
        $value = Get-NormalizedValue $Row.$key
        if ($value) {
            return $value
        }
    }

    throw 'Could not resolve gold route.'
}

function Resolve-PredictedRoute {
    param([psobject]$Row)

    foreach ($key in @('predicted_route', 'route')) {
        $value = Get-NormalizedValue $Row.$key
        if ($value) {
            return $value
        }
    }

    throw 'Could not resolve predicted route.'
}

function Parse-BoolOrNull {
    param([object]$Value)

    $text = (Get-NormalizedValue $Value).ToLowerInvariant()
    switch ($text) {
        'true' { return $true }
        '1' { return $true }
        'yes' { return $true }
        'y' { return $true }
        'false' { return $false }
        '0' { return $false }
        'no' { return $false }
        'n' { return $false }
        default { return $null }
    }
}

function Resolve-GoldShortCircuit {
    param([psobject]$Row, [string]$GoldRoute)

    $explicit = Parse-BoolOrNull $Row.gold_short_circuit
    if ($null -ne $explicit) {
        return [bool]$explicit
    }

    $complexity = Get-PreferredTextValue @($Row.seed_complexity, $Row.Complexity)
    if ($complexity) {
        return $complexity -eq 'short_circuit'
    }

    return $GoldRoute -eq 'short_circuit'
}

function Resolve-PredictedShortCircuit {
    param([psobject]$Row, [string]$PredictedRoute)

    $explicit = Parse-BoolOrNull $Row.predicted_short_circuit
    if ($null -ne $explicit) {
        return [bool]$explicit
    }

    $routingPath = Get-NormalizedValue $Row.routing_path
    if ($routingPath) {
        return $routingPath -eq 'short_circuit'
    }

    return $PredictedRoute -eq 'short_circuit'
}

function Parse-NullableNumber {
    param([object]$Value)

    $text = Get-NormalizedValue $Value
    if (-not $text) {
        return $null
    }

    return [double]$text
}

function Get-SafeRate {
    param([double]$Numerator, [double]$Denominator)

    if ($Denominator -eq 0) {
        return 0.0
    }

    return $Numerator / $Denominator
}

function Get-PercentText {
    param([double]$Value)

    return ('{0:N1}%' -f ($Value * 100.0))
}

function Get-NumberText {
    param([double]$Value)

    return ('{0:N2}' -f $Value)
}

function Get-Quantile {
    param(
        [double[]]$Values,
        [double]$Fraction
    )

    if (-not $Values -or $Values.Count -eq 0) {
        return 0.0
    }

    $ordered = @($Values | Sort-Object)
    if ($ordered.Count -eq 1) {
        return $ordered[0]
    }

    $position = ($ordered.Count - 1) * $Fraction
    $lowerIndex = [math]::Floor($position)
    $upperIndex = [math]::Ceiling($position)
    $lowerValue = $ordered[$lowerIndex]
    $upperValue = $ordered[$upperIndex]

    if ($lowerIndex -eq $upperIndex) {
        return $lowerValue
    }

    $weight = $position - $lowerIndex
    return $lowerValue + (($upperValue - $lowerValue) * $weight)
}

function Get-Average {
    param([double[]]$Values)

    if (-not $Values -or $Values.Count -eq 0) {
        return 0.0
    }

    return (($Values | Measure-Object -Average).Average)
}

function Get-Sum {
    param([double[]]$Values)

    if (-not $Values -or $Values.Count -eq 0) {
        return 0.0
    }

    return (($Values | Measure-Object -Sum).Sum)
}

function Get-Median {
    param([double[]]$Values)

    return Get-Quantile -Values $Values -Fraction 0.5
}

function ConvertTo-HtmlTable {
    param(
        [string[]]$Headers,
        [object[][]]$Rows
    )

    $headerHtml = ($Headers | ForEach-Object { "<th>$_</th>" }) -join ''
    $bodyHtml = ($Rows | ForEach-Object {
        $cells = ($_ | ForEach-Object { "<td>$_</td>" }) -join ''
        "<tr>$cells</tr>"
    }) -join ''

    return "<table><thead><tr>$headerHtml</tr></thead><tbody>$bodyHtml</tbody></table>"
}

if (-not (Test-Path -LiteralPath $Labels)) {
    throw "Labels CSV not found: $Labels"
}

if (-not (Test-Path -LiteralPath $Predictions)) {
    throw "Predictions CSV not found: $Predictions"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$labelRows = Import-Csv -LiteralPath $Labels
$predictionRows = Import-Csv -LiteralPath $Predictions

$predictionsByKey = @{}
foreach ($predictionRow in $predictionRows) {
    $predictionsByKey[(Get-JoinKey $predictionRow)] = $predictionRow
}

$matchedRows = New-Object System.Collections.Generic.List[object]
$missingPredictions = New-Object System.Collections.Generic.List[object]

foreach ($labelRow in $labelRows) {
    $key = Get-JoinKey $labelRow
    if (-not $predictionsByKey.ContainsKey($key)) {
        $missingPredictions.Add($labelRow)
        continue
    }

    $predictionRow = $predictionsByKey[$key]
    $goldRoute = Resolve-GoldRoute $labelRow
    $predictedRoute = Resolve-PredictedRoute $predictionRow
    $goldShortCircuit = Resolve-GoldShortCircuit -Row $labelRow -GoldRoute $goldRoute
    $predictedShortCircuit = Resolve-PredictedShortCircuit -Row $predictionRow -PredictedRoute $predictedRoute

    $matchedRows.Add([pscustomobject]@{
        row_id                  = Get-NormalizedValue $labelRow.row_id
        query                   = Get-PreferredTextValue @($labelRow.query, $labelRow.Query)
        gold_route              = $goldRoute
        predicted_route         = $predictedRoute
        gold_short_circuit      = [bool]$goldShortCircuit
        predicted_short_circuit = [bool]$predictedShortCircuit
        latency_ms              = Parse-NullableNumber $predictionRow.latency_ms
        prompt_tokens           = Parse-NullableNumber $predictionRow.prompt_tokens
        completion_tokens       = Parse-NullableNumber $predictionRow.completion_tokens
        total_tokens            = Parse-NullableNumber $predictionRow.total_tokens
        estimated_cost_usd      = Parse-NullableNumber $predictionRow.estimated_cost_usd
        routing_path            = Get-NormalizedValue $predictionRow.routing_path
        model                   = Get-NormalizedValue $predictionRow.model
    })
}

$totalLabels = $labelRows.Count
$matchedCount = $matchedRows.Count
$missingCount = $missingPredictions.Count

$correctRoutes = @($matchedRows | Where-Object { $_.gold_route -eq $_.predicted_route }).Count
$routeAccuracy = Get-SafeRate -Numerator $correctRoutes -Denominator $matchedCount

$tp = @($matchedRows | Where-Object { $_.gold_short_circuit -and $_.predicted_short_circuit }).Count
$tn = @($matchedRows | Where-Object { -not $_.gold_short_circuit -and -not $_.predicted_short_circuit }).Count
$fp = @($matchedRows | Where-Object { -not $_.gold_short_circuit -and $_.predicted_short_circuit }).Count
$fn = @($matchedRows | Where-Object { $_.gold_short_circuit -and -not $_.predicted_short_circuit }).Count

$shortCircuitCorrectRate = Get-SafeRate -Numerator $tp -Denominator ($tp + $fn)
$shortCircuitPrecision = Get-SafeRate -Numerator $tp -Denominator ($tp + $fp)
$shortCircuitBooleanAccuracy = Get-SafeRate -Numerator ($tp + $tn) -Denominator $matchedCount

$latencies = @($matchedRows | Where-Object { $null -ne $_.latency_ms } | ForEach-Object { [double]$_.latency_ms })
$promptTokens = @($matchedRows | Where-Object { $null -ne $_.prompt_tokens } | ForEach-Object { [double]$_.prompt_tokens })
$completionTokens = @($matchedRows | Where-Object { $null -ne $_.completion_tokens } | ForEach-Object { [double]$_.completion_tokens })
$totalTokens = @($matchedRows | Where-Object { $null -ne $_.total_tokens } | ForEach-Object { [double]$_.total_tokens })
$costs = @($matchedRows | Where-Object { $null -ne $_.estimated_cost_usd } | ForEach-Object { [double]$_.estimated_cost_usd })

$goldCounts = @{}
$predictedCounts = @{}
$routingPathCounts = @{}
$modelCounts = @{}

foreach ($row in $matchedRows) {
    $goldCounts[$row.gold_route] = 1 + (Get-HashtableValueOrDefault -Table $goldCounts -Key $row.gold_route)
    $predictedCounts[$row.predicted_route] = 1 + (Get-HashtableValueOrDefault -Table $predictedCounts -Key $row.predicted_route)
    if ($row.routing_path) {
        $routingPathCounts[$row.routing_path] = 1 + (Get-HashtableValueOrDefault -Table $routingPathCounts -Key $row.routing_path)
    }
    if ($row.model) {
        $modelCounts[$row.model] = 1 + (Get-HashtableValueOrDefault -Table $modelCounts -Key $row.model)
    }
}

$routes = @($goldCounts.Keys + $predictedCounts.Keys | Sort-Object -Unique)
$confusionMatrix = [ordered]@{}
foreach ($goldRoute in $routes) {
    $rowCounts = [ordered]@{}
    foreach ($predictedRoute in $routes) {
        $rowCounts[$predictedRoute] = 0
    }
    $confusionMatrix[$goldRoute] = $rowCounts
}

foreach ($row in $matchedRows) {
    $confusionMatrix[$row.gold_route][$row.predicted_route] += 1
}

$perRouteAccuracy = [ordered]@{}
foreach ($route in $routes) {
    $routeTotal = Get-HashtableValueOrDefault -Table $goldCounts -Key $route
    $routeCorrect = $confusionMatrix[$route][$route]
    $perRouteAccuracy[$route] = [ordered]@{
        count = $routeTotal
        accuracy = (Get-SafeRate -Numerator $routeCorrect -Denominator $routeTotal)
    }
}

$latencyMax = 0.0
if ($latencies.Count -gt 0) {
    $latencyMax = ($latencies | Measure-Object -Maximum).Maximum
}

$summary = [ordered]@{
    dataset = [ordered]@{
        total_labels = $totalLabels
        matched_predictions = $matchedCount
        missing_predictions = $missingCount
    }
    metrics = [ordered]@{
        route_accuracy = $routeAccuracy
        short_circuit_correct_rate = $shortCircuitCorrectRate
        short_circuit_precision = $shortCircuitPrecision
        short_circuit_boolean_accuracy = $shortCircuitBooleanAccuracy
        short_circuit_confusion = [ordered]@{
            true_positive = $tp
            true_negative = $tn
            false_positive = $fp
            false_negative = $fn
        }
    }
    latency_ms = [ordered]@{
        count = $latencies.Count
        avg = (Get-Average $latencies)
        p50 = (Get-Median $latencies)
        p95 = (Get-Quantile -Values $latencies -Fraction 0.95)
        max = $latencyMax
    }
    tokens = [ordered]@{
        avg_total_tokens = (Get-Average $totalTokens)
        avg_prompt_tokens = (Get-Average $promptTokens)
        avg_completion_tokens = (Get-Average $completionTokens)
        total_tokens = (Get-Sum $totalTokens)
    }
    cost_usd = [ordered]@{
        total = (Get-Sum $costs)
        avg = (Get-Average $costs)
    }
    distribution = [ordered]@{
        gold_routes = [ordered]@{}
        predicted_routes = [ordered]@{}
        routing_paths = [ordered]@{}
        models = [ordered]@{}
        per_route_accuracy = $perRouteAccuracy
    }
    confusion_matrix = $confusionMatrix
    missing_prediction_queries = @($missingPredictions | ForEach-Object { Get-PreferredTextValue @($_.query, $_.Query) })
}

foreach ($key in ($goldCounts.Keys | Sort-Object)) {
    $summary.distribution.gold_routes[$key] = $goldCounts[$key]
}
foreach ($key in ($predictedCounts.Keys | Sort-Object)) {
    $summary.distribution.predicted_routes[$key] = $predictedCounts[$key]
}
foreach ($key in ($routingPathCounts.Keys | Sort-Object)) {
    $summary.distribution.routing_paths[$key] = $routingPathCounts[$key]
}
foreach ($key in ($modelCounts.Keys | Sort-Object)) {
    $summary.distribution.models[$key] = $modelCounts[$key]
}

$summaryPath = Join-Path $OutputDir 'evaluation_summary.json'
$reportPath = Join-Path $OutputDir 'evaluation_report.md'
$dashboardPath = Join-Path $OutputDir 'evaluation_dashboard.html'

$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding utf8

$markdownLines = @(
    '# Phase 7 Evaluation Report',
    '',
    '## Dataset Coverage',
    "- Labels: $totalLabels",
    "- Matched predictions: $matchedCount",
    "- Missing predictions: $missingCount",
    '',
    '## Core Metrics',
    "- Route accuracy: $(Get-PercentText $routeAccuracy)",
    "- Correct short-circuit rate: $(Get-PercentText $shortCircuitCorrectRate)",
    "- Short-circuit precision: $(Get-PercentText $shortCircuitPrecision)",
    "- Short-circuit boolean accuracy: $(Get-PercentText $shortCircuitBooleanAccuracy)",
    '',
    '## Latency',
    "- Average latency: $(Get-NumberText $summary.latency_ms.avg) ms",
    "- P50 latency: $(Get-NumberText $summary.latency_ms.p50) ms",
    "- P95 latency: $(Get-NumberText $summary.latency_ms.p95) ms",
    "- Max latency: $(Get-NumberText $summary.latency_ms.max) ms",
    '',
    '## Tokens And Cost',
    "- Average total tokens: $(Get-NumberText $summary.tokens.avg_total_tokens)",
    "- Total tokens: $(Get-NumberText $summary.tokens.total_tokens)",
    ('- Total cost: ${0:N4}' -f $summary.cost_usd.total),
    ('- Average cost per query: ${0:N6}' -f $summary.cost_usd.avg),
    '',
    '## Route Accuracy By Gold Route',
    '| Route | Count | Accuracy |',
    '| --- | ---: | ---: |'
)

foreach ($route in $routes) {
    $markdownLines += "| $route | $($perRouteAccuracy[$route].count) | $(Get-PercentText $perRouteAccuracy[$route].accuracy) |"
}

$markdownLines += @(
    '',
    '## Routing Path Distribution',
    '| Routing Path | Count |',
    '| --- | ---: |'
)

foreach ($path in ($routingPathCounts.Keys | Sort-Object)) {
    $markdownLines += "| $path | $($routingPathCounts[$path]) |"
}

$markdownLines += @(
    '',
    '## Confusion Matrix',
    ('| Gold \ Predicted | ' + ($routes -join ' | ') + ' |'),
    ('| --- | ' + (($routes | ForEach-Object { '---:' }) -join ' | ') + ' |')
)

foreach ($goldRoute in $routes) {
    $rowValues = foreach ($predictedRoute in $routes) { $confusionMatrix[$goldRoute][$predictedRoute] }
    $markdownLines += ('| ' + $goldRoute + ' | ' + ($rowValues -join ' | ') + ' |')
}

$markdownLines -join [Environment]::NewLine | Set-Content -LiteralPath $reportPath -Encoding utf8

$routeRows = @(
foreach ($route in $routes) {
    @($route, [string]$perRouteAccuracy[$route].count, (Get-PercentText $perRouteAccuracy[$route].accuracy))
}
)

$pathRows = @(
foreach ($path in ($routingPathCounts.Keys | Sort-Object)) {
    @($path, [string]$routingPathCounts[$path])
}
)

if ($pathRows.Count -eq 0) {
    $pathRows = @(@('No routing path data', '0'))
}

$confusionRows = @(
foreach ($goldRoute in $routes) {
    $rowValues = foreach ($predictedRoute in $routes) { [string]$confusionMatrix[$goldRoute][$predictedRoute] }
    ,@($goldRoute) + $rowValues
}
)

$metricCards = @(
    "<section class='card'><h2>Route accuracy</h2><p>$(Get-PercentText $routeAccuracy)</p></section>",
    "<section class='card'><h2>Short-circuit correct rate</h2><p>$(Get-PercentText $shortCircuitCorrectRate)</p></section>",
    "<section class='card'><h2>P95 latency</h2><p>$(Get-NumberText $summary.latency_ms.p95) ms</p></section>",
    ('<section class=''card''><h2>Total cost</h2><p>${0:N4}</p></section>' -f $summary.cost_usd.total)
) -join ''

$latencyCostTable = ConvertTo-HtmlTable -Headers @('Metric', 'Value') -Rows @(
    @('Average latency', "$(Get-NumberText $summary.latency_ms.avg) ms"),
    @('P50 latency', "$(Get-NumberText $summary.latency_ms.p50) ms"),
    @('P95 latency', "$(Get-NumberText $summary.latency_ms.p95) ms"),
    @('Max latency', "$(Get-NumberText $summary.latency_ms.max) ms"),
    @('Average total tokens', (Get-NumberText $summary.tokens.avg_total_tokens)),
    @('Total tokens', (Get-NumberText $summary.tokens.total_tokens)),
    @('Total cost', ('${0:N4}' -f $summary.cost_usd.total)),
    @('Average cost per query', ('${0:N6}' -f $summary.cost_usd.avg))
)

$dashboardHtml = @"
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Phase 7 Evaluation Dashboard</title>
  <style>
    :root {
      --bg: #f3efe7;
      --panel: #fffaf2;
      --ink: #1f2933;
      --muted: #5f6c7b;
      --accent: #b85c38;
      --line: #e5d7c6;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: Georgia, 'Times New Roman', serif; background: linear-gradient(180deg, #efe5d6 0%, var(--bg) 50%, #f7f2ea 100%); color: var(--ink); }
    main { max-width: 1200px; margin: 0 auto; padding: 32px 20px 48px; }
    h1, h2 { margin: 0 0 12px; }
    h1 { font-size: 2.4rem; letter-spacing: 0.02em; }
    p.lede { max-width: 760px; color: var(--muted); font-size: 1.05rem; line-height: 1.6; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 24px 0 28px; }
    .card { background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 18px 20px; box-shadow: 0 12px 30px rgba(73, 50, 24, 0.08); }
    .card p { font-size: 2rem; margin: 0; color: var(--accent); }
    .section { margin-top: 24px; background: rgba(255, 250, 242, 0.82); border: 1px solid var(--line); border-radius: 20px; padding: 20px; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 0.96rem; }
    th, td { padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
    thead th { color: var(--muted); font-weight: 600; }
    .muted { color: var(--muted); }
    @media (max-width: 720px) {
      h1 { font-size: 1.9rem; }
      .card p { font-size: 1.7rem; }
      th, td { padding: 8px 10px; }
    }
  </style>
</head>
<body>
  <main>
    <h1>Phase 7 Evaluation Dashboard</h1>
    <p class="lede">This report measures route accuracy, short-circuit behavior, latency, tokens, and cost for the current classifier export. Use it as the lightweight decision surface for whether the router is ready to promote.</p>
    <div class="grid">$metricCards</div>
    <section class="section">
      <h2>Coverage</h2>
      <p class="muted">Matched $matchedCount of $totalLabels labeled queries. Missing predictions: $missingCount.</p>
    </section>
    <section class="section">
      <h2>Latency And Cost</h2>
      $latencyCostTable
    </section>
    <section class="section">
      <h2>Per-Route Accuracy</h2>
      $(ConvertTo-HtmlTable -Headers @('Route', 'Count', 'Accuracy') -Rows $routeRows)
    </section>
    <section class="section">
      <h2>Routing Path Distribution</h2>
      $(ConvertTo-HtmlTable -Headers @('Routing path', 'Count') -Rows $pathRows)
    </section>
    <section class="section">
      <h2>Confusion Matrix</h2>
      $(ConvertTo-HtmlTable -Headers (@('Gold \ Predicted') + $routes) -Rows $confusionRows)
    </section>
  </main>
</body>
</html>
"@

$dashboardHtml | Set-Content -LiteralPath $dashboardPath -Encoding utf8

Write-Host "Wrote summary to $summaryPath"
Write-Host "Wrote markdown report to $reportPath"
Write-Host "Wrote dashboard to $dashboardPath"