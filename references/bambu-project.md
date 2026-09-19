# H2S 原生工程与切片

STL 只表达网格；通用 3MF 不自动含 Studio 设置；Bambu 项目 3MF 用于精修；切片 `.gcode.3mf` 含机器路径，不替代可编辑项目，本阶段不发送打印。

优先复用本机 H2S 预设或用户提供的 H2S 基准工程。精确匹配 H2S 和喷嘴，不能套用 H2D。预设 `inherits` 交由 Studio 解析；CLI 如要求独立 JSON，完整解析继承并保留来源，不能仅复制叶子文件。

优先本机 CLI 导入、加载配置、导出工程；先核对本地帮助和输出语义。若 CLI 不支持颜色/工程创建，使用当前可用的 Studio UI 自动化。原生桌面控制不可用时不能假装已操作，继续交付模型并说明缺口。不手工拼 Bambu 私有元数据；模板方式必须具备已验证模板与回归测试，保持 object/instance/板引用、变换、耗材映射和新几何一致，不能遗留模板模型。

官方示例形态（必须用真实配置并核对本机版本）：
```
bambu-studio --load-settings "machine.json;process.json" --load-filaments "filament.json" --slice 0 --export-3mf sliced.3mf project.3mf
```
切片另存，不覆盖可编辑项目。保留厂商机型/起止代码，不从零生成机器运动指令。

多色装配需保留部件相对位置，不能把每个颜色体独立落床。工程逻辑耗材由用户之后映射实际料槽。摆盘余量、禁区、支撑和擦料塔以真实切片为准。

执行 `python scripts/inspect_3mf.py project.3mf --report project-check.json` 仅检查归档/XML/配置提示，不能授予切片合格状态。

真实切片需确认进程成功、日志无未处理错误、本轮新输出非空且含实际层路径、机器为 H2S 且喷嘴正确、全部部件存在且无越界/遗漏。保留必要日志，交付前排除账户信息。时间/耗材只引用切片器估算。

能使用 UI 时重新打开交付工程，检查尺寸、部件、配色及层预览；不能时注明仅 CLI 验证。`validation.json` 至少含 status、tools、assumptions、geometry_checks、profile_source、printer_model、nozzle_mm、project_inspection、slice_result、visual_review、limitations；缺失结果用 null 和说明，不伪造通过。

## Windows 2.8.2.61 本地验证经验

以下是该版本实测行为，不保证其他版本相同：

- `--load-assemble-list` 可把原位 STL 合为同一装配对象；不要逐个落床破坏相对位置。其 JSON 的 `plates[].objects[]` 包含 `path`、`count`、`filaments`、`assemble_index`、`pos_x`、`pos_y`、`pos_z`；测试中后五项为数组，同组部件使用相同 `assemble_index`。
- 指定 `--outputdir` 时，`--export-3mf` 传文件名而非绝对路径，避免输出目录被重复拼接。先输出工程，再对工程独立切片。
- 配置继承除 `inherits` 还有 `include`；被包含的模板可能没有 `type` 字段，不应因此丢弃。H2S 预设中的多个喷嘴变体不等于多个物理挤出机；按字段语义选择标准/高流量变体，不要凭数组长度截断未知字段。
- Windows 启动器的标准输出可能为空；不能凭无日志判定成功或失败。结合返回码、本轮生成的 `result.json` 和实际输出文件核验。工程导出和切片可能覆盖同一个 `result.json`，分别保存或检查最后结果确实含 `sliced_plates`。
- 切片结果应含非空实际 G-code、层信息以及与当前模型一致的三角面数。若有 G-code MD5 文件则核对。`warning_message`、各耗材用量、单盘对象数量均需检查；空的导出成功结果不等于切片成功。
- 部件耗材映射从 `model_settings.config` 的 `part/metadata` 读取。切片后可能多出对象级 `extruder`，不能把它误当成新增部件。

本地已完成 Blender 4.5.3 → 网格检查 → Bambu Studio 2.8.2.61 H2S 原生工程 → 单色/四色/七色实际切片。这个结果证明测试流程可行，不证明任意人物模型的相似度、实体强度或用户机器的料槽配置。公开仓库不包含测试使用的人物照片或私人模型。

官方依据（2026-09-18 查阅）：
- https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage
- https://github.com/bambulab/BambuStudio
- https://bambulab.com/it/support/buying-guide
