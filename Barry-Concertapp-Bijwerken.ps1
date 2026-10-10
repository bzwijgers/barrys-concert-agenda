# Barry's Concert Agenda - safe one-click update and installation
# Run from Barry-Concertapp-Bijwerken.bat. Requires Git, JDK/Gradle and Android SDK.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
function Fail($message) { Write-Host ("FOUT: " + $message) -ForegroundColor Red; exit 1 }
function Run($exe, [string[]]$arguments) {
  & $exe @arguments
  if ($LASTEXITCODE -ne 0) { Fail ("Opdracht mislukt: " + $exe + " " + ($arguments -join " ")) }
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "Git is niet gevonden." }
if (-not (Test-Path '.\gradlew.bat')) { Fail "Gradle wrapper ontbreekt; start dit vanuit de projectmap." }
Write-Host "Barry's Concertapp bijwerken - Backstage V3" -ForegroundColor Cyan
$changes = (& git status --porcelain)
if ($LASTEXITCODE -ne 0) { Fail "Dit is geen werkende Git-projectmap." }
if ($changes) { Fail "Er staan lokale wijzigingen. Bewaar/commit deze eerst; er wordt niets gewist." }
$branch = (& git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0) { Fail "Huidige Git-branch onbekend." }
if ($branch -ne 'preview/backstage-v3') { Fail "Je zit op branch '$branch', niet preview/backstage-v3. Wissel eerst veilig van branch." }
Write-Host "1/3 Nieuwste V3 ophalen..."
Run 'git' @('fetch','origin','preview/backstage-v3')
Run 'git' @('merge','--ff-only','origin/preview/backstage-v3')
Write-Host "2/3 Android-app bouwen en installeren..."
Run '.\gradlew.bat' @('installDebug')
Write-Host "3/3 App starten..."
$adb = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adb) {
  $sdk = $null
  if (Test-Path '.\local.properties') {
    $sdkline = Get-Content '.\local.properties' | Where-Object { $_ -match '^sdk\.dir=' } | Select-Object -First 1
    if ($sdkline) { $sdk = ($sdkline -replace '^sdk\.dir=','').Replace('\\', '\') }
  }
  if (-not $sdk -and $env:ANDROID_HOME) { $sdk = $env:ANDROID_HOME }
  if (-not $sdk -and $env:ANDROID_SDK_ROOT) { $sdk = $env:ANDROID_SDK_ROOT }
  if ($sdk -and (Test-Path (Join-Path $sdk 'platform-tools\adb.exe'))) { $adb = Join-Path $sdk 'platform-tools\adb.exe' }
}
if ($adb) {
  & $adb shell monkey -p com.example.barrysconcertagenda -c android.intent.category.LAUNCHER 1 | Out-Null
  if ($LASTEXITCODE -ne 0) { Write-Host "Geinstalleerd, maar automatisch openen lukte niet. Open de app op je telefoon." -ForegroundColor Yellow }
} else { Write-Host "Geinstalleerd. Open de app op je telefoon (adb niet gevonden)." -ForegroundColor Yellow }
Write-Host "GEREED: de nieuwste Backstage V3 staat op je Samsung." -ForegroundColor Green
