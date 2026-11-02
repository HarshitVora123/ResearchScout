param (
    [string]$Action = "start"
)

$env:PYTHONIOENCODING = "utf-8"
python "$PSScriptRoot\run.py" $Action $args
