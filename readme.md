# Linux应急响应工具集-单机版（瞎命名）

## 项目简介

基于原工具改造，添加了服务器本地文件分析功能，适合对自己服务器进行监控分析使用。
请尊重原工具开发者的作品，请勿用于非法用途。
原工具地址[https://github.com/Rabb1tQ/emergency_response]
## 免责声明！！！
1.本工具因不便于自己服务器长期监控使用，因此进行二次开发，仅供学习使用，请勿用于非法用途。
若侵权请联系我删除。

## 修改内容
1.增加了本地文件分析功能。
2.调整了目录结构，便于本地文件分析。
3.调整了部分接口内容。
4.调整了服务器检测脚本的生成文件目录。

## 使用方式
1.给 emergency_response.sh赋权限
2.修改 templates/emergency_report_viewer.html中'http://localhost:5000/analyze'、'http://localhost:35000/list_reports'、'http://localhost:35000/report/${encodeURIComponent(selectedFile)}'的端口，与rules_engine.py中的端口保持一致 
3.启动 engine
