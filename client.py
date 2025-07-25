import requests
import json
import os
from datetime import datetime

class MusicGenClient:
    def __init__(self, server_url="http://192.168.19.126:5000"):
        """
        初始化音乐生成客户端
        用于接收Agent生成的提示词并请求外部音乐生成服务
        
        Args:
            server_url: API服务器地址
        """
        self.server_url = server_url
        self.generate_url = f"{server_url}/generate_music"
        self.health_url = f"{server_url}/health"
    
    def check_health(self):
        """检查音乐生成服务状态"""
        try:
            response = requests.get(self.health_url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def generate_music(self, prompt, output_dir="generated_music"):
        """
        生成音乐
        
        Args:
            prompt: 音乐生成提示词
            output_dir: 输出目录
            
        Returns:
            生成的音频文件路径
        """
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 准备请求数据
        data = {"prompts": [prompt]}
        
        try:
            # 发送请求
            response = requests.post(
                self.generate_url,
                json=data,
                timeout=120  # 2分钟超时
            )
            
            if response.status_code == 200:
                # 生成文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"music_{timestamp}.wav"
                filepath = os.path.join(output_dir, filename)
                
                # 保存音频文件
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                print(f"音乐生成成功，文件保存位置: {filepath}")
                return filepath
            else:
                print(f"音乐生成失败，状态码: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"音乐生成异常: {e}")
            return None
    
                
    

def main():
    """主程序 - 仅用于测试客户端功能"""
    # 初始化客户端
    client = MusicGenClient()
    
    # 测试音乐生成
    test_prompt = "ambient, emotional, calm, contemplative"
    print(f"测试音乐生成，提示词: {test_prompt}")
    result = client.generate_music(test_prompt)
    
    if result:
        print(f"音乐生成成功！文件路径: {result}")
    else:
        print("音乐生成失败")

if __name__ == "__main__":
    main()