param(
    [Parameter(Mandatory = $true)]
    [string]$Executable,
    [uint32[]]$Batches = @(8192, 32768, 131072),
    [uint32[]]$Datasets = @(0, 1, 2, 3, 4),
    [ValidateSet('register', 'direct', 'warp', 'thread')]
    [string]$Kernel = 'register',
    [uint64]$TargetAttempts = 100000000,
    [int]$Repeats = 5,
    [int]$CooldownSeconds = 2,
    [string]$OutputDirectory = 'research/results'
)

$ErrorActionPreference = 'Stop'
$exe = (Resolve-Path -LiteralPath $Executable).Path
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$rawPath = Join-Path $OutputDirectory "cuda-raw-$stamp.csv"
$summaryPath = Join-Path $OutputDirectory "cuda-summary-$stamp.json"

function Read-Telemetry {
    $line = & nvidia-smi --query-gpu=temperature.gpu,power.draw,clocks.sm,clocks.mem --format=csv,noheader,nounits --id=0
    if ($LASTEXITCODE -ne 0) {
        throw 'nvidia-smi telemetry query failed'
    }
    $p = $line -split ',' | ForEach-Object { $_.Trim() }
    [pscustomobject]@{
        TemperatureC = [double]$p[0]
        PowerW = [double]$p[1]
        SmClockMHz = [double]$p[2]
        MemoryClockMHz = [double]$p[3]
    }
}

function Mean([double[]]$Values) {
    ($Values | Measure-Object -Average).Average
}

function StdDev([double[]]$Values) {
    if ($Values.Count -lt 2) { return 0.0 }
    $mean = Mean $Values
    $sum = 0.0
    foreach ($value in $Values) {
        $delta = $value - $mean
        $sum += $delta * $delta
    }
    [Math]::Sqrt($sum / ($Values.Count - 1))
}

$gpuMetadata = & nvidia-smi --query-gpu=name,driver_version,memory.total,power.limit --format=csv,noheader --id=0
if ($LASTEXITCODE -ne 0) {
    throw 'nvidia-smi metadata query failed'
}
$rows = [System.Collections.Generic.List[object]]::new()

foreach ($batch in $Batches) {
    $iterations = [Math]::Max(
        1, [int][Math]::Ceiling([double]$TargetAttempts / $batch))
    foreach ($dataset in $Datasets) {
        foreach ($repeat in 1..$Repeats) {
            $before = Read-Telemetry
            $started = (Get-Date).ToUniversalTime().ToString('o')
            $output = & $exe $batch $iterations $Kernel $dataset 2>&1
            if ($LASTEXITCODE -ne 0) {
                $output | Write-Error
                throw "benchmark failed for batch=$batch dataset=$dataset repeat=$repeat"
            }
            $result = $output | Where-Object {
                $_.ToString().StartsWith('RESULT_CSV,')
            } | Select-Object -Last 1
            if (-not $result) {
                throw 'benchmark emitted no RESULT_CSV record'
            }
            $p = $result.ToString().Split(',')
            if ($p.Count -ne 20) {
                throw "unexpected RESULT_CSV field count: $($p.Count)"
            }
            $after = Read-Telemetry
            $rows.Add([pscustomobject]@{
                StartedUtc = $started
                Repeat = $repeat
                Dataset = [uint32]$p[1]
                Batch = [uint32]$p[2]
                Iterations = [uint32]$p[3]
                Kernel = $p[4]
                GemmAlgorithm = $p[5]
                PipelineDepth = [uint32]$p[6]
                VectorUs = [double]$p[7]
                GemmUs = [double]$p[8]
                FinalUs = [double]$p[9]
                DeviceAttemptsPerSecond = [double]$p[10]
                HostAttemptsPerSecond = [double]$p[11]
                GemmSharePercent = [double]$p[12]
                AverageBoardPowerW = [double]$p[13]
                IntegratedEnergyUjPerAttempt = [double]$p[14]
                CounterEnergyUjPerAttempt = [double]$p[15]
                PipelineAttemptsPerSecond = [double]$p[16]
                PipelineAverageBoardPowerW = [double]$p[17]
                PipelineIntegratedEnergyUjPerAttempt = [double]$p[18]
                PipelineCounterEnergyUjPerAttempt = [double]$p[19]
                TemperatureBeforeC = $before.TemperatureC
                TemperatureAfterC = $after.TemperatureC
                SmClockBeforeMHz = $before.SmClockMHz
                SmClockAfterMHz = $after.SmClockMHz
                MemoryClockBeforeMHz = $before.MemoryClockMHz
                MemoryClockAfterMHz = $after.MemoryClockMHz
            })
            if ($CooldownSeconds -gt 0) {
                Start-Sleep -Seconds $CooldownSeconds
            }
        }
    }
}

$rows | Export-Csv -NoTypeInformation -Encoding utf8 -Path $rawPath
$summary = foreach ($group in ($rows | Group-Object Batch)) {
    $rates = [double[]]$group.Group.DeviceAttemptsPerSecond
    $shares = [double[]]$group.Group.GemmSharePercent
    $energy = [double[]]$group.Group.IntegratedEnergyUjPerAttempt
    $pipelineRates = [double[]]$group.Group.PipelineAttemptsPerSecond
    $pipelineEnergy =
        [double[]]$group.Group.PipelineIntegratedEnergyUjPerAttempt
    $rateMean = Mean $rates
    $rateStd = StdDev $rates
    [pscustomobject]@{
        Batch = [uint32]$group.Name
        Samples = $rates.Count
        DeviceAttemptsPerSecondMean = $rateMean
        DeviceAttemptsPerSecondStdDev = $rateStd
        DeviceAttemptsPerSecondCvPercent =
            $(if ($rateMean -eq 0) { 0 } else { 100 * $rateStd / $rateMean })
        GemmSharePercentMean = Mean $shares
        GemmSharePercentStdDev = StdDev $shares
        IntegratedEnergyUjPerAttemptMean = Mean $energy
        IntegratedEnergyUjPerAttemptStdDev = StdDev $energy
        PipelineAttemptsPerSecondMean = Mean $pipelineRates
        PipelineAttemptsPerSecondStdDev = StdDev $pipelineRates
        PipelineIntegratedEnergyUjPerAttemptMean = Mean $pipelineEnergy
        PipelineIntegratedEnergyUjPerAttemptStdDev = StdDev $pipelineEnergy
    }
}

[pscustomobject]@{
    GeneratedUtc = (Get-Date).ToUniversalTime().ToString('o')
    Executable = $exe
    GpuMetadata = $gpuMetadata
    TargetAttemptsPerRun = $TargetAttempts
    Repeats = $Repeats
    Datasets = $Datasets
    Summary = $summary
    RawCsv = (Resolve-Path -LiteralPath $rawPath).Path
} | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 -Path $summaryPath

Write-Output "raw: $rawPath"
Write-Output "summary: $summaryPath"
$summary | Format-Table -AutoSize
