# reset_demo.ps1
# Restores every benchmark bug file to its original buggy state,
# so you can re-run demos/rehearsals as many times as you want.
#
# Usage: .\reset_demo.ps1
# Run this from the debugging-agent root folder.

Write-Host "Resetting benchmark bugs to their original buggy state..." -ForegroundColor Cyan

$files = @(
    "sandbox\real-bugs-benchmark\bug1-apnumber\humanize_mini\bug_apnumber.py",
    "sandbox\real-bugs-benchmark\bug2-intword\humanize_mini2\bug_intword.py",
    "sandbox\real-bugs-benchmark\bug3-naturalsize\humanize_mini3\bug_naturalsize.py",
    "sandbox\benchmark-repo\mathlib\bug_average.py",
    "sandbox\benchmark-repo\mathlib\bug_is_even.py",
    "sandbox\benchmark-repo\mathlib\bug_factorial.py",
    "sandbox\benchmark-repo\mathlib\bug_find_max.py",
    "sandbox\benchmark-repo\mathlib\bug_count_vowels.py",
    "sandbox\sample-buggy-repo\calculator\__init__.py"
)

$resetCount = 0
$skippedCount = 0

foreach ($file in $files) {
    $backup = "$file.bak"
    if (Test-Path $backup) {
        Copy-Item $backup $file -Force
        Write-Host "  Reset: $file" -ForegroundColor Green
        $resetCount++
    } else {
        Write-Host "  Skipped (no .bak found): $file" -ForegroundColor Yellow
        $skippedCount++
    }
}

Write-Host "`nDone. Reset $resetCount file(s), skipped $skippedCount (no backup present)." -ForegroundColor Cyan
Write-Host "If a file was skipped, it may never have been patched yet, or its .bak lives elsewhere." -ForegroundColor Cyan
