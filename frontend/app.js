/* Appeal Management – basic frontend.
 * Talks to the FastAPI backend at /api. Token is kept in localStorage. */

const API = "/api";
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

const state = {
  token: localStorage.getItem("token"),
  user: null,
  categories: [],
  managers: [],
  currentAppeal: null,
};

/* ---------- helpers ---------- */

function toast(msg, type = "") {
  const el = $("#toast");
  el.textContent = msg;
  el.className = `toast ${type}`;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.add("hidden"), 3500);
}

function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString();
}

function badge(status) {
  return `<span class="badge badge-${status}">${status.replace("_", " ")}</span>`;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function api(path, { method = "GET", body, form } = {}) {
  const headers = {};
  if (state.token) headers["Authorization"] = `Bearer ${state.token}`;
  let payload;
  if (form) {
    payload = new URLSearchParams(form);
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (body !== undefined) {
    payload = JSON.stringify(body);
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(API + path, { method, headers, body: payload });
  if (res.status === 401 && state.token) {
    logout();
    throw new Error("Session expired, please log in again");
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(describeError(data, res.status));
  }
  return data;
}

function describeError(data, status) {
  const d = data?.detail;
  if (Array.isArray(d)) {
    return d.map((e) => `${(e.loc || []).slice(1).join(".")}: ${e.msg}`).join("; ");
  }
  if (typeof d === "string") return d;
  return `Request failed (${status})`;
}

function formData(formEl) {
  const obj = {};
  new FormData(formEl).forEach((v, k) => { obj[k] = v; });
  return obj;
}

/* ---------- views ---------- */

function showView(name) {
  $$(".view").forEach((v) => v.classList.add("hidden"));
  $(`#view-${name}`).classList.remove("hidden");
  $$(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
}

function applyRoleVisibility() {
  const role = state.user?.role;
  $$(".admin-only").forEach((el) => el.classList.toggle("hidden", role !== "ADMIN"));
  $$(".appealer-only").forEach((el) => el.classList.toggle("hidden", role !== "APPEALER"));
}

/* ---------- auth ---------- */

async function loadMe() {
  state.user = await api("/auth/me");
  $("#user-label").textContent = `${state.user.full_name || state.user.phone} · ${state.user.role}`;
  $("#nav").classList.remove("hidden");
  $("#userbox").classList.remove("hidden");
  applyRoleVisibility();
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem("token");
  $("#nav").classList.add("hidden");
  $("#userbox").classList.add("hidden");
  showView("auth");
}

$$(".tab").forEach((t) =>
  t.addEventListener("click", () => {
    $$(".tab").forEach((x) => x.classList.toggle("active", x === t));
    $("#login-form").classList.toggle("hidden", t.dataset.tab !== "login");
    $("#register-form").classList.toggle("hidden", t.dataset.tab !== "register");
  })
);

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const { phone, password } = formData(e.target);
  try {
    const data = await api("/auth/login", { method: "POST", form: { username: phone, password } });
    state.token = data.access_token;
    localStorage.setItem("token", state.token);
    await loadMe();
    await enterApp();
  } catch (err) { toast(err.message, "error"); }
});

$("#register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = formData(e.target);
  if (!body.full_name) delete body.full_name;
  try {
    await api("/auth/register", { method: "POST", body });
    toast("Account created, you can log in now", "success");
    $$(".tab")[0].click();
    $("#login-form").phone.value = body.phone;
  } catch (err) { toast(err.message, "error"); }
});

$("#logout-btn").addEventListener("click", logout);

/* ---------- navigation ---------- */

$$(".nav-btn").forEach((b) =>
  b.addEventListener("click", () => {
    const v = b.dataset.view;
    if (v === "appeals") loadAppeals();
    if (v === "notifications") loadNotifications();
    if (v === "categories") loadCategoriesView();
    if (v === "users") loadUsersView();
    if (v === "stats") loadStats();
    showView(v);
  })
);

async function enterApp() {
  await loadCategories();
  await loadAppeals();
  showView("appeals");
}

/* ---------- categories (shared) ---------- */

async function loadCategories() {
  state.categories = await api("/categories");
  const opts = state.categories.map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join("");
  $("#filter-category").innerHTML = `<option value="">All categories</option>${opts}`;
  $("#appeal-category").innerHTML = opts;
}

function categoryName(id) {
  return state.categories.find((c) => c.id === id)?.name || `#${id}`;
}

/* ---------- appeals list ---------- */

async function loadAppeals() {
  const params = new URLSearchParams();
  const st = $("#filter-status").value;
  const cat = $("#filter-category").value;
  if (st) params.set("status", st);
  if (cat) params.set("category_id", cat);
  params.set("limit", "100");
  try {
    const data = await api(`/appeals?${params}`);
    const items = Array.isArray(data) ? data : data.items || [];
    renderAppeals(items);
  } catch (err) { toast(err.message, "error"); }
}

function renderAppeals(items) {
  const el = $("#appeals-table");
  if (!items.length) { el.innerHTML = `<div class="empty">No appeals found</div>`; return; }
  const showAuthor = state.user.role !== "APPEALER";
  el.innerHTML = `
    <table>
      <thead><tr>
        <th>#</th><th>Status</th><th>Category</th>${showAuthor ? "<th>Author</th>" : ""}<th>Description</th><th>Source</th><th>Created</th>
      </tr></thead>
      <tbody>
        ${items.map((a) => `
          <tr class="clickable" data-id="${a.id}">
            <td>${a.id}</td>
            <td>${badge(a.status)}</td>
            <td>${esc(a.category?.name ?? categoryName(a.category_id))}</td>
            ${showAuthor ? `<td>${esc(a.author?.full_name || a.author?.phone || a.phone)}</td>` : ""}
            <td>${esc(a.description.length > 80 ? a.description.slice(0, 80) + "…" : a.description)}</td>
            <td>${esc(a.source)}</td>
            <td>${fmtDate(a.created_at)}</td>
          </tr>`).join("")}
      </tbody>
    </table>`;
  $$("#appeals-table tr.clickable").forEach((tr) => tr.addEventListener("click", () => openAppeal(+tr.dataset.id)));
}

$("#filter-status").addEventListener("change", loadAppeals);
$("#filter-category").addEventListener("change", loadAppeals);

/* ---------- appeal detail ---------- */

async function openAppeal(id) {
  try {
    const a = await api(`/appeals/${id}`);
    state.currentAppeal = a;
    renderDetail(a);
    showView("detail");
  } catch (err) { toast(err.message, "error"); }
}

function renderDetail(a) {
  const role = state.user.role;
  const canProcess = role === "MANAGER" || role === "ADMIN";
  const actions = [];
  if (canProcess) {
    if (a.status === "NEW") {
      actions.push(`<button class="btn btn-ghost" data-action="category">Change category</button>`);
      actions.push(`<button class="btn btn-success" data-action="accept">Accept</button>`);
      actions.push(`<button class="btn btn-danger" data-action="reject">Reject</button>`);
    }
    if (a.status === "IN_PROGRESS") {
      actions.push(`<button class="btn btn-success" data-action="close">Close</button>`);
      actions.push(`<button class="btn btn-danger" data-action="reject">Reject</button>`);
    }
  }
  const history = (a.history || []).slice().sort((x, y) => new Date(x.created_at) - new Date(y.created_at));
  $("#detail").innerHTML = `
    <div class="card">
      <h1>Appeal #${a.id} ${badge(a.status)}</h1>
      <dl class="kv">
        <dt>Category</dt><dd>${esc(a.category?.name ?? categoryName(a.category_id))}</dd>
        <dt>Assigned to</dt><dd>${esc(a.assigned_to?.full_name || a.assigned_to?.phone || a.category?.responsible_user?.full_name || "—")}</dd>
        <dt>Author</dt><dd>${esc(a.author?.full_name || a.author?.phone || "—")}</dd>
        <dt>Contact phone</dt><dd>${esc(a.phone)}</dd>
        <dt>Source</dt><dd>${esc(a.source)}</dd>
        <dt>Created</dt><dd>${fmtDate(a.created_at)}</dd>
        <dt>Updated</dt><dd>${fmtDate(a.updated_at)}</dd>
      </dl>
      <div class="description">${esc(a.description)}</div>
    </div>
    <div>
      ${actions.length ? `<div class="card" style="margin-bottom:16px"><h2>Actions</h2><div class="actions">${actions.join("")}</div></div>` : ""}
      <div class="card">
        <h2>Status history</h2>
        ${history.length ? `<ul class="timeline">${history.map((h) => `
          <li>
            <div>${h.previous_status ? badge(h.previous_status) + " → " : ""}${badge(h.new_status)}</div>
            <div class="meta">${esc(h.changed_by?.full_name || h.updated_by?.full_name || h.changed_by?.phone || "")} · ${fmtDate(h.created_at)}</div>
            ${h.comment ? `<div class="comment">${esc(h.comment)}</div>` : ""}
          </li>`).join("")}</ul>` : `<div class="empty">No history yet</div>`}
      </div>
    </div>`;
  $$("#detail [data-action]").forEach((b) => b.addEventListener("click", () => openAction(b.dataset.action)));
}

$("#back-btn").addEventListener("click", async () => { await loadAppeals(); showView("appeals"); });

/* ---------- actions modal ---------- */

const ACTIONS = {
  accept: { title: "Accept appeal", fields: `<label>Comment (optional) <textarea name="comment" rows="3"></textarea></label>`, path: (id) => `/appeals/${id}/accept`, method: "POST" },
  reject: { title: "Reject appeal", fields: `<label>Rejection reason (required) <textarea name="comment" rows="3" required minlength="3"></textarea></label>`, path: (id) => `/appeals/${id}/reject`, method: "POST" },
  close: { title: "Close appeal", fields: `<label>Resolution remark (required) <textarea name="comment" rows="3" required minlength="3"></textarea></label>`, path: (id) => `/appeals/${id}/close`, method: "POST" },
  category: {
    title: "Change category",
    fields: () => `<label>New category <select name="category_id" required>${state.categories.map((c) => `<option value="${c.id}" ${c.id === state.currentAppeal.category_id || c.id === state.currentAppeal.category?.id ? "selected" : ""}>${esc(c.name)}</option>`).join("")}</select></label>
                   <label>Comment (optional) <textarea name="comment" rows="2"></textarea></label>`,
    path: (id) => `/appeals/${id}/category`, method: "PATCH",
  },
};

let currentAction = null;

function openAction(name) {
  currentAction = ACTIONS[name];
  $("#modal-title").textContent = currentAction.title;
  $("#modal-fields").innerHTML = typeof currentAction.fields === "function" ? currentAction.fields() : currentAction.fields;
  $("#modal").classList.remove("hidden");
}

$("#modal-cancel").addEventListener("click", () => $("#modal").classList.add("hidden"));
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") $("#modal").classList.add("hidden"); });

$("#modal-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = formData(e.target);
  if (body.category_id) body.category_id = +body.category_id;
  if (body.comment === "") delete body.comment;
  try {
    const updated = await api(currentAction.path(state.currentAppeal.id), { method: currentAction.method, body });
    $("#modal").classList.add("hidden");
    // A manager who moves an appeal to someone else's category loses access to it.
    if (state.user.role === "MANAGER" && updated.category?.responsible_user_id !== state.user.id) {
      toast("Appeal moved to another category", "success");
      await loadAppeals();
      showView("appeals");
      return;
    }
    toast("Done", "success");
    state.currentAppeal = updated;
    renderDetail(updated);
  } catch (err) { toast(err.message, "error"); }
});

