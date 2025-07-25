#!/bin/bash
# LETDANCE 树莓派快速配置脚本

echo "🍓 LETDANCE树莓派自动投影系统配置"
echo "================================"

# 检查是否为树莓派
if [[ ! -f /proc/device-tree/model ]] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "⚠️  警告: 这不是树莓派系统，但仍可继续安装"
fi

# 更新系统
echo "📦 更新系统包..."
sudo apt update -y

# 安装Python和基础依赖
echo "🐍 安装Python环境..."
sudo apt install -y python3 python3-pip python3-venv git

# 安装系统依赖
echo "🔧 安装系统依赖..."
sudo apt install -y \
    libopencv-dev \
    python3-opencv \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    gfortran \
    openexr \
    libatlas-base-dev \
    python3-scipy \
    libjasper-dev \
    libqtgui4 \
    libqt4-test \
    libhdf5-dev \
    portaudio19-dev \
    alsa-utils

# 安装浏览器（用于投影显示）
echo "🌐 安装浏览器..."
sudo apt install -y chromium-browser

# 安装Python包
echo "📚 安装Python依赖包..."
pip3 install --upgrade pip
pip3 install \
    opencv-python \
    mediapipe \
    numpy \
    requests \
    langchain \
    langchain-openai \
    python-dotenv \
    pygame \
    pyaudio

echo "🎵 配置音频..."
# 确保音频设备可用
sudo usermod -a -G audio $USER

# 创建启动桌面快捷方式
echo "🖥️  创建桌面快捷方式..."
DESKTOP_DIR="$HOME/Desktop"
if [ -d "$DESKTOP_DIR" ]; then
    cat > "$DESKTOP_DIR/LETDANCE自动投影.desktop" << EOF
[Desktop Entry]
Name=LETDANCE自动投影
Comment=启动LETDANCE自动投影系统
Exec=python3 $(pwd)/start_auto_projector.py
Icon=applications-multimedia
Terminal=true
Type=Application
Categories=Application;AudioVideo;
StartupNotify=true
EOF
    chmod +x "$DESKTOP_DIR/LETDANCE自动投影.desktop"
fi

# 设置开机自启动（可选）
echo "🚀 是否设置开机自启动投影系统? (y/n)"
read -r auto_start
if [[ $auto_start == "y" || $auto_start == "Y" ]]; then
    # 创建systemd服务
    sudo tee /etc/systemd/system/letdance-projector.service > /dev/null << EOF
[Unit]
Description=LETDANCE Auto Projector
After=network.target sound.target graphical-session.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
Environment=DISPLAY=:0
Environment=HOME=$HOME
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/python3 $(pwd)/start_auto_projector.py
Restart=always
RestartSec=10

[Install]
WantedBy=graphical-session.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable letdance-projector.service
    echo "✅ 开机自启动已设置"
fi

# 配置显示设置（投影仪优化）
echo "📺 优化投影显示设置..."
if [ -f /boot/config.txt ]; then
    # 备份原配置
    sudo cp /boot/config.txt /boot/config.txt.backup
    
    # 添加投影仪优化设置
    echo "
# LETDANCE投影优化设置
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=82
hdmi_drive=2
config_hdmi_boost=7" | sudo tee -a /boot/config.txt
    
    echo "✅ 显示设置已优化"
fi

# 权限设置
echo "🔐 设置执行权限..."
chmod +x start_auto_projector.py
chmod +x setup_raspberry_pi.sh

echo ""
echo "🎉 LETDANCE树莓派配置完成!"
echo "================================"
echo "📋 使用说明:"
echo "   1. 启动系统: python3 start_auto_projector.py"
echo "   2. 浏览器访问: http://树莓派IP:8080/color.html"
echo "   3. 系统将自动分析并投影"
echo ""
echo "💡 提示:"
echo "   - 确保摄像头已连接"
echo "   - 确保投影仪已连接到HDMI"
echo "   - 系统会自动全屏显示投影效果"
echo ""
echo "🔄 如需重启使配置生效: sudo reboot" 