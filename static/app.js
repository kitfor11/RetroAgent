// 前端逻辑：用 fetch 调后端的 FastAPI 接口。
// 前端和后端同源（同一个服务），所以不用处理跨域。

const METHOD_LABEL = {
  solved: "✅ 学会新技能",
  reused_skill: "🔄 复用技能",
  failed: "⚠️ 记入教训",
};

async function postJSON(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error(`请求失败：HTTP ${resp.status}`);
  return resp.json();
}

function escapeHtml(s) {
  return String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

// ---------- 提交任务 ----------
async function submitTask() {
  const input = document.getElementById("task-input");
  const task = input.value.trim();
  if (!task) return;

  const btn = document.getElementById("task-btn");
  const result = document.getElementById("task-result");
  btn.disabled = true;
  result.innerHTML = `<p class="muted">Agent 正在思考…（可能要十几秒）</p>`;

  try {
    const data = await postJSON("/solve", { task });
    renderTaskResult(result, data);
  } catch (e) {
    result.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
  } finally {
    btn.disabled = false;
    refreshSkills();    // 任务结束后技能/记忆可能变了，刷新侧栏
    refreshMemories();
    refreshFiles();     // Agent 可能整理/移动了沙盒文件
  }
}

function renderTaskResult(el, data) {
  const label = METHOD_LABEL[data.method] || data.method;
  let extra = "";
  if (data.skill) extra = `（技能：${data.skill}）`;
  if (data.learned_skill) extra = `（新技能：${data.learned_skill}）`;
  if (data.learned_lesson) extra = `（教训：${data.learned_lesson}）`;

  const answer = data.answer ?? "（未完成，已把失败记录成教训）";

  let traceHtml = "";
  if (Array.isArray(data.trace) && data.trace.length) {
    const steps = data.trace
      .map((s, i) => `<div class="step"><span class="step-no">第 ${i + 1} 步</span><pre>${escapeHtml(s)}</pre></div>`)
      .join("");
    traceHtml = `<details class="trace"><summary>查看思维链（CoT）</summary>${steps}</details>`;
  }

  el.innerHTML = `
    <div class="badge method-${data.method}">${label}${escapeHtml(extra)}</div>
    <p class="answer">${escapeHtml(answer)}</p>
    ${traceHtml}
  `;
}

// ---------- 文档问答 ----------
async function buildIndex() {
  const status = document.getElementById("index-status");
  status.textContent = "索引中…";
  try {
    const data = await postJSON("/index", {});
    status.textContent = `已索引 ${data.indexed_chunks} 个 chunk`;
  } catch (e) {
    status.textContent = `索引失败：${e.message}`;
  }
}

async function askQuestion() {
  const input = document.getElementById("qa-input");
  const q = input.value.trim();
  if (!q) return;

  const result = document.getElementById("qa-result");
  result.innerHTML = `<p class="muted">检索中…</p>`;
  try {
    const data = await postJSON("/ask", { question: q });
    const sources = (data.sources || [])
      .map((s) => `<span class="source">${escapeHtml(s)}</span>`)
      .join(" ");
    result.innerHTML = `
      <p class="answer">${escapeHtml(data.answer)}</p>
      ${sources ? `<p class="muted">来源：${sources}</p>` : ""}
    `;
  } catch (e) {
    result.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
  }
}

// ---------- 沙盒文件 ----------
async function refreshFiles() {
  const list = document.getElementById("files-list");
  try {
    const resp = await fetch("/files");
    const tree = await resp.json();
    list.innerHTML = renderTree(tree);
  } catch (e) {
    list.innerHTML = `<li class="error">${escapeHtml(e.message)}</li>`;
  }
}

function renderTree(node) {
  if (node.type === "file") {
    return `<li class="file"><span>📄 ${escapeHtml(node.name)}</span><span class="size">${node.size_kb} KB</span></li>`;
  }
  const kids = (node.children || []).map(renderTree).join("");
  return `<li class="dir"><span class="dir-name">📁 ${escapeHtml(node.name)}</span><ul>${kids || '<li class="muted">（空）</li>'}</ul></li>`;
}

// ---------- 侧栏 ----------
async function refreshSkills() {
  const list = document.getElementById("skills-list");
  try {
    const resp = await fetch("/skills");
    const data = await resp.json();
    list.innerHTML = data.skills.length
      ? data.skills.map((s) => `<li>${escapeHtml(s)}</li>`).join("")
      : `<li class="muted">（还没有技能，去提交个任务吧）</li>`;
  } catch (e) {
    list.innerHTML = `<li class="error">${escapeHtml(e.message)}</li>`;
  }
}

async function refreshMemories() {
  const list = document.getElementById("memories-list");
  try {
    const resp = await fetch("/memories");
    const data = await resp.json();
    list.innerHTML = data.memories.length
      ? data.memories.map((m) => `<li>${escapeHtml(m)}</li>`).join("")
      : `<li class="muted">（还没有教训，很好）</li>`;
  } catch (e) {
    list.innerHTML = `<li class="error">${escapeHtml(e.message)}</li>`;
  }
}

// ---------- 绑定事件 ----------
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("task-btn").addEventListener("click", submitTask);
  document.getElementById("qa-btn").addEventListener("click", askQuestion);
  document.getElementById("index-btn").addEventListener("click", buildIndex);
  document.getElementById("files-refresh").addEventListener("click", refreshFiles);
  document.getElementById("skills-refresh").addEventListener("click", refreshSkills);
  document.getElementById("memories-refresh").addEventListener("click", refreshMemories);

  // 示例任务按钮：点击填入文本框
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.getElementById("task-input").value = chip.dataset.task;
    });
  });

  // 输入框回车：任务框 Ctrl+Enter 提交；问答框 Enter 提交
  document.getElementById("task-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submitTask();
  });
  document.getElementById("qa-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") askQuestion();
  });

  refreshFiles();
  refreshSkills();
  refreshMemories();
});