/* ---------- new appeal ---------- */

$("#new-appeal-btn").addEventListener("click", () => {
  $("#appeal-form").reset();
  $("#appeal-form").phone.value = state.user.phone;
  showView("new");
});
$("#cancel-new").addEventListener("click", () => showView("appeals"));

$("#appeal-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = formData(e.target);
  body.category_id = +body.category_id;
  try {
    const a = await api("/appeals", { method: "POST", body });
    toast(`Appeal #${a.id} submitted`, "success");
    await loadAppeals();
    showView("appeals");
  } catch (err) { toast(err.message, "error"); }
});

/* ---------- notifications ---------- */

async function loadNotifications() {
  try {
    const items = await api("/notifications");
    const el = $("#notifications-list");
    if (!items.length) { el.innerHTML = `<div class="empty">No notifications</div>`; return; }
    el.innerHTML = items.map((n) => `
      <div class="notif ${n.is_read ? "" : "unread"}">
        <div>${esc(n.message)}</div>
        <div class="meta">Appeal #${n.appeal_id} · ${fmtDate(n.created_at)}</div>
      </div>`).join("");
  } catch (err) { toast(err.message, "error"); }
}

/* ---------- admin: categories ---------- */

async function loadManagers() {
  state.managers = await api("/users?role=MANAGER");
  $("#category-manager").innerHTML = state.managers.map((u) => `<option value="${u.id}">${esc(u.full_name || u.phone)}</option>`).join("");
}

