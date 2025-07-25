#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LETDANCE 主Agent执行器
基于LangChain的工作流，协调图像分析和姿态分析，生成音乐关键词
"""

import json
import logging
import os
from typing import Dict, Any, Optional
from pprint import pformat

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI

from tools import get_all_tools
from config import *
from config.azure_config import AzureConfig
from client import MusicGenClient
from microphone import play, play_async

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LetDanceWorkflow:
    """LETDANCE 主工作流"""
    
    def __init__(self):
        self.tools = get_all_tools()
        self.llm = self._initialize_llm()
        self.agent_executor = self._create_agent_executor()
        self.music_client = MusicGenClient()
        
    def _initialize_llm(self) -> AzureChatOpenAI:
        """初始化Azure OpenAI LLM"""
        # 验证配置
        if not AzureConfig.validate_config():
            raise ValueError("Azure配置不完整，请检查配置文件")
        
        # 获取配置并初始化LLM
        config = AzureConfig.get_azure_chat_config()
        logger.info(f"初始化Azure OpenAI LLM，部署名称: {config['azure_deployment']}")
        
        return AzureChatOpenAI(**config)
    
    def _create_agent_executor(self) -> AgentExecutor:
        """创建Agent执行器"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是LETDANCE的智能分析助手。你需要使用同一个摄像头**按顺序执行**以下任务：

 **第一步：图像分析（快速拍照）**
- 使用 image_analysis 工具拍照并分析用户面部情感
- 这个步骤很快完成，会自动释放摄像头资源

 **第二步：姿态分析（实时检测）** 
- 等待第一步完成后，使用 pose_analysis 工具进行实时姿态分析
- 这将持续分析用户的肢体动作情感

**第三步：生成音乐关键词**
- 综合两种分析结果，生成4个英文音乐风格关键词

**重要提醒：**
- 必须按顺序执行，不能同时调用两个摄像头工具
- 先等图像分析完全完成，再开始姿态分析
- 确保每个步骤都成功完成后再进行下一步"""),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        return AgentExecutor(
            agent=agent, 
            tools=self.tools, 
            verbose=True,
            max_iterations=6,  # 增加迭代次数，确保有足够步骤
            early_stopping_method="generate"
        )
    
    def _format_laban_analysis(self, pose_data: Dict) -> str:
        """格式化拉班动作理论分析结果"""
        if not pose_data or not pose_data.get('success'):
            return "未获取到拉班分析数据"
        
        # 从新的数据结构中获取拉班分析
        laban = pose_data.get('laban_analysis')
        if not laban:
            return "拉班分析数据不可用"
            
        return f"""
拉班动作分析结果:
================
空间维度 (Space):
- 方向性: {laban.get('space', {}).get('direction', 'N/A')}
- 路径: {laban.get('space', {}).get('path', 'N/A')}
- 范围: {laban.get('space', {}).get('range', 'N/A')}

时间维度 (Time):
- 速度: {laban.get('time', {}).get('speed', 'N/A')}
- 节奏: {laban.get('time', {}).get('rhythm', 'N/A')}
- 持续性: {laban.get('time', {}).get('duration', 'N/A')}

力量维度 (Weight):
- 强度: {laban.get('weight', {}).get('strength', 'N/A')}
- 重量: {laban.get('weight', {}).get('weight', 'N/A')}
- 能量: {laban.get('weight', {}).get('energy', 'N/A')}

流动维度 (Flow):
- 控制度: {laban.get('flow', {}).get('control', 'N/A')}
- 连贯性: {laban.get('flow', {}).get('continuity', 'N/A')}
- 张力: {laban.get('flow', {}).get('tension', 'N/A')}

动作质量: {laban.get('movement_quality', 'N/A')}
主导情感: {pose_data.get('data', {}).get('dominant_emotion', 'N/A')}
"""
    
    def analyze_and_generate_music_keywords(self, duration: int = 10) -> Dict[str, Any]:
        """执行完整的分析流程并生成音乐关键词"""
        try:
            logger.info("开始LETDANCE分析流程")
            
            # 构建更简单直接的提示词
            input_message = f"""请按顺序执行以下分析：

1. 使用image_analysis工具拍照并分析用户情感：
   - action: capture_and_analyze
   - analysis_prompt: 分析用户情感状态和表情

2. 使用pose_analysis工具进行{duration}秒实时姿态分析：
   - action: analyze_realtime  
   - duration: {duration}
   - confidence_threshold: 0.5

3. 基于两个分析结果生成4个英文音乐风格关键词。

