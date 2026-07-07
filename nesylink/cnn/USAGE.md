# nesylink.cnn 使用说明

这个目录只迁移 CNN 模块本身。它负责从 `160x128` 的游戏像素图里识别组件，输出 CNN 检测框；它不负责规划、不负责动作选择，也暂时不自动接入 `nesylink.vision`。

## 1. 文件结构

```text
nesylink/cnn/
  components.py                类别表、JSON 标签转换、检测框绘制
  model.py                     TinyHybridCNN 模型和输出解码
  generate_synthetic_scene.py  生成单张 synthetic 场景 PNG/JSON
  generate_dataset.py          批量生成 train/test 数据集
  annotate_scene.py            用 JSON 标签给图片画标注框
  export_map_png.py            从已有 map 导出 160x128 PNG
  train.py                     训练 TinyHybridCNN
  infer_boxes.py               加载 checkpoint，对单张图片画预测框
  checkpoints/                 已训练 checkpoint
  generated/                   默认生成数据目录，已在本目录 .gitignore 忽略
```

已迁移的 checkpoint：

```text
nesylink/cnn/checkpoints/tiny_hybrid_cnn_exit_split.pt
nesylink/cnn/checkpoints/tiny_hybrid_cnn_exit_split.weights.pt
nesylink/cnn/checkpoints/tiny_hybrid_cnn_exit_split_preview.png
```

## 2. 输入输出

输入图片：

```text
shape: (128, 160, 3)
type:  uint8 RGB
grid:  10 x 8
tile:  16 x 16 pixels
```

模型是 `TinyHybridCNN`，输出三项：

```text
tile_logits
  shape: (B, num_tile_classes, 8, 10)
  负责静态、格子对齐的组件

dynamic_heatmap_logits
  shape: (B, 2, 32, 40)
  负责 player / monster 的中心点

dynamic_box
  shape: (B, 8, 32, 40)
  负责 player / monster 的像素框
```

tile head 类别：

```text
floor, wall, player, chest, monster, trap, button, switch, gap, bridge, exit_normal, exit_locked, npc, unknown
```

训练时 `player` 和 `monster` 会从 tile label 里移除，交给 dynamic head 学，因为它们可能按像素偏移，不一定正好在格子中心。

最终解码输出是 `ComponentBox`：

```python
ComponentBox(
    kind="monster",
    tiles=((8, 2),),
    bbox_px=(128, 32, 144, 48),
    score=0.98,
)
```

`tiles` 是由像素框中心点换算出来的 grid 坐标：

```text
tile_x = center_x // 16
tile_y = center_y // 16
```

出口已经区分为 `exit_normal` 和 `exit_locked`，可以识别上锁和不上锁两类。

## 3. 生成一张样例图

```bash
.venv/bin/python -m nesylink.cnn.generate_synthetic_scene \
  --seed 7 \
  --out nesylink/cnn/generated/synthetic_seed7.png
```

会同时生成：

```text
nesylink/cnn/generated/synthetic_seed7.png
nesylink/cnn/generated/synthetic_seed7.json
```

给它画标注框：

```bash
.venv/bin/python -m nesylink.cnn.annotate_scene \
  --image nesylink/cnn/generated/synthetic_seed7.png \
  --json nesylink/cnn/generated/synthetic_seed7.json \
  --out nesylink/cnn/generated/synthetic_seed7_annotated.png \
  --labels
```

## 4. 生成训练集和测试集

```bash
.venv/bin/python -m nesylink.cnn.generate_dataset \
  --train-dir nesylink/cnn/generated/train \
  --test-dir nesylink/cnn/generated/test \
  --train-count 300 \
  --test-count 30 \
  --annotate-test \
  --labels \
  --sheet-out nesylink/cnn/generated/test_annotated_sheet.png
```

生成后建议先看：

```text
nesylink/cnn/generated/test_annotated_sheet.png
```

确认标注框没问题，再开始训练。

## 5. 训练

```bash
.venv/bin/python -m nesylink.cnn.train \
  --data-dir nesylink/cnn/generated/train \
  --pattern 'train_*.json' \
  --epochs 30 \
  --batch-size 12 \
  --out nesylink/cnn/checkpoints/tiny_hybrid_cnn_exit_split.pt \
  --preview-out nesylink/cnn/checkpoints/tiny_hybrid_cnn_exit_split_preview.png \
  --device cpu
```

训练脚本会保存两个 checkpoint：

