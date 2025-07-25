// LETDANCE Web应用 JavaScript 逻辑

class LetDanceApp {
  constructor() {
    this.isProcessing = false;
    this.currentKeywords = [...currentKeywords];
    this.selectedRating = 0;

    this.init();
  }

  init() {
    this.initializeElements();
    this.bindEvents();
    this.loadInitialData();

    console.log("LETDANCE应用初始化完成");
  }

  initializeElements() {
    // 控制元素
    this.durationSlider = document.getElementById("duration");
    this.durationValue = document.getElementById("duration-value");
    this.analyzeBtn = document.getElementById("analyze-btn");
    this.completeWorkflowBtn = document.getElementById("complete-workflow-btn");
    this.generateMusicBtn = document.getElementById("generate-music-btn");

    // 关键词相关
    this.customKeywordsInput = document.getElementById("custom-keywords");
    this.addKeywordBtn = document.getElementById("add-keyword-btn");
    this.keywordsTags = document.getElementById("keywords-tags");

    // 结果显示
    this.statusIndicator = document.getElementById("status-indicator");
    this.resultsContent = document.getElementById("results-content");
    this.emptyState = document.getElementById("empty-state");
    this.analysisResults = document.getElementById("analysis-results");
    this.musicResults = document.getElementById("music-results");

    // 历史记录
    this.sessionList = document.getElementById("session-list");

    // 模态框
    this.feedbackModal = document.getElementById("feedback-modal");
    this.feedbackBtn = document.getElementById("feedback-btn");
    this.closeFeedbackModal = document.getElementById("close-feedback-modal");
    this.submitFeedbackBtn = document.getElementById("submit-feedback-btn");
    this.cancelFeedbackBtn = document.getElementById("cancel-feedback-btn");

    // 反馈表单
    this.feedbackType = document.getElementById("feedback-type");
    this.ratingStars = document.getElementById("rating-stars");
    this.feedbackContent = document.getElementById("feedback-content");

    // 其他
    this.loadingOverlay = document.getElementById("loading-overlay");
    this.viewProfileBtn = document.getElementById("view-profile-btn");
  }

