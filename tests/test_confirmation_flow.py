"""
测试确认生成流程

验证 _handle_confirmation 方法是否正常工作
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 设置UTF-8编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from agent.ppt_task_manager import get_ppt_task_manager, PPTTaskManager


def test_submit_task():
    """测试任务提交"""
    print("=== 测试任务提交 ===")

    manager = get_ppt_task_manager()
    print(f"任务管理器已初始化，最大并发数: {manager.executor._max_workers}")

    # 模拟任务执行函数
    def mock_task(topic, subject="", grade=""):
        print(f"  执行任务: {topic}")
        return ("test.pptx", topic)

    # 提交任务
    queue_info = manager.submit_task(
        task_id="test_task_1",
        user_id="test_user",
        user_nick="测试用户",
        conversation_id="test_conv",
        corp_id="test_corp",
        topic="测试主题",
        func=mock_task,
        topic_arg="测试主题",
        subject="数学",
        grade="高中",
    )

    print(f"任务提交完成")
    print(f"返回类型: {type(queue_info)}")
    print(f"返回内容: {queue_info}")

    # 验证返回值
    if isinstance(queue_info, dict):
        print("返回值是字典，可以使用 .get() 方法")
        queue_position = queue_info.get('queue_position', 0)
        estimated_wait = queue_info.get('estimated_wait_display', '未知')
        print(f"排队位置: {queue_position}")
        print(f"预计等待: {estimated_wait}")
    else:
        print("返回值不是字典，需要修改代码")


if __name__ == "__main__":
    test_submit_task()
    print("\n测试完成！")
