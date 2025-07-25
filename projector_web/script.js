// LETDANCE 自动投影系统 - 简化版

class AutoProjectorSystem {
  constructor() {
    this.currentTheme = null;
    this.particles = [];
    this.maxParticles = 50;
    this.particleContainer = document.getElementById("particles");
    this.colorDisplay = document.getElementById("colorDisplay");
    this.currentEmotionDisplay = document.getElementById("currentEmotion");

    // 自动模式设置
    this.autoUpdateInterval = null;
    this.isAutoMode = true;
    this.lastEmotionData = null;

    this.init();
    this.createInitialParticles();
    this.startImmediately(); // 立即启动
  }

  init() {
    // 窗口大小改变时重新计算粒子
    window.addEventListener("resize", () => {
      this.repositionParticles();
    });

    // 键盘监听 - 仅保留ESC退出全屏
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && document.fullscreenElement) {
        document.exitFullscreen();
      }
    });
  }

  startImmediately() {
    // 立即启动系统
    console.log("🚀 LETDANCE自动投影系统启动");

    // 立即尝试进入全屏
    this.attemptAutoFullscreen();

    // 启动自动更新
    this.startAutoUpdate();

    // 显示启动消息
    this.showMessage("🎨 LETDANCE自动投影系统已启动", 3000);
  }

  attemptAutoFullscreen() {
    // 尝试多种方法实现自动全屏
    const tryFullscreen = async () => {
      try {
        // 创建一个不可见的按钮并模拟点击
        const invisibleButton = document.createElement("button");
        invisibleButton.style.cssText = `
          position: fixed;
          top: -100px;
          left: -100px;
          width: 1px;
          height: 1px;
          opacity: 0;
          pointer-events: none;
        `;
        document.body.appendChild(invisibleButton);

        // 模拟用户交互
        const clickEvent = new MouseEvent("click", {
          view: window,
          bubbles: true,
          cancelable: true,
        });

        invisibleButton.addEventListener("click", async () => {
          try {
            await document.documentElement.requestFullscreen();
            document.body.classList.add("fullscreen-mode");
            console.log("✅ 自动全屏成功");
            this.showMessage("🎬 已进入全屏投影模式", 2000);
          } catch (err) {
            console.log("⚠️ 自动全屏失败:", err);
          }
          document.body.removeChild(invisibleButton);
        });

        // 延迟触发点击事件
        setTimeout(() => {
          invisibleButton.dispatchEvent(clickEvent);
        }, 500);
      } catch (err) {
        console.log("⚠️ 全屏初始化失败:", err);
        // 备用方案：监听第一次用户交互
        this.setupFirstInteractionFullscreen();
      }
    };

    // 延迟执行以确保页面完全加载
    setTimeout(tryFullscreen, 1000);
  }

  setupFirstInteractionFullscreen() {
    // 设置第一次用户交互时自动全屏
    const autoFullscreenOnInteraction = async () => {
      try {
        if (!document.fullscreenElement) {
          await document.documentElement.requestFullscreen();
          document.body.classList.add("fullscreen-mode");
          console.log("✅ 交互触发全屏成功");
          this.showMessage("🎬 已进入全屏投影模式", 2000);
        }
      } catch (err) {
        console.log("⚠️ 交互全屏失败:", err);
      }
    };

    // 监听各种用户交互事件
    const events = ["click", "touchstart", "keydown", "mousemove"];
    events.forEach((eventType) => {
      document.addEventListener(eventType, autoFullscreenOnInteraction, {
        once: true,
      });
    });
  }

  startAutoUpdate() {
    // 每秒检查情绪数据更新
    this.autoUpdateInterval = setInterval(async () => {
      await this.checkForEmotionUpdates();
    }, 1000);
  }

  async checkForEmotionUpdates() {
    try {
      const response = await fetch("/api/emotions");
      if (response.ok) {
        const emotions = await response.json();

        if (Object.keys(emotions).length > 0) {
          const emotionString = JSON.stringify(emotions);
          if (emotionString !== this.lastEmotionData) {
            this.lastEmotionData = emotionString;
            console.log("🎯 收到新的情绪数据:", emotions);
            this.applyProjectionEffect(emotions);
          }
        }
      }
    } catch (error) {
      // 静默处理错误
    }
  }

  applyProjectionEffect(emotions) {
    // 立即应用投影效果
    console.log("🎨 正在更新投影效果...");

    const emotionKeys = Object.keys(emotions);
    if (emotionKeys.length > 0) {
      const primaryEmotionKey = emotionKeys[0];
      const primaryEmotion = emotions[primaryEmotionKey];

      const themeIndex = primaryEmotionKey.replace("emotion", "");
      const displayText = `${primaryEmotion.keyword} (${primaryEmotion.emotion_text})`;

      // 激活投影效果
      this.activateProjection(themeIndex, displayText);

      console.log(`✅ 投影已更新: ${displayText}`);
    }
  }

  activateProjection(themeIndex, emotionText) {
    // 清除之前的主题
    this.colorDisplay.className = "color-display";

    // 应用新主题
    setTimeout(() => {
      this.colorDisplay.classList.add(`emotion-theme-${themeIndex}`);
      this.currentTheme = themeIndex;
      this.currentEmotionDisplay.textContent = emotionText;
      this.updateParticles();

      // 触觉反馈
      if ("vibrate" in navigator) {
        navigator.vibrate(200);
      }
    }, 100);
  }

  createInitialParticles() {
    for (let i = 0; i < this.maxParticles; i++) {
      this.createParticle();
    }
  }

  createParticle() {
    const particle = document.createElement("div");
    particle.className = "particle";

    const size = Math.random() * 20 + 10;
    const x = Math.random() * window.innerWidth;
    const y = Math.random() * window.innerHeight;

    particle.style.width = size + "px";
    particle.style.height = size + "px";
    particle.style.left = x + "px";
    particle.style.top = y + "px";
    particle.style.animationDelay = Math.random() * 6 + "s";

    this.particleContainer.appendChild(particle);
    this.particles.push(particle);
  }

  updateParticles() {
    // 添加新粒子增强效果
    for (let i = 0; i < 20; i++) {
      setTimeout(() => {
        this.createTemporaryParticle();
      }, i * 80);
    }
  }

  createTemporaryParticle() {
    const particle = document.createElement("div");
    particle.className = "particle";

    const size = Math.random() * 40 + 20;
    const x = Math.random() * window.innerWidth;
    const y = Math.random() * window.innerHeight;

    particle.style.width = size + "px";
    particle.style.height = size + "px";
    particle.style.left = x + "px";
    particle.style.top = y + "px";
    particle.style.animationDuration = "5s";

    this.particleContainer.appendChild(particle);

    setTimeout(() => {
      if (particle.parentNode) {
        particle.parentNode.removeChild(particle);
      }
    }, 5000);
  }

  repositionParticles() {
    this.particles.forEach((particle) => {
      const x = Math.random() * window.innerWidth;
      const y = Math.random() * window.innerHeight;
      particle.style.left = x + "px";
      particle.style.top = y + "px";
    });
  }

  showMessage(message, duration = 3000) {
    const messageDiv = document.createElement("div");
    messageDiv.style.cssText = `
      position: fixed;
      top: 50px;
      right: 50px;
      background: rgba(0, 0, 0, 0.9);
      color: white;
      padding: 20px 30px;
      border-radius: 15px;
      font-size: 16px;
      z-index: 9999;
      text-align: center;
      border: 2px solid rgba(255, 255, 255, 0.2);
      backdrop-filter: blur(10px);
      box-shadow: 0 8px 32px rgba(0,0,0,0.5);
      transition: opacity 0.5s ease;
    `;
    messageDiv.textContent = message;

    document.body.appendChild(messageDiv);

    setTimeout(() => {
      if (messageDiv.parentNode) {
        messageDiv.style.opacity = "0";
        setTimeout(() => {
          if (messageDiv.parentNode) {
            messageDiv.parentNode.removeChild(messageDiv);
          }
        }, 500);
      }
    }, duration);
  }
}

// 页面加载完成后立即启动
document.addEventListener("DOMContentLoaded", () => {
  const projectorSystem = new AutoProjectorSystem();

  console.log("🎨 LETDANCE自动投影系统已初始化");
  console.log("🤖 系统将自动接收分析结果并投影");
  console.log("🎬 自动全屏功能已启用");

  // 页面标题更新
  document.title = "LETDANCE自动投影 - 运行中";

  // 隐藏鼠标光标（全屏投影时）
  setTimeout(() => {
    if (document.fullscreenElement) {
      document.body.style.cursor = "none";
    }
  }, 5000);
});
