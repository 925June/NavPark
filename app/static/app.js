const elements = {
  authGate: document.querySelector("#auth-gate"),
  appShell: document.querySelector("#app-shell"),
  authForm: document.querySelector("#auth-form"),
  authPhone: document.querySelector("#auth-phone"),
  authCode: document.querySelector("#auth-code"),
  authName: document.querySelector("#auth-name"),
  authNameField: document.querySelector("#display-name-field"),
  authMessage: document.querySelector("#auth-message"),
  authCardTitle: document.querySelector("#auth-card-title"),
  authCardDescription: document.querySelector("#auth-card-description"),
  authSubmit: document.querySelector("#auth-submit"),
  authSubmitText: document.querySelector("#auth-submit-text"),
  registerTab: document.querySelector("#register-tab"),
  loginTab: document.querySelector("#login-tab"),
  requestCodeButton: document.querySelector("#request-code-button"),
  currentUserName: document.querySelector("#current-user-name"),
  currentUserPhone: document.querySelector("#current-user-phone"),
  logoutButton: document.querySelector("#logout-button"),
  conversation: document.querySelector("#conversation"),
  form: document.querySelector("#chat-form"),
  question: document.querySelector("#question"),
  voiceButton: document.querySelector("#voice-button"),
  voiceTitle: document.querySelector("#voice-title"),
  voiceStatus: document.querySelector("#voice-status"),
  language: document.querySelector("#language"),
  autoSend: document.querySelector("#auto-send"),
  sendButton: document.querySelector("#send-button"),
  serviceStatus: document.querySelector("#service-status"),
  modelName: document.querySelector("#model-name"),
  setupWarning: document.querySelector("#setup-warning"),
};

const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;
const speechRecognitionSupported = Boolean(
  SpeechRecognition && window.isSecureContext,
);

let recognition = null;
let recognitionPhase = "idle";
let recognitionStopTimer = null;
let recognitionFailed = false;
let recognitionError = "";
let recognitionPrefix = "";
let recognitionFinalTranscript = "";
let recognitionManualStop = false;
let busy = false;
let authMode = "register";
let authBusy = false;
let codeCooldownTimer = null;
let codeCooldownRemaining = 0;
let sessionId = sessionStorage.getItem("parking-ai-session");
let cachedLocation = null;
let cachedLocationAt = 0;

function appendMessage(role, text, options = {}) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  if (options.loading) article.classList.add("is-loading");
  if (options.error) article.classList.add("is-error");

  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = role === "user" ? "You" : "N";

  const body = document.createElement("div");
  body.className = "message-body";

  const author = document.createElement("span");
  author.className = "message-author";
  author.textContent = role === "user" ? "您" : "NavPark";

  const paragraph = document.createElement("p");
  paragraph.textContent = text;

  body.append(author, paragraph);
  article.append(avatar, body);
  elements.conversation.append(article);
  elements.conversation.scrollTop = elements.conversation.scrollHeight;

  return { article, paragraph };
}

function setBusy(value) {
  busy = value;
  elements.sendButton.disabled = value;
  elements.voiceButton.disabled = value || !speechRecognitionSupported;
  elements.question.disabled = value;
}

function setRecognitionPhase(phase) {
  recognitionPhase = phase;
  const active = phase !== "idle";
  elements.voiceButton.classList.toggle("is-listening", active);
  elements.voiceButton.setAttribute("aria-pressed", String(active));

  if (phase === "starting") {
    elements.voiceTitle.textContent = "正在打开麦克风…";
    elements.voiceStatus.textContent = "请稍候，再次点击可以取消";
    return;
  }
  if (phase === "listening") {
    elements.voiceTitle.textContent = "正在聆听…";
    elements.voiceStatus.textContent = "说完后会自动结束，再次点击可以停止";
    return;
  }
  if (phase === "stopping") {
    elements.voiceTitle.textContent = "正在停止…";
    elements.voiceStatus.textContent = "正在结束语音识别，请稍候";
    return;
  }

  elements.voiceTitle.textContent = "点击麦克风开始";
  elements.voiceStatus.textContent = "请允许浏览器使用麦克风";
}

function setAuthMessage(message, kind = "") {
  elements.authMessage.textContent = message;
  elements.authMessage.classList.toggle("is-error", kind === "error");
  elements.authMessage.classList.toggle("is-success", kind === "success");
}

