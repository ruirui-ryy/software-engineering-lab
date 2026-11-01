# 实验二设计工作区

项目：活动票务与报名系统。甲方：石祖屹；需求分析工程师：张辰曦。

- `planning/`：执行计划、业务缺口、需求追踪。
- `uml/`：PlantUML 源文件、PNG、SVG。类图、组件图、状态图、时序图，共四种。
- `ui/source/index.html`：可离线打开的交互式界面原型；`app.js`、`style.css` 为可编辑源文件。
- `ui/exports/`：基础界面及关键异常状态的 PNG。
- `checks/`：自动化检查结果、图片索引和人工可复核的检查范围。
- `tools/`：本地渲染、检查及打包脚本；PlantUML依赖按需下载，不随仓库保存。
- `report/`：实验报告 PDF 与可编辑 Markdown，张辰曦，学号241870077。

开始预览：直接打开 `ui/source/index.html` 可浏览；如需 CSV 下载，运行 `node tools/preview.cjs` 后访问 <http://127.0.0.1:4173>（当前 Chrome 会取消本地 file 页面发起的下载）。导航按示例身份展示。顶部“原型演示”入口是查看样例身份与异常状态的设计预览工具，不是产品授权机制。所有数据均为虚构示例，在当前页面内存中演示，不上传外部服务；跨页刷新会恢复样例，不是持久化业务系统。

实验一的 `requirements.md`、`chat.txt`、`report/report.md`、`.gitignore` 与标签保留原样。

提交包：`实验2_241870077_张辰曦.zip`。包内为实验报告.pdf、UML的PNG/PUML及UI界面的PNG，保留单一顶层目录。报告为11页纵向版。
