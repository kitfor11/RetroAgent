// 前端逻辑：用 fetch 调后端的 FastAPI 接口。
// 前端和后端同源（同一个服务），所以不用处理跨域。

const METHOD_LABEL = {
  solved: "✅ 学会新技能",
  reused_skill: "🔄 复用技能",
  failed: "⚠️ 记入教训",
};

async function postJSON(url, body, timeoutMs = 120000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!resp.ok) throw new Error(`请求失败：HTTP ${resp.status}`);
    return await resp.json();
  } catch (e) {
    if (e.name === "AbortError") throw new Error("请求超时（超过 120 秒），请重试");
    throw e;
  } finally {
    clearTimeout(timer);
  }
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
    refreshFiles(currentPath);  // Agent 可能整理/移动了文件，刷新当前浏览的目录
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

// ---------- 本地文件浏览 ----------
let currentPath = "";
let currentParent = "";

async function refreshFiles(path) {
  const list = document.getElementById("files-list");
  const cwdEl = document.getElementById("files-cwd");
  try {
    const url = path ? `/files?path=${encodeURIComponent(path)}` : "/files";
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    currentPath = data.path;
    currentParent = data.parent;
    cwdEl.textContent = data.path;
    renderEntries(list, data);
  } catch (e) {
    list.innerHTML = `<li class="error">${escapeHtml(e.message)}</li>`;
  }
}

function renderEntries(list, data) {
  const items = [];
  data.dirs.forEach((d) => {
    items.push(`<li class="entry" data-type="dir" data-name="${encodeURIComponent(d)}">📁 ${escapeHtml(d)}</li>`);
  });
  data.files.forEach((f) => {
    items.push(`<li class="entry file-entry" data-type="file" data-name="${encodeURIComponent(f.name)}">📄 ${escapeHtml(f.name)} <span class="size">${f.size_kb} KB</span></li>`);
  });
  list.innerHTML = items.length ? items.join("") : `<li class="muted">（空目录）</li>`;
}

function joinPath(dir, name) {
  return dir.endsWith("/") || dir.endsWith("\\") ? dir + name : dir + "/" + name;
}

function goUp() {
  if (currentParent) refreshFiles(currentParent);
}

function goTo() {
  const input = document.getElementById("files-path");
  const p = input.value.trim();
  if (p) refreshFiles(p);
}

async function previewFile(fullPath, name) {
  const preview = document.getElementById("file-preview");
  try {
    const resp = await fetch(`/file?path=${encodeURIComponent(fullPath)}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    preview.classList.remove("hidden");
    preview.innerHTML = `
      <div class="preview-head">${escapeHtml(name)} <button class="ghost" id="preview-close">关闭</button></div>
      <pre>${escapeHtml(data.content)}</pre>
    `;
    document.getElementById("preview-close").addEventListener("click", () => preview.classList.add("hidden"));
  } catch (e) {
    preview.classList.remove("hidden");
    preview.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
  }
}

async function chooseDir() {
  const btn = document.getElementById("files-choose");
  btn.disabled = true;
  btn.textContent = "等待选择…";
  try {
    const resp = await fetch("/choose-dir", { method: "POST" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    if (data.canceled) return;                    // 用户点了取消，不动
    document.getElementById("files-path").value = data.path;
    await refreshFiles(data.path);                 // 刷新到选中的文件夹
    await buildIndex();                            // 文档库也切换到选中文件夹
  } catch (e) {
    alert("打开文件夹选择窗口失败：" + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "📂 选择文件夹";
  }
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
  document.getElementById("files-choose").addEventListener("click", chooseDir);
  document.getElementById("files-refresh").addEventListener("click", () => refreshFiles(currentPath));
  document.getElementById("files-up").addEventListener("click", goUp);
  document.getElementById("files-go").addEventListener("click", goTo);
  document.getElementById("files-path").addEventListener("keydown", (e) => {
    if (e.key === "Enter") goTo();
  });
  document.getElementById("files-list").addEventListener("click", (e) => {
    const li = e.target.closest("li.entry");
    if (!li) return;
    const name = decodeURIComponent(li.dataset.name);
    const full = joinPath(currentPath, name);
    if (li.dataset.type === "dir") refreshFiles(full);
    else previewFile(full, name);
  });
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