function authErrorMessage(payload, fallback) {
  if (typeof payload?.detail === "string") {
    return payload.detail;
  }
  if (Array.isArray(payload?.detail) && payload.detail[0]?.msg) {
    return payload.detail[0].msg;
  }
  return fallback;
}

function normalizePhoneInput() {
  let digits = elements.authPhone.value.replace(/\D/g, "");
  if (digits.startsWith("0086")) digits = digits.slice(4);
  if (digits.startsWith("86") && digits.length > 11) digits = digits.slice(2);
  elements.authPhone.value = digits.slice(0, 11);
  return elements.authPhone.value;
}

function validPhone(phone) {
  return /^1[3-9]\d{9}$/.test(phone);
}

function setAuthMode(mode) {
  authMode = mode;
  const isRegister = mode === "register";
  elements.registerTab.classList.toggle("is-active", isRegister);
  elements.loginTab.classList.toggle("is-active", !isRegister);
  elements.registerTab.setAttribute("aria-selected", String(isRegister));
  elements.loginTab.setAttribute("aria-selected", String(!isRegister));
  elements.authNameField.hidden = !isRegister;
  elements.authCardTitle.textContent = isRegister
    ? "创建你的 NavPark 账号"
    : "欢迎回到 NavPark";
  elements.authCardDescription.textContent = isRegister
    ? "新用户使用手机号完成验证后即可进入。"
    : "使用已验证的手机号登录，继续你的停车会话。";
  elements.authSubmitText.textContent = isRegister
    ? "注册并进入"
    : "登录并进入";
  setAuthMessage("");
}

function updateAuthUser(user) {
  const phone = user.phone || "";
  const maskedPhone = phone.length >= 8
    ? `${phone.slice(2, 5)} **** ${phone.slice(-4)}`
    : phone;
  elements.currentUserName.textContent = user.display_name || "NavPark 用户";
  elements.currentUserPhone.textContent = maskedPhone;

  const storedUserId = sessionStorage.getItem("parking-ai-user-id");
  if (storedUserId && storedUserId !== user.id) {
    sessionId = null;
    sessionStorage.removeItem("parking-ai-session");
  }
  sessionStorage.setItem("parking-ai-user-id", user.id);
}

function showAuthenticatedApp(user) {
  updateAuthUser(user);
  elements.authGate.classList.add("is-hidden");
  elements.authGate.setAttribute("aria-hidden", "true");
  elements.appShell.classList.remove("is-hidden");
  elements.appShell.setAttribute("aria-hidden", "false");
  loadConfig();
  window.setTimeout(() => elements.question.focus(), 100);
}

function showAuthGate(message = "") {
  elements.appShell.classList.add("is-hidden");
  elements.appShell.setAttribute("aria-hidden", "true");
  elements.authGate.classList.remove("is-hidden");
  elements.authGate.setAttribute("aria-hidden", "false");
  if (message) setAuthMessage(message, "error");
  window.setTimeout(() => elements.authPhone.focus(), 100);
}

function startCodeCooldown(seconds) {
  window.clearInterval(codeCooldownTimer);
  codeCooldownRemaining = seconds;
  elements.requestCodeButton.disabled = true;

  const render = () => {
    elements.requestCodeButton.textContent =
      codeCooldownRemaining > 0
        ? `${codeCooldownRemaining}s 后重试`
        : "获取验证码";
    if (codeCooldownRemaining <= 0) {
      window.clearInterval(codeCooldownTimer);
      elements.requestCodeButton.disabled = false;
      return;
    }
    codeCooldownRemaining -= 1;
  };

  render();
  codeCooldownTimer = window.setInterval(render, 1000);
}

async function requestSmsCode() {
  const phone = normalizePhoneInput();
  if (!validPhone(phone)) {
    setAuthMessage("请输入有效的 11 位中国大陆手机号。", "error");
    elements.authPhone.focus();
    return;
  }

  elements.requestCodeButton.disabled = true;
  setAuthMessage("正在发送验证码…");
  try {
    const response = await fetch("/auth/sms/request", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        phone,
        purpose: authMode,
      }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(authErrorMessage(payload, "验证码发送失败。"));
    }

    if (payload.debug_code) {
      elements.authCode.value = payload.debug_code;
      setAuthMessage(
        `开发环境验证码：${payload.debug_code}，已自动填入。`,
        "success",
      );
    } else {
      setAuthMessage("验证码已发送，请在 5 分钟内完成验证。", "success");
    }
    startCodeCooldown(payload.resend_after || 60);
    elements.authCode.focus();
  } catch (error) {
    setAuthMessage(error.message, "error");
    elements.requestCodeButton.disabled = false;
  }
}