```text
tiny_hybrid_cnn_exit_split.pt
  完整 checkpoint，包含 epoch、optimizer、args 等训练信息。

tiny_hybrid_cnn_exit_split.weights.pt
  纯模型权重，后续接 Perception 时优先加载这个。
```

## 6. 单张图片预测可视化

```bash
.venv/bin/python -m nesylink.cnn.infer_boxes \
  --image nesylink/cnn/generated/test/test_0000.png \
  --checkpoint nesylink/cnn/checkpoints/tiny_hybrid_cnn_exit_split.weights.pt \
  --out nesylink/cnn/generated/test_0000_cnn_prediction.png \
  --threshold 0.50
```

这个命令会把 CNN 预测出来的 `ComponentBox` 画到图片上，并打印预测框数量。

## 7. vision adapter 详细写法

当前只迁移 CNN，所以没有直接改 `nesylink.vision`。后续如果要真的让 agent 用 CNN，需要额外写一个 vision adapter。这个 adapter 的职责是：

```text
raw obs 像素图
  -> crop/validate 成 (128, 160, 3)
  -> TinyHybridCNN forward
  -> component_boxes_from_hybrid_output 解码成 ComponentBox
  -> 后处理 player / monster 重复框
  -> 组装成项目已有的视觉输出结构
```

在当前 `nesylink` 代码里，推荐先输出 `PixelObservation`，因为 `student_agent/agent.py` 已经在用：

```python
from nesylink.vision import PixelObservation, classify_frame
```

建议新文件位置：

```text
nesylink/vision/cnn_classifier.py
```

先不要覆盖旧的 `classify_frame`。可以新增 `classify_frame_cnn`，调通之后再决定 agent 要不要切过去。

### 7.1 输出契约

如果接当前 `nesylink.vision.PixelObservation`，输出应该长这样：

```python
PixelObservation(
    grid=(
        ("floor", "wall", ...),
        ...
    ),
    tiles=(TileObservation(...), ...),
    player=EntityObservation(...) | None,
    monsters=(EntityObservation(...), ...),
    entities=(EntityObservation(...), ...),
)
```

字段含义：

```text
grid
  8 x 10 的字符串网格。每个位置是 floor / wall / chest / trap / exit_locked 等。

tiles
  每个格子的 TileObservation，给 grid 的每个 tile 一个 confidence。

player
  玩家实体，包含 bbox、center_px、tile、confidence。

monsters
  monster 实体列表。

entities
  player + monsters。静态物体不需要放进 entities，静态物体放 grid/tiles 里。
```

重要约定：

```text
exit_normal / exit_locked
  在 PixelObservation 里保持这两个 kind，不要合并成 exit。

player / monster
  用 dynamic head 的像素框结果，不要用 tile head。

静态物体
  用 tile head，写进 grid/tiles。
```

### 7.2 adapter 代码骨架

