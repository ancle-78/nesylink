from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CNN_DIR = Path(__file__).resolve().parent

from nesylink.core.constants import GRID_HEIGHT, GRID_WIDTH, MAP_PIXEL_HEIGHT, MAP_PIXEL_WIDTH
from nesylink.core.rendering import render_frame
from nesylink.core.state import PlayerState, tile_to_top_left_px
from nesylink.core.world.rooms import RoomManager


EDGE_EXIT_TILES = {
    "north": {(4, 0), (5, 0)},
    "south": {(4, GRID_HEIGHT - 1), (5, GRID_HEIGHT - 1)},
    "west": {(0, 3), (0, 4)},
    "east": {(GRID_WIDTH - 1, 3), (GRID_WIDTH - 1, 4)},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate one synthetic NesyLink scene PNG for CNN experiments.")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=CNN_DIR / "generated" / "synthetic_seed0.png")
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--full-frame", action="store_true")
    parser.add_argument(
        "--player-offset-px",
        nargs=2,
        type=int,
        metavar=("DX", "DY"),
        default=(0, 0),
        help="Move the rendered player by pixel offsets after room construction.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    payload = build_synthetic_room(rng)

    with tempfile.TemporaryDirectory(prefix="nesylink_cnn_scene_") as tmpdir:
        room_path = Path(tmpdir) / "synthetic_room.json"
        room_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        manager = RoomManager(room_path)
        room = manager.get_room(manager.start_room)
        player = PlayerState(position_px=tile_to_top_left_px(room.spawns[room.default_spawn_name]))
        apply_player_offset(player, tuple(args.player_offset_px))
        write_player_pixel_annotation(payload, player)
        frame = render_frame(room, player)

    image = frame if args.full_frame else frame[:MAP_PIXEL_HEIGHT, :MAP_PIXEL_WIDTH]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image).save(args.out)

    json_out = args.json_out
    if json_out is None:
        json_out = args.out.with_suffix(".json")
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"saved {args.out} shape={image.shape}")
    print(f"saved {json_out}")


def apply_player_offset(player: PlayerState, offset_px: tuple[int, int]) -> None:
    dx, dy = offset_px
    x, y = player.position_px
    max_x = MAP_PIXEL_WIDTH - player.size_px
    max_y = MAP_PIXEL_HEIGHT - player.size_px
    player.position_px = (
        float(max(0, min(max_x, x + dx))),
        float(max(0, min(max_y, y + dy))),
    )


def write_player_pixel_annotation(payload: dict[str, Any], player: PlayerState) -> None:
    left = int(round(player.position_px[0]))
    top = int(round(player.position_px[1]))
    right = left + int(player.size_px)
    bottom = top + int(player.size_px)
    payload["annotations"] = {
        "pixel_boxes": [
            {
                "kind": "player",
                "label": "player_px",
                "bbox_px": [left, top, right, bottom],
                "center_px": [(left + right) * 0.5, (top + bottom) * 0.5],
            }
        ]
    }


def build_synthetic_room(rng: random.Random) -> dict[str, Any]:
    blocked: set[tuple[int, int]] = set()
    layout = [["." for _x in range(GRID_WIDTH)] for _y in range(GRID_HEIGHT)]

    exit_direction = rng.choice(["north", "south", "west", "east"])
    reserved = set(EDGE_EXIT_TILES[exit_direction])

    dynamic_objects, dynamic_tiles = build_bridge_if_possible(rng, reserved)
    blocked.update(dynamic_tiles)

    player_pos = choose_free_tile(rng, blocked | reserved, margin=True)
    blocked.add(player_pos)

    wall_count = rng.randint(6, 12)
    for _ in range(wall_count):
        pos = choose_free_tile(rng, blocked | reserved, margin=False)
        layout[pos[1]][pos[0]] = "#"
        blocked.add(pos)

    objects: list[dict[str, Any]] = []
    occupied = set(blocked) | reserved
    add_chests(rng, objects, occupied, count=rng.randint(1, 3))
    add_monsters(rng, objects, occupied, count=rng.randint(1, 3))
    add_traps(rng, objects, occupied, count=rng.randint(2, 5))
    add_buttons_and_switches(rng, objects, occupied, enabled=bool(dynamic_objects))

    exit_type = rng.choice(["normal", "locked_key"])
    exit_config: dict[str, Any] = {
        "id": f"{exit_direction}_exit",
        "direction": exit_direction,
        "target_room": "synthetic_room",
        "target_entry": "default",
        "type": exit_type,
        "blocked_message": "NEED KEY",
        "success_message": "SYNTHETIC EXIT",
        "complete_task": True,
    }
    if exit_type == "locked_key":
        exit_config["requires"] = {"key_count": 1, "consume_key": False}

    return {
        "id": "synthetic_room",
        "coord": [0, 0],
        "layout": ["".join(row) for row in layout],
        "spawns": {"default": [player_pos[0], player_pos[1]]},
        "default_spawn": "default",
        "objects": objects,
        "dynamic_objects": dynamic_objects,
        "exits": [exit_config],
    }


