# 本地环境

安装步骤、依赖清单、跨平台说明与相对路径示例见 [INSTALL.md](../INSTALL.md)。先用 `scripts/check_environment.py` 检查当前 Python 和软件位置；所有脚本引用从技能根目录解析，不依赖调用者当前目录。Windows 再用下述发现脚本补充查找。

执行 `scripts/discover_windows.ps1`，只读查找进程、卸载注册信息、常见路径和 PATH。不扫描账号配置。无结果不等于未安装：询问可执行文件路径或用户从 Studio 保存的空白 H2S 工程，不索取访问码。不要递归扫描整盘。

记录 Studio 和建模器版本，实际运行 `--help`，参数以本机版本为准。使用超时，不结束用户原有 Studio 进程；Windows 后台进程隐藏窗口。

只安装需要的后端，复用现有安装。CadQuery 采用项目专用 Python 环境及匹配的二进制包；不要修改 Hermes 等应用自己的 Python。网格助手需要 `trimesh`、`numpy`。Blender 官方入口 `blender --background --python script.py`，设置 Python 异常退出码，并核实当前 STL 导出 API。预览使用真实几何渲染器，不强制为 CAD 安装 Blender。

缺依赖时准备独立环境，大型软件优先便携部署，不能悄悄替换现有版本。网络受限时保留成果并报告缺口，不把未运行脚本称为验证成功。脚本与参数使用 UTF-8；命令正确引用中文和含空格路径。

官方来源（2026-09-18 已查阅，部署时核实版本）：
- https://cadquery.readthedocs.io/en/stable/
- https://developer.blender.org/docs/handbook/testing/python/
- https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage
- https://github.com/ahujasid/mcp-for-blender （可选社区 MCP）
