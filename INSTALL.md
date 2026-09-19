# 安装、依赖与迁移

公开版提供自动安装入口：解压后在目录中运行 `python scripts/install.py --with-cad`，会复制技能、创建独立环境、安装 CAD 与检查依赖并运行自检。已有 Blender 用户可省略 `--with-cad`。`--destination` 指定目标技能目录，`--skip-deps` 仅复制，`--update` 明确允许更新已有技能。Bambu Studio 和 Blender 仍通过下面的官方渠道单独安装。手动安装步骤也保留如下。

## 需要哪些软件

| 组件 | 何时需要 | 安装与作用 |
|---|---|---|
| Python | 运行检查脚本、CadQuery 建模 | 推荐 Python 3.11，本技能检查工具已用该版本测试；从 https://www.python.org/downloads/ 安装 |
| numpy、trimesh | STL 几何检查 | 使用随附 requirements-check.txt 安装到独立环境 |
| Bambu Studio | 生成并验证最终 H2S 工程 | 从 https://bambulab.com/en/download/studio 安装支持 H2S 的版本；CLI 随 Studio 提供，不另装所谓 Bambu CLI 包 |
| CadQuery | 尺寸精确的零件、盒子、支架 | 可选建模后端，使用 requirements-cad.txt 安装；不需要另装 CAD 桌面程序 |
| Blender | 曲面、摆件、渲染或已有 Blender 工作流 | 从 https://www.blender.org/download/ 安装；CLI 与 Python 运行时随 Blender 提供 |
| OpenSCAD | 沿用用户已有 OpenSCAD 模型 | 可选，从 https://openscad.org/downloads.html 安装 |
| MCP、Node.js、AMS | 本阶段无强制依赖 | 不需要安装打印机 MCP 或连接打印机 |

建模后端至少选择一种。CadQuery 与 Blender 不要求同时安装。PNG 预览仍需可用渲染器，已有 CAD 渲染器可复用，Blender 是可选统一渲染方案。原生界面自动操作需要当前客户端提供对应工具；安装 Python 并不会自动获得桌面控制能力。

## 目录和路径规则

将整个 `h2s-model-design` 文件夹放进 Codex 的个人 skills 目录，或保留在指定技能位置。不要只复制 SKILL.md。保持 scripts、references 和依赖清单的相对位置。

以下示例先切换到技能目录，所有路径均相对该目录。任务调用时也可以直接指定脚本位置，但必须根据实际技能根目录解析。输入和报告相对路径按当前工作目录解释；环境配置中的相对软件路径则按配置文件所在目录解释。

迁移不复制 `.venv`、Python 缓存、临时模型或软件快捷方式。Python 虚拟环境不可保证移动后工作，应在目标电脑重建。完整离线部署需为目标操作系统及 Python 版本提前准备 wheel 包和官方应用安装包；本技能 ZIP 不包含大型应用或 Python 运行时。

## Windows 安装检查依赖

在技能目录打开 PowerShell：

```powershell
py -3.11 -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r ./requirements-check.txt
& ./.venv/Scripts/python.exe ./scripts/check_environment.py --report ./work/environment.json
```

若没有 `py`，使用已安装的 `python` 替代 `py -3.11`。无需激活环境，因此无需修改 PowerShell 执行策略。不要向其他应用自己的 Python 环境安装依赖。

选择 CadQuery 时，再执行：

```powershell
& ./.venv/Scripts/python.exe -m pip install -r ./requirements-cad.txt
& ./.venv/Scripts/python.exe -c "import cadquery as cq; assert cq.Workplane('XY').box(10,10,10).val().isValid(); print('CAD OK')"
```

检查脚本的 numpy/trimesh 版本已验证。公开版固定 CadQuery 2.8.0 和解析成功的 trame-vtk 版本以减少依赖回溯；安装后仍须运行上面的实体测试并记录实际版本。依赖下载包含较大的几何内核和可视化库，首次安装可能需要数分钟及数百 MB 下载。完整模型任务还需实际导出、预览和切片验证。安装遇到无匹配二进制包，先确认 Python/平台支持，勿盲目触发大型源码编译。

## 软件发现与指定位置

优先在 PATH 查找，也支持环境变量 `BAMBU_STUDIO_EXE`、`BLENDER_EXE`、`OPENSCAD_EXE`。这些是目标机器的本地设置，不写入技能源码。Windows 可补充运行 `scripts/discover_windows.ps1` 查找进程和安装注册信息。

也可自行创建 `tools.local.json`，例如以下便携目录结构：

```text
portable-workspace/
  tools.local.json
  tools/
    bambu-studio/bambu-studio.exe
    blender/blender.exe
  h2s-model-design/
```

对应配置：

```json
{
  "bambu_studio": "tools/bambu-studio/bambu-studio.exe",
  "blender": "tools/blender/blender.exe"
}
```

从技能目录检查：

```powershell
& ./.venv/Scripts/python.exe ./scripts/check_environment.py --config ../tools.local.json
```

此示例只演示路径布局，并非承诺任意安装版本都支持直接复制为便携软件。正常安装的软件可使用 PATH/环境变量。检查器只发现路径，不启动软件；下一步针对查到的可执行文件运行 `--help` 并核实版本。Blender 内置 Python 与 `.venv` 是两套环境，不默认共享已安装模块。

## 检查模型与工程

```powershell
& ./.venv/Scripts/python.exe ./scripts/check_mesh.py ./work/part.stl --report ./work/mesh-check.json
& ./.venv/Scripts/python.exe ./scripts/inspect_3mf.py ./work/project.3mf --report ./work/project-check.json
```

模型助手退出码：0 基础检查通过；2 模型存在检查失败；1 输入或运行错误。3MF 助手退出码：0 归档检查完成；1 错误。环境助手退出码 0 仅表示检查完成，缺少可选软件在报告中体现。任何检查器成功均不代替 H2S 实际切片。

## macOS / Linux

Python 助手不依赖 Windows；使用 `python3 -m venv .venv`，将示例中的解释器改为 `./.venv/bin/python`。安装对应系统的 Studio 与建模器，使用 PATH 或本地配置。Windows 发现脚本仅适用于 Windows，不在其他系统运行。基础检查与几何示例已通过 Windows/macOS/Linux CI；完整 CAD 安装在 Windows 实测，其他系统上的 CAD、Studio CLI 与渲染仍需验证。

## 目标机器验收

依次确认环境发现、所选后端创建实体、STL 尺寸及封闭性、真实几何预览、Studio H2S 预设、原生工程导出、实际切片。不要将软件路径找到或 Python 包安装成功当作端到端完成。几何可先离线生成；缺少 Studio 时明确交付状态未达到 slice_verified。
