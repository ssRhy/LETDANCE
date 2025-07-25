#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LETDANCE 心情记录Web应用
简化版本，专注于情绪分析功能
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from flask import Flask, render_template, request, jsonify, session
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI

from config.azure_config import AzureConfig

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask应用
app = Flask(__name__)
app.secret_key = 'letdance_secret_key_2024'

class EmotionAnalysisAgent:
    """情绪分析Agent - 简化版本，专注于情绪分析"""
    
    def __init__(self):
        self.llm = self._initialize_llm()
        
        # 情绪雷达图维度定义
        self.emotion_dimensions = [
            "快乐", "悲伤", "愤怒", "恐惧", "惊讶", "厌恶", "平静", "兴奋"
        ]
        
        # 情绪分析提示模板
        self.emotion_prompt = ChatPromptTemplate.from_template("""
        你是专业的情绪分析专家。请分析用户的心情描述，提取情绪关键词。

        用户心情: {mood_input}

        请完成以下任务：
        1. 分析当前心情的核心情绪（如：开心、焦虑、平静等）
        2. 提取3-4个情绪关键词（中英文均可）
        3. 推荐适合的音乐风格
        4. **重要**：为以下8个情绪维度评分（0-10分）：快乐、悲伤、愤怒、恐惧、惊讶、厌恶、平静、兴奋

        请以JSON格式返回结果：
        {{
            "core_emotion": "核心情绪",
            "keywords": ["关键词1", "关键词2", "关键词3"],
            "music_style": ["音乐风格1", "音乐风格2"],
            "emotion_radar": {{
                "快乐": 7,
                "悲伤": 2,
                "愤怒": 1,
                "恐惧": 3,
                "惊讶": 5,
                "厌恶": 1,
                "平静": 6,
                "兴奋": 4
            }}
        }}
        """)
    
    def _initialize_llm(self) -> AzureChatOpenAI:
        """初始化Azure OpenAI LLM"""
        try:
            config = AzureConfig()
            llm = AzureChatOpenAI(
                azure_endpoint=config.azure_endpoint,
                api_key=config.api_key,
                api_version=config.api_version,
                deployment_name=config.deployment_name,
                temperature=0.7,
                max_tokens=1000
            )
            logger.info("Azure OpenAI LLM 初始化成功")
            return llm
        except Exception as e:
            logger.error(f"LLM初始化失败: {e}")
            raise e
    

    
    def analyze_mood(self, user_id: str, mood_input: str) -> Dict[str, Any]:
        """分析用户心情，包含雷达图数据"""
        try:
            # 构建prompt并调用LLM
            prompt = self.emotion_prompt.format(mood_input=mood_input)
            response = self.llm.invoke(prompt)
            
            # 解析回复
            analysis_result = self._parse_llm_response(response.content)
            
            logger.info(f"用户 {user_id} 情绪分析完成: {analysis_result['core_emotion']}")
            
            return {
                'success': True,
                'message': f'心情 "{mood_input}" 分析完成',
                'analysis': analysis_result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"情绪分析失败: {e}")
            return {
                'success': False,
                'error': f'分析失败: {str(e)}',
                'analysis': self._get_default_analysis()
            }
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """解析LLM响应，提取JSON内容"""
        try:
            import json
            import re
            
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                # 确保包含雷达图数据
                if 'emotion_radar' not in result:
                    result['emotion_radar'] = self._generate_default_radar_scores()
                return result
            
            # 如果没有JSON，手动解析
            return self._manual_parse(response_text)
            
        except Exception as e:
            logger.warning(f"解析LLM响应失败: {e}")
            return self._get_default_analysis()
    
    def _manual_parse(self, text: str) -> Dict[str, Any]:
        """手动解析LLM回复"""
        return {
            "core_emotion": "平静",
            "keywords": ["情绪", "记录", "分析"],
            "music_style": ["ambient", "soft"],
            "emotion_radar": self._generate_default_radar_scores()
        }
    


    def _generate_default_radar_scores(self) -> Dict[str, int]:
        """生成默认的雷达图评分"""
        return {
            "快乐": 5,
            "悲伤": 3,
            "愤怒": 2,
            "恐惧": 2,
            "惊讶": 3,
            "厌恶": 1,
            "平静": 7,
            "兴奋": 4
        }
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """默认分析结果"""
        return {
            "core_emotion": "平静",
            "keywords": ["默认", "情绪"],
            "music_style": ["ambient"],
            "emotion_radar": self._generate_default_radar_scores()
        }
    

    


# 全局情绪分析agent
emotion_agent = EmotionAnalysisAgent()

def get_user_id():
    """获取或生成用户ID"""
    if 'user_id' not in session:
        import uuid
        session['user_id'] = f"user_{uuid.uuid4().hex[:8]}"
    return session['user_id']

@app.route('/')
def index():
    """主页"""
    user_id = get_user_id()
    
    return render_template('index.html', user_id=user_id)

@app.route('/api/mood', methods=['POST'])
def record_mood():
    """记录心情API - 情绪分析"""
    try:
        data = request.get_json()
        user_id = data.get('user_id') or get_user_id()
        mood = data.get('mood', '').strip()
        
        if not mood:
            return jsonify({'success': False, 'error': '心情不能为空'})
        
        # 使用emotion agent分析心情
        result = emotion_agent.analyze_mood(user_id, mood)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"记录心情失败: {e}")
        return jsonify({'success': False, 'error': '服务器错误'})

@app.route('/api/mood/history')
def get_mood_history():
    """获取心情历史API - 简化版本，暂不支持历史记录"""
    try:
        return jsonify({
            'success': True,
            'history': []
        })
        
    except Exception as e:
        logger.error(f"获取历史记录失败: {e}")
        return jsonify({'success': False, 'error': '服务器错误'})

@app.route('/api/user/insights')
def get_user_insights():
    """获取用户洞察API - 简化版本"""
    try:
        return jsonify({
            'success': True,
            'insights': {
                'total_records': 0,
                'learning_status': '已启动情绪分析功能'
            }
        })
        
    except Exception as e:
        logger.error(f"获取用户洞察失败: {e}")
        return jsonify({'success': False, 'error': '服务器错误'})

@app.route('/api/memory/summary')
def get_memory_summary():
    """获取系统状态摘要"""
    try:
        return jsonify({
            'success': True,
            'memory_summary': {
                'total_messages': 0,
                'recent_conversations': []
            }
        })
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        return jsonify({'success': False, 'error': '服务器错误'})

if __name__ == '__main__':
    logger.info("🎵 LETDANCE 心情记录应用启动 (简化版本)")
    logger.info("📱 访问地址: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000) 