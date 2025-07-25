#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LETDANCE 记忆配置管理
"""

from dataclasses import dataclass

@dataclass
class MemoryConfig:
    """记忆系统配置"""
    
    max_token_limit: int = 3000
    memory_key: str = "chat_history"
    
    @classmethod
    def default(cls) -> 'MemoryConfig':
        """默认配置"""
        return cls() 