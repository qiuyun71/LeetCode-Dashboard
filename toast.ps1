param(
  [string]$Title = "力扣提醒",
  [string]$Body = ""
)
# Windows 只给「有开始菜单快捷方式背书的 AUMID」弹横幅，没有的会被静默压进通知中心。
# 所以优先借系统自带的 Windows PowerShell AUMID（它是注册过的，横幅能弹出来）；
# 失败再试自定义 AUMID；都不行就退回托盘气泡（NotifyIcon，系统给进程临时注册身份）。
function Fail($m) { Write-Output ("TOAST_FAIL: " + $m); exit 0 }
function Esc($s) { $s -replace '&','&amp;' -replace '<','&lt;' -replace '>','&gt;' }

try {
  [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
  [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
} catch { Fail ("WinRT 加载失败: " + $_.Exception.Message) }

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xmlStr = '<toast><visual><binding template="ToastGeneric"><text>' + (Esc $Title) +
  '</text><text>' + (Esc $Body) + '</text></binding></visual></toast>'
$xml.LoadXml($xmlStr)
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml

$ids = @(
  '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe',
  '力扣刷题'
)
$lastErr = ""
foreach ($id in $ids) {
  try {
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($id).Show($toast)
    Write-Output ("TOAST_OK:" + $id)
    exit 0
  } catch { $lastErr = $_.Exception.Message }
}

# 兜底：托盘气泡（Win10/11 会把它渲染成系统通知，无需注册身份）
try {
  Add-Type -AssemblyName System.Windows.Forms
  Add-Type -AssemblyName System.Drawing
  $ni = New-Object System.Windows.Forms.NotifyIcon
  $ni.Icon = [System.Drawing.SystemIcons]::Information
  $ni.Visible = $true
  $ni.BalloonTipTitle = $Title
  $ni.BalloonTipText = $Body
  $ni.ShowBalloonTip(10000)
  Start-Sleep -Seconds 11
  $ni.Dispose()
  Write-Output "TOAST_OK:balloon"
  exit 0
} catch { Fail ("通知失败: " + $lastErr + " / " + $_.Exception.Message) }
