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

// Must match server/app.py's API_VERSION. The browser always loads the
// current app.js, but the server may be an older process that never
// restarted — this turns that into a clear message instead of a 404.
const REQUIRED_API = 2;

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
                dupeOffset: 0, stages: new Map(),
                treePrefix: null, treeAfter: null, treeLoaded: false,
                treeFileCount: 0 };

// ───────────────────────────── nav ─────────────────────────────

document.querySelectorAll("nav button").forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll("nav button").forEach((b) => b.classList.remove("on"));
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("on"));
    btn.classList.add("on");
    $("view-" + btn.dataset.view).classList.add("on");
    if (btn.dataset.view === "dupes") { loadDuplicates(); refreshPending(); }
    if (btn.dataset.view === "tree" && !state.treeLoaded) loadTree();
    if (btn.dataset.view === "plan") loadPlan();
    if (btn.dataset.view === "jobs") loadJobs();
  };
});

$("cloud").onchange = (e) => {
  $("cloudopts").style.display = e.target.checked ? "" : "none";
};

// ───────────────────────────── system ─────────────────────────────

function staleServerBanner(found) {
  if (document.getElementById("stalebanner")) return;
  const bar = document.createElement("div");
  bar.id = "stalebanner";
  bar.style.cssText =
    "background:var(--danger);color:#fff;padding:10px 20px;font-size:13px;" +
    "position:sticky;top:0;z-index:20";
  bar.textContent =
    `This page is newer than the server it is talking to (needs API v${REQUIRED_API}, ` +
    `server has v${found}). Restart the server to pick up the new endpoints — ` +
    `until then some buttons will not work.`;
  document.body.prepend(bar);
}