async function submitAuthForm(event) {
  event.preventDefault();
  if (authBusy) return;

  const phone = normalizePhoneInput();
  const code = elements.authCode.value.replace(/\D/g, "");
  if (!validPhone(phone)) {
    setAuthMessage("请输入有效的 11 位中国大陆手机号。", "error");
    return;
  }
  if (!/^\d{6}$/.test(code)) {
    setAuthMessage("请输入 6 位数字验证码。", "error");
    elements.authCode.focus();
    return;
  }

  authBusy = true;
  elements.authSubmit.disabled = true;
  setAuthMessage("正在验证手机号…");
  try {
    const response = await fetch("/auth/sms/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        phone,
        code,
        purpose: authMode,
        display_name: authMode === "register"
          ? elements.authName.value.trim()
          : null,
      }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(authErrorMessage(payload, "登录失败，请稍后重试。"));
    }

    elements.authCode.value = "";
    elements.authForm.reset();
    showAuthenticatedApp(payload.user);
  } catch (error) {
    setAuthMessage(error.message, "error");
  } finally {
    authBusy = false;
    elements.authSubmit.disabled = false;
  }
}

async function loadCurrentUser() {
  try {
    const response = await fetch("/auth/me", {
      cache: "no-store",
    });
    if (!response.ok) {
      showAuthGate();
      return;
    }
    const payload = await response.json();
    showAuthenticatedApp(payload.user);
  } catch {
    showAuthGate("无法连接登录服务，请稍后刷新页面。");
  }
}

async function logout() {
  elements.logoutButton.disabled = true;
  try {
    await fetch("/auth/logout", { method: "POST" });
  } finally {
    sessionStorage.removeItem("parking-ai-session");
    sessionStorage.removeItem("parking-ai-user-id");
    window.location.reload();
  }
}

function updateServiceStatus(configured, model) {
  elements.modelName.textContent = model || "DeepSeek";
  elements.serviceStatus.replaceChildren();

  const dot = document.createElement("span");
  dot.className = "status-dot";
  elements.serviceStatus.append(dot, configured ? "已就绪" : "待配置");

  elements.serviceStatus.classList.toggle("is-error", !configured);
  elements.setupWarning.hidden = configured;
}

async function loadConfig() {
  try {
    const response = await fetch("/config", { cache: "no-store" });
    if (!response.ok) throw new Error("无法读取配置");
    const config = await response.json();
    updateServiceStatus(config.configured, config.model);
  } catch {
    elements.serviceStatus.textContent = "服务不可用";
    elements.serviceStatus.classList.add("is-error");
  }
}

function isNavigationQuestion(question) {
  const normalized = question.toLowerCase();
  return /导航|带我去|怎么去|怎么走|路线|navigate|directions|route to/.test(
    normalized,
  );
}

function isParkingSpotReference(question) {
  return /(?:b\s*[1-3]\s*(?:层|楼)?\s*的?\s*[-–—\s]*[a-c]\s*区?\s*[-–—\s]*\d{1,3}|[a-c]\s*区?\s*[-–—\s]*\d{3})/i.test(
    question,
  );
}

function needsLiveLocation(question) {
  const normalized = question.toLowerCase();
  const asksForLocation = /最近|附近|哪里|哪儿|nearest|where/.test(normalized);
  const asksForParking = /空车位|空闲车位|空位|车位|停车|available.*(spot|parking)|parking|spot/.test(
    normalized,
  );
  const parkingReference = isParkingSpotReference(question);
  const asksForNavigation = isNavigationQuestion(question);
  return (
    (asksForLocation && (asksForParking || parkingReference))
    || (asksForNavigation && (asksForParking || parkingReference))
  );
}

async function getLiveLocation() {
  if (cachedLocation && Date.now() - cachedLocationAt < 120000) {
    return cachedLocation;
  }
  if (!navigator.geolocation) {
    return null;
  }

  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        cachedLocation = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        };
        cachedLocationAt = Date.now();
        resolve(cachedLocation);
      },
      () => resolve(null),
      {
        enableHighAccuracy: false,
        maximumAge: 60000,
        timeout: 5000,
      },
    );
  });
}

function navigationFromPayload(payload) {
  return (
    payload?.navigation
    || payload?.api_result?.parking_availability?.navigation
    || null
  );
}

