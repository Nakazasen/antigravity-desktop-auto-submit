Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
projectRoot = fso.GetParentFolderName(currentDir)
daemonPath = projectRoot & "\scripts\antigravity_auto_submit_daemon.py"

' Kiem tra xem daemon da chay hay chua (tranh chay trung lap nhieu lan)
Set objWMI = GetObject("winmgmts:\\.\root\cimv2")
Set colProcesses = objWMI.ExecQuery("SELECT * FROM Win32_Process WHERE CommandLine LIKE '%antigravity_auto_submit_daemon.py%'")

If colProcesses.Count > 0 Then
    ans = MsgBox("Antigravity Auto-Submit Daemon da dang chay san trong he thong (" & colProcesses.Count & " tien trinh)." & vbCrLf & vbCrLf & _
                 "Ban co muon KHOI DONG LAI daemon de lam moi ket noi den Antigravity khong?", 36, "Antigravity Auto-Submit")
    If ans = 6 Then ' vbYes
        For Each objProc in colProcesses
            objProc.Terminate()
        Next
        WScript.Sleep 500
        cmd = "py -3 -u """ & daemonPath & """"
        WshShell.Run cmd, 0, False
        MsgBox "Da khoi dong lai Antigravity Auto-Submitter chay ngam thanh cong!", 64, "Antigravity Auto-Submit"
    End If
Else
    cmd = "py -3 -u """ & daemonPath & """"
    WshShell.Run cmd, 0, False
    MsgBox "Antigravity Auto-Submit da chay ngam. Mo Desktop va IDE nhu binh thuong; daemon se tu bam Submit.", 64, "Antigravity Auto-Submit"
End If
