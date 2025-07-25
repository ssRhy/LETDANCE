#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LETDANCE 主启动脚本
一键启动所有功能：
1. Web服务（情绪分析）
2. 自动投影系统
3. 智能分析工作流（图像+姿态+音乐生成）
4. 其他扩展功能
"""

import os
import sys
import time
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from pprint import pformat

# 确保项目根目录在Python路径中
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入音乐生成相关模块
from client import MusicGenClient
from microphone import play_async

# 导入LangChain工作流相关模块
try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.messages import HumanMessage
    from langchain_openai import AzureChatOpenAI
    from tools import get_all_tools
    from config.azure_config import AzureConfig
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    logging.warning(f"LangChain模块导入失败: {e}，智能分析功能将不可用")
    LANGCHAIN_AVAILABLE = False

def setup_logging():
    """配置日志系统"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # 创建logs目录
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/letdance.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

def check_dependencies() -> bool:
    """检查所有必要的依赖和文件"""
    required_files = [
        'auto_projector.py',
        'simple_flask_app.py',
        'client.py',
        'microphone.py',
        'projector_web/color.html',
        'projector_web/script.js',
        'projector_web/style.css',
        'templates/index.html',
        'static/css/style.css',
        'static/js/app.js'
    ]
    
    required_dirs = [
        'templates',
        'static',
        'logs',
        'data',
        'generated_music'
    ]
    
    # 检查目录
    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            os.makedirs(dir_path)
            logging.info(f"创建目录: {dir_path}")
    
    # 检查文件
    missing_files = []
    for file in required_files:
        if not (project_root / file).exists():
            missing_files.append(file)
    
    if missing_files:
        logging.error("缺少必要文件:")
        for file in missing_files:
            logging.error(f" - {file}")
        return False
    
    logging.info("✅ 所有依赖检查完成")
    return True

class LetDanceWorkflow:
    """LETDANCE 智能分析工作流"""
    
    def __init__(self):
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain依赖不可用，无法初始化智能分析工作流")
        
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
        logging.info(f"初始化Azure OpenAI LLM，部署名称: {config['azure_deployment']}")
        
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
            max_iterations=6,
            early_stopping_method="generate"
        )
    
    def analyze_and_generate_music_keywords(self, duration: int = 10) -> Dict[str, Any]:
        """执行完整的分析流程并生成音乐关键词"""
        try:
            logging.info("开始LETDANCE智能分析流程")
            
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
            
            # 提取音乐关键词
            music_keywords = self._extract_music_keywords(result['output'])
            
            return {
                'success': True,
                'message': '智能分析完成，音乐关键词已生成',
                'agent_output': result['output'],
                'music_keywords': music_keywords,
                'ready_for_music_generation': True
            }
            
        except Exception as e:
            logging.error(f"智能分析流程异常: {e}")
            return {
                'success': False,
                'message': f'智能分析流程异常: {str(e)}',
                'music_keywords': [],
                'ready_for_music_generation': False
            }
    
    def _extract_music_keywords(self, agent_output: str) -> list:
        """从Agent输出中提取音乐关键词"""
        try:
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
            logging.error(f"关键词提取失败: {e}")
            return ["ambient", "emotional", "calm", "contemplative"]  # 默认关键词
    
    def generate_music(self, keywords: list) -> Dict[str, Any]:
        """使用类内部的音乐客户端生成音乐"""
        try:
            # 检查音乐生成服务状态
            if not self.music_client.check_health():
                logging.warning("音乐生成服务不可用，跳过音乐生成")
                return {'success': False, 'message': '音乐生成服务不可用'}
            
            # 将关键词转换为提示词
            prompt = ", ".join(keywords)
            logging.info(f"开始生成音乐，关键词: {prompt}")
            
            # 生成音乐
            music_file = self.music_client.generate_music(prompt)
            
            if music_file and os.path.exists(music_file):
                logging.info(f"音乐生成成功: {music_file}")
                
                # 异步播放音乐
                play_thread = play_async(music_file)
                logging.info("音乐开始播放")
                
                return {
                    'success': True,
                    'message': '音乐生成成功并已开始播放',
                    'music_file': music_file
                }
            else:
                logging.error("音乐生成失败")
                return {'success': False, 'message': '音乐生成失败'}
                
        except Exception as e:
            logging.error(f"音乐生成异常: {e}")
            return {'success': False, 'message': f'音乐生成异常: {str(e)}'}
    
    def run_complete_workflow(self, duration: int = 10) -> Dict[str, Any]:
        """运行完整工作流：分析 -> 生成音乐关键词 -> 生成音乐"""
        # 步骤1: 智能分析并生成关键词
        analysis_result = self.analyze_and_generate_music_keywords(duration)
        
        if not analysis_result['success']:
            return analysis_result
        
        # 步骤2: 使用类内部的音乐客户端生成音乐
        music_result = self.generate_music(analysis_result['music_keywords'])
        
        return {
            'success': True,
            'message': '完整智能工作流执行完成',
            'analysis_result': analysis_result,
            'music_result': music_result,
            'final_keywords': analysis_result['music_keywords']
        }

