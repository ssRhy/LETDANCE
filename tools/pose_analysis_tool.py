#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LETDANCE 姿态分析工具
基于LangChain的姿态分析工具，支持YOLO姿态检测和拉班运动分析
"""

import os
import cv2
import json
import math
import logging
import numpy as np
from datetime import datetime
from collections import deque
from typing import Optional, Dict, List, Type, Any

from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logging.warning("YOLO未安装，姿态检测功能将不可用")

# 导入图像存储管理器
from .image_storage_utils import storage_manager

# 配置已直接填入，无需导入config

# 配置日志
logger = logging.getLogger(__name__)

# 姿态关键点名称 - 简化版，只包含必要的8个关键点
KEYPOINT_NAMES = [
    '左肩', '右肩', '左肘', '右肘',
    '左髋', '右髋', '左膝', '右膝'
]

# YOLO关键点到简化关键点的索引映射
YOLO_TO_SIMPLIFIED_MAPPING = {
    0: 5,   # 左肩 -> YOLO索引5
    1: 6,   # 右肩 -> YOLO索引6
    2: 7,   # 左肘 -> YOLO索引7
    3: 8,   # 右肘 -> YOLO索引8
    4: 11,  # 左髋 -> YOLO索引11
    5: 12,  # 右髋 -> YOLO索引12
    6: 13,  # 左膝 -> YOLO索引13
    7: 14   # 右膝 -> YOLO索引14
}

class PoseAnalysisInput(BaseModel):
    """姿态分析工具输入模型"""
    action: str = Field(
        description="操作类型：'analyze_realtime'(实时分析), 'get_summary'(获取汇总)"
    )
    model_path: Optional[str] = Field(
        default="yolov8n-pose.pt",
        description="YOLO模型路径"
    )
    confidence_threshold: float = Field(
        default=0.5,
        description="检测置信度阈值"
    )
    duration: Optional[int] = Field(
        default=10,
        description="实时分析持续时间（秒）"
    )
    save_frames: Optional[bool] = Field(
        default=True,
        description="是否保存关键帧到本地存储"
    )
    save_interval: Optional[int] = Field(
        default=30,
        description="保存帧的间隔（每N帧保存一次）"
    )

class LabanMovementAnalyzer:
    """基于拉班运动分析理论的情感识别器 - 简化版，只使用8个关键点"""
    
    def __init__(self, history_length=10):
        self.history_length = history_length
        self.keypoint_history = deque(maxlen=history_length)
        
        # 拉班运动质量维度
        self.effort_qualities = {
            'weight': 0,    # 重量：轻-重
            'time': 0,      # 时间：快-慢
            'flow': 0,      # 流动性：自由-约束
            'space': 0      # 空间：直接-间接
        }
        
        # 情感映射（针对舞蹈动作优化）
        self.emotion_map = {
            '快乐/欢快': {'weight': 0.5, 'time': 0.6, 'flow': 0.7, 'space': 0.4},
            '优雅/平静': {'weight': -0.3, 'time': -0.4, 'flow': 0.8, 'space': -0.2},
            '激情/兴奋': {'weight': 0.8, 'time': 0.7, 'flow': 0.5, 'space': 0.6},
            '忧郁/悲伤': {'weight': -0.6, 'time': -0.5, 'flow': -0.3, 'space': -0.4},
            '紧张/焦虑': {'weight': 0.4, 'time': 0.3, 'flow': -0.6, 'space': -0.5},
            '放松/舒缓': {'weight': -0.4, 'time': -0.6, 'flow': 0.6, 'space': 0.2},
            '力量/决心': {'weight': 0.7, 'time': 0.2, 'flow': 0.3, 'space': 0.5},
            '轻盈/飘逸': {'weight': -0.7, 'time': 0.4, 'flow': 0.8, 'space': 0.3}
        }
    
    def calculate_distance(self, p1, p2):
        """计算两点间距离"""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    
    def calculate_angle(self, p1, p2, p3):
        """计算三点形成的角度"""
        v1 = (p1[0] - p2[0], p1[1] - p2[1])
        v2 = (p3[0] - p2[0], p3[1] - p2[1])
        
        dot_product = v1[0] * v2[0] + v1[1] * v2[1]
        magnitude1 = math.sqrt(v1[0]**2 + v1[1]**2)
        magnitude2 = math.sqrt(v2[0]**2 + v2[1]**2)
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0
        
        cos_angle = dot_product / (magnitude1 * magnitude2)
        cos_angle = max(-1, min(1, cos_angle))
        
        return math.degrees(math.acos(cos_angle))
    
    def analyze_body_expansion(self, keypoints):
        """分析身体扩张度 - Shape维度（基于8个关键点）"""
        if len(keypoints) < 8:
            return 0
        
        # 关键点索引（简化版）：0=左肩, 1=右肩, 2=左肘, 3=右肘, 4=左髋, 5=右髋, 6=左膝, 7=右膝
        
        # 计算肩宽（基准）
        left_shoulder = keypoints[0][:2]   # 左肩
        right_shoulder = keypoints[1][:2]  # 右肩
        shoulder_width = self.calculate_distance(left_shoulder, right_shoulder)
        
        if shoulder_width <= 0:
            return 0
        
        # 计算手臂展开程度（使用肘部）
        left_elbow = keypoints[2][:2]   # 左肘
        right_elbow = keypoints[3][:2]  # 右肘
        arm_span = self.calculate_distance(left_elbow, right_elbow)
        
        # 计算腿部张开程度（使用膝部）
        left_knee = keypoints[6][:2]   # 左膝
        right_knee = keypoints[7][:2]  # 右膝
        leg_span = self.calculate_distance(left_knee, right_knee)
        
        # 综合身体扩张度（归一化到-1到1）
        arm_expansion = (arm_span / shoulder_width - 1.2) / 1.2  # 肘部正常比例约1.2
        leg_expansion = (leg_span / shoulder_width - 0.8) / 0.8  # 膝部正常比例约0.8
        
        # 限制在-1到1之间
        expansion = (arm_expansion + leg_expansion) / 2
        return max(-1, min(1, expansion))
    
    def analyze_vertical_position(self, keypoints):
        """分析身体垂直位置 - Shape维度（基于躯干关键点）"""
        if len(keypoints) < 8:
            return 0
        
        # 计算躯干重心：肩膀和髋部的中点
        left_shoulder = keypoints[0][:2]   # 左肩
        right_shoulder = keypoints[1][:2]  # 右肩
        left_hip = keypoints[4][:2]        # 左髋
        right_hip = keypoints[5][:2]       # 右髋
        
        shoulder_center_y = (left_shoulder[1] + right_shoulder[1]) / 2
        hip_center_y = (left_hip[1] + right_hip[1]) / 2
        
        # 计算躯干长度
        torso_length = abs(hip_center_y - shoulder_center_y)
        
        if torso_length <= 0:
            return 0
        
        # 计算膝部相对于髋部的位置
        left_knee = keypoints[6][:2]   # 左膝
        right_knee = keypoints[7][:2]  # 右膝
        knee_center_y = (left_knee[1] + right_knee[1]) / 2
        
        # 垂直偏移（负值表示膝部较高，正值表示膝部较低）
        vertical_offset = (knee_center_y - hip_center_y) / torso_length
        
        # 翻转符号，正值表示向上的动作倾向
        return -max(-1, min(1, vertical_offset))
    
    def analyze_movement_speed(self, current_keypoints):
        """分析运动速度 - Time维度（基于8个关键点）"""
        if len(self.keypoint_history) < 2:
            return 0
        
        prev_keypoints = self.keypoint_history[-1]
        
        # 使用所有8个关键点计算运动速度
        key_indices = [0, 1, 2, 3, 4, 5, 6, 7]  # 所有8个关键点
        total_movement = 0
        valid_points = 0
        
        for i in key_indices:
            if (i < len(current_keypoints) and i < len(prev_keypoints) and 
                current_keypoints[i][2] > 0.5 and prev_keypoints[i][2] > 0.5):
                movement = self.calculate_distance(current_keypoints[i][:2], prev_keypoints[i][:2])
                total_movement += movement
                valid_points += 1
        
        if valid_points > 0:
            avg_movement = total_movement / valid_points
            # 归一化到-1到1，快速运动为正值
            normalized_speed = min(avg_movement / 15.0, 1.0) * 2 - 1  # 15像素作为基准
            return normalized_speed
        else:
            return 0
    
    def analyze_flow_consistency(self, current_keypoints):
        """分析动作流畅性 - Flow维度（基于肩肘关键点）"""
        if len(self.keypoint_history) < 3:
            return 0
        
        # 重点分析肩膀和肘部的流畅性
        key_indices = [0, 1, 2, 3]  # 肩膀和肘部
        speed_changes = []
        
        for i in range(len(self.keypoint_history) - 1):
            curr_frame = self.keypoint_history[i]
            next_frame = self.keypoint_history[i + 1]
            
            frame_movement = 0
            valid_points = 0
            
            for j in key_indices:
                if (j < len(curr_frame) and j < len(next_frame) and
                    curr_frame[j][2] > 0.5 and next_frame[j][2] > 0.5):
                    movement = self.calculate_distance(curr_frame[j][:2], next_frame[j][:2])
                    frame_movement += movement
                    valid_points += 1
            
            if valid_points > 0:
                speed_changes.append(frame_movement / valid_points)
        
        if len(speed_changes) < 2:
            return 0
        
        # 计算流畅性（变化越小越流畅）
        mean_speed = sum(speed_changes) / len(speed_changes)
        if mean_speed == 0:
            return 1
            
        variance = sum((x - mean_speed) ** 2 for x in speed_changes) / len(speed_changes)
        relative_variance = variance / (mean_speed + 1e-6)
        
        # 归一化到-1到1，流畅为正值，不流畅为负值
        flow_score = 1 / (1 + relative_variance)
        return flow_score * 2 - 1
    
    def analyze_space_directness(self, keypoints):
        """分析空间使用的直接性 - Space维度（基于8个关键点）"""
        if len(keypoints) < 8:
            return 0
        
        # 计算身体中心（肩膀和髋部的中点）
        center_x = (keypoints[0][0] + keypoints[1][0] + keypoints[4][0] + keypoints[5][0]) / 4
        center_y = (keypoints[0][1] + keypoints[1][1] + keypoints[4][1] + keypoints[5][1]) / 4
        
        # 分析四肢相对于身体中心的位置（使用肘部和膝部）
        limb_positions = []
        for idx in [2, 3, 6, 7]:  # 肘部和膝部
            if keypoints[idx][2] > 0.5:
                distance = self.calculate_distance([center_x, center_y], keypoints[idx][:2])
                limb_positions.append(distance)
        
        if not limb_positions:
            return 0
        
        # 计算动作范围（间接性指标）
        avg_distance = sum(limb_positions) / len(limb_positions)
        max_distance = max(limb_positions)
        
        # 如果动作范围大且变化大，则更间接
        if avg_distance > 0:
            range_ratio = max_distance / avg_distance
            # 归一化到-1到1，大范围动作为正值（间接），小范围为负值（直接）
            space_score = min((range_ratio - 1.0) / 2.0, 1.0)
            return max(-1, min(1, space_score))
        
        return 0
    
    def calculate_laban_qualities(self, keypoints):
        """计算拉班运动质量"""
        self.keypoint_history.append(keypoints)
        
        expansion = self.analyze_body_expansion(keypoints)
        vertical_pos = self.analyze_vertical_position(keypoints)
        movement_speed = self.analyze_movement_speed(keypoints)
        flow_consistency = self.analyze_flow_consistency(keypoints)
        space_directness = self.analyze_space_directness(keypoints)
        
        # Weight: 基于身体扩张度（扩张为强，收缩为轻）
        self.effort_qualities['weight'] = float(expansion * 0.7 + vertical_pos * 0.3)
        
        # Time: 直接使用标准化后的运动速度
        self.effort_qualities['time'] = float(movement_speed)
        
        # Flow: 直接使用标准化后的流畅性
        self.effort_qualities['flow'] = float(flow_consistency)
        
        # Space: 直接使用标准化后的空间直接性
        self.effort_qualities['space'] = float(space_directness)
        
        # 确保值在-1到1范围内
        for key in self.effort_qualities:
            self.effort_qualities[key] = max(-1, min(1, self.effort_qualities[key]))
        
        return {k: float(v) for k, v in self.effort_qualities.items()}
    
    def recognize_emotion(self, laban_qualities):
        """基于拉班质量识别情感"""
        emotion_scores = {}
        
        # 计算与每种情感的相似度
        for emotion, template in self.emotion_map.items():
            # 使用加权欧氏距离
            weights = {'weight': 1.2, 'time': 1.0, 'flow': 1.1, 'space': 0.9}
            distance = 0
            for quality in ['weight', 'time', 'flow', 'space']:
                diff = laban_qualities[quality] - template[quality]
                distance += weights[quality] * (diff ** 2)
            
            distance = math.sqrt(distance)
            # 使用更温和的相似度函数
            similarity = math.exp(-distance / 0.8)  # 0.8是温度参数
            emotion_scores[emotion] = float(similarity)
        
        # 找到最高得分的情感
        if emotion_scores:
            best_emotion = max(emotion_scores.items(), key=lambda x: x[1])[0]
            best_score = emotion_scores[best_emotion]
            
            # 如果最高得分太低，认为是中性状态
            if best_score < 0.3:
                recognized_emotion = '中性/自然'
            else:
                recognized_emotion = best_emotion
        else:
            recognized_emotion = '中性/自然'
        
        return recognized_emotion, emotion_scores

def ensure_json_serializable(obj):
    """确保对象可以JSON序列化"""
    if isinstance(obj, dict):
        return {k: ensure_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [ensure_json_serializable(item) for item in obj]
    elif isinstance(obj, (np.integer, np.floating, np.ndarray)):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj.item()
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    else:
        return str(obj)

class PoseAnalysisTool(BaseTool):
    """LangChain姿态分析工具"""
    
    name: str = "pose_analysis"
    description: str = """
    姿态分析工具，支持以下功能：
    1. 实时分析：从摄像头实时分析姿态和情感（基于拉班运动理论）
    2. 获取汇总：获取分析结果汇总
    
    使用示例：
    - {"action": "analyze_realtime", "duration": 10} - 实时分析10秒
    - {"action": "get_summary"} - 获取分析汇总
    """
    args_schema: Type[BaseModel] = PoseAnalysisInput
    # 移除 return_direct，让Agent能够处理工具输出
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 延迟初始化组件，避免在工具创建时就加载所有依赖
        self._model = None
        self._analyzer = None
        self._analysis_results = []
    
    def _detect_available_cameras(self):
        """检测可用摄像头（改进版，只检测摄像头0）"""
        available_cameras = []
        
        # 首先尝试释放可能被占用的摄像头资源
        import gc
        gc.collect()  # 强制垃圾回收
        
        cap = None
        try:
            print("检测摄像头 0...")
            cap = cv2.VideoCapture(0)
            
            # 设置较短的超时时间
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if cap.isOpened():
                # 尝试读取一帧来确认摄像头真正可用
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    available_cameras.append(0)
                    print("✅ 发现可用摄像头: 0")
                else:
                    print("❌ 摄像头 0 打开但无法读取数据")
            else:
                print("❌ 无法打开摄像头 0")
                
        except Exception as e:
            print(f"❌ 检测摄像头 0 时出错: {e}")
        finally:
            # 确保释放资源
            if cap is not None:
                cap.release()
                
        # 再次垃圾回收
        gc.collect()
        
        if available_cameras:
            print("✅ 摄像头 0 可用")
        else:
            print("⚠️ 摄像头 0 不可用")
            
        return available_cameras
    
    def _get_analyzer(self):
        """获取拉班运动分析器（延迟加载）"""
        if self._analyzer is None:
            self._analyzer = LabanMovementAnalyzer()
            logger.info("拉班运动分析器初始化成功")
        return self._analyzer
    
    def _load_model(self, model_path: str) -> bool:
        """加载YOLO模型"""
        if not YOLO_AVAILABLE:
            logger.error("YOLO未安装，无法加载模型")
            return False
        
        try:
            if not os.path.exists(model_path):
                logger.warning(f"模型文件不存在: {model_path}，尝试下载默认模型")
                model_path = "yolov8n-pose.pt"
            
            self._model = YOLO(model_path)
            logger.info(f"YOLO模型加载成功: {model_path}")
            return True
        except Exception as e:
            logger.error(f"YOLO模型加载失败: {e}")
            return False
    
    def _detect_pose(self, frame, confidence_threshold: float = 0.5) -> Optional[List]:
        """检测姿态关键点并转换为简化的8个关键点"""
        if not self._model:
            return None
        
        try:
            results = self._model(frame, verbose=False, conf=confidence_threshold, max_det=1)
            
            if results[0].keypoints is not None and len(results[0].keypoints) > 0:
                yolo_keypoints = results[0].keypoints.data[0].cpu().numpy()
                
                # 转换为简化的8个关键点
                simplified_keypoints = []
                for simplified_idx, yolo_idx in YOLO_TO_SIMPLIFIED_MAPPING.items():
                    if yolo_idx < len(yolo_keypoints):
                        kp = yolo_keypoints[yolo_idx]
                        # 将numpy float32转换为Python float
                        simplified_keypoints.append([float(kp[0]), float(kp[1]), float(kp[2])])
                    else:
                        # 如果YOLO关键点不足，使用默认值
                        simplified_keypoints.append([0.0, 0.0, 0.0])
                
                return simplified_keypoints
            else:
                return None
        except Exception as e:
            logger.error(f"姿态检测失败: {e}")
            return None
    
    def _draw_pose_keypoints(self, frame, keypoints: List, min_confidence: float = 0.5):
        """在帧上绘制简化的8个姿态关键点"""
        if not keypoints or len(keypoints) < 8:
            return frame
        
        # 定义简化的关键点连接（基于8个关键点）
        # 索引：0=左肩, 1=右肩, 2=左肘, 3=右肘, 4=左髋, 5=右髋, 6=左膝, 7=右膝
        pose_connections = [
            (0, 2),   # 左肩-左肘
            (1, 3),   # 右肩-右肘
            (0, 1),   # 左肩-右肩
            (4, 6),   # 左髋-左膝
            (5, 7),   # 右髋-右膝
            (4, 5),   # 左髋-右髋
            (0, 4),   # 左肩-左髋
            (1, 5),   # 右肩-右髋
        ]
        
        # 绘制关键点连接线
        for connection in pose_connections:
            pt1_idx, pt2_idx = connection
            if pt1_idx < len(keypoints) and pt2_idx < len(keypoints):
                x1, y1, conf1 = keypoints[pt1_idx]
                x2, y2, conf2 = keypoints[pt2_idx]
                
                if conf1 > min_confidence and conf2 > min_confidence:
                    cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        
        # 关键点名称和颜色映射
        keypoint_colors = {
            0: (255, 0, 0),    # 左肩 - 蓝色
            1: (255, 0, 0),    # 右肩 - 蓝色
            2: (0, 255, 0),    # 左肘 - 绿色
            3: (0, 255, 0),    # 右肘 - 绿色
            4: (0, 0, 255),    # 左髋 - 红色
            5: (0, 0, 255),    # 右髋 - 红色
            6: (255, 255, 0),  # 左膝 - 青色
            7: (255, 255, 0),  # 右膝 - 青色
        }
        
        # 绘制关键点
        for i, (x, y, confidence) in enumerate(keypoints):
            if confidence > min_confidence and i < len(KEYPOINT_NAMES):
                color = keypoint_colors.get(i, (128, 128, 128))
                
                cv2.circle(frame, (int(x), int(y)), 6, color, -1)
                # 添加关键点名称
                cv2.putText(frame, KEYPOINT_NAMES[i], (int(x) + 8, int(y) - 8), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
        
        return frame
    
    def _analyze_realtime(self, duration: int, confidence_threshold: float, 
                         save_frames: bool = True, save_interval: int = 30) -> Dict[str, Any]:
        """实时姿态分析 - 改进版，处理摄像头资源冲突"""
        import time
        import gc
        
        print(f"🎯 开始{duration}秒实时姿态分析...")
        
        # 强制释放可能占用的摄像头资源
        print("⏳ 等待摄像头资源完全释放...")
        gc.collect()  # 垃圾回收
        cv2.destroyAllWindows()  # 关闭所有OpenCV窗口
        time.sleep(2)  # 增加等待时间，确保资源释放
        
        # 检测可用摄像头
        available_cameras = self._detect_available_cameras()
        
        if not available_cameras:
            # 如果没有可用摄像头，尝试等待并重新检测
            print("⚠️ 首次检测未发现摄像头，等待5秒后重试...")
            time.sleep(5)
            available_cameras = self._detect_available_cameras()
            
            if not available_cameras:
                return {
                    'success': False,
                    'message': '未发现可用摄像头，可能被其他程序占用。请确保图像分析已完成。',
                    'data': None
                }
        
        # 使用第一个可用摄像头
        camera_id = available_cameras[0]
        print(f"📹 使用摄像头 {camera_id} 进行实时姿态分析")
        
        cap = None
        try:
            cap = cv2.VideoCapture(camera_id)
            if not cap.isOpened():
                # 尝试重新打开
                print("🔄 重新尝试打开摄像头...")
                time.sleep(2)
                cap.release()
                cap = cv2.VideoCapture(camera_id)
                
                if not cap.isOpened():
                    return {
                        'success': False,
                        'message': f'无法打开摄像头 {camera_id}，可能被占用',
                        'data': None
                    }
            
            # 设置分辨率和缓冲区
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 减少缓冲区
            
            # 等待摄像头完全初始化
            time.sleep(1)
            
            analyzer = self._get_analyzer()
            analysis_results = []
            start_time = time.time()
            frame_count = 0
            consecutive_failures = 0
            
            print("🎬 开始实时姿态分析...")
            
            while (time.time() - start_time) < duration:
                ret, frame = cap.read()
                if not ret or frame is None:
                    consecutive_failures += 1
                    if consecutive_failures > 10:
                        print("❌ 连续读取失败过多，可能摄像头被断开")
                        break
                    print("⏭️ 跳过无效帧")
                    time.sleep(0.1)
                    continue
                
                consecutive_failures = 0  # 重置失败计数
                frame_count += 1
                
                # 检测姿态
                keypoints = self._detect_pose(frame, confidence_threshold)
                if keypoints is None:
                    if frame_count % 10 == 0:  # 每10帧打印一次
                        print(f"📊 帧 {frame_count}: 未检测到姿态")
                    continue
                
                visible_keypoints = len([kp for kp in keypoints if kp[2] > 0.5])
                print(f"✅ 帧 {frame_count}: 检测到 {visible_keypoints}/8 个关键点")
                
                # 拉班运动分析
                laban_qualities = analyzer.calculate_laban_qualities(keypoints)
                emotion, emotion_scores = analyzer.recognize_emotion(laban_qualities)
                
                result = {
                    'timestamp': datetime.now().isoformat(),
                    'frame_count': frame_count,
                    'laban_qualities': laban_qualities,
                    'recognized_emotion': emotion,
                    'emotion_scores': emotion_scores,
                    'visible_keypoints': visible_keypoints
                }
                
                # 保存关键帧到本地存储
                if save_frames and frame_count % save_interval == 0:
                    try:
                        # 在帧上绘制姿态关键点
                        annotated_frame = self._draw_pose_keypoints(frame.copy(), keypoints)
                        
                        # 生成文件名
                        filename = storage_manager.generate_filename(
                            f"pose_frame_{frame_count}_{emotion}", ".jpg"
                        )
                        
                        # 保存带姿态标注的帧
                        saved_path = storage_manager.save_image_from_frame(
                            annotated_frame, filename, "pose_analysis"
                        )
                        
                        if saved_path:
                            result['saved_frame_path'] = saved_path
                            print(f"📁 帧 {frame_count} 已保存到: {saved_path}")
                        else:
                            print(f"⚠️ 帧 {frame_count} 保存失败")
                            
                    except Exception as e:
                        print(f"❌ 保存帧 {frame_count} 时出错: {e}")
                        logger.error(f"保存姿态帧失败: {e}")
                
                analysis_results.append(result)
                print(f"💭 帧 {frame_count}: 检测到情感 -> {emotion}")
                
                # 短暂休眠避免CPU过载
                time.sleep(0.1)
            
            # 统计分析
            if not analysis_results:
                return {
                    'success': False,
                    'message': '分析期间未检测到有效姿态数据',
                    'data': None
                }
            
            emotions = [r['recognized_emotion'] for r in analysis_results]
            emotion_counts = {}
            for emotion in emotions:
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else '未知'
            
            # 计算平均拉班质量
            avg_laban = {}
            for quality in ['weight', 'time', 'flow', 'space']:
                avg_laban[quality] = float(sum(r['laban_qualities'][quality] for r in analysis_results) / len(analysis_results))
            
            # 统计保存的帧数
            saved_frames = [r for r in analysis_results if 'saved_frame_path' in r]
            saved_frame_paths = [r['saved_frame_path'] for r in saved_frames]
            
            summary = {
                'duration_seconds': int(time.time() - start_time),
                'total_frames': frame_count,
                'valid_analyses': len(analysis_results),
                'dominant_emotion': dominant_emotion,
                'emotion_distribution': emotion_counts,
                'average_laban_qualities': avg_laban,
                'latest_results': analysis_results[-5:],  # 只保留最后5个结果
                'saved_frames_count': len(saved_frames),
                'saved_frame_paths': saved_frame_paths,
                'frame_saving_enabled': save_frames,
                'save_interval': save_interval
            }
            
            self._analysis_results.append(summary)
            
            print(f"🎉 姿态分析完成！处理{frame_count}帧，有效分析{len(analysis_results)}次")
            print(f"🎭 主导情感: {dominant_emotion}")
            
            return {
                'success': True,
                'message': f'实时分析完成，处理{frame_count}帧，有效分析{len(analysis_results)}次',
                'data': summary
            }
            
        except Exception as e:
            logger.error(f"实时分析异常: {e}")
            return {
                'success': False,
                'message': f'实时分析异常: {str(e)}',
                'data': None
            }
        finally:
            # 确保释放摄像头资源
            if cap is not None:
                cap.release()
                print("📹 姿态分析摄像头已释放")
            
            # 强制垃圾回收
            gc.collect()
            cv2.destroyAllWindows()  # 关闭所有OpenCV窗口
    
    def _get_analysis_summary(self) -> Dict[str, Any]:
        """获取分析汇总"""
        # 检测摄像头可用性
        available_cameras = self._detect_available_cameras()
        
        return {
            'total_analyses': len(self._analysis_results),
            'yolo_available': YOLO_AVAILABLE,
            'model_loaded': self._model is not None,
            'available_cameras': available_cameras,
            'camera_count': len(available_cameras),
            'analyzer_initialized': self._analyzer is not None,
            'keypoint_names': KEYPOINT_NAMES,
            'emotion_categories': list(LabanMovementAnalyzer().emotion_map.keys())
        }
    
    def _format_laban_analysis_dict(self, analysis_data: Dict) -> Dict[str, Any]:
        """将分析数据格式化为拉班分析字典"""
        if not analysis_data or 'average_laban_qualities' not in analysis_data:
            return None
            
        laban = analysis_data['average_laban_qualities']
        return {
            'space': {
                'direction': 'direct' if laban.get('space', 0) > 0 else 'indirect',
                'path': 'straight' if laban.get('space', 0) > 0.5 else 'curved',
                'range': 'wide' if abs(laban.get('space', 0)) > 0.5 else 'narrow'
            },
            'time': {
                'speed': 'fast' if laban.get('time', 0) > 0 else 'slow',
                'rhythm': 'regular' if abs(laban.get('time', 0)) < 0.5 else 'irregular',
                'duration': 'sustained' if laban.get('time', 0) < 0 else 'quick'
            },
            'weight': {
                'strength': 'strong' if laban.get('weight', 0) > 0 else 'light',
                'weight': 'heavy' if laban.get('weight', 0) > 0.5 else 'light',
                'energy': 'powerful' if laban.get('weight', 0) > 0 else 'gentle'
            },
            'flow': {
                'control': 'controlled' if laban.get('flow', 0) < 0 else 'free',
                'continuity': 'bound' if laban.get('flow', 0) < 0 else 'flowing',
                'tension': 'tense' if laban.get('flow', 0) < -0.5 else 'relaxed'
            },
            'movement_quality': analysis_data.get('dominant_emotion', '未知'),
            'raw_qualities': laban
        }

    def _run(
        self,
        action: str,
        model_path: str = "yolov8n-pose.pt",
        confidence_threshold: float = 0.5,
        duration: int = 10,
        save_frames: bool = True,
        save_interval: int = 30,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """执行工具操作"""
        try:
            logger.info(f"执行姿态分析操作: {action}")
            
            if action == "analyze_realtime":
                # 检查YOLO可用性
                if not YOLO_AVAILABLE:
                    return {
                        'success': False,
                        'message': 'YOLO未安装，请运行: pip install ultralytics',
                        'data': None,
                        'laban_analysis': None
                    }
                
                # 加载模型
                if not self._load_model(model_path):
                    return {
                        'success': False,
                        'message': f'无法加载YOLO模型: {model_path}',
                        'data': None,
                        'laban_analysis': None
                    }
                
                result = self._analyze_realtime(duration, confidence_threshold, save_frames, save_interval)
                
                # 如果分析成功，添加拉班分析数据到顶层
                if result['success'] and result['data']:
                    result['laban_analysis'] = self._format_laban_analysis_dict(result['data'])
                
                return result
                
            elif action == "get_summary":
                summary = self._get_analysis_summary()
                return {
                    'success': True,
                    'message': '获取分析汇总成功',
                    'data': summary,
                    'laban_analysis': None
                }
                
            else:
                return {
                    'success': False,
                    'message': f'不支持的操作类型: {action}',
                    'data': None,
                    'laban_analysis': None
                }
                
        except Exception as e:
            logger.error(f"工具执行异常: {e}")
            return {
                'success': False,
                'message': f'工具执行异常: {str(e)}',
                'data': None,
                'laban_analysis': None
            }

def main():
    """独立运行测试函数"""
    print("🤖 LETDANCE 姿态分析工具 - 简化版（8个关键点）")
    print("=" * 60)
    
    # 创建工具实例
    tool = PoseAnalysisTool()
    
    # 显示工具信息
    print(f"工具名称: {tool.name}")
    print(f"工具描述: {tool.description}")
    print(f"YOLO可用性: {YOLO_AVAILABLE}")
    print(f"关键点数量: {len(KEYPOINT_NAMES)}")
    print(f"关键点列表: {', '.join(KEYPOINT_NAMES)}")
    
    # 测试获取汇总
    print("\n📊 获取分析汇总...")
    summary_result = tool._run(action="get_summary")
    print(f"汇总结果: {summary_result}")
    
    # 如果YOLO可用，提供实时分析选项
    if YOLO_AVAILABLE:
        print("\n🎯 是否进行实时姿态分析？")
        choice = input("输入 y 进行5秒实时分析，其他键跳过: ").strip().lower()
        
        if choice == 'y':
            print("开始5秒实时姿态分析...")
            print("💡 注意：现在只使用8个关键点进行拉班运动分析")
            analysis_result = tool._run(
                action="analyze_realtime",
                duration=5,
                confidence_threshold=0.5
            )
            print(f"分析结果: {analysis_result}")
    else:
        print("\n⚠️  YOLO未安装，无法进行实时分析")
        print("安装命令: pip install ultralytics")
    
    print("\n✅ 测试完成")

if __name__ == "__main__":
    main()