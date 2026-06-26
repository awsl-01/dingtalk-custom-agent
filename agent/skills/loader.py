"""
技能加载器 - 自动加载 agent/skills/ 目录下的所有技能

新技能只需在 agent/skills/ 目录下创建 .py 文件，无需修改 main.py
"""
import os
import importlib
import logging

logger = logging.getLogger(__name__)


def load_skills():
    """
    自动加载 skills 目录下的所有技能模块

    每个技能文件末尾需要调用 skill_registry.register() 注册自己
    """
    skills_dir = os.path.dirname(__file__)
    loaded = []

    for filename in os.listdir(skills_dir):
        if filename.endswith('.py') and filename not in (
            '__init__.py', 'registry.py', 'loader.py'
        ):
            module_name = filename[:-3]
            try:
                importlib.import_module(f'.{module_name}', package='agent.skills')
                loaded.append(module_name)
                logger.info(f"加载技能模块: {module_name}")
            except Exception as e:
                logger.error(f"加载技能模块 {module_name} 失败: {e}")

    return loaded
