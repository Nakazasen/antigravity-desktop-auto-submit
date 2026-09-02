Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
projectRoot = fso.GetParentFolderName(currentDir)
daemonPath = projectRoot & "\scripts\antigravity_auto_submit_daemon.py"

cmd = "py -3 -u """ & daemonPath & """"
WshShell.Run cmd, 0, False

MsgBox "Antigravity Desktop 2.0 Auto-Submitter đã được khởi động chạy ngầm thành công!", 64, "Antigravity Auto-Submit"