function appendMapAction(message, navigation) {
  if (!navigation || !window.NavParkRouteMap) return;

  const action = document.createElement("button");
  action.type = "button";
  action.className = "message-map-action";
  action.textContent = "查看实时导航地图";
  action.addEventListener("click", () => {
    window.NavParkRouteMap?.focusMap();
  });
  message.article.querySelector(".message-body")?.append(action);
}

async function submitQuestion() {
  const question = elements.question.value.trim();
  if (!question || busy) return;

  appendMessage("user", question);
  elements.question.value = "";
  const wantsLocation = needsLiveLocation(question);
  const wantsNavigation = (
    isNavigationQuestion(question)
    || isParkingSpotReference(question)
  );
  const pending = appendMessage(
    "assistant",
    wantsLocation
      ? (
        wantsNavigation
          ? "正在定位并生成实时导航地图"
          : "正在定位并查询空车位"
      )
      : "正在思考",
    { loading: true },
  );
  setBusy(true);

  try {
    const location = wantsLocation ? await getLiveLocation() : null;
    const requestBody = {
      question,
      session_id: sessionId,
    };
    if (location) {
      requestBody.location = location;
    }

    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
    });

    const payload = await response.json().catch(() => ({}));
    if (response.status === 401) {
      showAuthGate("登录已过期，请重新登录。");
      throw new Error("登录已过期，请重新登录。");
    }
    if (!response.ok) {
      throw new Error(authErrorMessage(
        payload,
        "请求失败，请稍后重试",
      ));
    }

    if (payload.session_id) {
      sessionId = payload.session_id;
      sessionStorage.setItem("parking-ai-session", sessionId);
    }

    pending.article.classList.remove("is-loading");
    pending.paragraph.textContent =
      payload.response || "抱歉，这次没有生成有效回答。";
    const navigation = navigationFromPayload(payload);
    if (navigation) {
      appendMapAction(pending, navigation);
      Promise.resolve(window.NavParkRouteMap?.showRoute(navigation))
        .catch(() => {});
    } else if (wantsNavigation) {
      window.NavParkRouteMap?.clearRoute("未生成路线");
    }
    elements.conversation.scrollTop = elements.conversation.scrollHeight;
  } catch (error) {
    pending.article.classList.remove("is-loading");
    pending.article.classList.add("is-error");
    pending.paragraph.textContent = error.message;
  } finally {
    setBusy(false);
    elements.question.focus();
  }
}

function clearRecognitionStopTimer() {
  if (recognitionStopTimer !== null) {
    window.clearTimeout(recognitionStopTimer);
    recognitionStopTimer = null;
  }
}

function finalizeRecognition() {
  if (recognitionPhase === "idle") return;

  clearRecognitionStopTimer();
  const failed = recognitionFailed;
  const error = recognitionError;
  const manuallyStopped = recognitionManualStop;
  const finalText = recognitionFinalTranscript.trim();
  const transcript = elements.question.value.trim();
  const hasNewText = transcript && transcript !== recognitionPrefix;

  setRecognitionPhase("idle");
  recognitionManualStop = false;

  if (failed && !manuallyStopped) {
    elements.voiceStatus.textContent = error;
  } else if (manuallyStopped) {
    elements.voiceStatus.textContent = hasNewText
      ? "语音输入已停止，识别文字可以编辑或发送"
      : "语音输入已停止，没有识别到新内容";
    if (hasNewText && elements.autoSend.checked) {
      submitQuestion();
    }
  } else if (finalText) {
    elements.voiceStatus.textContent = "识别完成，可以发送";
    if (elements.autoSend.checked) {
      submitQuestion();
    }
  } else {
    elements.voiceStatus.textContent = "没有识别到内容，请再试一次";
  }

  if (!transcript) {
    elements.question.focus();
  }
}

function forceStopRecognition() {
  clearRecognitionStopTimer();
  try {
    recognition?.abort();
  } catch {
    // Some mobile browsers throw if the recognizer already ended.
  }
  finalizeRecognition();
}

function scheduleRecognitionStopFallback() {
  clearRecognitionStopTimer();
  recognitionStopTimer = window.setTimeout(() => {
    if (recognitionPhase === "idle") return;
    forceStopRecognition();
  }, 900);
}

