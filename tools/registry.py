#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LETDANCE 工具注册中心
集中管理和提供所有LangChain工具
"""

import logging
from typing import List, Dict, Any
from langchain_core.tools import BaseTool

from .image_analysis_tool import ImageAnalysisTool
from .pose_analysis_tool import PoseAnalysisTool

# 配置日志
logger = logging.getLogger(__name__)

class ToolRegistry:
    """工具注册中心"""
    
    def __init__(self):
        self._tools = {}
        self._initialize_tools()
    
    def _initialize_tools(self):
        """初始化所有工具"""
        try:
            # 图像分析工具
            self._tools['image_analysis'] = ImageAnalysisTool()
            logger.info("图像分析工具注册成功")
            
            # 姿态分析工具
            self._tools['pose_analysis'] = PoseAnalysisTool()
            logger.info("姿态分析工具注册成功")
            
        except Exception as e:
            logger.error(f"工具初始化失败: {e}")
    
    def get_tool(self, tool_name: str) -> BaseTool:
        """获取指定工具"""
        if tool_name not in self._tools:
            raise ValueError(f"工具 '{tool_name}' 未注册")
        return self._tools[tool_name]
    
    def get_all_tools(self) -> List[BaseTool]:
        """获取所有工具列表"""
        return list(self._tools.values())
    
    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        return list(self._tools.keys())
    
    def get_tools_info(self) -> Dict[str, Dict[str, Any]]:
        """获取所有工具信息"""
        info = {}
        for name, tool in self._tools.items():
            info[name] = {
                'name': tool.name,
                'description': tool.description,
                'args_schema': tool.args_schema.schema() if tool.args_schema else None,
                'return_direct': getattr(tool, 'return_direct', False)
            }
        return info

# 全局工具注册实例
_registry = None

def get_tool_registry() -> ToolRegistry:
    """获取工具注册中心实例（单例模式）"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry

def get_all_tools() -> List[BaseTool]:
    """快捷方法：获取所有工具"""
    return get_tool_registry().get_all_tools()

def get_tool(tool_name: str) -> BaseTool:
    """快捷方法：获取指定工具"""
    return get_tool_registry().get_tool(tool_name)

def get_tools_info() -> Dict[str, Dict[str, Any]]:
    """快捷方法：获取工具信息"""
    return get_tool_registry().get_tools_info()

if __name__ == "__main__":
    # 测试工具注册
    registry = get_tool_registry()
    tools = registry.get_all_tools()
    
    print("=== LETDANCE 工具注册中心 ===")
    print(f"已注册工具数量: {len(tools)}")
    
    for tool_name in registry.get_tool_names():
        tool = registry.get_tool(tool_name)
        print(f"\n工具名称: {tool.name}")
        print(f"描述: {tool.description[:100]}...")
        
    print(f"\n工具详细信息:")
    import json
    print(json.dumps(registry.get_tools_info(), indent=2, ensure_ascii=False)) 