# 飞书 XLSX 图片等比例修复 / Feishu XLSX Image Repair

当飞书导出的 XLSX 文件在 WPS 中打开后，内嵌图片（如收据、发票或截图）被拉伸、变形时，使用此 Skill 将图片恢复为原始宽高比。

Use this Skill when embedded images in a Feishu-exported XLSX workbook—such as receipts, invoices, or screenshots—appear stretched or distorted in WPS. It restores each image's native aspect ratio.

## 适用范围 / When to use it

- 输入文件是从飞书表格导出的 `.xlsx`，并且压缩包中包含嵌入图片（`xl/media/`）。
- 在 WPS 中打开时，图片被拉伸、压扁或比例异常。
- 需要保留工作表、单元格、公式和原始图片文件。

- The input is a Feishu-exported `.xlsx` workbook with embedded images under `xl/media/`.
- Images look stretched, squashed, or otherwise distorted when opened in WPS.
- Worksheets, cells, formulas, and the original image files must remain unchanged.

不适用于普通表格排版调整、没有嵌入图片的工作簿，或仅处理 PDF 的需求。

This Skill is not for general spreadsheet formatting, workbooks without embedded images, or PDF-only tasks.

## 前置条件 / Prerequisites

准备以下文件：

1. 待修复的飞书导出 `.xlsx` 文件。
2. 对应的飞书 PNG 快照：在飞书中选择“下载为图片（Image）”得到。它用于在 WPS 中人工核验最终视觉效果，不会被脚本读取。

Prepare both of the following:

1. The original Feishu-exported `.xlsx` workbook to repair.
2. The corresponding PNG snapshot downloaded from Feishu by choosing **Image**. It is a visual reference for WPS verification; the script does not read it.

还需要 Python 3 和 Pillow：

Python 3 and Pillow are also required:

```bash
python3 -m pip install Pillow
```

## 使用方法 / Usage

不要覆盖原始工作簿。建议输出到一个新文件，例如 `<源文件名>_等比例修复.xlsx`。

Never overwrite the original workbook. Write to a new file, such as `<source-stem>_等比例修复.xlsx`.

在仓库根目录运行：

Run this command from the repository root:

```bash
python3 .codex/skills/feishu-xlsx-image-repair/scripts/repair_image_anchors.py "SOURCE.xlsx" "OUTPUT_等比例修复.xlsx"
```

例如 / Example:

```bash
python3 .codex/skills/feishu-xlsx-image-repair/scripts/repair_image_anchors.py "投流充值记录.xlsx" "投流充值记录_等比例修复.xlsx"
```

也可以在其他目录运行，但需传入正确的脚本路径和文件路径，例如：

```bash
python3 /path/to/repair_image_anchors.py "/path/to/SOURCE.xlsx" "/path/to/OUTPUT_等比例修复.xlsx"
```

You can run it from another directory as well, as long as the script path and workbook paths are correct.

## 工作原理 / How it works

脚本只处理 XLSX 内的图片绘图锚点：它读取每张图片的原始像素尺寸和所在单元格区域，将图片等比例缩放并居中放入原有区域，同时把锚点偏移量规范为非负值。它不会修改单元格数据、公式、工作表结构或替换图片文件。

The script changes only image drawing anchors inside the XLSX archive. It reads each image's native pixel dimensions and its existing cell area, fits the image proportionally and centers it within that area, and normalizes anchor offsets to non-negative values. It does not modify cell data, formulas, worksheet structure, or replace image files.

## 校验结果 / Verify the result

1. 检查输出工作簿的 ZIP 结构：

   Validate the output workbook's ZIP structure:

   ```bash
   unzip -t "OUTPUT_等比例修复.xlsx"
   ```

2. 确认输出文件仍保留与源文件相同数量的 `xl/media/` 图片。
3. 在 WPS 中打开输出文件，将每张收据、发票或截图与飞书 PNG 快照逐一对比。

   Confirm that the output contains the same number of images under `xl/media/` as the source. Then open it in WPS and compare every receipt, invoice, and screenshot against the Feishu PNG snapshot.

图片周围出现留白是正常现象：这是为了保留原始宽高比，而不是拉伸图片以填满原有区域。

Empty space around an image is expected. It preserves the original aspect ratio instead of stretching the image to fill the previous area.

## 常见问题 / Troubleshooting

| 现象 | 处理方式 |
| --- | --- |
| 脚本提示没有修复图片 | 确认源文件中存在 `xl/media/`，且图片使用的是双单元格锚点。 |
| 输出文件已存在 | 不要覆盖原文件；改用新名称，或在确认后手动处理旧输出文件。 |
| WPS 仍与飞书快照不一致 | 截取存在差异的 WPS 区域，仅针对对应图片锚点继续调整；不要修改单元格或替换图片。 |

| Issue | What to do |
| --- | --- |
| The script reports that no pictures were repaired | Confirm that the source contains `xl/media/` images and that the pictures use two-cell anchors. |
| The output file already exists | Do not overwrite the source. Choose a new output name, or handle the old output manually after confirming it is safe. |
| WPS still differs from the Feishu snapshot | Capture the mismatched area in WPS and adjust only the affected image anchors; do not alter cells or replace images. |
