param(
  [string]$Url = "http://localhost:3000/cozinha"
)

$edgeCandidates = @(
  (Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"),
  (Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe")
)
$edgePath = $edgeCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if (-not $edgePath) {
  Write-Error "Microsoft Edge não foi encontrado. Instale o Edge ou ajuste o caminho no script."
  exit 1
}

try {
  $defaultPrinter = Get-CimInstance Win32_Printer -ErrorAction Stop |
    Where-Object { $_.Default } |
    Select-Object -First 1

  if (-not $defaultPrinter) {
    Write-Warning "Nenhuma impressora padrão foi encontrada no Windows."
  } elseif ($defaultPrinter.Name -notlike "*EPSON TM-T20X*") {
    Write-Warning "A impressora padrão atual é '$($defaultPrinter.Name)'. Defina a EPSON TM-T20X Receipt como padrão antes de imprimir."
  } else {
    Write-Host "Impressora padrão confirmada: $($defaultPrinter.Name)" -ForegroundColor Green
  }
} catch {
  Write-Warning "Não foi possível consultar a impressora padrão. Confirme manualmente a EPSON TM-T20X Receipt no Windows."
}

$profilePath = Join-Path $env:LOCALAPPDATA "MaviConnect\EdgePrintProfile"
New-Item -ItemType Directory -Path $profilePath -Force | Out-Null

$arguments = @(
  "--user-data-dir=$profilePath",
  "--kiosk-printing",
  "--app=$Url",
  "--no-first-run"
)

Write-Host "Abrindo o Modo de Impressão Mavi..." -ForegroundColor Cyan
Write-Host "Neste navegador, window.print() envia diretamente para a impressora padrão." -ForegroundColor Cyan
Start-Process -FilePath $edgePath -ArgumentList $arguments
