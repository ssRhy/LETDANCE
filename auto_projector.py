#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LETDANCE 全自动投影系统
自动运行分析并立即投影，无需人为操作
"""

import json
import logging
import threading
import time
import webbrowser
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from main_agent import LetDanceWorkflow

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class EmotionMapper:
    """情绪关键词映射器"""
    
    KEYWORD_MAPPING = {
        # 主题1: 快乐/兴奋类 - 暖色调
        'theme1': {
            'keywords': ['energetic', 'upbeat', 'cheerful', 'joyful', 'vibrant', 'lively', 'happy', 'excited', 'bright', 'dynamic'],
            'emotion_text': '充满活力'
        },
        # 主题2: 平静/舒缓类 - 冷色调
        'theme2': {
            'keywords': ['ambient', 'calm', 'peaceful', 'relaxing', 'gentle', 'serene', 'soft', 'soothing', 'tranquil', 'mellow'],
            'emotion_text': '宁静舒缓'
        },
        # 主题3: 忧郁/深沉类 - 深色调
        'theme3': {
            'keywords': ['melancholic', 'contemplative', 'introspective', 'emotional', 'sad', 'thoughtful', 'moody', 'nostalgic', 'brooding', 'reflective'],
            'emotion_text': '深度思考'
        },
        # 主题4: 强烈/激情类 - 热色调
        'theme4': {
            'keywords': ['intense', 'powerful', 'dramatic', 'epic', 'strong', 'aggressive', 'passionate', 'bold', 'fierce', 'energizing'],
            'emotion_text': '强烈激情'
        }
    }
    
    @classmethod
    def map_keywords_to_themes(cls, keywords):
        """将关键词映射到情绪主题"""
        if not keywords:
            return {}
            
        result = {}
        for i, keyword in enumerate(keywords[:4]):  # 最多处理4个关键词
            best_theme = cls._find_best_theme(keyword.lower())
            theme_num = int(best_theme.replace('theme', ''))
            result[f'emotion{theme_num}'] = {
                'keyword': keyword,
                'emotion_text': cls.KEYWORD_MAPPING[best_theme]['emotion_text']
            }
        
        return result
    
    @classmethod
    def _find_best_theme(cls, keyword):
        """找到关键词最匹配的主题"""
        for theme, data in cls.KEYWORD_MAPPING.items():
            if keyword in data['keywords']:
                return theme
        
        # 如果没有直接匹配，使用简单的语义匹配
        if any(word in keyword for word in ['calm', 'soft', 'gentle', 'peace', 'quiet', 'slow']):
            return 'theme2'
        elif any(word in keyword for word in ['sad', 'dark', 'deep', 'melancholy', 'contemplative']):
            return 'theme3'
        elif any(word in keyword for word in ['hard', 'fast', 'strong', 'power', 'intense', 'dramatic']):
            return 'theme4'
        else:
            return 'theme1'  # 默认主题

class AutoProjectorHandler(SimpleHTTPRequestHandler):
    """自动投影处理器"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="projector_web", **kwargs)
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/emotions':
            emotions = getattr(self.server, 'current_emotions', {})
            self._send_json_response(emotions)
        elif parsed_path.path == '/api/status':
            self._send_json_response({'status': 'ready', 'auto_mode': True})
        else:
            super().do_GET()
    
    def _send_json_response(self, data, status=200):
        """发送JSON响应"""
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def log_message(self, format, *args):
        """禁用HTTP请求日志"""
        pass

