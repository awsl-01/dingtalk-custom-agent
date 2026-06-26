' 钉钉机器人管理后台 - 静默启动脚本
' 放入启动文件夹实现开机自启

Set WshShell = CreateObject("WScript.Shell")

' 切换到项目目录
WshShell.CurrentDirectory = "D:\claude"

' 启动后端服务（隐藏窗口）
WshShell.Run "cmd /c D:\miniconda\python.exe -m uvicorn web.app:app --host 0.0.0.0 --port 8913", 0, False

' 等待后端启动
WScript.Sleep 3000

' 启动前端（如果需要开发模式，取消下面注释）
' WshShell.Run "cmd /c cd /d D:\claude\web-frontend && npm run dev", 0, False