  bindEvents() {
    // 时长滑块
    this.durationSlider.addEventListener("input", (e) => {
      this.durationValue.textContent = e.target.value;
    });

    // 主要功能按钮
    this.analyzeBtn.addEventListener("click", () => this.startAnalysis());
    this.completeWorkflowBtn.addEventListener("click", () =>
      this.startCompleteWorkflow()
    );
    this.generateMusicBtn.addEventListener("click", () => this.generateMusic());

    // 关键词管理
    this.addKeywordBtn.addEventListener("click", () => this.addCustomKeyword());
    this.customKeywordsInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        this.addCustomKeyword();
      }
    });



    // 标签页切换
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", (e) =>
        this.switchTab(e.target.dataset.tab)
      );
    });

    // 反馈功能
    this.feedbackBtn.addEventListener("click", () => this.showFeedbackModal());
    this.closeFeedbackModal.addEventListener("click", () =>
      this.hideFeedbackModal()
    );
    this.cancelFeedbackBtn.addEventListener("click", () =>
      this.hideFeedbackModal()
    );
    this.submitFeedbackBtn.addEventListener("click", () =>
      this.submitFeedback()
    );

    // 评分星星
    this.ratingStars.addEventListener("click", (e) => {
      if (e.target.classList.contains("fa-star")) {
        this.setRating(parseInt(e.target.dataset.rating));
      }
    });

    // 用户档案
    this.viewProfileBtn.addEventListener("click", () => this.showUserProfile());

    // 关闭模态框（点击外部）
    this.feedbackModal.addEventListener("click", (e) => {
      if (e.target === this.feedbackModal) {
        this.hideFeedbackModal();
      }
    });

    // 键盘快捷键
    document.addEventListener("keydown", (e) => {
      if (e.ctrlKey && e.key === "Enter") {
        if (!this.isProcessing) {
          this.startCompleteWorkflow();
        }
      }
    });
  }



  loadInitialData() {
    this.renderKeywords();
  }

  // 核心功能方法
  async startAnalysis() {
    if (this.isProcessing) return;

    const duration = parseInt(this.durationSlider.value);

    try {
      this.setProcessing(true);
      this.updateStatus("正在分析...", "processing");
      this.hideEmptyState();

      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ duration }),
      });

      const result = await response.json();

      if (result.success) {
        this.displayAnalysisResults(result);
        this.updateStatus("分析完成", "success");

        // 自动更新关键词
        if (result.music_keywords) {
          this.currentKeywords = result.music_keywords;
          this.renderKeywords();
        }
      } else {
        this.showError(result.message);
        this.updateStatus("分析失败", "error");
      }
    } catch (error) {
      this.showError("分析请求失败: " + error.message);
      this.updateStatus("分析失败", "error");
    } finally {
      this.setProcessing(false);
    }
  }

  async startCompleteWorkflow() {
    if (this.isProcessing) return;

    const duration = parseInt(this.durationSlider.value);

    try {
      this.setProcessing(true);
      this.updateStatus("执行完整流程...", "processing");
      this.hideEmptyState();

      const response = await fetch("/api/complete_workflow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ duration }),
      });

      const result = await response.json();

      if (result.success) {
        this.displayWorkflowResults(result);
        this.updateStatus("流程完成", "success");

        // 更新关键词
        if (result.final_keywords) {
          this.currentKeywords = result.final_keywords;
          this.renderKeywords();
        }
      } else {
        this.showError(result.message);
        this.updateStatus("流程失败", "error");
      }
    } catch (error) {
      this.showError("流程执行失败: " + error.message);
      this.updateStatus("流程失败", "error");
    } finally {
      this.setProcessing(false);
    }
  }

  async generateMusic() {
    if (this.isProcessing || this.currentKeywords.length === 0) return;

    try {
      this.setProcessing(true);
      this.updateStatus("生成音乐...", "processing");

      const response = await fetch("/api/generate_music", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keywords: this.currentKeywords }),
      });

      const result = await response.json();

      if (result.success) {
        this.displayMusicResults(result);
        this.updateStatus("音乐生成完成", "success");
      } else {
        this.showError(result.message);
        this.updateStatus("音乐生成失败", "error");
      }
    } catch (error) {
      this.showError("音乐生成失败: " + error.message);
      this.updateStatus("音乐生成失败", "error");
    } finally {
      this.setProcessing(false);
    }
  }

  // 结果显示方法
  displayAnalysisResults(result) {
    this.analysisResults.style.display = "block";

    // 图像分析结果
    const imageAnalysisData = document.getElementById("image-analysis-data");
    if (result.image_analysis) {
      imageAnalysisData.textContent = JSON.stringify(
        result.image_analysis,
        null,
        2
      );
    } else {
      imageAnalysisData.textContent = "图像分析数据不可用";
    }

    // 姿态分析结果
    const poseAnalysisData = document.getElementById("pose-analysis-data");
    if (result.pose_analysis) {
      poseAnalysisData.textContent = JSON.stringify(
        result.pose_analysis,
        null,
        2
      );
    } else {
      poseAnalysisData.textContent = "姿态分析数据不可用";
    }

    // 拉班分析结果
    const labanAnalysisData = document.getElementById("laban-analysis-data");
    if (result.laban_analysis_text) {
      labanAnalysisData.textContent = result.laban_analysis_text;
    } else {
      labanAnalysisData.textContent = "拉班分析数据不可用";
    }

    this.analysisResults.classList.add("fade-in");
  }

  displayWorkflowResults(result) {
    // 显示分析结果
    if (result.analysis_result) {
      this.displayAnalysisResults(result.analysis_result);
    }

    // 显示音乐结果
    if (result.music_result) {
      this.displayMusicResults(result.music_result);
    }
  }

  displayMusicResults(result) {
    this.musicResults.style.display = "block";

    const musicInfo = document.getElementById("music-info");
    const musicPlayer = document.getElementById("music-player");

    let infoHtml = `
            <div class="music-generation-info">
                <h4>音乐生成信息</h4>
                <p><strong>状态:</strong> ${
                  result.success ? "成功" : "失败"
                }</p>
                <p><strong>消息:</strong> ${result.message}</p>
                <p><strong>关键词:</strong> ${
                  result.keywords_used ? result.keywords_used.join(", ") : "无"
                }</p>
        `;

    if (result.music_file) {
      infoHtml += `<p><strong>文件:</strong> ${result.music_file}</p>`;

      // 配置音频播放器
      musicPlayer.src = `/api/play_music?file=${encodeURIComponent(
        result.music_file
      )}`;
      musicPlayer.style.display = "block";
    }

    infoHtml += "</div>";
    musicInfo.innerHTML = infoHtml;

    this.musicResults.classList.add("fade-in");
  }

  // 关键词管理
  addCustomKeyword() {
    const keyword = this.customKeywordsInput.value.trim();
    if (keyword && !this.currentKeywords.includes(keyword)) {
      this.currentKeywords.push(keyword);
      this.renderKeywords();
      this.customKeywordsInput.value = "";
    }
  }

  removeKeyword(keyword) {
    this.currentKeywords = this.currentKeywords.filter((k) => k !== keyword);
    this.renderKeywords();
  }

  renderKeywords() {
    this.keywordsTags.innerHTML = "";

    this.currentKeywords.forEach((keyword) => {
      const tag = document.createElement("span");
      tag.className = "keyword-tag";
      tag.dataset.keyword = keyword;
      tag.innerHTML = `
                ${keyword}
                <i class="fas fa-times" onclick="app.removeKeyword('${keyword}')"></i>
            `;
      this.keywordsTags.appendChild(tag);
    });

    // 更新生成按钮状态
    this.generateMusicBtn.disabled =
      this.currentKeywords.length === 0 || this.isProcessing;
  }



  // 标签页切换
  switchTab(tabName) {
    // 更新标签按钮状态
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tabName);
    });

    // 更新标签内容显示
    document.querySelectorAll(".tab-content").forEach((content) => {
      content.classList.toggle("active", content.id === `${tabName}-tab`);
    });

    // 加载对应数据
    if (tabName === "history") {
      this.loadSessionList();
    }
  }

  // 历史记录功能

  async loadSessionList() {
    try {
      const response = await fetch("/api/sessions");
      const result = await response.json();

      if (result.success) {
        this.renderSessionList(result.sessions);
      }
    } catch (error) {
      console.error("加载会话列表失败:", error);
      this.sessionList.innerHTML = "<p>加载失败</p>";
    }
  }

  renderSessionList(sessions) {
    if (sessions.length === 0) {
      this.sessionList.innerHTML = "<p>暂无历史会话</p>";
      return;
    }

    this.sessionList.innerHTML = "";

    sessions.forEach((session) => {
      const sessionDiv = document.createElement("div");
      sessionDiv.className = "session-item";
      sessionDiv.onclick = () => this.loadSession(session.session_id);

      const startTime = new Date(session.start_time).toLocaleDateString();
      const lastTime = new Date(session.last_time).toLocaleString();

      sessionDiv.innerHTML = `
                <div class="session-item-header">
                    <span class="session-id">${session.session_id.substring(
                      0,
                      8
                    )}...</span>
                    <span class="session-time">${startTime}</span>
                </div>
                <div class="session-stats">
                    ${session.message_count} 条消息 • 最后活动: ${lastTime}
                </div>
            `;

      this.sessionList.appendChild(sessionDiv);
    });
  }

  async loadSession(sessionId) {
    try {
      const response = await fetch(`/api/load_session/${sessionId}`);
      const result = await response.json();

      if (result.success) {
        this.showSuccess(`会话 ${sessionId.substring(0, 8)} 加载成功`);
      } else {
        this.showError(result.message);
      }
    } catch (error) {
      this.showError("加载会话失败: " + error.message);
    }
  }

  // 反馈功能
  showFeedbackModal() {
    this.feedbackModal.classList.add("active");
    this.resetFeedbackForm();
  }

  hideFeedbackModal() {
    this.feedbackModal.classList.remove("active");
  }

  resetFeedbackForm() {
    this.feedbackType.value = "general";
    this.feedbackContent.value = "";
    this.setRating(0);
  }

  setRating(rating) {
    this.selectedRating = rating;

    this.ratingStars.querySelectorAll("i").forEach((star, index) => {
      star.classList.toggle("active", index < rating);
    });
  }

  async submitFeedback() {
    if (this.selectedRating === 0) {
      this.showError("请选择评分");
      return;
    }

    const feedbackData = {
      type: this.feedbackType.value,
      rating: this.selectedRating,
      content: this.feedbackContent.value.trim(),
      keywords: this.currentKeywords,
    };

    try {
      const response = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(feedbackData),
      });

      const result = await response.json();

      if (result.success) {
        this.showSuccess(result.message);
        this.hideFeedbackModal();
      } else {
        this.showError(result.message);
      }
    } catch (error) {
      this.showError("反馈提交失败: " + error.message);
    }
  }

  // 用户档案
  async showUserProfile() {
    try {
      const response = await fetch("/api/user_profile");
      const result = await response.json();

      if (result.success) {
        alert(JSON.stringify(result.profile, null, 2));
      }
    } catch (error) {
      this.showError("获取用户档案失败: " + error.message);
    }
  }

  // 状态管理
  setProcessing(processing) {
    this.isProcessing = processing;
    this.analyzeBtn.disabled = processing;
    this.completeWorkflowBtn.disabled = processing;
    this.generateMusicBtn.disabled =
      processing || this.currentKeywords.length === 0;

    if (processing) {
      this.showLoading();
    } else {
      this.hideLoading();
    }
  }

  updateStatus(message, type = "ready") {
    const indicator = this.statusIndicator;
    const icon = indicator.querySelector("i");
    const text = indicator.querySelector("span");

    text.textContent = message;

    // 重置所有状态类
    indicator.classList.remove("processing", "error");

    if (type === "processing") {
      indicator.classList.add("processing");
    } else if (type === "error") {
      indicator.classList.add("error");
    }
  }

  hideEmptyState() {
    this.emptyState.style.display = "none";
  }

  showLoading() {
    this.loadingOverlay.classList.add("active");
  }

  hideLoading() {
    this.loadingOverlay.classList.remove("active");
  }

  // 消息提示
  showError(message) {
    this.showToast(message, "error");
  }

  showSuccess(message) {
    this.showToast(message, "success");
  }

  showToast(message, type = "info") {
    // 创建临时提示元素
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: ${
              type === "error" ? "var(--error-color)" : "var(--success-color)"
            };
            color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow-lg);
            z-index: 3000;
            animation: slideInRight 0.3s ease-out;
        `;
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
      toast.remove();
    }, 5000);
  }
}

// 初始化应用
let app;
document.addEventListener("DOMContentLoaded", () => {
  app = new LetDanceApp();
});

// 添加滑入动画样式
const style = document.createElement("style");
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);
