' =====================================================================
'  Matikan Screener Praktis
'  Klik dua kali berkas ini untuk menghentikan aplikasi Screener.
' =====================================================================
Option Explicit
Dim fso, sh, dir, pidFile, f, pid
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
pidFile = dir & "\screener.pid"

If fso.FileExists(pidFile) Then
    Set f = fso.OpenTextFile(pidFile, 1)
    pid = Trim(f.ReadAll)
    f.Close
    If Len(pid) > 0 Then
        sh.Run "taskkill /PID " & pid & " /F", 0, True
        On Error Resume Next
        fso.DeleteFile pidFile, True
        On Error Goto 0
        MsgBox "Aplikasi Screener dihentikan.", vbInformation, "Screener Praktis"
    End If
Else
    MsgBox "Aplikasi Screener tidak sedang berjalan.", vbInformation, "Screener Praktis"
End If
