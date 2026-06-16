const messages = document.querySelector("#messages");
const form = document.querySelector("#chatForm");
const questionInput = document.querySelector("#question");
const sendButton = document.querySelector("#sendButton");
const clearButton = document.querySelector("#clearButton");
const humanButton = document.querySelector("#humanButton");
const statusDot = document.querySelector("#statusDot");
const statusText = document.querySelector("#statusText");
const modelText = document.querySelector("#modelText");
const storeName = document.querySelector("#storeName");

let history = [];
let missCount = 0;

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatAnswer(value) {
  const safe = escapeHtml(value);
  return safe
    .split(/\n{2,}/)
    .map((paragraph) => `<p>${paragraph.replaceAll("\n", "<br>")}</p>`)
    .join("");
}

function emotionLabel(emotion) {
  if (emotion === "angry") return "已识别：用户不满";
  if (emotion === "anxious") return "已识别：用户着急";
  return "";
}

function addMessage(role, content, options = {}) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "您" : "AI";

  const messageContent = document.createElement("div");
  messageContent.className = "message-content";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = formatAnswer(content);

  const label = emotionLabel(options.emotion);
  if (label) {
    const emotionTag = document.createElement("div");
    emotionTag.className = "emotion-tag";
    emotionTag.textContent = label;
    bubble.prepend(emotionTag);
  }

  if (options.needsHuman) {
    const humanTag = document.createElement("div");
    humanTag.className = "human-tag";
    humanTag.textContent = "已建议人工处理";
    bubble.appendChild(humanTag);
  }

  if (options.sources?.length) {
    const sourceBox = document.createElement("details");
    sourceBox.className = "sources";
    const summary = document.createElement("summary");
    summary.textContent = `查看 ${options.sources.length} 条本地知识来源`;
    sourceBox.appendChild(summary);

    options.sources.forEach((source) => {
      const item = document.createElement("div");
      item.className = "source-item";
      item.innerHTML = `<span>${escapeHtml(source.source)}</span><strong>${Number(source.score).toFixed(3)}</strong>`;
      sourceBox.appendChild(item);
    });
    bubble.appendChild(sourceBox);
  }

  const meta = document.createElement("span");
  meta.className = "message-time";
  meta.textContent = role === "user" ? "您" : "客服助手";

  messageContent.append(bubble, meta);
  article.append(avatar, messageContent);
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health", { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "服务异常");
    statusDot.classList.add("online");
    statusText.textContent = "服务在线";
    modelText.textContent = `${data.model} / ${data.index_chunks} 个知识块`;
    storeName.textContent = `${data.store_name}售后客服`;
  } catch (error) {
    statusDot.classList.remove("online");
    statusText.textContent = "服务未连接";
    modelText.textContent = error.message;
  }
}

async function askQuestion(question) {
  addMessage("user", question);
  const pending = addMessage("assistant", "正在检索本地售后规则并组织回答...");
  pending.querySelector(".bubble").classList.add("typing");
  sendButton.disabled = true;
  humanButton.disabled = true;
  questionInput.disabled = true;

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        history,
        miss_count: missCount,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "请求失败");

    pending.remove();
    addMessage("assistant", data.answer, {
      sources: data.sources || [],
      emotion: data.emotion,
      needsHuman: data.needs_human,
    });
    missCount = Number(data.miss_count || 0);
    history.push(
      { role: "user", content: question },
      { role: "assistant", content: data.answer },
    );
    history = history.slice(-8);
  } catch (error) {
    pending.remove();
    addMessage("assistant", `请求失败：${error.message}`);
  } finally {
    sendButton.disabled = false;
    humanButton.disabled = false;
    questionInput.disabled = false;
    questionInput.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;
  questionInput.value = "";
  askQuestion(question);
});

questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

document.querySelectorAll(".quick-card").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.prompt;
    questionInput.focus();
  });
});

humanButton.addEventListener("click", () => {
  askQuestion("我要转人工客服");
});

clearButton.addEventListener("click", () => {
  history = [];
  missCount = 0;
  messages.innerHTML = "";
  addMessage("assistant", "本轮对话已清空。请告诉我您现在需要处理的问题。");
  questionInput.focus();
});

checkHealth();
questionInput.focus();
