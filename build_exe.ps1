
# PowerShell script to activate venv, kill running exe, and build with PyInstaller
$exeName = "S-pankki_to_YNAB.exe"

# Kill running process if exists
$proc = Get-Process | Where-Object { $_.ProcessName -eq ($exeName -replace ".exe", "") }
if ($proc) {
    Write-Host "Killing running process: $exeName"
    $proc | Stop-Process -Force
}

# Build with PyInstaller
pyinstaller --onefile --noconsole --name $exeName --distpath . --workpath ./pybuild main.py
