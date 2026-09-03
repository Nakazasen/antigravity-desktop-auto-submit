Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
projectRoot = fso.GetParentFolderName(currentDir)
daemonPath = projectRoot & "\scripts\antigravity_auto_submit_daemon.py"

' Kiem tra xem daemon da chay hay chua (tranh chay trung lap nhieu lan)
Set objWMI = GetObject("winmgmts:\\.\root\cimv2")
Set colProcesses = objWMI.ExecQuery("SELECT * FROM Win32_Process WHERE CommandLine LIKE '%antigravity_auto_submit_daemon.py%'")

If colProcesses.Count > 0 Then
    MsgBox "Antigravity Auto-Submit Daemon da dang chay san trong he thong!" & vbCrLf & _
           "(Dang co " & colProcesses.Count & " tien trinh hoat dong)", 64, "Antigravity Auto-Submit"
Else
    cmd = "py -3 -u """ & daemonPath & """"
    WshShell.Run cmd, 0, False
    MsgBox "Antigravity Desktop 2.0 Auto-Submitter da duoc khoi dong chay ngam thanh cong!", 64, "Antigravity Auto-Submit"
End If
