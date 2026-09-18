[CmdletBinding()]
param(
    [string]$LogoPath = (Join-Path $PSScriptRoot "logo.jpg"),
    [string]$StartScriptPath = (Join-Path $PSScriptRoot "start_ai.ps1"),
    [string]$ShortcutName = "Start Local AI"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $LogoPath -PathType Leaf)) {
    throw "Logo file not found: $LogoPath"
}

if (-not (Test-Path -LiteralPath $StartScriptPath -PathType Leaf)) {
    throw "Start script not found: $StartScriptPath"
}

$iconPath = Join-Path (Split-Path -Parent $LogoPath) "start_local_ai.ico"
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "$ShortcutName.lnk"

Add-Type -AssemblyName System.Drawing

$sourceImage = [System.Drawing.Image]::FromFile((Resolve-Path -LiteralPath $LogoPath))
$iconBitmap = [System.Drawing.Bitmap]::new(256, 256)

try {
    $graphics = [System.Drawing.Graphics]::FromImage($iconBitmap)
    try {
        $graphics.Clear([System.Drawing.Color]::Transparent)
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality

        $scale = [Math]::Min(256 / $sourceImage.Width, 256 / $sourceImage.Height)
        $width = [int]($sourceImage.Width * $scale)
        $height = [int]($sourceImage.Height * $scale)
        $left = [int]((256 - $width) / 2)
        $top = [int]((256 - $height) / 2)
        $graphics.DrawImage($sourceImage, $left, $top, $width, $height)
    }
    finally {
        $graphics.Dispose()
    }

    $pngStream = [System.IO.MemoryStream]::new()
    try {
        $iconBitmap.Save($pngStream, [System.Drawing.Imaging.ImageFormat]::Png)
        $pngBytes = $pngStream.ToArray()
    }
    finally {
        $pngStream.Dispose()
    }

    $iconStream = [System.IO.File]::Create($iconPath)
    try {
        $writer = [System.IO.BinaryWriter]::new($iconStream)
        try {
            $writer.Write([uint16]0)
            $writer.Write([uint16]1)
            $writer.Write([uint16]1)
            $writer.Write([byte]0)
            $writer.Write([byte]0)
            $writer.Write([byte]0)
            $writer.Write([byte]0)
            $writer.Write([uint16]1)
            $writer.Write([uint16]32)
            $writer.Write([uint32]$pngBytes.Length)
            $writer.Write([uint32]22)
            $writer.Write($pngBytes)
        }
        finally {
            $writer.Dispose()
        }
    }
    finally {
        $iconStream.Dispose()
    }
}
finally {
    $iconBitmap.Dispose()
    $sourceImage.Dispose()
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = (Get-Command powershell.exe).Source
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$((Resolve-Path -LiteralPath $StartScriptPath).Path)`""
$shortcut.WorkingDirectory = Split-Path -Parent (Resolve-Path -LiteralPath $StartScriptPath)
$shortcut.IconLocation = "$iconPath,0"
$shortcut.Description = "Start Local AI services"
$shortcut.Save()

Write-Host "Created icon: $iconPath"
Write-Host "Created shortcut: $shortcutPath"