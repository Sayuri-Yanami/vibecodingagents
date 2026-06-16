const messages = document.querySelector("#messages");
const form = document.querySelector("#chatForm");
const questionInput = document.querySelector("#question");
const sendButton = document.querySelector("#sendButton");
const clearButton = document.querySelector("#clearButton");
const statusDot = document.querySelector("#statusDot");
const statusText = document.querySelector("#statusText");
const modelText = document.querySelector("#modelText");

let history = [];

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

function addMessage(role, content, sources = []) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "你" : "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = formatAnswer(content);

  if (sources.length) {
    const sourceBox = document.createElement("div");
    sourceBox.className = "sources";
    sourceBox.innerHTML = "<strong>本地检索来源</strong>";
    sources.forEach((source) => {
      const item = document.createElement("div");
      item.className = "source-item";
      item.textContent = `${source.source} · 相关度 ${Number(source.score).toFixed(3)}`;
      sourceBox.appendChild(item);
    });
    bubble.appendChild(sourceBox);
  }

  article.append(avatar, bubble);
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
    statusText.textContent = "服务已就绪";
    modelText.textContent = `${data.model} · ${data.index_chunks} 个知识块`;
  } catch (error) {
    statusDot.classList.remove("online");
    statusText.textContent = "服务未连接";
    modelText.textContent = error.message;
  }
}

async function askQuestion(question) {
  addMessage("user", question);
  const pending = addMessage("assistant", "正在检索知识库并生成回答...");
  pending.querySelector(".bubble").classList.add("typing");
  sendButton.disabled = true;
  questionInput.disabled = true;

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "请求失败");

    pending.remove();
    addMessage("assistant", data.answer, data.sources || []);
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

document.querySelectorAll(".prompt-chip").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.prompt;
    questionInput.focus();
  });
});

clearButton.addEventListener("click", () => {
  history = [];
  messages.innerHTML = "";
  addMessage("assistant", "本轮对话已清空。可以开始新的面试练习。");
  questionInput.focus();
});

checkHealth();
questionInput.focus();

