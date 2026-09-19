# H2S 自然语言建模 / Natural-language modeling skill

将你的想法变成可修改的 3D 模型、真实几何预览和 Bambu Lab H2S 切片工程，由你在 Bambu Studio 精修后决定是否打印。

这是供 **Codex 等支持技能文件的 AI 编程助手**使用的技能，不是独立聊天应用，也不内置 AI 模型。它提供工作流程、安装入口、检查工具和示例；复杂模型由 AI 根据需求编写 CAD/Blender 脚本。**目前不是一个无需外部软件、任意描述都能一键成功的生成器。**

## 下载后怎么用

1. 在 [Releases](https://github.com/chengtaoo/h2s-model-design/releases) 下载 `h2s-model-design.zip`，解压；也可点击 Code → Download ZIP。
2. 安装 [Python 3.11](https://www.python.org/downloads/) 和 [Bambu Studio](https://bambulab.com/en/download/studio)。在 Studio 中启用 H2S 对应喷嘴预设。
3. 在解压目录打开终端。精确零件建模建议运行：

```powershell
python scripts/install.py --with-cad
```

安装器将技能复制到个人 Codex skills 目录，并在技能内部创建独立 Python 环境、安装检查依赖和 CadQuery、运行自检。支持 `CODEX_HOME`，不会修改系统 Python 包。若电脑只有 Windows Python launcher，可以用 `py -3.11` 替代 `python`。

已有 Blender 并主要做造型时，运行 `python scripts/install.py`，再单独安装/指定 [Blender](https://www.blender.org/download/)。默认安装只含检查依赖，不包含建模软件。已有同名技能会停止；明确更新时使用 `--update`。复制但暂不装依赖可用 `--skip-deps`。

4. 新建 Codex 任务，输入：

> 使用 $h2s-model-design，设计一个长 160、宽 100、高 65 毫米的三格收纳盒，圆角，白色主体、蓝色文字，生成预览和 H2S 可切片工程。由我打开 Bambu Studio 后决定是否打印。

其他 AI 助手可读取 [SKILL.md](SKILL.md)，但自动发现/调用机制取决于客户端。首次任务让助手执行环境检查；Studio 未在 PATH 时，按 [安装与迁移说明](INSTALL.md) 指定本地位置。**不需要打印机访问码、AMS 或打印机 MCP。**

## 无打印机自测

也可以不安装技能，直接在下载目录创建环境并测试：

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements-check.txt
./.venv/Scripts/python.exe -m unittest discover -s tests -v
./.venv/Scripts/python.exe examples/make_demo.py --output work/demo
./.venv/Scripts/python.exe scripts/check_mesh.py work/demo/demo.stl --report work/demo/check.json
```

打开 `work/demo/preview.svg` 看真实网格的投影，`demo.stl` 可以导入 Studio。这个 20×30×40 mm 示例只证明几何生成与检查可用，**不是原生 H2S 工程或切片测试**。macOS/Linux 将解释器路径改成 `.venv/bin/python`。

安装 CadQuery 后可进一步运行 `examples/make_cad_tray.py`，生成带 2 mm 壁厚的开口收纳盘、STEP/STL 和几何 SVG。支持 `--length`、`--width`、`--height`、`--wall`、`--output` 参数；仍需 Studio 选择 H2S 配置并切片。

## 能得到什么

- 可编辑源文件和参数，后续用自然语言修改。
- STL/STEP/通用 3MF 等适当的模型文件和真实几何预览。
- 条件满足时由实际 Studio 生成并验证的 H2S 工程。
- 几何、预览和切片检查报告，明确未检查项。

H2S 标称空间 340×320×340 mm，实际摆盘还需考虑支撑、裙边和擦料塔。未知配置采用明确标注的 0.4 mm 喷嘴、PLA、0.20 mm 层高设计假设，不冒充实机读数。多色先做部件/逻辑耗材映射，用户之后选择实际耗材。

## 验证范围与限制

本地 Windows 已验证检查工具、迁移路径及安装流程，并使用 Blender 4.5.3 和 Bambu Studio 2.8.2.61 完成人物模型的单色、四色、七色 H2S 实际切片；未实体试打。仓库包含 Windows/macOS/Linux 自动检查工作流；是否通过请查看 [Actions](https://github.com/chengtaoo/h2s-model-design/actions)。CI 不安装 Bambu Studio，也不验证真实打印。

已知只有四个料槽时，可要求“最多四种耗材、单盘一次任务”，并使用 `scripts/inspect_3mf.py --max-filaments 4` 核对显式颜色映射。部件数可以多于耗材数。人物任务先审看头像近照，调整脸型、眼镜、五官关系和发型，再完成切片；详见 [人物与颜色预算](references/portraits-and-palettes.md)。参考照片和私人模型不包含在公开分发包中。

完整 Studio 工程导出、H2S 切片和颜色显示需要在目标机器使用实际软件验证。归档检查不等于可切片，几何封闭也不代表壁厚、强度或支撑正确。该技能区分 `geometry_only`、`project_created`、`slice_verified`、`studio_reviewed` 四级结果，不编造成功结果。

不上传模型、不连接打印机、不启动打印。不包含厂商软件、配置包或账号凭据。依赖和第三方软件遵循各自许可证。项目与 Bambu Lab、Blender、OpenAI 无官方关联。

## English quick start

This is a portable AI-agent skill, not a standalone text-to-3D application. Install Python 3.11 and Bambu Studio separately. Run `python scripts/install.py --with-cad` for a parameterized CAD workflow, or omit `--with-cad` and provide Blender. Start a new Codex task and invoke `$h2s-model-design`. No printer connection is required; the user reviews and prints in Bambu Studio. See [INSTALL.md](INSTALL.md) for dependencies, relative tool paths, and offline/migration notes. Actual H2S slicing must be validated on the target machine.

## License

[MIT](LICENSE). Issues with reproducible examples are welcome; remove credentials and private paths from diagnostic reports before posting.
