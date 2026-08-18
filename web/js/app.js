//
// Project: File_Deduplification
// File: app.js
// Purpose: Front end for the workbench — run, review, execute
//
// Description:
// Vanilla ES modules, no build step, to match the rest of the project.
// The only piece with real subtlety is the SSE reader: it tracks the
// last sequence number it saw and passes it back on reconnect, so a
// dropped connection resumes without a gap and without duplicates.
//
// Author: Tim Canady
// Created: 2026-08-17
// Version: 0.1.0
//

const $ = (id) => document.getElementById(id);
const api = async (path, opts) => {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch { /* not JSON */ }
    throw new Error(detail);
  }
  return res.json();
};
const post = (path, body) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" },
              body: JSON.stringify(body || {}) });

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function bytes(n) {
  if (!n) return "0 B";
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${i === 0 ? n : n.toFixed(1)} ${u[i]}`;
}
const num = (n) => (n ?? 0).toLocaleString();

// ───────────────────────────── state ─────────────────────────────

const state = { jobId: null, jobStatus: null, planTotal: 0, planOffset: 0,
                dupeOffset: 0, stages: new Map() };

// ───────────────────────────── nav ─────────────────────────────

document.querySelectorAll("nav button").forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll("nav button").forEach((b) => b.classList.remove("on"));
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("on"));
    btn.classList.add("on");
    $("view-" + btn.dataset.view).classList.add("on");
    if (btn.dataset.view === "dupes") loadDuplicates();
    if (btn.dataset.view === "plan") loadPlan();
    if (btn.dataset.view === "jobs") loadJobs();
  };
});

$("cloud").onchange = (e) => {
  $("cloudopts").style.display = e.target.checked ? "" : "none";
};

// ───────────────────────────── system ─────────────────────────────

(async function loadSystem() {
  try {
    const s = await api("/api/system");
    const h = s.hardware;
    $("hw").textContent =
      `${h.performance_cores}P + ${h.efficiency_cores}E cores · ${h.memory_gb} GB · ` +
      s.stages.filter((x) => x.kind === "process").map((x) => x.workers)[0] +
      ` process workers`;
    $("hw").title = s.stages
      .map((x) => `${x.stage}: ${x.kind === "serial" ? "serial" : x.workers + "× " + x.kind} (${x.reason})`)
      .join("\n");
  } catch { $("hw").textContent = ""; }
})();

// ───────────────────────────── run ─────────────────────────────

function logLine(text, level) {
  const el = $("log");
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
  const span = document.createElement("div");
  if (level && level !== "info") span.className = level;
  span.textContent = text;
  el.appendChild(span);
  if (atBottom) el.scrollTop = el.scrollHeight;
}

// `label` is optional: progress events carry only the stage id, and
// passing that through would overwrite the human label the stage_start
// event already set ("Classifying files" becoming "classify").
function stageRow(stage, label, policy) {
  let row = state.stages.get(stage);
  if (!row) {
    if (state.stages.size === 0) $("stages").innerHTML = "";
    row = document.createElement("div");
    row.className = "stage";
    row.innerHTML =
      `<div class="stage-head"><span class="stage-name">${esc(stage)}</span>` +
      `<span class="stage-meta"></span></div><div class="bar"><i></i></div>`;
    $("stages").appendChild(row);
    state.stages.set(stage, row);
  }
  if (label) row.querySelector(".stage-name").textContent = label;
  if (policy) row.querySelector(".stage-meta").textContent = policy;
  return row;
}

function handleEvent(ev) {
  switch (ev.type) {
    case "stage_start":
      stageRow(ev.stage, ev.label, ev.policy || "");
      break;
    case "progress": {
      const row = stageRow(ev.stage);   // keep the stage_start label
      const pct = ev.total ? (ev.done / ev.total) * 100 : 0;
      row.querySelector("i").style.width = pct + "%";
      row.querySelector(".stage-meta").textContent =
        `${num(ev.done)} / ${num(ev.total)} · ${num(Math.round(ev.rate))}/s` +
        (ev.eta_seconds ? ` · ${ev.eta_seconds}s left` : "");
      break;
    }
    case "stage_end": {
      const row = state.stages.get(ev.stage);
      if (row) {
        row.classList.add("done");
        row.querySelector("i").style.width = "100%";
        row.querySelector(".stage-meta").textContent =
          `${ev.summary || "done"} · ${ev.elapsed}s`;
      }
      break;
    }
    case "log":
      logLine(ev.message, ev.level);
      break;
    case "done":
    case "cancelled":
      renderResult(ev.result, ev.type);
      finishRun(ev.type);
      break;
    case "error":
      logLine("ERROR: " + ev.message, "error");
      finishRun("error");
      break;
  }
}

function renderResult(r, status) {
  if (!r) { $("result").innerHTML = `<div class="empty">${esc(status)}</div>`; return; }
  const tiles = [
    ["Scanned", num(r.files_scanned)],
    ["Unique", num(r.unique_files)],
    ["Duplicates", num(r.duplicate_files)],
    ["Reclaimable", bytes(r.reclaimable_bytes)],
    ["Classified", num(r.classified)],
    ["Operations", num(r.planned_operations)],
    ["Duration", (r.duration_seconds ?? 0) + "s"],
  ];
  if (r.llm_resolved) tiles.push(["LLM resolved", num(r.llm_resolved)]);
  if (r.cloud_resolved) tiles.push(["Cloud resolved", num(r.cloud_resolved)]);
  if (r.cloud_spent_usd) tiles.push(["Cloud spend", "$" + r.cloud_spent_usd.toFixed(2)]);
  if (r.files_tagged) tiles.push(["Tagged", num(r.files_tagged)]);
  if (r.images_analyzed) tiles.push(["Images", num(r.images_analyzed)]);

  const cats = Object.entries(r.category_counts || {})
    .map(([k, v]) => `<span class="tag">${esc(k)} ${num(v)}</span>`).join(" ");

  $("result").innerHTML =
    `<div class="stats">` +
    tiles.map(([k, v]) => `<div class="stat"><b>${esc(v)}</b><span>${esc(k)}</span></div>`).join("") +
    `</div>` + (cats ? `<div style="margin-top:14px">${cats}</div>` : "");
}

function finishRun(status) {
  state.jobStatus = status;
  $("start").disabled = false;
  $("cancel").disabled = true;
  $("jobstatus").textContent = `job ${state.jobId} — ${status}`;
  $("exec").disabled = status !== "done";
  loadJobs();
}

// Reconnect-safe SSE: `after` is the last seq we processed, so a dropped
// connection resumes exactly where it left off.
function follow(jobId) {
  let lastSeq = 0;
  let closed = false;

  const open = () => {
    if (closed) return;
    const src = new EventSource(`/api/jobs/${jobId}/stream?after=${lastSeq}`);
    src.onmessage = (msg) => {
      const ev = JSON.parse(msg.data);
      if (ev.type === "stream_end") { closed = true; src.close(); return; }
      if (ev.seq) lastSeq = ev.seq;
      handleEvent(ev);
    };
    src.onerror = () => {
      src.close();
      if (!closed) setTimeout(open, 1500);  // network blip — resume
    };
  };
  open();
}

$("start").onclick = async () => {
  $("starterr").textContent = "";
  const body = {
    source: $("src").value.trim(),
    base_dir: $("dst").value.trim(),
    file_types: $("ftypes").value.trim() || null,
    max_files: $("maxfiles").value ? Number($("maxfiles").value) : null,
    use_db: $("usedb").checked,
    skip_duplicates: $("skipdupes").checked,
    llm_classify: $("llm").checked,
    cloud_classify: $("cloud").checked,
    cloud_cost_limit_usd: Number($("cap").value || 1),
    cloud_model: $("cmodel").value.trim() || null,
    ai_tagging: $("aitag").checked,
    analyze_images: $("images").checked,
  };
  try {
    const job = await post("/api/jobs", body);
    state.jobId = job.id;
    state.jobStatus = job.status;
    state.stages.clear();
    $("stages").innerHTML = "";
    $("log").innerHTML = "";
    $("result").innerHTML = '<div class="empty">Running…</div>';
    $("start").disabled = true;
    $("cancel").disabled = false;
    $("exec").disabled = true;
    $("jobstatus").textContent = `job ${job.id} — running`;
    follow(job.id);
  } catch (e) {
    $("starterr").textContent = e.message;
  }
};

$("cancel").onclick = async () => {
  if (!state.jobId) return;
  $("cancel").disabled = true;
  try { await post(`/api/jobs/${state.jobId}/cancel`); }
  catch (e) { logLine("Cancel failed: " + e.message, "error"); }
};

// ─────────────────────────── duplicates ───────────────────────────

async function loadDuplicates(offset = 0) {
  if (!state.jobId) return;
  const tbody = $("dupetable").querySelector("tbody");
  try {
    const page = await api(`/api/jobs/${state.jobId}/duplicates?offset=${offset}&limit=100`);
    state.dupeOffset = offset;
    $("dupesum").innerHTML =
      `<div class="stat"><b>${num(page.total)}</b><span>groups</span></div>` +
      `<div class="stat"><b>${bytes(page.total_reclaimable)}</b><span>reclaimable on this page</span></div>`;
    if (!page.rows.length) {
      tbody.innerHTML = `<tr><td colspan="4"><div class="empty">No duplicates found.</div></td></tr>`;
      $("dupepager").innerHTML = "";
      return;
    }
    tbody.innerHTML = page.rows.map((g) => `
      <tr>
        <td>${g.count}</td>
        <td>${bytes(g.size)}</td>
        <td><b>${bytes(g.reclaimable)}</b></td>
        <td class="path">${g.paths.map((p) =>
          `<div${p.is_duplicate ? ' class="dim"' : ""}>${esc(p.path)}` +
          `${p.is_duplicate ? "" : " <span class=\"tag\">keep</span>"}</div>`).join("")}</td>
      </tr>`).join("");
    pager("dupepager", page, loadDuplicates);
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="4"><div class="empty">${esc(e.message)}</div></td></tr>`;
  }
}