请确保两个工具都被调用，然后提供最终的音乐关键词。"""

            # 执行Agent工作流
            result = self.agent_executor.invoke({"input": input_message})
            
            # 从Agent的中间步骤中提取工具结果
            pose_data = None
            image_data = None
            
            # 检查Agent执行历史中的工具调用结果
            if hasattr(result, 'intermediate_steps'):
                for step in result.intermediate_steps:
                    if len(step) >= 2:
                        action, observation = step[0], step[1]
                        if hasattr(action, 'tool') and action.tool == 'pose_analysis':
                            if isinstance(observation, dict):
                                pose_data = observation
                        elif hasattr(action, 'tool') and action.tool == 'image_analysis':
                            if isinstance(observation, dict):
                                image_data = observation

            # 从Agent输出中提取音乐关键词
            music_keywords = self._extract_music_keywords(result['output'])
            
            return {
                'success': True,
                'message': '分析完成，音乐关键词已生成',
                'agent_output': result['output'],
                'pose_analysis': pose_data,
                'image_analysis': image_data,
                'laban_analysis_text': self._format_laban_analysis(pose_data) if pose_data else None,
                'music_keywords': music_keywords,
                'ready_for_music_generation': True
            }
            
        except Exception as e:
            logger.error(f"分析流程异常: {e}")
            return {
                'success': False,
                'message': f'分析流程异常: {str(e)}',
                'music_keywords': [],
                'ready_for_music_generation': False
            }
    
    def _extract_music_keywords(self, agent_output: str) -> list:
        """从Agent输出中提取音乐关键词"""
        try:
            # 使用LLM提取关键词
            extraction_prompt = f"""
            从以下分析结果中提取4个音乐风格关键词。
            
            分析结果：
            {agent_output}
            
            请只返回4个英文音乐风格关键词，用逗号分隔，例如：ambient, emotional, energetic, peaceful
            """
            
            response = self.llm.invoke([HumanMessage(content=extraction_prompt)])
            keywords_text = response.content.strip()
            
            # 解析关键词
            keywords = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]
            return keywords[:4]  # 确保只返回4个关键词
            
        except Exception as e:
            logger.error(f"关键词提取失败: {e}")
            return ["ambient", "emotional", "calm", "contemplative"]  # 默认关键词
    
    def generate_music(self, keywords: list) -> Dict[str, Any]:
        """音乐生成接口"""
        logger.info(f"音乐生成接口被调用，关键词: {keywords}")
        
        try:
            # 将关键词转换为音乐生成提示词
            prompt = ", ".join(keywords)
            logger.info(f"生成音乐提示词: {prompt}")
            
            # 调用音乐生成客户端
            music_file = self.music_client.generate_music(prompt)
            
            # 检查音乐文件是否生成成功
            if music_file is None:
                logger.error("音乐生成失败：外部服务返回空文件路径")
                return {
                    'success': False,
                    'message': '音乐生成失败：外部服务无法生成音乐',
                    'keywords_used': keywords,
                    'music_file': None
                }
            
            # 检查文件是否真实存在
            if not os.path.exists(music_file):
                logger.error(f"音乐文件不存在: {music_file}")
                return {
                    'success': False,
                    'message': f'音乐生成失败：文件不存在 {music_file}',
                    'keywords_used': keywords,
                    'music_file': None
                }
            
            # 自动播放生成的音乐（异步播放，带验证）
            logger.info(f"开始播放音乐: {music_file}")
            
            # 启动异步播放并等待一小段时间验证
            import time
            play_thread = play_async(music_file)
            
            # 等待0.5秒，让播放线程启动
            time.sleep(0.5)
            
            # 检查线程是否还活着（如果立即退出说明播放失败）
            if not play_thread.is_alive():
                logger.error("音频播放线程异常退出")
                return {
                    'success': False,
                    'message': '音乐生成成功但播放失败，请检查音频设备',
                    'keywords_used': keywords,
                    'music_file': music_file
                }
            
            logger.info("音频播放已成功启动")
            
            return {
                'success': True,
                'message': '音乐生成成功并已开始播放',
                'keywords_used': keywords,
                'music_file': music_file
            }
        except Exception as e:
            logger.error(f"音乐生成失败: {e}")
            return {
                'success': False,
                'message': f'音乐生成失败: {str(e)}',
                'keywords_used': keywords,
                'music_file': None
            }
    
    def run_complete_workflow(self, duration: int = 10) -> Dict[str, Any]:
        """运行完整工作流：分析 -> 生成音乐关键词 -> 生成音乐"""
        # 步骤1: 分析并生成关键词
        analysis_result = self.analyze_and_generate_music_keywords(duration)
        
        if not analysis_result['success']:
            return analysis_result
        
        # 步骤2: 生成音乐
        music_result = self.generate_music(analysis_result['music_keywords'])
        
        return {
            'success': True,
            'message': '完整工作流执行完成',
            'analysis_result': analysis_result,
            'music_result': music_result,
            'final_keywords': analysis_result['music_keywords']
        }

def main():
    """主函数"""
    try:
        # 创建工作流
        workflow = LetDanceWorkflow()
        logger.info("LETDANCE工作流初始化成功")
        
        # 执行完整分析流程
        result = workflow.run_complete_workflow(duration=10)
        
        # 输出结果
        print("\n" + "="*50)
        print("LETDANCE 分析结果")
        print("="*50)
        print(f"执行状态: {'成功' if result['success'] else '失败'}")
        print(f"消息: {result['message']}")
        
        if result['success']:
            # 显示拉班分析结果
            if result['analysis_result'].get('laban_analysis_text'):
                print("\n拉班动作理论分析:")
                print(result['analysis_result']['laban_analysis_text'])
            
            print("\n生成的音乐关键词:")
            print(", ".join(result['final_keywords']))
            
            # 显示音乐生成结果
            if result['music_result']['success']:
                print(f"\n音乐生成成功并已开始播放！")
                print(f"音乐文件路径: {result['music_result']['music_file']}")
                print("提示: 按 Ctrl+C 可停止播放")
            else:
                print(f"\n音乐生成失败: {result['music_result']['message']}")
            
            # 显示详细的姿态分析数据（调试模式）
            if logger.level == logging.DEBUG and result['analysis_result'].get('pose_analysis'):
                print("\n详细姿态分析数据 (DEBUG):")
                print(pformat(result['analysis_result']['pose_analysis']))
        
        return result
        
    except Exception as e:
        logger.error(f"主函数执行异常: {e}")
        return {
            'success': False,
            'message': f'主函数执行异常: {str(e)}'
        }

if __name__ == "__main__":
    main() 