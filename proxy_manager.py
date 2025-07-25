#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理管理模块 - 自动检测和配置代理设置
"""

import os
import urllib.request


def detect_proxy():
    """检测是否使用代理服务器"""
    # 检查环境变量中的代理设置
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
    for var in proxy_vars:
        if os.environ.get(var):
            print(f"检测到代理设置: {var}={os.environ.get(var)}")
            return True
    
    # 检查系统代理设置
    try:
        proxy_handler = urllib.request.getproxies()
        if proxy_handler:
            print(f"检测到系统代理: {proxy_handler}")
            return True
    except:
        pass
    
    return False


def configure_proxy_settings():
    """配置代理设置以确保兼容性"""
    # 如果检测到代理，确保相关设置正确
    if detect_proxy():
        print("代理模式：正在配置代理兼容设置...")
        
        # 设置请求超时时间
        os.environ["REQUESTS_TIMEOUT"] = "30"
        
        # 如果有代理但没有设置no_proxy，添加本地地址
        if not os.environ.get('NO_PROXY') and not os.environ.get('no_proxy'):
            os.environ['NO_PROXY'] = 'localhost,127.0.0.1,::1'
            
    else:
        print("直连模式：使用直接连接...")
        # 清除可能影响连接的代理设置
        proxy_vars_to_clear = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
        for var in proxy_vars_to_clear:
            if var in os.environ:
                del os.environ[var]


def get_proxy_status():
    """获取当前代理状态信息"""
    if detect_proxy():
        return "代理模式"
    else:
        return "直连模式"


def print_proxy_info():
    """打印代理配置信息"""
    print("=== 代理配置信息 ===")
    
    # 检查环境变量代理
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
    for var in proxy_vars:
        value = os.environ.get(var)
        if value:
            print(f"{var}: {value}")
    
    # 检查no_proxy设置
    no_proxy = os.environ.get('NO_PROXY') or os.environ.get('no_proxy')
    if no_proxy:
        print(f"NO_PROXY: {no_proxy}")
    
    # 检查系统代理
    try:
        system_proxies = urllib.request.getproxies()
        if system_proxies:
            print(f"系统代理: {system_proxies}")
    except:
        pass
    
    print(f"当前状态: {get_proxy_status()}")
    print("==================") 