async function loadCategoriesView() {
  try {
    await Promise.all([loadCategories(), loadManagers()]);
    const el = $("#categories-table");
    if (!state.categories.length) { el.innerHTML = `<div class="empty">No categories yet</div>`; return; }
    el.innerHTML = `<table><thead><tr><th>#</th><th>Name</th><th>Responsible manager</th><th></th></tr></thead><tbody>
      ${state.categories.map((c) => {
        const m = c.responsible_user || state.managers.find((u) => u.id === c.responsible_user_id);
        return `<tr>
          <td>${c.id}</td><td>${esc(c.name)}</td>
          <td>${esc(m ? (m.full_name || m.phone) : `#${c.responsible_user_id}`)}</td>
          <td><button class="btn btn-ghost" data-cat="${c.id}">Reassign</button></td>
        </tr>`;
      }).join("")}</tbody></table>`;
    $$("#categories-table [data-cat]").forEach((b) => b.addEventListener("click", () => reassignCategory(+b.dataset.cat)));
  } catch (err) { toast(err.message, "error"); }
}

function reassignCategory(id) {
  const cat = state.categories.find((c) => c.id === id);
  currentAction = { path: () => `/categories/${id}`, method: "PATCH" };
  $("#modal-title").textContent = `Reassign "${cat.name}"`;
  $("#modal-fields").innerHTML = `<label>Responsible manager <select name="responsible_user_id" required>
    ${state.managers.map((u) => `<option value="${u.id}" ${u.id === cat.responsible_user_id ? "selected" : ""}>${esc(u.full_name || u.phone)}</option>`).join("")}
  </select></label>`;
  $("#modal").classList.remove("hidden");
  $("#modal-form").onsubmit = async (e) => {
    e.preventDefault();
    const body = formData(e.target);
    body.responsible_user_id = +body.responsible_user_id;
    try {
      await api(`/categories/${id}`, { method: "PATCH", body });
      $("#modal").classList.add("hidden");
      toast("Category updated", "success");
      $("#modal-form").onsubmit = null;
      await loadCategoriesView();
    } catch (err) { toast(err.message, "error"); }
  };
}

