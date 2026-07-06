# Map Creation Guide

NesyLink maps are JSON world definitions. They describe the dungeon layout and
objects only; reward logic and training objectives belong in Python rewards or
task specs.

## File Layout

Built-in themed maps live under:

```text
nesylink/map_data/<theme>/
```

Supported lookup patterns:

- `nesylink/map_data/<theme>/<task_name>/dungeon.json`
- `nesylink/map_data/<theme>/<task_name>/room_001.json`
- `nesylink/map_data/<theme>/<task_name>.json`

That means this works when `room_001.json` exists under `mathematical_logic/task_1/`:

```python
env = make_env(map_id="mathematical_logic/task_1", reward_id="mathematical_logic/task_1")
```

## Standalone Room

A minimal single-room map:

```json
{
  "id": "room_001",
  "coord": [0, 0],
  "layout": [
    "..........",
    "..........",
    "..........",
    "..........",
    "..........",
    "..........",
    "..........",
    ".........."
  ],
  "spawns": {
    "default": [4, 6]
  },
  "default_spawn": "default",
  "objects": [],
  "exits": []
}
```

The playable area is fixed at 10 columns by 8 rows. `.` is floor and `#` is
wall.

## Objects

Supported object kinds:

- `chest`
- `monster`
- `trap`
- `button`
- `switch`
- `npc`

Examples:

```json
{
  "id": "chest_key",
  "kind": "chest",
  "pos": [1, 3],
  "loot": {"kind": "key", "key_id": "task_key"}
}
```

```json
{
  "id": "monster_1",
  "kind": "monster",
  "pos": [7, 4],
  "monster_type": "chaser",
  "hp": 2,
  "damage": 1
}
```

Traps support two runtime types. The default `spike` trap keeps the original
behavior: stepping on it deals damage and immediately respawns the player at the
room spawn named by `respawn_to`.

| Demo | Trap type |
|---|---|
| <img src="../../assets/game-content/trap.png" width="64" alt="Spike trap demo"> | `spike` |
| <img src="../../assets/game-content/trap-abyss.png" width="64" alt="Abyss trap demo"> | `abyss` |

```json
{
  "id": "spike_1",
  "kind": "trap",
  "trap_type": "spike",
  "pos": [3, 4],
  "damage": 1,
  "respawn_to": "default"
}
```

An `abyss` trap deals damage, locks player control for a short delay, then
respawns the player on a safe adjacent tile. Safe tiles exclude walls, dynamic
blocking tiles, and active traps.

```json
{
  "id": "abyss_1",
  "kind": "trap",
  "trap_type": "abyss",
  "pos": [4, 4],
  "damage": 1,
  "respawn_delay_steps": 2
}
```

Large trap areas can be declared with `tiles` or `rects` on a `trap` object. The
loader expands them into individual runtime traps:

```json
{
  "id": "center_abyss",
  "kind": "trap",
  "trap_type": "abyss",
  "damage": 1,
  "respawn_delay_steps": 2,
  "rects": [{"from": [0, 0], "to": [9, 7]}]
}
```

Switches are reusable map-dynamics triggers. They do not declare rewards or task
success conditions. In the first dynamic-map version, switches support
`activation: "interact"` and a `cycle_state` effect:

```json
{
  "id": "west_switch",
  "kind": "switch",
  "pos": [1, 5],
  "activation": "interact",
  "effect": {
    "type": "cycle_state",
    "target": "center_bridge",
    "order": ["west_to_east", "west_to_north", "west_to_south"]
  }
}
```

## Dynamic Objects

Rooms may declare `dynamic_objects`. Dynamic objects patch the runtime map from
their current state without changing the static `layout`. `gap` is not passable;
`bridge` is passable. The first supported dynamic object kind is
`rotating_bridge`:

| Demo | Dynamic tile |
|---|---|
| <img src="../../assets/game-content/gap.png" width="64" alt="Gap tile demo"> | `gap` |
| <img src="../../assets/game-content/bridge.png" width="64" alt="Bridge tile demo"> | `bridge` |

```json
{
  "dynamic_objects": [
    {
      "id": "center_bridge",
      "kind": "rotating_bridge",
      "initial_state": "west_to_east",
      "background_tile": "gap",
      "active_tile": "bridge",
      "states": {
        "west_to_east": {"tiles": [[2, 4], [3, 4], [4, 4]]},
        "west_to_north": {"tiles": [[2, 4], [3, 4], [3, 3]]}
      }
    }
  ]
}
```

Dynamic object ids are dungeon-wide ids so switches can target objects in other
rooms. Rewards should inspect observations and `info["dynamic"]` rather than
adding task-specific fields to map JSON.

Use `"background_tile": "none"` when inactive dynamic-object tiles should reveal
the room's normal objects, such as abyss traps under an inactive bridge path.

Chests can be hidden until a generic environment event reveals them:

```json
{
  "id": "final_chest",
  "kind": "chest",
  "pos": [4, 4],
  "hidden": true,
  "reveal_on": {"event": "all_monsters_defeated", "room_id": "south"},
  "loot": {"kind": "gold", "amount": 1}
}
```

Item loot may also grant and equip a tool:

| Demo | Loot JSON intent |
|---|---|
| <img src="../../assets/game-content/sword.png" width="96" alt="Sword item demo"> | Add `sword` to inventory/tools and equip it to slot A. |
| <img src="../../assets/game-content/shield.png" width="96" alt="Shield item demo"> | Add `shield` to inventory/tools and equip it to slot B. |

```json
{
  "kind": "item",
  "item_id": "sword",
  "tool": "sword",
  "equip_slot": "A"
}
```

## Exits

Exit directions are fixed to `north`, `south`, `west`, and `east`. The engine
uses fixed two-tile doorway shapes for each direction.

Normal exit:

```json
{
  "id": "north_exit",
  "direction": "north",
  "target_room": "room_001",
  "target_entry": "from_south",
  "type": "normal",
  "success_message": "CLEARED!"
}
```

Locked key exit:

```json
{
  "id": "east_exit",
  "direction": "east",
  "target_room": "room_2",
  "target_entry": "from_west",
  "type": "locked_key",
  "requires": {"key_count": 1, "consume_key": true},
  "blocked_message": "NEED KEY"
}
```

Conditional exit:

```json
{
  "id": "south_exit",
  "direction": "south",
  "target_room": "room_3",
  "target_entry": "from_north",
  "type": "conditional",
  "requires": {"button_pressed": "button_1"}
}
```

Set `complete_task: true` on an exit when reaching it should produce an
environment-completion event.

## Multi-room Dungeon

A dungeon root file references room files:

```json
{
  "schema_version": 1,
  "dungeon_id": "prototype",
  "start_room": "room_0_0",
  "room_files": [
    "rooms/room_0_0.json",
    "rooms/room_1_0.json"
  ]
}
```

Each referenced room is a normal room JSON file with an `id`, `coord`,
`layout`, `spawns`, `objects`, and `exits`.
