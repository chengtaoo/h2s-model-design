# Tripo 图生 3D 与 H2S

用户明确要求 Tripo 或提供已有 Tripo 模型时读取。不得把本次授权当作所有未来用户的云端上传或付费授权。

## 分工与相似度

Tripo 生成真实网格和贴图，轻量 Python 程序检查/修改网格，Bambu Studio 负责物理耗材涂色与 H2S 切片；这条默认路线不需要 Blender。保留原始 GLB；后处理可重跑，不因改变尺寸或配色重复付费生成。用真实模型分别渲染原贴图、无贴图头像、最终有限色版本。不要把贴图里的眼睛/阴影误认为几何细节。单图不可见的背部由模型推断。

官方资料（实现时重新核对）：
- [中国区 V3 文档](https://developers.tripo3d.com/zh/docs/generation-image-to-model/standard)
- [官方 CLI](https://developers.tripo3d.com/en/docs/cli)：提供 `tripo mcp`；不是 H2S 切片器。
- [格式转换](https://developers.tripo3d.ai/en/docs/models-convert)：3MF 标注单色，顶点颜色参数仅适用于 OBJ/GLTF。
- [计费](https://developers.tripo3d.com/zh/pricing)：API 与网页端积分独立，先查余额。

2026-09 实测：CLI 0.5.1 的 `examples/print` 彩色 3MF 示例与转换接口文档矛盾。不能据此声称 `--for print` 已保留四色。纹理对有限色分配有用，不能照搬“打印不需要纹理”的单色建议。

## 依赖与凭据

直接 API 客户端 `scripts/tripo_api.py` 仅需 Python 标准库，不强制安装 SDK/CLI。可选 CLI 需要 Node.js >=20：`npm install -g tripo-cli@0.5.1`。Windows 可以调用 `tripo.cmd`，无需放宽执行策略。需要隔离安装时用 `npm install --prefix <tools-dir> tripo-cli@0.5.1`。

环境变量 `TRIPO_API_KEY` 存 API key，`TRIPO_REGION=cn` 对应中国区；CLI 全球区为 `ov`，本技能 Python 客户端参数为 `--region global`。中国区 API 为 `https://openapi.tripo3d.com/v3`，全球区为 `https://openapi.tripo3d.ai/v3`。密钥绑定区域；401 时先核对区域，不要重复付费提交。`tcli_` client ID 不是认证密钥。

不要把密钥放在命令参数、脚本、截图、报告、README 或 Git 中。可在本机交互终端通过隐藏输入设定进程变量：

```powershell
$secret = Read-Host 'Tripo API key' -AsSecureString
$env:TRIPO_API_KEY = [System.Net.NetworkCredential]::new('', $secret).Password
$env:TRIPO_REGION = 'cn'
python scripts/tripo_api.py --region cn balance
```

任务结束可 `Remove-Item Env:TRIPO_API_KEY`。这只是进程环境，未来新进程需重新配置或使用操作系统凭据管理；不要假装已永久安装密钥。

## 一次提交、可恢复下载

```text
python scripts/tripo_api.py --region cn generate --image reference.png --job work/job.json --allow-paid-generation
python scripts/tripo_api.py --region cn fetch --job work/job.json --output work/raw --wait-seconds 50
```

示例高质量预设使用 H3.1、detailed 几何和贴图、原图颜色优先、关闭自动改图。查询当日价格后设置本次测试上限；该预设当时预计 60 积分。用户要求高相似度时避免默认低模 P 系列。不要随意填未文档化的参数。保存任务 ID、输入哈希、参数、余额差和实际消费，不保存临时签名下载 URL。

客户端在付费提交前创建记录；若中断后只有 `submitting`，需通过官方账户历史找回任务，不能删除记录后盲目重交。网络轮询失败只能重查现有任务，不能重新生成。下载 URL 短时有效，过期后重新查询；下载请求不要附带 API 密钥。

## 进入本地打印处理

1. `python scripts/extract_glb.py --input model.glb --output work/extracted --height 150`：直接读取 GLB，转换到毫米并提取真实网格、UV 采样与原始贴图。仅支持一个网格、一张基础颜色贴图；不支持的结构明确停止。`--rotate-z` 可按真实预览调整，不假定所有来源都朝 +X。无需 Blender。
2. 检查接缝合并、朝向、封闭性、孤立壳体、薄发丝及底部。修改法线不应移动顶点；网格简化须以毫米公差、体积变化和头像预览核对。不得静默删除有意义的附件。底座需与模型有体积交叠。原图保留，结构修改记录参数。
3. 贴图量化成用户指定的物理色板，按真实网格预览检查肤色阴影、眼睛和嘴唇。合并噪声色块，避免把衣服阴影分配成唇色。不能只把图片减少成四色后称为可打印。

提供了可执行起点：`python scripts/prepare_portrait_mesh.py --input work/extracted --output work/portrait`（默认 0.02 mm 简化、3 mm 裁底、5 mm 底座；参数可改，孤立壳体会停止）。初始最近色量化常有杂色，必须检查。`python scripts/refine_portrait_palette.py --project work/portrait` 是暖肤色/橄榄棕衣服配色的特定启发式，**不是任意人像语义分割器**；其他衣服颜色应调整规则。可用 `--lip-box xmin ymin zmin xmax ymax zmax` 按当前模型坐标限制唇色，不能照抄另一个人的坐标。

`python scripts/render_mesh.py --input work/portrait/print-mesh.npz --output work/portrait/preview.png --palette "#857047" "#E8CBB3" "#242326" "#8C4048"` 直接渲染同一涂色网格。`--face` 头像近照，`--clay` 无色几何，`--back` 背面。也可渲染提取后的 `scaled-original.glb`。预览用 pyrender/OpenGL，需要可用显卡驱动；无 OpenGL 时明确报告预览未完成，不能用不相关图替代。无须可见桌面窗口。Blender 提取与渲染脚本仅保留为可选兼容工具，不在默认链路中调用。
4. 写出 `print-mesh.npz`：`vertices` 为毫米坐标 N×3，`faces` 为 M×3 索引，`labels` 为每个三角面 1..4 的耗材号。这个中间格式保留闭合整块几何，涂色无需拆成开放表面 STL。
5. 使用用户现有或本地工厂预设创建的 H2S 原生工程作为设置模板，模板需已有相同数量的 PLA 耗材。模板只读取 `project_settings.config`，不复用旧几何、预览或 G-code。

若新色板与模板不同，必须重新计算或显式提供 `--flush-matrix purge.json`，文件为 N×N 的 mm³ 数组，对角线 0。不能沿用不相关颜色的旧冲刷矩阵。Studio 的推荐值仍需实际材料验证；手工初始值要在交付说明中标注为未试打的假设。`smooth_palette.py --project ...` 可抑制小色点；`paint_regions.py --project ... --config ...` 支持记录可重跑的毫米坐标区域改色，这两种操作都不移动脸部顶点。

```text
python scripts/painted_3mf.py --mesh work/print-mesh.npz --template h2s-four-filaments.3mf --output portrait.3mf --palette "#857047" "#E8CBB3" "#242326" "#8C4048"
python scripts/inspect_3mf.py portrait.3mf --max-filaments 4 --report project-check.json
```

6. 用安装的 Studio 执行 `--slice 0 --outputdir <work-dir> --export-3mf portrait.gcode.3mf <portrait.3mf>`；输出文件名用 basename，不能把绝对输出路径拼入 export 参数。检查 `result.json` 的 `sliced_plates`、实际面数、1 盘、每色 `main_used_g > 0`、警告及 G-code 的真实层高/换料。只有通过才升为 `slice_verified`。
7. Bambu 原生涂色使用 `paint_color`，不属于通用 3MF 颜色标准。当前写入器仅实现完整三角面四槽编码（`4`、`8`、`0C`、`1C`），依据官方 BambuStudio v02.08.02.61 `Model.cpp` 和 `TriangleSelector.cpp`，并必须以实际切片验证。归档检查器检查部件与三角面树里的槽位，不能只数色板长度。

照片及模型留在用户本地交付目录；发布技能只提交可移植脚本、匿名合成测试和文档。打印支撑、擦料塔和冲刷量来自实际切片；预览纹理效果不是四色实物承诺。