下面是推荐写法，核心逻辑已经列出来了。真实实现时可以直接按这个拆函数。

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from nesylink.core.constants import GRID_HEIGHT, GRID_WIDTH, TILE_SIZE
from nesylink.vision.pixel_classifier import (
    EntityObservation,
    PixelObservation,
    TileObservation,
    classify_frame as classify_frame_legacy,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKPOINT = PACKAGE_ROOT / "cnn" / "checkpoints" / "tiny_hybrid_cnn_exit_split.weights.pt"
OBS_HEIGHT = GRID_HEIGHT * TILE_SIZE
OBS_WIDTH = GRID_WIDTH * TILE_SIZE

STATIC_SKIP_KINDS = {"floor", "player", "monster"}
DYNAMIC_KINDS = {"player", "monster"}


class CnnClassifierUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class CnnDetection:
    kind: str
    tile: tuple[int, int]
    bbox: tuple[int, int, int, int]
    center_px: tuple[float, float]
    confidence: float


@dataclass
class CnnFrameResult:
    observation: PixelObservation
    detections: tuple[CnnDetection, ...]
    fallback_reason: str | None = None


def classify_frame_cnn(frame: np.ndarray) -> PixelObservation:
    return classify_frame_cnn_debug(frame).observation


def classify_frame_cnn_debug(frame: np.ndarray) -> CnnFrameResult:
    try:
        detections = _get_detector().detect(frame)
    except CnnClassifierUnavailable as exc:
        return CnnFrameResult(
            observation=classify_frame_legacy(frame),
            detections=(),
            fallback_reason=str(exc),
        )

    if not any(det.kind == "player" for det in detections):
        return CnnFrameResult(
            observation=classify_frame_legacy(frame),
            detections=detections,
            fallback_reason="cnn did not detect player",
        )

    return CnnFrameResult(
        observation=_detections_to_observation(detections),
        detections=detections,
    )
```

这里的设计重点是：CNN 能用就用 CNN；CNN 不可用时退回旧的颜色规则 `classify_frame`，这样不会因为没装 PyTorch 或 checkpoint 路径不对直接把 agent 弄崩。

### 7.3 Detector 加载和推理

Detector 建议做成全局懒加载：第一次调用时加载 checkpoint，之后复用同一个模型。

```python
_CNN_DETECTOR: CnnDetector | None = None


@dataclass
class CnnDetector:
    model: Any
    torch: Any
    device: Any
    component_classes: tuple[str, ...]
    dynamic_boxes_from_output: Any
    tile_threshold: float
    dynamic_threshold: float
    dynamic_top_k: int
    monster_max_count: int
    nms_iou_threshold: float

    def detect(self, frame: np.ndarray) -> tuple[CnnDetection, ...]:
        obs = _map_only(frame)
        array = obs.astype(np.float32) / 255.0
        tensor = self.torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0).to(self.device)

        with self.torch.no_grad():
            output = self.model(tensor)

        static = self._decode_tile_head(output["tile_logits"])
        dynamic = self._decode_dynamic_head(output)
        detections = static + dynamic
        return tuple(_postprocess(detections, self.monster_max_count, self.nms_iou_threshold))

    def _decode_tile_head(self, tile_logits: Any) -> list[CnnDetection]:
        probs = self.torch.softmax(tile_logits, dim=1)[0].detach().cpu()
        scores, class_ids = probs.max(dim=0)
        detections: list[CnnDetection] = []

        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                score = float(scores[y, x])
                class_id = int(class_ids[y, x])
                kind = self.component_classes[class_id]
                if score < self.tile_threshold or kind in STATIC_SKIP_KINDS:
                    continue

                left = x * TILE_SIZE
                top = y * TILE_SIZE
                right = left + TILE_SIZE
                bottom = top + TILE_SIZE
                detections.append(
                    CnnDetection(
                        kind=kind,
                        tile=(x, y),
                        bbox=(left, top, right, bottom),
                        center_px=((left + right) * 0.5, (top + bottom) * 0.5),
                        confidence=score,
                    )
                )
        return detections

    def _decode_dynamic_head(self, output: dict[str, Any]) -> list[CnnDetection]:
        boxes = self.dynamic_boxes_from_output(
            output["dynamic_heatmap_logits"],
            output["dynamic_box"],
            min_score=self.dynamic_threshold,
            top_k=self.dynamic_top_k,
        )[0]

        detections: list[CnnDetection] = []
        for box in boxes:
            if box.kind not in DYNAMIC_KINDS:
                continue
            left, top, right, bottom = box.bbox_px
            center = ((left + right) * 0.5, (top + bottom) * 0.5)
            detections.append(
                CnnDetection(
                    kind=box.kind,
                    tile=_pixel_to_tile(center),
                    bbox=(left, top, right, bottom),
                    center_px=center,
                    confidence=float(box.score),
                )
            )
        return detections
