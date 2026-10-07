param(
  [string]$Title = "力扣提醒",
  [string]$Body = ""
)
try {
  [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
  [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
  $esc = { param($s) ($s -replace '&','&amp;' -replace '<','&lt;' -replace '>','&gt;') }
  $t = & $esc $Title
  $b = & $esc $Body
  $xmlStr = '<toast><visual><binding template="ToastGeneric"><text>' + $t + '</text><text>' + $b + '</text></binding></visual></toast>'
  $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
  $xml.LoadXml($xmlStr)
  $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
  [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('力扣刷题').Show($toast)
  Write-Output "TOAST_OK"
} catch {
  Write-Output ("TOAST_FAIL: " + $_.Exception.Message)
}
