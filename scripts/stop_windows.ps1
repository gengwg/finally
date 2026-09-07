# Stop and remove the FinAlly container. The data volume is kept. Idempotent.
$Container = 'finally'

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Docker is not running. Start Docker Desktop and try again.' -ForegroundColor Red
    exit 1
}

# docker rm -f exits 0 for a missing container, so check first
$existing = docker ps -aq -f "name=^$Container$"
if ($existing) {
    docker rm -f $Container *> $null
    Write-Host "Stopped and removed container $Container."
} else {
    Write-Host "Container $Container is not running."
}

Write-Host 'Volume finally-data kept - your portfolio persists.'
