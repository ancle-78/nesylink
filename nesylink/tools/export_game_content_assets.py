from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from nesylink.core.constants import (
    COLOR_MONSTER_AMBUSHER,
    COLOR_MONSTER_CHASER,
    COLOR_MONSTER_PATROLLER,
    COLOR_NPC,
    TILE_SIZE,
)
from nesylink.core.rendering.sprites import (
    draw_abyss,
    draw_bridge,
    draw_button,
    draw_chest,
    draw_coin,
    draw_floor,
    draw_gap,
    draw_heal,
    draw_key,
    draw_monster,
    draw_npc,
    draw_player_sprite,
    draw_shield_icon,
    draw_sword_icon,
    draw_trap,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "assets" / "game-content"
SCALE = 4


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    _save_entity("player-down", lambda frame: draw_player_sprite(frame, 8, 8, "down"))
    _save_entity("player-up", lambda frame: draw_player_sprite(frame, 8, 8, "up"))
    _save_entity("player-side", lambda frame: draw_player_sprite(frame, 8, 8, "right"))

    _save_entity(
        "monster-chaser",
        lambda frame: draw_monster(frame, (8.0, 8.0), TILE_SIZE, "chaser", COLOR_MONSTER_CHASER),
    )
    _save_entity(
        "monster-patroller",
        lambda frame: draw_monster(frame, (8.0, 8.0), TILE_SIZE, "patroller", COLOR_MONSTER_PATROLLER),
    )
    _save_entity(
        "monster-ambusher",
        lambda frame: draw_monster(frame, (8.0, 8.0), TILE_SIZE, "ambusher", COLOR_MONSTER_AMBUSHER),
    )

    _save_tile("chest-key", lambda frame: draw_chest(frame, 0, 0, opened=False, loot_kind="key"))
    _save_tile("chest-gold", lambda frame: draw_chest(frame, 0, 0, opened=False, loot_kind="gold"))
    _save_tile("chest-heal", lambda frame: draw_chest(frame, 0, 0, opened=False, loot_kind="heal"))
    _save_tile("trap", lambda frame: draw_trap(frame, 0, 0))
    _save_tile("trap-abyss", lambda frame: draw_abyss(frame, 0, 0))
    _save_tile("gap", lambda frame: draw_gap(frame, 0, 0))
    _save_tile("bridge", lambda frame: draw_bridge(frame, 0, 0))
    _save_tile("button", lambda frame: draw_button(frame, 0, 0, pressed=False))
    _save_tile("button-pressed", lambda frame: draw_button(frame, 0, 0, pressed=True))
    _save_tile("npc", lambda frame: draw_npc(frame, 0, 0, COLOR_NPC))

    _save_icon("sword", lambda frame: draw_sword_icon(frame, 9, 7))
    _save_icon("shield", lambda frame: draw_shield_icon(frame, 9, 9))
    _save_icon("key", lambda frame: draw_key(frame, (12, 12)))
    _save_icon("gold", lambda frame: draw_coin(frame, (12, 12)))
    _save_icon("heal", lambda frame: draw_heal(frame, (12, 12)))


def _base_frame(width: int = 32, height: int = 32) -> np.ndarray:
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    for row in range((height + TILE_SIZE - 1) // TILE_SIZE):
        for col in range((width + TILE_SIZE - 1) // TILE_SIZE):
            draw_floor(frame, col, row)
    return frame


def _save_entity(name: str, draw) -> None:
    frame = _base_frame()
    draw(frame)
    _save(name, frame)


def _save_tile(name: str, draw) -> None:
    frame = _base_frame(TILE_SIZE, TILE_SIZE)
    draw(frame)
    _save(name, frame)


def _save_icon(name: str, draw) -> None:
    frame = _base_frame()
    draw(frame)
    _save(name, frame)


def _save(name: str, frame: np.ndarray) -> None:
    image = Image.fromarray(frame)
    image = image.resize((image.width * SCALE, image.height * SCALE), Image.Resampling.NEAREST)
    image.save(OUTPUT_DIR / f"{name}.png")


if __name__ == "__main__":
    main()
