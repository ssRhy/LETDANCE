#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频播放模块 - 树莓派优化版
支持多种音频播放方式，确保在树莓派上稳定运行
"""

import os
import logging
import subprocess
import threading
import time

# 配置日志
logger = logging.getLogger(__name__)

def play_with_aplay(audio_file: str, device: str = None):
    """
    使用aplay命令播放音频
    
    Args:
        audio_file: 音频文件路径
        device: 音频输出设备（可选）
    """
    try:
        cmd = ['aplay']
        if device:
            cmd.extend(['-D', device])
        cmd.append(audio_file)
        
        logger.info(f"使用aplay播放: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("aplay播放成功")
            return True
        else:
            logger.error(f"aplay播放失败: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"aplay播放异常: {e}")
        return False

def play_with_pygame(audio_file: str, volume: float = 0.7):
    """
    使用pygame播放音频（备用方式）
    
    Args:
        audio_file: 音频文件路径
        volume: 音量 (0.0 - 1.0)
    """
    try:
        import pygame
        
        # 初始化pygame音频模块，使用适合树莓派的设置
        pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        
        # 加载音频文件
        pygame.mixer.music.load(audio_file)
        
        # 设置音量
        pygame.mixer.music.set_volume(volume)
        
        # 播放音频
        pygame.mixer.music.play()
        
        logger.info(f"pygame开始播放音频: {audio_file}")
        
        # 等待播放完成
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        logger.info("pygame播放完成")
        return True
        
    except ImportError:
        logger.error("pygame未安装，无法使用pygame播放")
        return False
    except Exception as e:
        logger.error(f"pygame播放失败: {e}")
        return False
    finally:
        # 清理资源
        try:
            pygame.mixer.quit()
        except:
            pass

def play_with_omxplayer(audio_file: str):
    """
    使用omxplayer播放音频（树莓派专用播放器）
    
    Args:
        audio_file: 音频文件路径
    """
    try:
        cmd = ['omxplayer', '--no-keys', audio_file]
        logger.info(f"使用omxplayer播放: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("omxplayer播放成功")
            return True
        else:
            logger.error(f"omxplayer播放失败: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"omxplayer播放异常: {e}")
        return False

def detect_audio_devices():
    """检测可用的音频输出设备"""
    try:
        # 检查ALSA设备
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("可用音频设备:")
            logger.info(result.stdout)
            return result.stdout
        else:
            logger.warning("无法检测音频设备")
            return None
    except Exception as e:
        logger.error(f"检测音频设备失败: {e}")
        return None

def play(audio_file: str, volume: float = 0.7):
    """
    播放音频文件（自动选择最佳播放方式）
    
    Args:
        audio_file: 音频文件路径
        volume: 音量 (0.0 - 1.0)
    """
    # 检查文件是否存在
    if not os.path.exists(audio_file):
        logger.error(f"音频文件不存在: {audio_file}")
        return False
    
    logger.info(f"开始播放音频: {audio_file}")
    
    # 检测音频设备
    detect_audio_devices()
    
    # 尝试多种播放方式
    
    # 方式1: 使用aplay（最稳定）
    logger.info("尝试使用aplay播放...")
    if play_with_aplay(audio_file):
        return True
    
    # 方式2: 使用aplay指定设备
    logger.info("尝试使用aplay指定设备播放...")
    if play_with_aplay(audio_file, 'hw:0,0'):
        return True
    
    # 方式3: 使用omxplayer
    logger.info("尝试使用omxplayer播放...")
    if play_with_omxplayer(audio_file):
        return True
    
    # 方式4: 使用pygame（最后备选）
    logger.info("尝试使用pygame播放...")
    if play_with_pygame(audio_file, volume):
        return True
    
    logger.error("所有播放方式都失败了")
    return False

def play_async(audio_file: str, volume: float = 0.7):
    """
    异步播放音频文件（不阻塞主线程）
    
    Args:
        audio_file: 音频文件路径
        volume: 音量 (0.0 - 1.0)
    """
    def _play_thread():
        try:
            logger.info(f"异步播放线程开始播放: {audio_file}")
            success = play(audio_file, volume)
            if success:
                logger.info(" 异步音频播放完成")
            else:
                logger.error("异步音频播放失败")
        except Exception as e:
            logger.error(f" 异步播放线程异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # 先检查文件是否存在
    if not os.path.exists(audio_file):
        logger.error(f"音频文件不存在，无法播放: {audio_file}")
        # 创建一个立即退出的虚拟线程
        def dummy_thread():
            pass
        thread = threading.Thread(target=dummy_thread)
        thread.start()
        thread.join()  # 让线程立即结束
        return thread
    
    thread = threading.Thread(target=_play_thread)
    thread.daemon = True
    thread.start()
    logger.info(f" 异步音频播放线程已启动，文件: {audio_file}")
    return thread

def test_audio_playback():
    """测试音频播放功能"""
    logger.info("开始音频播放测试...")
    
    # 检测音频设备
    detect_audio_devices()
    
    # 查找测试音频文件
    test_files = []
    
    # 查找generated_music目录中的文件
    if os.path.exists("generated_music"):
        for file in os.listdir("generated_music"):
            if file.endswith(('.wav', '.mp3')):
                test_files.append(os.path.join("generated_music", file))
    
    if not test_files:
        logger.warning("未找到测试音频文件")
        return False
    
    # 测试播放第一个找到的文件
    test_file = test_files[0]
    logger.info(f"测试播放文件: {test_file}")
    
    return play(test_file)

if __name__ == "__main__":
    # 配置日志级别以便调试
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 50)
    print("树莓派音频播放模块测试")
    print("=" * 50)
    
    # 执行测试
    success = test_audio_playback()
    
    if success:
        print(" 音频播放测试成功!")
    else:
        print("音频播放测试失败!")
        print("请检查:")
        print("1. 音频设备连接")
        print("2. ALSA配置")
        print("3. 系统音量设置")
        print("4. 音频文件是否存在")