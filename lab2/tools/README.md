# 复现工具

- `render-uml.ps1`：使用 Java 和 PlantUML 1.2026.0 渲染7张图为 PNG/SVG。无需外部在线渲染服务。
- `export-ui.cjs`：使用本机 Playwright 与 Chrome 导出所有清单场景并检查实际交互。默认路径对应本机；其他环境通过 `PLAYWRIGHT_MODULE` 和 `BROWSER_PATH` 指定。
- `verify.py`：检查基线文件/标签、需求覆盖、图片匹配，并生成图片预览索引和检查摘要。
- `preview.cjs`：`node lab2/tools/preview.cjs`，只在 `127.0.0.1:4173` 提供原型，支持 CSV 下载。关闭终端进程即停止；不公开到互联网。
- `build-report.py`：使用Codex bundled Python执行，从 `report/实验报告.md` 和现有图生成PDF，并以bundled Poppler渲染逐页检查图片；不会生成提交压缩包。报告中的界面图仅裁去预览栏、导航或页尾空白，不改变业务内容。

下载来源：<https://repo.maven.apache.org/maven2/net/sourceforge/plantuml/plantuml/1.2026.0/plantuml-1.2026.0.jar>。
PlantUML 官方命令行文档：<https://plantuml.com/command-line>。
渲染器遵循自身 GPL 许可证，工具依赖不是实验设计内容。不要将 jar 混入课程提交包。

当前示例为界面与设计技术验证。真正的数据库并发、服务端越权防护、故障回滚和 REQ-029 性能验收须在后续后端实现后执行。

打包：`python lab2/tools/package-submission.py --student-id 241870077 --name 张辰曦`。脚本只加入PDF、UML的PNG/PUML和UI图片，并验证ZIP及每个文件的哈希。
