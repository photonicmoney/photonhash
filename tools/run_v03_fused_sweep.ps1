param(
    [string]$Executable = ".\ph_v03_recurrent_fused_cutlass.exe",
    [int[]]$Dimensions = @(1024),
    [int[]]$Batches = @(8192, 32768, 131072),
    [int[]]$Rounds = @(1, 2, 4, 8, 16, 32, 64, 128),
    [int]$Repeats = 5,
    [string]$OutputCsv = "research\v0.3\results\r1-fused-electronic-sweep.csv"
)

$ErrorActionPreference = "Stop"
$resolvedExecutable = (Resolve-Path $Executable).Path
$outputDirectory = Split-Path -Parent $OutputCsv
if ($outputDirectory) {
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
}

$gpuMetadata = (& nvidia-smi --query-gpu=name,driver_version,memory.total,power.limit --format=csv,noheader,nounits | Select-Object -First 1).Trim()
if (-not $gpuMetadata) {
    throw "read-only nvidia-smi metadata query failed"
}

$rows = [System.Collections.Generic.List[object]]::new()
foreach ($dimension in $Dimensions) {
    foreach ($batch in $Batches) {
        foreach ($roundCount in $Rounds) {
            Write-Host "R1-F n=$dimension batch=$batch rounds=$roundCount repeats=$Repeats"
            $lines = & $resolvedExecutable $dimension $batch $roundCount $Repeats 2>&1
            $exitCode = $LASTEXITCODE
            $lines | ForEach-Object { Write-Host $_ }
            if ($exitCode -ne 0) {
                throw "benchmark failed with exit code $exitCode"
            }
            $resultLine = $lines |
                Where-Object { $_ -match "^RESULT_JSON " } |
                Select-Object -Last 1
            if (-not $resultLine) {
                throw "benchmark did not emit RESULT_JSON"
            }
            $payload = ($resultLine -replace "^RESULT_JSON ", "") |
                ConvertFrom-Json
            $rows.Add([pscustomobject]@{
                measured_utc = [DateTime]::UtcNow.ToString("o")
                gpu_metadata = $gpuMetadata
                executable = Split-Path -Leaf $resolvedExecutable
                n = [int]$payload.n
                batch = [int]$payload.batch
                rounds = [int]$payload.rounds
                repeats = [int]$payload.repeats
                fused_us_attempt = [double]$payload.fused_us_attempt
                projected_accelerable_share = [double]$payload.projected_accelerable_share
            })
        }
    }
}

$rows | Export-Csv -NoTypeInformation -Encoding utf8 -Path $OutputCsv
Write-Host "Wrote $($rows.Count) rows to $OutputCsv"
Write-Host "Safety: the sweep used user-space CUDA and read-only telemetry only."
