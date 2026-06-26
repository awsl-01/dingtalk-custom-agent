"""
PPT队列管理功能测试

测试排队位置、预计等待时间等功能
"""
import sys
import time
import threading
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.ppt_task_manager import get_ppt_task_manager, PPTTaskManager, PPTTaskStatus


def test_queue_position():
    """测试排队位置计算"""
    print("\n=== 测试排队位置计算 ===")

    # 创建一个新的任务管理器（不使用全局实例）
    manager = PPTTaskManager(max_workers=2)

    # 模拟任务执行函数
    def slow_task(duration):
        time.sleep(duration)
        return ("test.pptx", "测试PPT")

    # 提交3个任务
    tasks = []
    for i in range(3):
        task = manager.submit_task(
            task_id=f"task_{i}",
            user_id=f"user_{i}",
            user_nick=f"用户{i}",
            conversation_id=f"conv_{i}",
            corp_id="test_corp",
            topic=f"测试主题{i}",
            func=slow_task,
            duration=0.5,  # 0.5秒
        )
        tasks.append(task)
        print(f"任务 {i} 提交完成，状态: {task.get('status')}")

    # 检查排队位置
    time.sleep(0.1)  # 等待任务开始执行
    for i in range(3):
        position = manager.get_queue_position(f"task_{i}")
        print(f"任务 {i} 排队位置: {position}")

    # 等待所有任务完成
    time.sleep(2)
    print("所有任务完成")


def test_estimated_wait_time():
    """测试预计等待时间计算"""
    print("\n=== 测试预计等待时间计算 ===")

    manager = PPTTaskManager(max_workers=2)

    # 模拟任务执行函数
    def slow_task(duration):
        time.sleep(duration)
        return ("test.pptx", "测试PPT")

    # 先完成几个任务，记录生成时间
    for i in range(3):
        manager.submit_task(
            task_id=f"history_{i}",
            user_id=f"user_{i}",
            user_nick=f"用户{i}",
            conversation_id=f"conv_{i}",
            corp_id="test_corp",
            topic=f"历史任务{i}",
            func=slow_task,
            duration=0.3,
        )
        time.sleep(0.4)

    # 检查平均生成时间
    avg_time = manager._get_average_generation_time()
    print(f"平均生成时间: {avg_time:.2f}秒")

    # 提交新任务
    manager.submit_task(
        task_id="new_task",
        user_id="new_user",
        user_nick="新用户",
        conversation_id="new_conv",
        corp_id="test_corp",
        topic="新任务",
        func=slow_task,
        duration=0.5,
    )

    # 检查预计等待时间
    estimated_wait = manager.get_estimated_wait_time("new_task")
    print(f"预计等待时间: {estimated_wait}秒")

    # 检查完整队列信息
    queue_info = manager.get_queue_info("new_task")
    print(f"\n队列信息:")
    for key, value in queue_info.items():
        print(f"  {key}: {value}")


def test_queue_info():
    """测试队列信息获取"""
    print("\n=== 测试队列信息获取 ===")

    manager = PPTTaskManager(max_workers=2)

    # 模拟任务执行函数
    def slow_task(duration):
        time.sleep(duration)
        return ("test.pptx", "测试PPT")

    # 提交多个任务
    for i in range(4):
        manager.submit_task(
            task_id=f"task_{i}",
            user_id=f"user_{i}",
            user_nick=f"用户{i}",
            conversation_id=f"conv_{i}",
            corp_id="test_corp",
            topic=f"测试主题{i}",
            func=slow_task,
            duration=0.5,
        )

    # 等待任务开始
    time.sleep(0.1)

    # 获取所有队列状态
    all_status = manager.get_all_queue_status()
    print("\n所有队列状态:")
    print(f"  并发配置: {all_status['concurrency']}")
    print(f"  排队任务数: {len(all_status['queue'])}")
    print(f"  统计信息: {all_status['stats']}")

    # 打印排队列表
    print("\n排队列表:")
    for item in all_status['queue']:
        print(f"  {item['position']}. {item['topic']} ({item['estimated_wait_display']})")

    # 等待所有任务完成
    time.sleep(2)


def test_global_manager():
    """测试全局任务管理器"""
    print("\n=== 测试全局任务管理器 ===")

    manager = get_ppt_task_manager()
    print(f"最大并发数: {manager.executor._max_workers}")

    # 获取当前状态
    stats = manager.get_stats()
    print(f"当前任务统计: {stats}")


if __name__ == "__main__":
    # 设置UTF-8编码
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

    print("开始测试PPT队列管理功能...")

    try:
        test_queue_position()
        test_estimated_wait_time()
        test_queue_info()
        test_global_manager()

        print("\n[SUCCESS] 所有测试完成！")
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
