## Examples 参考实现

仓库的 `examples/` 目录给出了两个 Python 参考实现，用于演示如何通过当前 `nesylink` 框架接口运行内置任务：

| 文件 | 对应任务 | 说明 |
|---|---|---|
| `examples/task1_reference.py` | `mathematical_logic/task_1` | 使用固定像素级动作序列完成“拿钥匙并通过北侧锁门”的任务。 |
| `examples/task2_reference.py` | `mathematical_logic/task_2` | 演示符号状态、邻接谓词和 BFS 子目标规划，完成当前 `mathematical_logic/task_2`。 |

运行方式：

```bash
python docs/Mathematical_logic/examples/task1_reference.py
python docs/Mathematical_logic/examples/task2_reference.py
# 测评
python utils/evaluate_policy.py \
  --policy docs/Mathematical_logic/examples/agent.py \
  --tasks mathematical_logic/task_1 \
  --num-envs 10 \
  --json-out /private/tmp/task1_agent_eval.json
```

它们是本作业给出的参考实现，重点是展示：

1. 如何从 raw pixels 中抽取离散符号状态，并利用 `info` 做状态抽象与调试。
2. 如何把 tile 级计划展开为像素级动作 replay。
3. 如何通过 `terminated/truncated`、`info["terminal_reason"]` 和 `info["game"]["world_completed"]` 检查真实环境执行结果。