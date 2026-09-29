"""完整进化演示：一键跑通「解决 → 复用 → 失败 → 记教训 → 跨语言复用」。

用法：venv/Scripts/python tests/demo_full.py

会真实调用大模型（DeepSeek），演示 Agent 的完整进化闭环。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.agent import solve_task
from app.memory.store import RedisMemoryStore
from app.skills.store import RedisSkillStore


def main() -> None:
    skill_store = RedisSkillStore()
    memory_store = RedisMemoryStore()
    # 清空，从干净状态开始演示
    skill_store.r.delete(skill_store.key)
    memory_store.r.delete(memory_store.key)

    print("=" * 60)
    print("EvoAgent 完整进化演示")
    print("=" * 60)

    # 场景 1：第一次解决新任务 → 学成技能
    print("\n【场景 1】第一次解决新任务")
    r1 = solve_task("reverse the text hello world", skill_store, memory_store)
    print(f"  method = {r1['method']}")
    print(f"  学到的技能 = {r1.get('learned_skill')}")

    # 场景 2：再提交同样任务 → 复用技能（越用越强）
    print("\n【场景 2】再提交同样任务")
    r2 = solve_task("reverse the text hello world", skill_store, memory_store)
    print(f"  method = {r2['method']}")
    print(f"  复用的技能 = {r2.get('skill')}")

    # 场景 3：办不到的任务 → 失败，提炼教训
    # （注意：大模型有随机性，可能直接用自己的知识翻译成功，两种结果都正常）
    print("\n【场景 3】提交办不到的任务（翻译）")
    r3 = solve_task("translate hello to chinese", skill_store, memory_store)
    print(f"  method = {r3['method']}")
    if r3["method"] == "failed":
        print(f"  教训 = {r3['learned_lesson'][:60]}...")

    # 场景 4：跨语言复用——中文任务命中英文技能（只有真实 embedding 做得到）
    print("\n【场景 4】中文任务复用英文技能（语义检索）")
    r4 = solve_task("把 hello world 反转", skill_store, memory_store)
    print(f"  method = {r4['method']}")
    print(f"  复用的技能 = {r4.get('skill')}")

    # 汇总：看看进化成果
    print("\n" + "=" * 60)
    print("进化成果汇总")
    print("=" * 60)
    print("技能库：")
    for s in skill_store.list_all():
        print(f"  - {s.name}  (复用 {s.use_count} 次)")
    print("经验记忆：")
    for m in memory_store.list_all():
        print(f"  - {m.lesson[:60]}...")
    print("=" * 60)


if __name__ == "__main__":
    main()