class AutoProjectorSystem:
    """全自动投影系统"""
    
    def __init__(self, port=8080):
        self.port = port
        self.server = None
        self.workflow = None
        self.running = True
        
    def start_server(self):
        """启动Web服务器"""
        try:
            self.server = HTTPServer(('0.0.0.0', self.port), AutoProjectorHandler)
            self.server.current_emotions = {}
            
            logger.info(f" 自动投影系统启动: http://localhost:{self.port}/color.html")
            
            # 启动服务器线程
            server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            server_thread.start()
            
            #  立即设置默认投影状态 - 让投影仪马上有漂亮的色彩显示
            self._set_default_projection()
            
            return True
        except Exception as e:
            logger.error(f"启动服务器失败: {e}")
            return False

    def _set_default_projection(self):
        """设置默认投影状态 - 立即显示色彩效果"""
        # 使用情绪主题2（宁静舒缓的蓝色调）作为默认启动效果
        default_emotions = {
            'emotion2': {
                'keyword': 'ambient',
                'emotion_text': ' LETDANCE启动中...'
            }
        }
        self.server.current_emotions = default_emotions
        logger.info("🎨 已设置默认投影主题 - 投影仪将立即显示蓝色宁静效果")
    
    def update_projection(self, keywords):
        """更新投影效果"""
        try:
            emotions = EmotionMapper.map_keywords_to_themes(keywords)
            self.server.current_emotions = emotions
            
            logger.info(f"🎨 投影更新: {keywords} -> {list(emotions.keys())}")
            
            # 选择主要情绪主题进行投影
            if emotions:
                primary_emotion = list(emotions.keys())[0]
                emotion_data = emotions[primary_emotion]
                logger.info(f"🎯 主要投影主题: {emotion_data['emotion_text']} ({emotion_data['keyword']})")
            
            return True
        except Exception as e:
            logger.error(f"更新投影失败: {e}")
            return False
    
    def run_continuous_analysis(self, interval=30):
        """持续运行分析投影"""
        logger.info(f"🔄 开始持续分析，间隔{interval}秒")
        
        # 初始化工作流
        try:
            self.workflow = LetDanceWorkflow()
            logger.info("✅ LETDANCE工作流初始化成功")
        except Exception as e:
            logger.error(f"❌ 工作流初始化失败: {e}")
            return
        
        analysis_count = 0
        
        while self.running:
            try:
                analysis_count += 1
                logger.info(f"\n{'='*20} 第{analysis_count}轮分析 {'='*20}")
                
                # 运行分析
                result = self.workflow.analyze_and_generate_music_keywords(duration=10)
                
                if result['success'] and result['music_keywords']:
                    keywords = result['music_keywords']
                    logger.info(f"✅ 分析完成，关键词: {keywords}")
                    
                    # 立即更新投影
                    if self.update_projection(keywords):
                        logger.info("🎨 投影效果已自动更新")
                    
                    # 显示拉班分析摘要
                    if result.get('laban_analysis_text'):
                        logger.info("🤸 拉班动作分析完成")
                    
                else:
                    logger.warning(f"⚠️  分析未成功: {result.get('message', '未知错误')}")
                
                # 等待下一轮分析
                if self.running:
                    logger.info(f"⏳ 等待{interval}秒后进行下一轮分析...")
                    for i in range(interval):
                        if not self.running:
                            break
                        time.sleep(1)
                
            except KeyboardInterrupt:
                logger.info("🛑 收到停止信号")
                break
            except Exception as e:
                logger.error(f"❌ 分析过程异常: {e}")
                logger.info("⏳ 等待10秒后重试...")
                time.sleep(10)
    
    def stop(self):
        """停止系统"""
        self.running = False
        if self.server:
            self.server.shutdown()
            logger.info("🛑 系统已停止")

def open_projection_page(port):
    """自动打开投影页面"""
    def delayed_open():
        time.sleep(2)  # 等待服务器完全启动
        try:
            url = f"http://localhost:{port}/color.html"
            webbrowser.open(url)
            logger.info(f"🌐 已自动打开投影页面: {url}")
        except:
            logger.info(f"📋 请手动访问: http://localhost:{port}/color.html")
    
    threading.Thread(target=delayed_open, daemon=True).start()

def main():
    """主函数"""
    print("🎨 LETDANCE 全自动投影系统")
    print("="*50)
    print("🚀 系统将自动运行分析并立即投影")
    print("🎯 无需任何人为操作")
    print("🛑 按 Ctrl+C 可停止系统")
    print("="*50)
    
    # 创建自动投影系统
    projector = AutoProjectorSystem()
    
    try:
        # 启动Web服务器
        if not projector.start_server():
            return
        
        # 自动打开投影页面
        open_projection_page(projector.port)
        
        # 等待一下让服务器完全启动
        time.sleep(3)
        
        # 开始持续分析投影
        projector.run_continuous_analysis(interval=30)
        
    except KeyboardInterrupt:
        print("\n🛑 用户中断...")
    except Exception as e:
        logger.error(f"❌ 系统异常: {e}")
    finally:
        projector.stop()
        print("👋 LETDANCE投影系统已关闭")

if __name__ == "__main__":
    main() 