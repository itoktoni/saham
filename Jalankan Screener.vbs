' =====================================================================
'  Jalankan Screener Praktis Saham IDX
'  Klik dua kali berkas ini. Aplikasi akan menyala dan peramban terbuka
'  sendiri. Untuk berhenti, lihat "Cara menutup" di bawah.
' =====================================================================
Option Explicit
Dim sh, fso, dir
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = dir

On Error Resume Next
' pythonw = tanpa jendela hitam.
sh.Run "pythonw """ & dir & "\app\app-screener.py""", 0, False
If Err.Number <> 0 Then
    Err.Clear
    ' fallback: python biasa, tetap disembunyikan (mode 0)
    sh.Run "python """ & dir & "\app\app-screener.py""", 0, False
End If
If Err.Number <> 0 Then
    MsgBox "Gagal menjalankan Python." & vbCrLf & _
           "Pastikan Python terpasang, atau jalankan app-screener.py langsung.", _
           vbExclamation, "Screener Praktis"
End If
