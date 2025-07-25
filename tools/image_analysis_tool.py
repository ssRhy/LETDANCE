#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LETDANCE 图像分析工具
基于LangChain的图像分析工具，支持摄像头拍照和Azure OpenAI图像分析
"""

import os
import cv2
import json
import time
import base64
import logging
import numpy as np
from datetime import datetime
from typing import Optional, Dict, List, Type, Any

from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field

try:
    from openai import AzureOpenAI
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logging.warning("Azure OpenAI未安装，图像分析功能将不可用")

# 导入图像存储管理器
from .image_storage_utils import storage_manager

# Azure OpenAI配置已直接填入，无需导入config

# 配置日志
logger = logging.getLogger(__name__)

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

class ImageAnalysisInput(BaseModel):
    """图像分析工具输入模型"""
    action: str = Field(
        description="操作类型：'capture_and_analyze'(拍照并分析), 'analyze_file'(分析文件), 'get_summary'(获取汇总)"
    )
    image_path: Optional[str] = Field(
        default=None,
        description="图像文件路径（当action为analyze_file时必需）"
    )
    analysis_prompt: Optional[str] = Field(
        default="请分析这张图片中的人物情感状态，并根据情感推荐合适的音乐风格。包括：1.人物表情和肢体语言分析 2.情感状态判断 3.音乐风格推荐",
        description="自定义分析提示词"
    )

class ImageAnalysisTool(BaseTool):
    """LangChain图像分析工具"""
    
    name: str = "image_analysis"
    description: str = """
    图像分析工具，支持以下功能：
    1. 拍照并分析：从摄像头拍照并进行AI分析
    2. 分析文件：分析指定的图像文件
    3. 获取汇总：获取分析结果汇总
    
    使用示例：
    - {"action": "capture_and_analyze"} - 拍照并分析情感
    - {"action": "analyze_file", "image_path": "photo.jpg"} - 分析指定文件
    - {"action": "get_summary"} - 获取分析汇总
    """
    args_schema: Type[BaseModel] = ImageAnalysisInput
    # 移除 return_direct，让Agent能够处理工具输出
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 延迟初始化组件，避免在工具创建时就加载所有依赖
        self._azure_client = None
        self._camera_manager = None
        self._analysis_results = []
    
    def _get_camera_manager(self):
        """获取摄像头管理器（简化版，直接使用OpenCV）"""
        # 不再依赖外部camera_manager模块，直接返回True表示可用
        logger.info("使用内置摄像头管理")
        return True
    
    def _get_azure_client(self):
        """获取Azure OpenAI客户端（延迟加载）"""
        if self._azure_client is None:
            if not AZURE_AVAILABLE:
                logger.error("Azure OpenAI未安装")
                self._azure_client = False
                return None
            
            try:
                # 配置代理设置
                try:
                    from proxy_manager import configure_proxy_settings
                    configure_proxy_settings()
                except ImportError:
                    logger.warning("代理管理器未找到，使用默认网络设置")
                
                self._azure_client = AzureOpenAI(
                    azure_endpoint="https://ai-philxia4932ai122623990161.openai.azure.com/",
                    api_key="ES3vLOAy8MUTMui8udIAk2vZO1Fo7qCBHKlaAvcprOXicYTkjzwbJQQJ99BDACHYHv6XJ3w3AAAAACOG4FT8",
                    api_version="2024-02-15-preview"
                )
                logger.info("Azure OpenAI客户端初始化成功")
            except Exception as e:
                logger.error(f"Azure OpenAI客户端初始化失败: {e}")
                self._azure_client = False
        
        return self._azure_client if self._azure_client is not False else None
    
    def _capture_photo(self) -> Optional[Dict[str, Any]]:
        """从摄像头拍照并返回图像数据和保存路径（改进版，使用统一的摄像头接口）"""
        import gc
        
        # 强制清理资源
        gc.collect()
        
        cap = None
        try:
            # 尝试使用第一个可用摄像头
            for camera_id in range(3):
                try:
                    print(f"尝试打开摄像头 {camera_id} 进行拍照...")
                    cap = cv2.VideoCapture(camera_id)
                    if cap.isOpened():
                        # 设置摄像头参数
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        
                        # 等待摄像头稳定
                        time.sleep(1)
                        
                        # 尝试读取几帧，取最后一帧
                        for _ in range(3):
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                break
                        
                        if ret and frame is not None and frame.size > 0:
                            print(f"✅ 成功从摄像头 {camera_id} 拍照")
                            
                            # 将图像编码为字节数据
                            _, buffer = cv2.imencode('.jpg', frame)
                            image_data = buffer.tobytes()
                            
                            # 保存图像到本地存储
                            filename = storage_manager.generate_filename("captured_photo", ".jpg")
                            saved_path = storage_manager.save_image_from_bytes(
                                image_data, filename, "image_analysis"
                            )
                            
                            if saved_path:
                                print(f"📁 图像已保存到: {saved_path}")
                            else:
                                print("⚠️ 图像保存失败，但继续进行分析")
                            
                            return {
                                'image_data': image_data,
                                'saved_path': saved_path,
                                'frame': frame.copy()  # 保留原始帧供后续使用
                            }
                        else:
                            print(f"❌ 摄像头 {camera_id} 无法读取有效数据")
                            
                except Exception as e:
                    print(f"❌ 摄像头 {camera_id} 拍照失败: {e}")
                finally:
                    if cap is not None:
                        cap.release()
                        cap = None
            
            logger.error("所有摄像头都无法用于拍照")
            return None
            
        except Exception as e:
            logger.error(f"拍照过程异常: {e}")
            return None
        finally:
            # 确保资源释放
            if cap is not None:
                cap.release()
            gc.collect()
            cv2.destroyAllWindows()
            print("📸 拍照完成，摄像头资源已释放")
    
    def _encode_image_to_base64(self, image_data: bytes) -> Optional[str]:
        """将图像数据编码为base64"""
        try:
            return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            logger.error(f"图像编码失败: {e}")
            return None
    
    def _encode_file_to_base64(self, image_path: str) -> Optional[str]:
        """将图像文件编码为base64"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"文件编码失败: {e}")
            return None
    
    def _analyze_image(self, base64_image: str, prompt: str) -> Dict[str, Any]:
        """使用Azure OpenAI分析图像"""
        azure_client = self._get_azure_client()
        if not azure_client:
            return {
                'success': False,
                'message': 'Azure OpenAI客户端未初始化',
                'analysis': None
            }
        
        try:
            response = azure_client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            analysis_result = response.choices[0].message.content
            
            result = {
                'success': True,
                'message': '图像分析完成',
                'analysis': analysis_result,
                'timestamp': datetime.now().isoformat(),
                'prompt_used': prompt
            }
            
            return result
            
        except Exception as e:
            logger.error(f"图像分析失败: {e}")
            return {
                'success': False,
                'message': f'分析失败: {str(e)}',
                'analysis': None
            }
    
    def _capture_and_analyze(self, prompt: str) -> Dict[str, Any]:
        """拍照并分析（改进版）"""
        print("🔍 开始图像分析：拍照 -> 保存 -> 编码 -> AI分析")
        
        # 拍照（内部已包含资源管理和本地保存）
        capture_result = self._capture_photo()
        if not capture_result:
            return {
                'success': False,
                'message': '拍照失败，无法访问摄像头',
                'data': None
            }
        
        # 编码图像
        base64_image = self._encode_image_to_base64(capture_result['image_data'])
        if not base64_image:
            return {
                'success': False,
                'message': '图像编码失败',
                'data': None
            }
        
        print("🤖 正在进行AI图像分析...")
        
        # 分析图像
        result = self._analyze_image(base64_image, prompt)
        
        # 添加保存的图像路径信息
        if result['success']:
            result['saved_image_path'] = capture_result['saved_path']
            result['image_stored_locally'] = capture_result['saved_path'] is not None
            self._analysis_results.append(result)
            print("✅ 图像分析完成")
        else:
            print("❌ 图像分析失败")
        
        return {
            'success': result['success'],
            'message': '拍照分析完成' if result['success'] else result['message'],
            'data': result,
            'saved_image_path': capture_result['saved_path']
        }
    
    def _analyze_file(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """分析指定图像文件"""
        if not os.path.exists(image_path):
            return {
                'success': False,
                'message': f'图像文件不存在: {image_path}',
                'data': None
            }
        
        # 编码图像文件
        base64_image = self._encode_file_to_base64(image_path)
        if not base64_image:
            return {
                'success': False,
                'message': '图像文件编码失败',
                'data': None
            }
        
        # 分析图像
        result = self._analyze_image(base64_image, prompt)
        result['image_path'] = image_path
        
        if result['success']:
            self._analysis_results.append(result)
        
        return {
            'success': result['success'],
            'message': '文件分析完成' if result['success'] else result['message'],
            'data': result
        }
    
    def _get_analysis_summary(self) -> Dict[str, Any]:
        """获取分析汇总"""
        successful = len([r for r in self._analysis_results if r.get('success', False)])
        failed = len(self._analysis_results) - successful
        
        # 获取最新分析结果
        latest_analysis = None
        if self._analysis_results:
            latest_analysis = self._analysis_results[-1]
        
        return {
            'total_analyses': len(self._analysis_results),
            'successful': successful,
            'failed': failed,
            'latest_analysis': latest_analysis,
            'camera_available': self._get_camera_manager() is not None,
            'azure_client_available': self._get_azure_client() is not None
        }
    
    def _run(
        self,
        action: str,
        image_path: Optional[str] = None,
        analysis_prompt: str = "请分析这张图片中的人物情感状态，并根据情感推荐合适的音乐风格。包括：1.人物表情和肢体语言分析 2.情感状态判断 3.音乐风格推荐",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """执行工具操作"""
        try:
            logger.info(f"执行图像分析操作: {action}")
            
            if action == "capture_and_analyze":
                result = self._capture_and_analyze(analysis_prompt)
                
            elif action == "analyze_file":
                if not image_path:
                    return {
                        'success': False,
                        'message': '缺少image_path参数',
                        'data': None
                    }
                
                result = self._analyze_file(image_path, analysis_prompt)
                
            elif action == "get_summary":
                summary = self._get_analysis_summary()
                result = {
                    'success': True,
                    'message': '获取分析汇总成功',
                    'data': summary
                }
                
            else:
                result = {
                    'success': False,
                    'message': f'不支持的操作类型: {action}',
                    'data': None
                }
            
            # 确保结果可以JSON序列化
            safe_result = ensure_json_serializable(result)
            return safe_result
                
        except Exception as e:
            logger.error(f"工具执行异常: {e}")
            return {
                'success': False,
                'message': f'工具执行异常: {str(e)}',
                'data': None
            }

def main():
    """独立运行测试函数"""
    print("�� LETDANCE 图像分析工具 - 独立测试")
    print("=" * 50)
    
    # 创建工具实例
    tool = ImageAnalysisTool()
    
    # 显示工具信息
    print(f"工具名称: {tool.name}")
    print(f"工具描述: {tool.description}")
    print(f"Azure OpenAI可用性: {AZURE_AVAILABLE}")
    
    # 测试获取汇总
    print("\n📊 获取分析汇总...")
    summary_result = tool._run(action="get_summary")
    print(f"汇总结果: {summary_result}")
    
    # 如果Azure OpenAI可用，提供分析选项
    if AZURE_AVAILABLE:
        print("\n🎯 选择分析模式:")
        print("1. 拍照并分析 (需要摄像头)")
        print("2. 分析本地图像文件")
        print("3. 跳过分析测试")
        
        choice = input("请选择 (1/2/3): ").strip()
        
        if choice == '1':
            print("开始拍照并分析...")
            analysis_result = tool._run(action="capture_and_analyze")
            print(f"分析结果: {analysis_result}")
            
        elif choice == '2':
            image_path = input("请输入图像文件路径: ").strip()
            if image_path and os.path.exists(image_path):
                print(f"分析图像文件: {image_path}")
                analysis_result = tool._run(
                    action="analyze_file",
                    image_path=image_path
                )
                print(f"分析结果: {analysis_result}")
            else:
                print("文件不存在或路径为空")
                
        else:
            print("跳过分析测试")
    else:
        print("\n⚠️  Azure OpenAI未安装，无法进行图像分析")
        print("安装命令: pip install openai")
    
    print("\n✅ 测试完成")

if __name__ == "__main__":
    main()