(async function loadSystem() {
  try {
    const s = await api("/api/system");
    if ((s.api_version || 0) < REQUIRED_API) staleServerBanner(s.api_version || 0);
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
  const showResolved = $("dupeshowresolved").checked ? 1 : 0;
  try {
    const page = await api(
      `/api/jobs/${state.jobId}/duplicates?offset=${offset}&limit=100` +
      `&show_resolved=${showResolved}`);
    state.dupeOffset = offset;
    $("dupesum").innerHTML =
      `<div class="stat"><b>${num(page.total)}</b><span>groups to review</span></div>` +
      `<div class="stat"><b>${bytes(page.total_reclaimable)}</b><span>reclaimable on this page</span></div>` +
      (page.resolved_hidden
        ? `<div class="stat"><b>${num(page.resolved_hidden)}</b><span>resolved (hidden)</span></div>` : "");
    if (!page.rows.length) {
      tbody.innerHTML = `<tr><td colspan="5"><div class="empty">` +
        (page.resolved_hidden ? "All duplicate groups are resolved. 🎉"
                              : "No duplicates found.") + `</div></td></tr>`;
      $("dupepager").innerHTML = "";
      return;
    }
    tbody.innerHTML = page.rows.map((g, i) => `
      <tr data-hash="${esc(g.hash)}" data-row="${i}">
        <td>${g.count}</td>
        <td>${bytes(g.size)}</td>
        <td><b>${bytes(g.reclaimable)}</b></td>
        <td class="path">${g.paths.map((p) => {
          const kept = g.resolved ? (g.kept || []).includes(p.path) : !p.is_duplicate;
          return `<label style="display:flex;gap:6px;align-items:baseline;margin:1px 0;cursor:pointer">` +
            `<input type="checkbox" data-keep="${esc(p.path)}" ${kept ? "checked" : ""}>` +
            `<span${kept ? "" : ' class="dim"'}>${esc(p.path)}</span></label>`;
        }).join("")}</td>
        <td style="white-space:nowrap">${g.resolved
          ? `<span class="tag" style="color:var(--ok)">resolved</span>
             <button class="ghost" data-unresolve="${esc(g.hash)}">Unresolve</button>`
          : `<button class="act" data-resolve="${esc(g.hash)}">Keep&nbsp;selected</button>`}</td>
      </tr>`).join("");

    tbody.querySelectorAll("button[data-resolve]").forEach((b) => {
      b.onclick = async () => {
        const tr = b.closest("tr");
        const keep = [...tr.querySelectorAll("input[data-keep]:checked")]
          .map((c) => c.dataset.keep);
        if (!keep.length) { alert("Tick at least one copy to keep."); return; }
        b.disabled = true;
        try {
          await post("/api/db/duplicates/resolutions",
                     { hash: b.dataset.resolve, keep });
          loadDuplicates(state.dupeOffset);
        } catch (e) { alert("Could not save: " + e.message); b.disabled = false; }
      };
    });
    tbody.querySelectorAll("button[data-unresolve]").forEach((b) => {
      b.onclick = async () => {
        b.disabled = true;
        try {
          await api(`/api/db/duplicates/resolutions/${encodeURIComponent(b.dataset.unresolve)}`,
                    { method: "DELETE" });
          loadDuplicates(state.dupeOffset);
        } catch (e) { alert("Could not unresolve: " + e.message); b.disabled = false; }
      };
    });
    pager("dupepager", page, loadDuplicates);
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty">${esc(e.message)}</div></td></tr>`;
  }
}

$("dupeshowresolved").onchange = () => loadDuplicates(0);

// ───────────────────────── folder picker ─────────────────────────

const fsdlg = $("fsdlg");
let fsTarget = null;      // input element the picker fills
let fsCurrent = null;     // path currently listed

async function fsShow(path) {
  try {
    const d = await api(`/api/fs/dirs?path=${encodeURIComponent(path)}`);
    fsCurrent = d.path;
    $("fspath").textContent = d.path + (d.truncated ? "  (first 500 shown)" : "");
    $("fsup").disabled = !d.parent;
    $("fslist").innerHTML = d.dirs.length
      ? d.dirs.map((n) => `<button data-dir="${esc(n)}">📁 ${esc(n)}</button>`).join("")
      : `<div class="empty">No subfolders.</div>`;
    $("fslist").querySelectorAll("button[data-dir]").forEach((b) => {
      b.onclick = () => fsShow(
        (fsCurrent === "/" ? "" : fsCurrent) + "/" + b.dataset.dir);
    });
  } catch (e) {
    if (!fsCurrent && path !== "/") return fsShow("/");   // bad start path
    $("fslist").innerHTML = `<div class="empty">${esc(e.message)}</div>`;
  }
}

document.querySelectorAll("button.browse").forEach((b) => {
  b.onclick = () => {
    fsTarget = $(b.dataset.pick);
    fsdlg.showModal();
    // Start where the input already points, else somewhere sensible.
    fsShow(fsTarget.value.trim() || "/Volumes");
  };
});
$("fsup").onclick = () => {
  const parent = fsCurrent.split("/").slice(0, -1).join("/") || "/";
  fsShow(parent);
};
$("fscancel").onclick = () => fsdlg.close();
$("fsuse").onclick = () => {
  if (fsTarget && fsCurrent) {
    fsTarget.value = fsCurrent;
    if (fsTarget.id === "treeprefix") loadTree(fsCurrent);
  }
  fsdlg.close();
};

// ──────────────────── duplicate trees (database) ────────────────────

function dupPctSpan(pct) {
  const color = pct >= 80 ? "var(--danger)" : pct >= 40 ? "var(--warn)" : "inherit";
  return `<span style="color:${color};font-weight:600">${pct}%</span>`;
}

function renderCrumb(prefix) {
  const parts = prefix.split("/").filter(Boolean);
  let acc = "";
  const links = parts.map((p) => {
    acc += "/" + p;
    const target = acc;
    return `<a href="#" data-crumb="${esc(target)}">${esc(p)}</a>`;
  });
  $("treecrumb").innerHTML = "/ " + links.join(" / ");
  $("treecrumb").querySelectorAll("a[data-crumb]").forEach((a) => {
    a.onclick = (e) => { e.preventDefault(); loadTree(a.dataset.crumb); };
  });
}

async function loadTree(prefix, refresh = false) {
  prefix = prefix || $("treeprefix").value.trim() || "/Volumes/home";
  state.treeLoaded = true;
  state.treePrefix = prefix;
  $("treeprefix").value = prefix;
  renderCrumb(prefix);
  const tbody = $("treetable").querySelector("tbody");
  tbody.innerHTML = `<tr><td colspan="7"><div class="empty">Aggregating… a broad
    directory can take a minute or two on the first load.</div></td></tr>`;
  $("treestatus").textContent = "computing…";

  try {
    // Same contract as the tree: the totals are an aggregate over every
    // row, so the server hands back {status:"computing"} and we poll.
    // Swallowing errors here is deliberate — the banner is a nicety and
    // must never hold up the tree below it.
    (async () => {
      try {
        let st = await api("/api/db/duplicates/status");
        while (st.status === "computing") {
          $("treesum").innerHTML =
            `<div class="stat"><b>…</b><span>totalling the database ` +
            `(${Math.round(st.elapsed_seconds || 0)}s)</span></div>`;
          await new Promise((r) => setTimeout(r, 3000));
          st = await api("/api/db/duplicates/status");
        }
        $("treesum").innerHTML =
          `<div class="stat"><b>${num(st.files)}</b><span>files in database</span></div>` +
          `<div class="stat"><b>${num(st.duplicates)}</b><span>duplicates</span></div>` +
          `<div class="stat"><b>${bytes(st.duplicate_bytes)}</b><span>duplicate bytes (hashed only)</span></div>`;
      } catch {
        $("treesum").innerHTML = "";
      }
    })();

    // The server never blocks: poll until the aggregation is ready.
    let tree = await api(
      `/api/db/duplicates/tree?prefix=${encodeURIComponent(prefix)}` +
      (refresh ? "&refresh=1" : ""));
    while (tree.status === "computing") {
      if (state.treePrefix !== prefix) return;   // user navigated away
      $("treestatus").textContent =
        `computing… ${Math.round(tree.elapsed_seconds || 0)}s (the database is ` +
        `shared with any running scan)`;
      await new Promise((r) => setTimeout(r, 3000));
      tree = await api(`/api/db/duplicates/tree?prefix=${encodeURIComponent(prefix)}`);
    }
    if (state.treePrefix !== prefix) return;
    $("treestatus").textContent =
      `computed in ${tree.elapsed_seconds}s · cached 15 min` +
      (tree.truncated ? " · list truncated" : "");

    if (!tree.children.length) {
      tbody.innerHTML = `<tr><td colspan="7"><div class="empty">Nothing under this prefix.</div></td></tr>`;
    } else {
      tbody.innerHTML = tree.children.map((c) => `
        <tr>
          <td class="path">${c.is_dir
            ? `<a href="#" data-dir="${esc(c.name)}">${esc(c.name)}/</a>`
            : esc(c.name)}</td>
          <td>${num(c.files)}</td>
          <td>${num(c.duplicates)}</td>
          <td>${dupPctSpan(c.dup_pct)}</td>
          <td>${bytes(c.duplicate_bytes)}</td>
          <td>${c.unhashed ? `<span style="color:var(--warn)">${num(c.unhashed)}</span>` : "0"}</td>
          <td class="dim">${c.originals_in.map((t) =>
            `${esc(t.tree)} ${t.pct}%`).join(" · ") || "—"}</td>
        </tr>`).join("");
      tbody.querySelectorAll("a[data-dir]").forEach((a) => {
        a.onclick = (e) => {
          e.preventDefault();
          loadTree(state.treePrefix + "/" + a.dataset.dir);
        };
      });
    }
    loadTreeFiles(true);
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7"><div class="empty">${esc(e.message)}</div></td></tr>`;
    $("treestatus").textContent = "";
  }
}

async function loadTreeFiles(reset) {
  const tbody = $("treefiles").querySelector("tbody");
  if (reset) { state.treeAfter = null; state.treeFileCount = 0; tbody.innerHTML = ""; }
  const dupsOnly = $("treedupsonly").checked ? 1 : 0;
  try {
    const page = await api(
      `/api/db/duplicates/files?prefix=${encodeURIComponent(state.treePrefix)}` +
      `&dups_only=${dupsOnly}&limit=100` +
      (state.treeAfter ? `&after=${encodeURIComponent(state.treeAfter)}` : ""));
    if (!page.rows.length && reset) {
      tbody.innerHTML = `<tr><td colspan="3"><div class="empty">No matching files.</div></td></tr>`;
    } else {
      tbody.insertAdjacentHTML("beforeend", page.rows.map((r) => `
        <tr>
          <td class="path">${esc(r.path)}${r.unhashed
            ? ' <span class="tag" style="color:var(--warn)">unhashed</span>' : ""}</td>
          <td>${bytes(r.size)}</td>
          <td class="path dim">${r.duplicate_of ? esc(r.duplicate_of) : "—"}</td>
        </tr>`).join(""));
    }
    state.treeFileCount += page.rows.length;
    state.treeAfter = page.next_after;
    $("treemore").style.display = page.next_after ? "" : "none";
    $("treefilecount").textContent =
      `${num(state.treeFileCount)} shown${page.next_after ? " — more available" : ""}`;
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="3"><div class="empty">${esc(e.message)}</div></td></tr>`;
  }
}

$("treego").onclick = () => loadTree($("treeprefix").value.trim());
$("treeprefix").onkeydown = (e) => { if (e.key === "Enter") loadTree(e.target.value.trim()); };
$("treerefresh").onclick = () => loadTree(state.treePrefix, true);
$("treedupsonly").onchange = () => loadTreeFiles(true);
$("treemore").onclick = () => loadTreeFiles(false);

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

// ─────────────────────── trash, undo, and commit ───────────────────────
//
// Saving a duplicate decision never deletes anything. Deletion happens
// here, once, against every resolved group — and it moves files to the
// Trash so a mistake is recoverable both from this screen and from Finder.

async function refreshPending() {
  const sum = $("pendingsum");
  const note = $("pendingnote");
  const prot = $("protectednote");
  try {
    // Cold, this walks the candidate directories over the network and can
    // take minutes; the server hands back {status:"computing"} and we poll.
    let p = await api("/api/db/duplicates/pending");
    while (p.status === "computing") {
      sum.innerHTML =
        `<div class="stat"><b>…</b><span>working out what would be trashed ` +
        `(${Math.round(p.elapsed_seconds || 0)}s)</span></div>`;
      $("commitbtn").disabled = true;
      await new Promise((r) => setTimeout(r, 2000));
      p = await api("/api/db/duplicates/pending");
    }
    sum.innerHTML =
      `<div class="stat"><b>${num(p.groups)}</b><span>groups decided</span></div>` +
      `<div class="stat"><b>${num(p.files)}</b><span>copies to trash</span></div>` +
      `<div class="stat"><b>${bytes(p.bytes)}</b><span>reclaimed</span></div>`;

    const bits = [];
    if (p.missing) bits.push(`${num(p.missing)} already gone from disk`);
    if (p.already_trashed) bits.push(`${num(p.already_trashed)} currently in the Trash`);
    if (p.skipped_empty)
      bits.push(`${num(p.skipped_empty)} zero-byte files excluded (deleting them frees nothing)`);
    note.textContent = bits.length
      ? bits.join(" · ")
      : "Kept copies are never touched, so no group can lose its last copy.";

    prot.innerHTML = p.protected_total
      ? `<p class="dim">Excluding <b>${num(p.protected_total)}</b> companion ` +
        `file(s) that a media file still needs — e.g. ` +
        `<code>${esc((p.protected[0] || {}).path || "")}</code> ` +
        `(${esc((p.protected[0] || {}).reason || "")}).</p>`
      : "";

    $("commitbtn").disabled = p.files === 0;
    $("commitbtn").textContent = p.files
      ? `Review and trash ${num(p.files)} file${p.files === 1 ? "" : "s"}…`
      : "Nothing to trash";
  } catch (e) {
    sum.innerHTML = "";
    note.textContent = /not found/i.test(e.message)
      ? "This server does not have the review-and-commit endpoints — it was " +
        "started before they existed. Restart it and reload this page."
      : e.message;
    $("commitbtn").disabled = true;
  }

  try {
    const u = await api("/api/db/duplicates/undo");
    $("undobtn").disabled = !u.available;
    $("undonote").textContent = u.available
      ? `${num(u.files)} file(s) from the last batch can be put back`
      : "";
  } catch { $("undobtn").disabled = true; }
}

const trashDlg = $("trashconfirm");

$("commitbtn").onclick = async () => {
  let p = await api("/api/db/duplicates/pending");
  while (p.status === "computing") {
    await new Promise((r) => setTimeout(r, 1500));
    p = await api("/api/db/duplicates/pending");
  }
  $("trashbody").innerHTML =
    `About to move <b>${num(p.files)}</b> duplicate file(s) to the Trash, ` +
    `reclaiming <b>${bytes(p.bytes)}</b> across ${num(p.groups)} group(s).<br><br>` +
    `The copies you chose to keep are not touched. Nothing is erased — ` +
    `everything goes to the Trash on its own volume, and this screen can ` +
    `put the whole batch back.`;
  $("trashprotected").textContent = p.protected_total
    ? `${num(p.protected_total)} companion file(s) are excluded and will be left alone.`
    : "";
  $("trashtext").value = "";
  $("trashyes").disabled = true;
  trashDlg.showModal();
};
$("trashtext").oninput = (e) => {
  $("trashyes").disabled = e.target.value !== "TRASH THEM";
};
$("trashno").onclick = () => trashDlg.close();
$("trashyes").onclick = async () => {
  trashDlg.close();
  $("commitbtn").disabled = true;
  $("commitbtn").textContent = "Moving to Trash…";
  try {
    const r = await post("/api/db/duplicates/delete", { confirm: "TRASH THEM" });
    let msg = `Moved ${num(r.trashed)} file(s) to the Trash, reclaiming ${bytes(r.bytes)}.`;
    if (r.failed) msg += ` ${num(r.failed)} could not be moved.`;
    if (r.protected_skipped) msg += ` ${num(r.protected_skipped)} companion file(s) left alone.`;
    $("pendingnote").textContent = msg;
  } catch (e) {
    $("pendingnote").textContent = "Nothing was deleted — " + e.message;
  }
  await refreshPending();
  await loadDuplicates(state.dupeOffset || 0);
};

$("undobtn").onclick = async () => {
  $("undobtn").disabled = true;
  $("undonote").textContent = "Putting files back…";
  try {
    const r = await post("/api/db/duplicates/undo");
    $("undonote").textContent =
      `Restored ${num(r.restored)} file(s)` +
      (r.failed ? `, ${num(r.failed)} could not be put back` : "");
  } catch (e) {
    $("undonote").textContent = e.message;
  }
  await refreshPending();
};