```

加载函数：

```python
def _get_detector() -> CnnDetector:
    global _CNN_DETECTOR
    if _CNN_DETECTOR is not None:
        return _CNN_DETECTOR

    checkpoint_path = Path(os.environ.get("NESYLINK_CNN_CHECKPOINT", str(DEFAULT_CHECKPOINT)))
    if not checkpoint_path.exists():
        raise CnnClassifierUnavailable(f"checkpoint not found: {checkpoint_path}")

    try:
        import torch
        from nesylink.cnn.components import COMPONENT_CLASSES
        from nesylink.cnn.model import TinyHybridCNN, dynamic_boxes_from_output
    except ImportError as exc:
        raise CnnClassifierUnavailable("PyTorch or nesylink.cnn is unavailable") from exc

    device_name = os.environ.get("NESYLINK_CNN_DEVICE", "cpu")
    if device_name == "auto":
        device_name = "cuda" if torch.cuda.is_available() else "cpu"
    if device_name == "cuda" and not torch.cuda.is_available():
        raise CnnClassifierUnavailable("CUDA requested but unavailable")
    device = torch.device(device_name)

    model = TinyHybridCNN().to(device)
    try:
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    except TypeError:
        checkpoint = torch.load(checkpoint_path, map_location=device)

    state_dict = checkpoint.get("model_state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
    model.load_state_dict(state_dict)
    model.eval()

    _CNN_DETECTOR = CnnDetector(
        model=model,
        torch=torch,
        device=device,
        component_classes=tuple(COMPONENT_CLASSES),
        dynamic_boxes_from_output=dynamic_boxes_from_output,
        tile_threshold=float(os.environ.get("NESYLINK_CNN_TILE_THRESHOLD", "0.50")),
        dynamic_threshold=float(os.environ.get("NESYLINK_CNN_DYNAMIC_THRESHOLD", "0.60")),
        dynamic_top_k=int(os.environ.get("NESYLINK_CNN_DYNAMIC_TOP_K", "12")),
        monster_max_count=int(os.environ.get("NESYLINK_CNN_MONSTER_MAX", "5")),
        nms_iou_threshold=float(os.environ.get("NESYLINK_CNN_NMS_IOU", "0.30")),
    )
    return _CNN_DETECTOR
```

### 7.4 detections 转 PixelObservation

转换规则：

```text
1. grid 先全填 floor。
2. 静态物体写进 static_by_tile。
3. player / monster 写进 dynamic_by_tile。
4. 同一个 tile 有多个预测时，保留 confidence 最高的。
5. 输出 grid 时 dynamic 优先覆盖 static。
6. entities 只放 player 和 monster。
```

代码骨架：

```python
def _detections_to_observation(detections: tuple[CnnDetection, ...]) -> PixelObservation:
    static_by_tile: dict[tuple[int, int], CnnDetection] = {}
    dynamic_by_tile: dict[tuple[int, int], CnnDetection] = {}

    for det in detections:
        bucket = dynamic_by_tile if det.kind in DYNAMIC_KINDS else static_by_tile
        old = bucket.get(det.tile)
        if old is None or det.confidence > old.confidence:
            bucket[det.tile] = det

    rows: list[list[str]] = [["floor" for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
    tiles: list[TileObservation] = []

    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            tile = (x, y)
            det = dynamic_by_tile.get(tile) or static_by_tile.get(tile)
            kind = det.kind if det is not None else "floor"
            confidence = det.confidence if det is not None else 1.0
            rows[y][x] = kind
            tiles.append(
                TileObservation(
                    kind=kind,
                    tile=tile,
                    confidence=confidence,
                    scores={kind: confidence},
                )
            )

    entities = tuple(
        EntityObservation(
            kind=det.kind,
            bbox=det.bbox,
            center_px=det.center_px,
            tile=det.tile,
            confidence=det.confidence,
        )
        for det in sorted(dynamic_by_tile.values(), key=lambda item: (item.kind != "player", item.tile[1], item.tile[0]))
    )
    player = next((entity for entity in entities if entity.kind == "player"), None)
    monsters = tuple(entity for entity in entities if entity.kind == "monster")

    return PixelObservation(
        grid=tuple(tuple(row) for row in rows),
        tiles=tuple(tiles),
        player=player,
        monsters=monsters,
        entities=entities,
    )
```

### 7.5 后处理和工具函数

player 只保留最高分的一个；monster 可能多个，所以做 NMS。

```python
def _postprocess(
    detections: list[CnnDetection],
    monster_max_count: int,
    nms_iou_threshold: float,
) -> list[CnnDetection]:
    static = [det for det in detections if det.kind not in DYNAMIC_KINDS]
    players = [det for det in detections if det.kind == "player"]
    monsters = [det for det in detections if det.kind == "monster"]

    out = list(static)
    if players:
        out.append(max(players, key=lambda det: det.confidence))
    out.extend(_nms(monsters, nms_iou_threshold)[:monster_max_count])
    return out


def _nms(detections: list[CnnDetection], threshold: float) -> list[CnnDetection]:
    ordered = sorted(detections, key=lambda det: det.confidence, reverse=True)
    kept: list[CnnDetection] = []
    for det in ordered:
        if all(_iou(det.bbox, old.bbox) < threshold for old in kept):
            kept.append(det)
    return kept


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    left = max(a[0], b[0])
    top = max(a[1], b[1])
    right = min(a[2], b[2])
    bottom = min(a[3], b[3])
    intersection = max(0, right - left) * max(0, bottom - top)
    if intersection == 0:
        return 0.0
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    union = area_a + area_b - intersection
    return float(intersection / union) if union > 0 else 0.0


def _map_only(frame: np.ndarray) -> np.ndarray:
    arr = np.asarray(frame)
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError(f"expected RGB frame with shape (H, W, 3), got {arr.shape}")
    if arr.shape[0] < OBS_HEIGHT or arr.shape[1] < OBS_WIDTH:
        raise ValueError(f"frame is too small for NesyLink map: {arr.shape}")
    return arr[:OBS_HEIGHT, :OBS_WIDTH, :3]


def _pixel_to_tile(center_px: tuple[float, float]) -> tuple[int, int]:
    x, y = center_px
    tile_x = min(GRID_WIDTH - 1, max(0, int(x // TILE_SIZE)))
    tile_y = min(GRID_HEIGHT - 1, max(0, int(y // TILE_SIZE)))
    return tile_x, tile_y
```

### 7.6 怎么切到 agent 里

调通以后可以在 `nesylink/vision/__init__.py` 暴露新函数：

```python
from .cnn_classifier import classify_frame_cnn, classify_frame_cnn_debug
```

然后在 agent 里临时切换：

```python
from nesylink.vision import PixelObservation, classify_frame_cnn as classify_frame
```

更稳的做法是保留两个入口：

```python
from nesylink.vision import classify_frame
from nesylink.vision.cnn_classifier import classify_frame_cnn_debug

result = classify_frame_cnn_debug(obs)
vision = result.observation
if result.fallback_reason is not None:
    print("CNN fallback:", result.fallback_reason)
```

### 7.7 如果接旧版 Perception

如果不是接 `PixelObservation`，而是接旧 `student_agent/state.py` 里的 `Perception`，映射规则稍微不同：

```text
exit_normal / exit_locked
  Perception.grid 里都写成 "exit"。
  locked 的位置额外放进 perception.locked_exits。

player
  perception.player = player_tile
  perception.player_marker_px = player_bbox_center

monster / chest / trap / button / switch / unknown
  除了写 grid，还分别写入 monsters / chests / traps / buttons / switches / unknowns。
```

旧版 Perception 的组装逻辑大概是：

```python
def build_perception_from_detections(detections: list[CnnDetection]) -> Perception:
    grid = [["floor" for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
    player = None
    player_marker_px = None
    chests = []
    monsters = []
    traps = []
    buttons = []
    switches = []
    exits = []
    locked_exits = []
    unknowns = []

    for det in detections:
        x, y = det.tile
        if det.kind == "exit_normal":
            grid[y][x] = "exit"
            exits.append(det.tile)
        elif det.kind == "exit_locked":
            grid[y][x] = "exit"
            exits.append(det.tile)
            locked_exits.append(det.tile)
        else:
            grid[y][x] = det.kind

        if det.kind == "player":
            player = det.tile
            player_marker_px = (round(det.center_px[0]), round(det.center_px[1]))
        elif det.kind == "monster":
            monsters.append(det.tile)
        elif det.kind == "chest":
            chests.append(det.tile)
        elif det.kind == "trap":
            traps.append(det.tile)
        elif det.kind == "button":
            buttons.append(det.tile)
        elif det.kind == "switch":
            switches.append(det.tile)
        elif det.kind == "unknown":
            unknowns.append(det.tile)

    return Perception(
        grid=grid,
        player=player,
        player_marker_px=player_marker_px,
        chests=chests,
        monsters=monsters,
        traps=traps,
        buttons=buttons,
        switches=switches,
        exits=exits,
        locked_exits=locked_exits,
        unknowns=unknowns,
    )
```

### 7.8 调试 checklist

```text
1. 先跑 infer_boxes.py，看预测框是否肉眼正确。
2. 再跑 classify_frame_cnn_debug(obs)，打印 fallback_reason。
3. 检查 player 是否一定能识别到；没有 player 时不要让 agent 硬走。
4. 检查 exit_normal / exit_locked 有没有被误合并。
5. 检查 monster 数量是否因为 heatmap top_k 太大而重复。
6. 检查 grid 中 dynamic 是否覆盖 static，比如玩家站在 exit 上时会遮挡出口。
7. 如果 CNN 漏检 player / monster，先调低 NESYLINK_CNN_DYNAMIC_THRESHOLD。
8. 如果静态物体误检多，调高 NESYLINK_CNN_TILE_THRESHOLD。
```

常用环境变量：

```text
NESYLINK_CNN_CHECKPOINT=nesylink/cnn/checkpoints/tiny_hybrid_cnn_exit_split.weights.pt
NESYLINK_CNN_DEVICE=cpu
NESYLINK_CNN_TILE_THRESHOLD=0.50
NESYLINK_CNN_DYNAMIC_THRESHOLD=0.60
NESYLINK_CNN_DYNAMIC_TOP_K=12
NESYLINK_CNN_MONSTER_MAX=5
NESYLINK_CNN_NMS_IOU=0.30
```