function createRecognition() {
  recognition = new SpeechRecognition();
  recognition.lang = elements.language.value;
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    recognitionPrefix = elements.question.value.trim();
    recognitionFinalTranscript = "";
    recognitionFailed = false;
    recognitionError = "";

    if (recognitionPhase === "stopping") {
      window.setTimeout(forceStopRecognition, 0);
      return;
    }
    setRecognitionPhase("listening");
  };

  recognition.onresult = (event) => {
    let interimTranscript = "";

    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const transcript = event.results[index][0].transcript;
      if (event.results[index].isFinal) {
        recognitionFinalTranscript += transcript;
      } else {
        interimTranscript += transcript;
      }
    }

    const spokenText = (
      `${recognitionFinalTranscript}${interimTranscript}`
    ).trim();
    elements.question.value = [
      recognitionPrefix,
      spokenText,
    ].filter(Boolean).join(" ");
  };

  recognition.onerror = (event) => {
    if (event.error === "aborted" && recognitionManualStop) {
      return;
    }
    recognitionFailed = true;
    const messages = {
      "not-allowed": "麦克风权限被拒绝，请在浏览器设置中允许访问",
      "service-not-allowed": "当前浏览器不允许使用语音识别服务",
      "audio-capture": "没有检测到可用的麦克风",
      "no-speech": "没有听到声音，请再试一次",
      network: "浏览器的语音识别服务网络不可用",
      aborted: "语音输入已停止",
    };
    recognitionError =
      messages[event.error] || "语音识别失败，请稍后重试";
    elements.voiceStatus.textContent = recognitionError;
  };

  recognition.onend = finalizeRecognition;
  setRecognitionPhase("idle");
}

function startRecognition() {
  if (!recognition || busy || recognitionPhase !== "idle") return;

  if (!window.isSecureContext) {
    elements.voiceStatus.textContent = "麦克风需要 HTTPS 页面";
    return;
  }

  clearRecognitionStopTimer();
  recognitionManualStop = false;
  recognitionFailed = false;
  recognitionError = "";
  recognition.lang = elements.language.value;
  setRecognitionPhase("starting");
  try {
    recognition.start();
  } catch (error) {
    try {
      recognition.abort();
    } catch {
      // Ignore cleanup errors from an incomplete recognition start.
    }
    setRecognitionPhase("idle");
    elements.voiceStatus.textContent = (
      error?.name === "InvalidStateError"
        ? "语音状态已重置，请再点击一次"
        : "麦克风正在初始化，请稍后重试"
    );
  }
}

function stopRecognition() {
  if (!recognition || recognitionPhase === "idle") return;
  if (recognitionPhase === "stopping") {
    forceStopRecognition();
    return;
  }

  recognitionManualStop = true;
  setRecognitionPhase("stopping");
  try {
    recognition.stop();
  } catch {
    try {
      recognition.abort();
    } catch {
      // The fallback timer below will reset the UI regardless.
    }
  }
  scheduleRecognitionStopFallback();
}

function toggleRecording() {
  if (!recognition || busy) return;
  if (recognitionPhase === "idle") {
    startRecognition();
  } else {
    stopRecognition();
  }
}

elements.registerTab.addEventListener("click", () => setAuthMode("register"));
elements.loginTab.addEventListener("click", () => setAuthMode("login"));
elements.authPhone.addEventListener("input", normalizePhoneInput);
elements.authCode.addEventListener(
  "input",
  () => {
    elements.authCode.value = elements.authCode.value
      .replace(/\D/g, "")
      .slice(0, 6);
  },
);
elements.requestCodeButton.addEventListener("click", requestSmsCode);
elements.authForm.addEventListener("submit", submitAuthForm);
elements.logoutButton.addEventListener("click", logout);

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  submitQuestion();
});

elements.question.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.form.requestSubmit();
  }
});

elements.voiceButton.addEventListener("click", toggleRecording);

if (speechRecognitionSupported) {
  createRecognition();
} else if (!SpeechRecognition) {
  elements.voiceButton.disabled = true;
  elements.voiceTitle.textContent = "当前浏览器不支持语音输入";
  elements.voiceStatus.textContent = "请使用最新版 Edge 或 Chrome";
} else {
  elements.voiceButton.disabled = true;
  elements.voiceTitle.textContent = "麦克风需要 HTTPS";
  elements.voiceStatus.textContent = "请使用手机扫码页面提供的 HTTPS 地址";
}

setAuthMode("register");
loadCurrentUser();
document.documentElement.dataset.navparkApp = "ready";
document.documentElement.dataset.voiceMode = speechRecognitionSupported
  ? "ready"
  : "unavailable";
