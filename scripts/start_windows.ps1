# Build (if needed) and run the FinAlly container. Idempotent.
param(
    [switch]$Build,
    [switch]$NoOpen
)

$Image = 'finally'
$Container = 'finally'
$Volume = 'finally-data'
$Url = 'http://localhost:8000'
$Root = Split-Path -Parent $PSScriptRoot

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Docker is not running. Start Docker Desktop and try again.' -ForegroundColor Red
    exit 1
}

$EnvFile = Join-Path $Root '.env'
if (-not (Test-Path $EnvFile)) {
    Write-Host "Missing $EnvFile - copy .env.example to .env and set OPENROUTER_API_KEY." -ForegroundColor Red
    exit 1
}

docker image inspect $Image *> $null
if ($Build -or $LASTEXITCODE -ne 0) {
    Write-Host "Building $Image..."
    docker build -t $Image $Root
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

docker rm -f $Container *> $null

docker run -d --name $Container -p 8000:8000 --env-file $EnvFile -v "${Volume}:/app/db" $Image *> $null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "FinAlly is starting at $Url"
Write-Host "Logs: docker logs -f $Container"

if (-not $NoOpen) {
    Start-Process $Url
}