// ────────────────────────── plan review ──────────────────────────

async function loadPlan(offset = 0) {
  if (!state.jobId) return;
  const tbody = $("plantable").querySelector("tbody");
  const q = encodeURIComponent($("planq").value.trim());
  const cat = encodeURIComponent($("plancat").value);
  try {
    const page = await api(
      `/api/jobs/${state.jobId}/plan?offset=${offset}&limit=200&q=${q}&category=${cat}`);
    state.planOffset = offset;
    state.planTotal = page.total;
    $("plancount").textContent = `${num(page.total)} operations`;
    if (!page.rows.length) {
      tbody.innerHTML = `<tr><td colspan="4"><div class="empty">Nothing matches.</div></td></tr>`;
      $("planpager").innerHTML = "";
      return;
    }
    // Populate the category filter once, from what the plan contains.
    if ($("plancat").options.length === 1) {
      const seen = [...new Set(page.rows.map((r) => r.type).filter(Boolean))].sort();
      seen.forEach((c) => $("plancat").add(new Option(c, c)));
    }
    tbody.innerHTML = page.rows.map((r) => `
      <tr>
        <td><span class="tag">${esc(r.type || "?")}</span></td>
        <td class="path">${esc(r.src)}${r.is_duplicate ? ' <span class="tag">dup</span>' : ""}</td>
        <td class="path dim">${esc(r.dest)}</td>
        <td>${bytes(r.size)}</td>
      </tr>`).join("");
    pager("planpager", page, loadPlan);
    $("exec").disabled = state.jobStatus !== "done";
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="4"><div class="empty">${esc(e.message)}</div></td></tr>`;
  }
}

$("planreload").onclick = () => loadPlan(0);
$("planq").onkeydown = (e) => { if (e.key === "Enter") loadPlan(0); };

function pager(id, page, fn) {
  const el = $(id);
  const from = page.offset + 1;
  const to = Math.min(page.offset + page.limit, page.total);
  el.innerHTML = "";
  const prev = Object.assign(document.createElement("button"),
    { className: "ghost", textContent: "← Prev", disabled: page.offset === 0 });
  const next = Object.assign(document.createElement("button"),
    { className: "ghost", textContent: "Next →", disabled: to >= page.total });
  prev.onclick = () => fn(Math.max(0, page.offset - page.limit));
  next.onclick = () => fn(page.offset + page.limit);
  const label = document.createElement("span");
  label.className = "dim";
  label.textContent = `${num(from)}–${num(to)} of ${num(page.total)}`;
  el.append(prev, next, label);
}

// ─────────────────────────── execute ───────────────────────────

const dlg = $("confirm");

$("exec").onclick = () => {
  $("confirmbody").innerHTML =
    `About to copy <b>${num(state.planTotal)}</b> files into their planned ` +
    `destinations. Sources are left in place; only the destination tree is ` +
    `written.`;
  $("confirmtext").value = "";
  $("confirmyes").disabled = true;
  dlg.showModal();
};
$("confirmtext").oninput = (e) => {
  $("confirmyes").disabled = e.target.value !== "COPY FILES";
};
$("confirmno").onclick = () => dlg.close();
$("confirmyes").onclick = async () => {
  dlg.close();
  try {
    const job = await post(`/api/jobs/${state.jobId}/execute`, { confirm: "COPY FILES" });
    // Watch the execute job on the Run screen, where progress already renders.
    document.querySelector('nav button[data-view="run"]').click();
    state.jobId = job.id;
    state.stages.clear();
    $("stages").innerHTML = "";
    $("log").innerHTML = "";
    $("jobstatus").textContent = `job ${job.id} — copying`;
    $("cancel").disabled = false;
    $("start").disabled = true;
    follow(job.id);
  } catch (e) {
    logLine("Execute refused: " + e.message, "error");
    document.querySelector('nav button[data-view="run"]').click();
  }
};

// ───────────────────────────── jobs ─────────────────────────────

async function loadJobs() {
  const tbody = $("jobtable").querySelector("tbody");
  try {
    const { jobs } = await api("/api/jobs");
    if (!jobs.length) {
      tbody.innerHTML = `<tr><td colspan="5"><div class="empty">No jobs yet.</div></td></tr>`;
      return;
    }
    tbody.innerHTML = jobs.map((j) => `
      <tr>
        <td class="dim">${new Date(j.created_at * 1000).toLocaleTimeString()}</td>
        <td>${esc(j.kind)}</td>
        <td>${esc(j.status)}${j.error ? ` <span class="err">${esc(j.error)}</span>` : ""}</td>
        <td class="path dim">${esc(j.source || "")}</td>
        <td><button class="ghost" data-job="${esc(j.id)}">Open</button></td>
      </tr>`).join("");
    tbody.querySelectorAll("button[data-job]").forEach((b) => {
      b.onclick = () => {
        state.jobId = b.dataset.job;
        const job = jobs.find((j) => j.id === state.jobId);
        state.jobStatus = job.status;
        state.planOffset = 0;
        $("plancat").length = 1;
        renderResult(job.result, job.status);
        $("jobstatus").textContent = `job ${job.id} — ${job.status}`;
        document.querySelector('nav button[data-view="plan"]').click();
      };
    });
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty">${esc(e.message)}</div></td></tr>`;
  }
}

loadJobs();
