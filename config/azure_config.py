#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure OpenAI 配置
按照LangChain官方文档的标准格式
"""

import os
from typing import Dict, Any
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from proxy_manager import configure_proxy_settings, get_proxy_status

class AzureConfig:
    """Azure OpenAI配置管理"""
    
    # Azure OpenAI 配置
    API_KEY = "ES3vLOAy8MUTMui8udIAk2vZO1Fo7qCBHKlaAvcprOXicYTkjzwbJQQJ99BDACHYHv6XJ3w3AAAAACOG4FT8"
    INSTANCE_NAME = "ai-philxia4932ai122623990161"
    DEPLOYMENT_NAME = "gpt-4.1"
    API_VERSION = "2024-02-15-preview"
    
    def __init__(self):
        """初始化Azure配置"""
        self.setup_environment()
        self.api_key = self.API_KEY
        self.deployment_name = self.DEPLOYMENT_NAME
        self.api_version = self.API_VERSION
        self.azure_endpoint = f"https://{self.INSTANCE_NAME}.openai.azure.com/"
    
    @classmethod
    def setup_environment(cls) -> None:
        """设置Azure OpenAI环境变量和网络配置"""
        # 配置代理设置
        configure_proxy_settings()
        print(f"网络状态: {get_proxy_status()}")
        
        # 设置Azure OpenAI环境变量
        os.environ["AZURE_OPENAI_API_KEY"] = cls.API_KEY
        os.environ["AZURE_OPENAI_API_INSTANCE_NAME"] = cls.INSTANCE_NAME
        os.environ["AZURE_OPENAI_API_DEPLOYMENT_NAME"] = cls.DEPLOYMENT_NAME
        os.environ["AZURE_OPENAI_API_VERSION"] = cls.API_VERSION
        
        # 设置连接超时和重试参数
        os.environ["OPENAI_API_TIMEOUT"] = "30"
        os.environ["OPENAI_MAX_RETRIES"] = "3"
    
    @classmethod
    def get_azure_chat_config(cls) -> Dict[str, Any]:
        """获取AzureChatOpenAI配置参数"""
        cls.setup_environment()
        return {
            "azure_endpoint": f"https://{cls.INSTANCE_NAME}.openai.azure.com/",
            "api_key": cls.API_KEY,
            "azure_deployment": cls.DEPLOYMENT_NAME,
            "api_version": cls.API_VERSION,
            "temperature": 0.7,
            "timeout": 30,
            "max_retries": 3,
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """验证配置完整性"""
        required_fields = [
            cls.API_KEY,
            cls.INSTANCE_NAME,
            cls.DEPLOYMENT_NAME,
            cls.API_VERSION
        ]
        return all(field for field in required_fields) 