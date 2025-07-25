#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LETDANCE 用户偏好记忆系统
学习并适应用户的行为偏好
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter

from .memory_config import MemoryConfig

logger = logging.getLogger(__name__)

class UserPreferenceMemory:
    """用户偏好记忆系统（内存版本）"""
    
    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig.default()
        
        # 内存存储
        self.user_behaviors = defaultdict(list)  # user_id -> [behaviors]
        self.user_preferences = defaultdict(lambda: defaultdict(Counter))  # user_id -> category -> Counter
        
        logger.info("用户偏好记忆系统初始化完成")
    

    
    def record_behavior(self, action_type: str, action_data: Dict[str, Any], 
                       user_id: str = 'default', session_id: Optional[str] = None):
        """记录用户行为"""
        behavior = {
            'action_type': action_type,
            'action_data': action_data,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }
        
        # 保存到内存，只保留最近100条行为
        self.user_behaviors[user_id].append(behavior)
        if len(self.user_behaviors[user_id]) > 100:
            self.user_behaviors[user_id] = self.user_behaviors[user_id][-100:]
        
        # 分析行为并更新偏好
        self._analyze_and_update_preferences(action_type, action_data, user_id)
        
        logger.debug(f"记录用户行为: {action_type}")
    
    def _analyze_and_update_preferences(self, action_type: str, action_data: Dict[str, Any], user_id: str):
        """分析用户行为并更新偏好"""
        try:
            if action_type == 'music_generation':
                keywords = action_data.get('keywords', [])
                if keywords:
                    for keyword in keywords:
                        self.user_preferences[user_id]['music_style'][keyword] += 1
        except Exception as e:
            logger.error(f"分析用户行为失败: {e}")
    
    def get_preference(self, user_id: str, category: str, key: str) -> Dict[str, Any]:
        """获取特定偏好"""
        if user_id not in self.user_preferences:
            return {'value': None, 'confidence': 0.0, 'frequency': 0}
        
        if category not in self.user_preferences[user_id]:
            return {'value': None, 'confidence': 0.0, 'frequency': 0}
        
        frequency = self.user_preferences[user_id][category][key]
        confidence = min(1.0, frequency / 10.0)  # 简单的置信度计算
        
        return {
            'value': key if frequency > 0 else None,
            'confidence': confidence,
            'frequency': frequency
        }
    
    def get_category_preferences(self, user_id: str, category: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """获取某类别的top偏好"""
        if user_id not in self.user_preferences or category not in self.user_preferences[user_id]:
            return []
        
        preferences = []
        for key, frequency in self.user_preferences[user_id][category].most_common(top_k):
            confidence = min(1.0, frequency / 10.0)
            preferences.append({
                'key': key,
                'value': key,
                'confidence': confidence,
                'frequency': frequency
            })
        
        return preferences
    
    def get_recommended_music_style(self, user_id: str = 'default', count: int = 4) -> List[str]:
        """获取推荐的音乐风格"""
        preferences = self.get_category_preferences(user_id, 'music_style', top_k=count*2)
        
        # 根据置信度和频率加权选择
        recommended = []
        for pref in preferences:
            if pref['confidence'] > 0.3:  # 只推荐置信度较高的
                recommended.append(pref['value'])
                if len(recommended) >= count:
                    break
        
        # 如果推荐不足，填充默认值
        defaults = ['ambient', 'emotional', 'calm', 'contemplative']
        while len(recommended) < count:
            for default in defaults:
                if default not in recommended:
                    recommended.append(default)
                    break
            if len(recommended) >= count:
                break
        
        return recommended[:count]
    
    def get_user_profile(self, user_id: str = 'default') -> Dict[str, Any]:
        """获取用户偏好档案"""
        profile = {
            'user_id': user_id,
            'music_preferences': self.get_category_preferences(user_id, 'music_style', 10),
            'stats': self._get_user_stats(user_id)
        }
        
        return profile
    
    def _get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户统计信息"""
        total_behaviors = len(self.user_behaviors.get(user_id, []))
        
        # 计算偏好统计
        total_preferences = 0
        total_frequency = 0
        if user_id in self.user_preferences:
            for category in self.user_preferences[user_id]:
                total_preferences += len(self.user_preferences[user_id][category])
                total_frequency += sum(self.user_preferences[user_id][category].values())
        
        avg_confidence = total_frequency / max(total_preferences, 1) / 10.0 if total_preferences > 0 else 0.0
        
        return {
            'total_behaviors': total_behaviors,
            'total_preferences': total_preferences,
            'avg_confidence': min(1.0, avg_confidence),
            'total_frequency': total_frequency
        }
    

    
    def export_preferences(self, user_id: str = 'default') -> Dict[str, Any]:
        """导出用户偏好数据"""
        preferences = []
        if user_id in self.user_preferences:
            for category, counter in self.user_preferences[user_id].items():
                for key, frequency in counter.items():
                    preferences.append({
                        'category': category,
                        'key': key,
                        'value': key,
                        'frequency': frequency,
                        'confidence': min(1.0, frequency / 10.0)
                    })
        
        behaviors = self.user_behaviors.get(user_id, [])
        
        return {
            'user_id': user_id,
            'preferences': preferences,
            'behaviors': behaviors,
            'export_time': datetime.now().isoformat(),
            'stats': self._get_user_stats(user_id)
        }
    
    def cleanup_old_data(self):
        """清理旧数据（内存版本）"""
        # 对每个用户，只保留最近50条行为记录
        for user_id in self.user_behaviors:
            if len(self.user_behaviors[user_id]) > 50:
                self.user_behaviors[user_id] = self.user_behaviors[user_id][-50:]
        
        logger.info("内存数据清理完成") 