def add_chests(
    rng: random.Random,
    objects: list[dict[str, Any]],
    blocked: set[tuple[int, int]],
    *,
    count: int,
) -> None:
    loot_kinds = [
        {"kind": "key", "key_id": "synthetic_key"},
        {"kind": "gold", "amount": 1},
        {"kind": "heal", "amount": 1},
    ]
    for index in range(count):
        pos = choose_free_tile(rng, blocked, margin=False)
        blocked.add(pos)
        objects.append(
            {
                "id": f"chest_{index}",
                "kind": "chest",
                "pos": [pos[0], pos[1]],
                "loot": rng.choice(loot_kinds),
            }
        )


def add_monsters(
    rng: random.Random,
    objects: list[dict[str, Any]],
    blocked: set[tuple[int, int]],
    *,
    count: int,
) -> None:
    monster_types = ["chaser", "ambusher", "patroller"]
    for index in range(count):
        pos = choose_free_tile(rng, blocked, margin=True)
        blocked.add(pos)
        objects.append(
            {
                "id": f"monster_{index}",
                "kind": "monster",
                "pos": [pos[0], pos[1]],
                "monster_type": rng.choice(monster_types),
                "hp": rng.randint(1, 3),
                "damage": 1,
            }
        )


def add_traps(
    rng: random.Random,
    objects: list[dict[str, Any]],
    blocked: set[tuple[int, int]],
    *,
    count: int,
) -> None:
    for index in range(count):
        pos = choose_free_tile(rng, blocked, margin=False)
        blocked.add(pos)
        trap_type = rng.choice(["spike", "abyss"])
        objects.append(
            {
                "id": f"trap_{index}",
                "kind": "trap",
                "pos": [pos[0], pos[1]],
                "trap_type": trap_type,
                "damage": 1,
                "respawn_to": "default",
            }
        )


def add_buttons_and_switches(
    rng: random.Random,
    objects: list[dict[str, Any]],
    blocked: set[tuple[int, int]],
    *,
    enabled: bool,
) -> None:
    button_pos = choose_free_tile(rng, blocked, margin=True)
    blocked.add(button_pos)
    objects.append(
        {
            "id": "button_0",
            "kind": "button",
            "pos": [button_pos[0], button_pos[1]],
            "message": "SYNTH BUTTON",
        }
    )

    if not enabled:
        return

    switch_pos = choose_free_tile(rng, blocked, margin=True)
    blocked.add(switch_pos)
    objects.append(
        {
            "id": "switch_0",
            "kind": "switch",
            "pos": [switch_pos[0], switch_pos[1]],
            "message": "SYNTH SWITCH",
            "effect": {
                "type": "cycle_state",
                "target": "bridge_0",
                "order": ["horizontal", "vertical"],
            },
        }
    )


def build_bridge_if_possible(
    rng: random.Random,
    blocked: set[tuple[int, int]],
) -> tuple[list[dict[str, Any]], set[tuple[int, int]]]:
    candidates = [
        (((3, 3), (4, 3), (5, 3)), ((4, 2), (4, 3), (4, 4))),
        (((2, 4), (3, 4), (4, 4)), ((3, 3), (3, 4), (3, 5))),
        (((5, 3), (6, 3), (7, 3)), ((6, 2), (6, 3), (6, 4))),
    ]
    rng.shuffle(candidates)
    for horizontal_tiles, vertical_tiles in candidates:
        all_tiles = set(horizontal_tiles) | set(vertical_tiles)
        if all(tile not in blocked for tile in all_tiles):
            return (
                [
                    {
                        "id": "bridge_0",
                        "kind": "rotating_bridge",
                        "initial_state": "horizontal",
                        "background_tile": "gap",
                        "active_tile": "bridge",
                        "states": {
                            "horizontal": {"tiles": [[x, y] for x, y in horizontal_tiles]},
                            "vertical": {"tiles": [[x, y] for x, y in vertical_tiles]},
                        },
                    }
                ],
                all_tiles,
            )
    return [], set()


def choose_free_tile(
    rng: random.Random,
    blocked: set[tuple[int, int]],
    *,
    margin: bool,
) -> tuple[int, int]:
    xs = range(1, GRID_WIDTH - 1) if margin else range(GRID_WIDTH)
    ys = range(1, GRID_HEIGHT - 1) if margin else range(GRID_HEIGHT)
    candidates = [(x, y) for y in ys for x in xs if (x, y) not in blocked]
    if not candidates:
        raise RuntimeError("no free tile available")
    return rng.choice(candidates)


if __name__ == "__main__":
    main()