# 全局工作流实例
workflow_instance = None

def initialize_workflow():
    """初始化智能分析工作流"""
    global workflow_instance
    try:
        if LANGCHAIN_AVAILABLE:
            workflow_instance = LetDanceWorkflow()
            logging.info("智能分析工作流初始化成功")
            return True
        else:
            logging.warning("LangChain不可用，智能分析功能将不可用")
            return False
    except Exception as e:
        logging.error(f"智能分析工作流初始化失败: {e}")
        return False

def start_intelligent_analysis(duration: int = 10):
    """启动智能分析（图像+姿态+音乐生成）"""
    global workflow_instance
    
    if workflow_instance is None:
        logging.error("智能分析工作流未初始化")
        return {
            'success': False,
            'message': '智能分析工作流未初始化'
        }
    
    try:
        logging.info("开始智能分析工作流...")
        result = workflow_instance.run_complete_workflow(duration)
        
        # 输出结果
        print("\n" + "="*50)
        print("🎵 LETDANCE 智能分析结果")
        print("="*50)
        print(f"执行状态: {'成功' if result['success'] else '失败'}")
        print(f"消息: {result['message']}")
        
        if result['success']:
            print("\n生成的音乐关键词:")
            print(", ".join(result['final_keywords']))
            
            if result['music_result']['success']:
                print(f"\n🎵 音乐生成成功并已开始播放！")
                print(f"音乐文件: {result['music_result']['music_file']}")
            else:
                print(f"\n❌ 音乐生成失败: {result['music_result']['message']}")
        
        return result
        
    except Exception as e:
        logging.error(f"智能分析工作流执行异常: {e}")
        return {
            'success': False,
            'message': f'智能分析工作流执行异常: {str(e)}'
        }

def generate_and_play_music(keywords: str = "ambient, emotional, calm, contemplative"):
    """生成并播放音乐"""
    logger = logging.getLogger(__name__)
    
    try:
        # 初始化音乐生成客户端
        music_client = MusicGenClient()
        
        # 检查音乐生成服务状态
        if not music_client.check_health():
            logger.warning("音乐生成服务不可用，跳过音乐生成")
            return {'success': False, 'message': '音乐生成服务不可用'}
        
        logger.info(f"开始生成音乐，关键词: {keywords}")
        
        # 生成音乐
        music_file = music_client.generate_music(keywords)
        
        if music_file and os.path.exists(music_file):
            logger.info(f"音乐生成成功: {music_file}")
            
            # 异步播放音乐
            play_thread = play_async(music_file)
            logger.info("音乐开始播放")
            
            return {
                'success': True,
                'message': '音乐生成成功并已开始播放',
                'music_file': music_file
            }
        else:
            logger.error("音乐生成失败")
            return {'success': False, 'message': '音乐生成失败'}
            
    except Exception as e:
        logger.error(f"音乐生成异常: {e}")
        return {'success': False, 'message': f'音乐生成异常: {str(e)}'}

def start_web_service(host: str = '0.0.0.0', port: int = 5000):
    """启动Web服务"""
    from simple_flask_app import app
    logging.info(f"启动Web服务 http://{host}:{port}")
    app.run(host=host, port=port, debug=False)

def start_projector():
    """启动投影系统"""
    try:
        from auto_projector import main as projector_main
        logging.info("启动自动投影系统")
        projector_main()
    except Exception as e:
        logging.error(f"投影系统启动失败: {e}")

def main():
    """主函数"""
    print("""
🎵 LETDANCE 智能舞蹈系统启动
================================
1. Web服务（情绪分析）
2. 自动投影系统
3. 智能分析工作流（图像+姿态+音乐）
4. 其他扩展功能
================================
    """)
    
    # 设置日志
    logger = setup_logging()
    
    # 检查依赖
    if not check_dependencies():
        logger.error("依赖检查失败，系统启动中止")
        sys.exit(1)
    
    # 初始化智能分析工作流
    initialize_workflow()
    
    try:
        # 创建线程启动各个服务
        web_thread = threading.Thread(
            target=start_web_service,
            args=('0.0.0.0', 5000),
            daemon=True
        )
        
        projector_thread = threading.Thread(
            target=start_projector,
            daemon=True
        )
        
        # 启动所有服务
        web_thread.start()
        logger.info("Web服务启动成功")
        
        projector_thread.start()
        logger.info("投影系统启动成功")
        
        logger.info("智能分析工作流已就绪")
        
        # 保持主线程运行
        print("\n提示:")
        print("- 系统已启动，按 Ctrl+C 退出")
        print("- 访问 http://localhost:5000 使用Web界面")
        print("- 使用 generate_and_play_music('关键词') 生成音乐")
        print("- 使用 start_intelligent_analysis(10) 开始智能分析")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭系统...")
    except Exception as e:
        logger.error(f"系统运行出错: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 