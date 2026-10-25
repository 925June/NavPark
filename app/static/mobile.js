const urlNode = document.querySelector("#mobile-url");
const openLink = document.querySelector("#open-url");
const copyButton = document.querySelector("#copy-url");
const secureNotice = document.querySelector("#secure-notice");
const secureMessage = document.querySelector("#secure-message");

async function loadMobileInfo() {
  try {
    const response = await fetch("/mobile/info", { cache: "no-store" });
    if (!response.ok) throw new Error("无法读取手机访问地址");
    const info = await response.json();

    urlNode.textContent = info.url;
    urlNode.href = info.url;
    openLink.href = info.url;
    secureMessage.textContent = info.message;
    secureNotice.classList.toggle("is-secure", info.secure_context);
  } catch (error) {
    urlNode.textContent = "地址生成失败";
    secureMessage.textContent = error.message;
  }
}

copyButton.addEventListener("click", async () => {
  const text = urlNode.textContent.trim();
  if (!text || text === "地址生成失败") return;

  try {
    await navigator.clipboard.writeText(text);
    copyButton.textContent = "已复制";
  } catch {
    copyButton.textContent = "请长按地址复制";
  }

  window.setTimeout(() => {
    copyButton.textContent = "复制地址";
  }, 1800);
});

loadMobileInfo();
