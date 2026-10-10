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
# Prefer the standard Android Studio SDK. A malformed local.properties
# path must never turn a successful installation into a script failure.
$adbExe = $null
$adbCommand = Get-Command adb.exe -ErrorAction SilentlyContinue
if ($adbCommand) { $adbExe = $adbCommand.Source }
if (-not $adbExe) {
  $sdkRoots = @(
    (Join-Path $env:LOCALAPPDATA 'Android\Sdk'),
    $env:ANDROID_HOME,
    $env:ANDROID_SDK_ROOT
  ) | Where-Object { $_ }
  foreach ($sdkRoot in $sdkRoots) {
    $candidate = Join-Path $sdkRoot 'platform-tools\adb.exe'
    if (Test-Path -LiteralPath $candidate) { $adbExe = $candidate; break }
  }
}
if ($adbExe) {
  & $adbExe shell monkey -p com.example.barrysconcertagenda -c android.intent.category.LAUNCHER 1 | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Geinstalleerd. Automatisch openen lukte niet; open de app op de telefoon." -ForegroundColor Yellow
  }
} else {
  Write-Host "Geinstalleerd. ADB niet gevonden; open de app op je telefoon." -ForegroundColor Yellow
}
Write-Host "GEREED: de nieuwste Backstage V3 staat op je Samsung." -ForegroundColor Green
