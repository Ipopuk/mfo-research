param(
    [string]$DocumentPath = '',
    [string]$ReviewPdf = (Join-Path (Split-Path $PSScriptRoot -Parent) 'submission\review\kt2_report_review.pdf')
)

$ErrorActionPreference = 'Stop'
if (-not $DocumentPath) {
    $reports = @(Get-ChildItem -LiteralPath (Join-Path (Split-Path $PSScriptRoot -Parent) 'report') -Filter '*.docx' | Where-Object { $_.Name -match '2\.docx$' })
    if ($reports.Count -ne 1) { throw 'Expected exactly one KT2 DOCX in report/.' }
    $DocumentPath = $reports[0].FullName
}
$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Open((Resolve-Path -LiteralPath $DocumentPath).Path)
    $document.Repaginate()
    foreach ($toc in $document.TablesOfContents) { $toc.Update() }
    $document.Fields.Update() | Out-Null
    $document.Repaginate()
    foreach ($toc in $document.TablesOfContents) { $toc.UpdatePageNumbers() }
    $document.Save()

    $directory = Split-Path $ReviewPdf -Parent
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    $document.ExportAsFixedFormat($ReviewPdf, 17)
    Write-Output "Updated DOCX: $DocumentPath"
    Write-Output "Review PDF: $ReviewPdf"
}
finally {
    if ($document) { $document.Close($false) }
    if ($word) { $word.Quit() }
}
