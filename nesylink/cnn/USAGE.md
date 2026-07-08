# nesylink.cnn 使用说明

这个目录里的 CNN 模块负责一件事：

```text
160x128 游戏像素图 -> 识别地图组件、人物、怪物 -> 输出检测结果
```

它不负责规划，也不负责决定下一步动作。

## 1. 输入

模型输入是一张 RGB 图片：

```text
图片大小: 160 x 128
通道: RGB
地图网格: 10 x 8
每个格子: 16 x 16 pixels
```

训练数据是一对文件：

```text
xxx.png   游戏画面
xxx.json  对应标签
```

例如：

```text
nesylink/cnn/generated/retrain/train/train_0000.png
nesylink/cnn/generated/retrain/train/train_0000.json
```

## 2. 输出

CNN 最终输出 `ComponentBox` 列表。

每个 `ComponentBox` 表示识别到的一个组件：

```python
ComponentBox(
    kind="monster",
    tiles=((8, 2),),
    bbox_px=(128, 32, 144, 48),
    score=0.98,
)
```

字段含义：

```text
kind     组件类别
tiles    对应 grid 坐标
bbox_px  像素框，格式是 (x1, y1, x2, y2)
score    置信度
```

当前类别包括：

```text
floor
wall
player
chest
monster
trap
button
switch
gap
bridge
exit_normal
exit_locked
npc
unknown
```

输出规则：

```text
wall / chest / trap / button / switch / gap / bridge / npc
  按一个格子一个框输出。

player / monster
  按像素位置输出，不要求在格子正中心。

exit_normal / exit_locked
  分别表示不上锁的门和上锁的门。
  门是两格宽，所以两个门格会合并成一个框。
```

## 3. 生成数据集

生成 300 张训练图和 30 张测试图：

```bash
python -m nesylink.cnn.generate_dataset \
  --train-dir nesylink/cnn/generated/retrain/train \
  --test-dir nesylink/cnn/generated/retrain/test \
  --train-count 300 \
  --test-count 30 \
  --annotate-test \
  --labels \
  --sheet-out nesylink/cnn/generated/retrain/test_annotated_sheet.png
```

生成后先看这张总览图，确认标注框是否正确：

```text
nesylink/cnn/generated/retrain/test_annotated_sheet.png
```

## 4. 训练

训练命令：

```bash
python -m nesylink.cnn.train \
  --data-dir nesylink/cnn/generated/retrain/train \
  --pattern 'train_*.json' \
  --epochs 30 \
  --batch-size 12 \
  --out nesylink/cnn/checkpoints/tiny_hybrid_cnn_retrain.pt \
  --preview-out nesylink/cnn/checkpoints/tiny_hybrid_cnn_retrain_preview.png \
  --device auto
```

训练完成后会得到：

```text
nesylink/cnn/checkpoints/tiny_hybrid_cnn_retrain.pt
nesylink/cnn/checkpoints/tiny_hybrid_cnn_retrain.weights.pt
```

后续接 Perception 时，一般加载：

```text
tiny_hybrid_cnn_retrain.weights.pt
```

训练日志里重点看：

```text
obj_acc  静态物体识别准确率
dyn+     player / monster 正样本响应，越高越好
dyn-     背景误响应，越低越好
```

## 5. 单张图片预测

对一张测试图做预测并画框：

```bash
python -m nesylink.cnn.infer_boxes \
  --image nesylink/cnn/generated/retrain/test/test_0000.png \
  --checkpoint nesylink/cnn/checkpoints/tiny_hybrid_cnn_retrain.weights.pt \
  --out nesylink/cnn/generated/retrain/test_0000_prediction.png \
  --threshold 0.50
```

输出图片：

```text
nesylink/cnn/generated/retrain/test_0000_prediction.png
```

如果预测框太少，可以降低 `--threshold`，例如 `0.30`。
如果错误框太多，可以提高 `--threshold`，例如 `0.70`。

## 6. 单张图片标注

如果已经有 `png/json`，可以用 JSON 给图片画标准答案框：

```bash
python -m nesylink.cnn.annotate_scene \
  --image nesylink/cnn/generated/retrain/test/test_0000.png \
  --json nesylink/cnn/generated/retrain/test/test_0000.json \
  --out nesylink/cnn/generated/retrain/test/test_0000_label.png \
  --labels
```

这一步不是模型预测，只是把标准答案画出来，方便检查数据集标签。
