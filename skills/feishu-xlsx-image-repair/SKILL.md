---
name: feishu-xlsx-image-repair
description: Repair embedded images that become stretched or distorted when a Feishu-exported XLSX workbook is opened in WPS. Use when a user mentions Feishu Sheets/Excel exports, WPS image distortion, stretched receipts or screenshots, or restoring image proportions; do not use for ordinary spreadsheet formatting or PDF-only exports.
---

# Feishu XLSX Image Repair

Repair the image layer only. Preserve worksheets, cells, formulas, and the embedded image files.

## Required inputs

Before repairing, identify both files in the project:

1. The original Feishu-exported `.xlsx` workbook to repair.
2. A corresponding reference snapshot `.png`, downloaded from Feishu by choosing **Image**. Use it as the visual acceptance baseline after opening the repaired workbook in WPS.

If either file is absent or multiple candidates are ambiguous, ask the user to identify the correct files. Do not use a WPS screenshot as a substitute for the Feishu snapshot.

## Repair workflow

1. Inspect the source archive and confirm it has embedded files under `xl/media/`. If no embedded images exist, explain that this skill does not apply.
2. Pick a new output name: `<source-stem>_等比例修复.xlsx`. Never overwrite the source. If the output name already exists, ask whether to overwrite it or use another name.
3. Run the bundled script with the current environment's Python:

   ```bash
   python3 scripts/repair_image_anchors.py "SOURCE.xlsx" "OUTPUT_等比例修复.xlsx"
   ```

   Run it from the directory containing the chosen files, or pass paths relative to that directory. The script does not reuse coordinates from prior workbooks: on every run it reads the current workbook's sheet geometry, picture anchors, and embedded image dimensions.
4. Validate the output archive with `unzip -t`. Confirm that it retains the same number of `xl/media/` images as the source and that its drawing XML contains no negative `colOff` or `rowOff` values.
5. Give the repaired workbook path and reference snapshot path to the user. Ask them to open the repaired file in WPS and compare every receipt, invoice, and screenshot with the Feishu snapshot. Empty space around an image is expected; it preserves the original aspect ratio.

## Why this works

Feishu exports may use negative drawing-anchor offsets and picture boxes that fill their cells. WPS can interpret those boxes by stretching images. The script normalizes the offsets and fits each original image proportionally within its existing anchor area. The snapshot is a visual acceptance baseline, not a hard-coded coordinate template.

## If WPS still differs from the snapshot

Do not alter cells or replace images. Ask for a WPS screenshot showing the remaining mismatch, then adjust only the affected image anchors and revalidate the copied workbook.
