#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LETDANCE 图像存储工具
提供统一的图像保存和管理功能
"""

import os
import cv2
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# 配置日志
logger = logging.getLogger(__name__)

class ImageStorageManager:
    """图像存储管理器"""
    
    def __init__(self, base_dir: str = "data/images"):
        self.base_dir = base_dir
        self.image_analysis_dir = os.path.join(base_dir, "image_analysis")
        self.pose_analysis_dir = os.path.join(base_dir, "pose_analysis")
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保存储目录存在"""
        for directory in [self.base_dir, self.image_analysis_dir, self.pose_analysis_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"创建存储目录: {directory}")
    
    def generate_filename(self, prefix: str = "img", extension: str = ".jpg") -> str:
        """生成带时间戳的文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 包含毫秒
        return f"{prefix}_{timestamp}{extension}"
    
    def save_image_from_bytes(self, image_bytes: bytes, filename: str, 
                            category: str = "image_analysis") -> Optional[str]:
        """
        从字节数据保存图像
        
        Args:
            image_bytes: 图像字节数据
            filename: 文件名
            category: 类别 ('image_analysis' 或 'pose_analysis')
            
        Returns:
            保存的文件路径，失败返回None
        """
        try:
            # 选择保存目录
            if category == "image_analysis":
                save_dir = self.image_analysis_dir
            elif category == "pose_analysis":
                save_dir = self.pose_analysis_dir
            else:
                save_dir = self.base_dir
            
            filepath = os.path.join(save_dir, filename)
            
            # 保存图像
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            logger.info(f"图像保存成功: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存图像失败: {e}")
            return None
    
    def save_image_from_frame(self, frame, filename: str, 
                            category: str = "pose_analysis") -> Optional[str]:
        """
        从OpenCV帧保存图像
        
        Args:
            frame: OpenCV图像帧
            filename: 文件名
            category: 类别 ('image_analysis' 或 'pose_analysis')
            
        Returns:
            保存的文件路径，失败返回None
        """
        try:
            # 选择保存目录
            if category == "image_analysis":
                save_dir = self.image_analysis_dir
            elif category == "pose_analysis":
                save_dir = self.pose_analysis_dir
            else:
                save_dir = self.base_dir
            
            filepath = os.path.join(save_dir, filename)
            
            # 保存图像
            success = cv2.imwrite(filepath, frame)
            
            if success:
                logger.info(f"图像保存成功: {filepath}")
                return filepath
            else:
                logger.error(f"OpenCV保存图像失败: {filepath}")
                return None
                
        except Exception as e:
            logger.error(f"保存图像失败: {e}")
            return None
    
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        info = {
            'base_dir': self.base_dir,
            'image_analysis_dir': self.image_analysis_dir,
            'pose_analysis_dir': self.pose_analysis_dir,
            'directories_exist': {
                'base': os.path.exists(self.base_dir),
                'image_analysis': os.path.exists(self.image_analysis_dir),
                'pose_analysis': os.path.exists(self.pose_analysis_dir)
            }
        }
        
        # 统计文件数量
        for category, directory in [
            ('image_analysis', self.image_analysis_dir),
            ('pose_analysis', self.pose_analysis_dir)
        ]:
            if os.path.exists(directory):
                files = [f for f in os.listdir(directory) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                info[f'{category}_count'] = len(files)
            else:
                info[f'{category}_count'] = 0
        
        return info
    
    def cleanup_old_images(self, days_old: int = 7) -> int:
        """
        清理旧图像文件
        
        Args:
            days_old: 保留天数
            
        Returns:
            删除的文件数量
        """
        import time
        from pathlib import Path
        
        deleted_count = 0
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        
        for directory in [self.image_analysis_dir, self.pose_analysis_dir]:
            if not os.path.exists(directory):
                continue
                
            for file_path in Path(directory).glob('*'):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info(f"删除旧文件: {file_path}")
                    except Exception as e:
                        logger.error(f"删除文件失败 {file_path}: {e}")
        
        return deleted_count

# 全局存储管理器实例
storage_manager = ImageStorageManager() 