$("#category-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = formData(e.target);
  body.responsible_user_id = +body.responsible_user_id;
  try {
    await api("/categories", { method: "POST", body });
    toast("Category created", "success");
    e.target.reset();
    await loadCategoriesView();
  } catch (err) { toast(err.message, "error"); }
});

/* ---------- admin: users ---------- */

async function loadUsersView() {
  try {
    const users = await api("/users");
    const el = $("#users-table");
    el.innerHTML = `<table><thead><tr><th>#</th><th>Phone</th><th>Name</th><th>Role</th><th>Telegram</th></tr></thead><tbody>
      ${users.map((u) => `<tr>
        <td>${u.id}</td><td>${esc(u.phone)}</td><td>${esc(u.full_name || "—")}</td>
        <td><span class="badge badge-role">${esc(u.role)}</span></td>
        <td>${u.telegram_id ? "linked" : "—"}</td>
      </tr>`).join("")}</tbody></table>`;
  } catch (err) { toast(err.message, "error"); }
}

$("#user-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = formData(e.target);
  if (!body.full_name) delete body.full_name;
  try {
    await api("/users", { method: "POST", body });
    toast("User created", "success");
    e.target.reset();
    await loadUsersView();
  } catch (err) { toast(err.message, "error"); }
});

/* ---------- admin: stats ---------- */

async function loadStats() {
  try {
    const s = await api("/stats");
    const byStatus = s.by_status || {};
    const byCategory = Array.isArray(s.by_category) ? s.by_category : Object.entries(s.by_category || {}).map(([name, count]) => ({ name, count }));
    const maxCat = Math.max(1, ...byCategory.map((c) => c.count));
    const statusOrder = ["NEW", "IN_PROGRESS", "REJECTED", "CLOSED"];
    $("#stats").innerHTML = `
      <div class="card stat"><div class="num">${s.total ?? 0}</div><div class="label">Total appeals</div></div>
      <div class="card stat"><div class="num">${s.accepted ?? 0}</div><div class="label">Accepted</div></div>
      <div class="card stat"><div class="num">${s.rejected ?? 0}</div><div class="label">Rejected</div></div>
      <div class="card stat"><div class="num">${s.closed ?? 0}</div><div class="label">Closed</div></div>
      <div class="card stat-list"><h2>By status</h2>
        ${statusOrder.map((st) => `<div class="bar"><span class="name">${badge(st)}</span><div class="track"><div class="fill" style="width:${(byStatus[st] || 0) / Math.max(1, s.total || 1) * 100}%"></div></div><span class="count">${byStatus[st] || 0}</span></div>`).join("")}
      </div>
      <div class="card stat-list"><h2>By category</h2>
        ${byCategory.length ? byCategory.map((c) => `<div class="bar"><span class="name">${esc(c.name || c.category_name || `#${c.category_id}`)}</span><div class="track"><div class="fill" style="width:${c.count / maxCat * 100}%"></div></div><span class="count">${c.count}</span></div>`).join("") : `<div class="empty">No data</div>`}
      </div>`;
  } catch (err) { toast(err.message, "error"); }
}

/* ---------- boot ---------- */

(async function boot() {
  if (!state.token) { showView("auth"); return; }
  try {
    await loadMe();
    await enterApp();
  } catch (err) {
    logout();
  }
})();
