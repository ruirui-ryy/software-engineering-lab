$ErrorActionPreference = 'Stop'
$labRoot = Split-Path -Parent $PSScriptRoot
$jarPath = Join-Path $PSScriptRoot 'plantuml.jar'
if (-not (Test-Path -LiteralPath $jarPath)) {
    throw 'Missing tools/plantuml.jar. See tools/README.md for the pinned download.'
}
$sourcePattern = Join-Path $labRoot 'uml/*.puml'
& java -jar $jarPath -charset UTF-8 -tpng $sourcePattern
if ($LASTEXITCODE -ne 0) { throw 'PlantUML PNG rendering failed' }
& java -jar $jarPath -charset UTF-8 -tsvg $sourcePattern
if ($LASTEXITCODE -ne 0) { throw 'PlantUML SVG rendering failed' }
