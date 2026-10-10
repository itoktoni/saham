' Kolektor labarugi pasar (background, detached).
Option Explicit
Dim sh, dir
Set sh = CreateObject("WScript.Shell")
dir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = dir
On Error Resume Next
sh.Run "pythonw """ & dir & "\scripts\collect-labarugi-pasar.py"" --repair", 0, False
