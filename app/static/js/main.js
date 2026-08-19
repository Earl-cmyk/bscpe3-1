// Shared client state drives the calendar, class fund, and planner views.
const state = {
  tasks: [],
  entries: [],
  balance: 0,
  tab: "tasks",
  view: "month",
  cursor: new Date(),
  selected: new Date(),
  editingId: null,
  auditUnlock: false,
};
const $ = (s) => document.querySelector(s),
  esc = (v) =>
    String(v ?? "").replace(
      /[&<>'"]/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          "'": "&#39;",
          '"': "&quot;",
        })[c],
    ),
  day = (d) => d.toISOString().slice(0, 10),
  date = (t) => new Date(t.deadline),
  money = (v) => `₱${Number(v).toFixed(2)}`;
async function api(u, o = {}) {
  const r = await fetch(u, o),
    d = await r.json();
  if (!r.ok) throw Error(d.error || "Request failed");
  return d;
}
async function load() {
  const [t, b] = await Promise.all([api("/api/tasks"), api("/api/budget")]);
  state.tasks = t.tasks;
  state.entries = b.entries;
  state.balance = b.balance;
  render();
}
function on(d) {
  return state.tasks
    .filter((t) => day(date(t)) === day(d))
    .sort((a, b) => date(a) - date(b));
}
function render() {
  if (state.tab === "budget") return budget();
  const c = $("#calendar"),
    title = $("#calendarTitle");
  if (state.view === "month") {
    title.textContent = state.cursor.toLocaleDateString(undefined, {
      month: "long",
      year: "numeric",
    });
    const first = new Date(
        Date.UTC(state.cursor.getUTCFullYear(), state.cursor.getUTCMonth(), 1),
      ),
      start = new Date(first);
    start.setUTCDate(1 - first.getUTCDay());
    let h =
      '<div class="month-grid"><div class="weekday">SUN</div><div class="weekday">MON</div><div class="weekday">TUE</div><div class="weekday">WED</div><div class="weekday">THU</div><div class="weekday">FRI</div><div class="weekday">SAT</div>';
    for (let i = 0; i < 42; i++) {
      const d = new Date(start);
      d.setUTCDate(start.getUTCDate() + i);
      h += `<div class="day-cell" data-date="${day(d)}"><span class="day-number">${d.getUTCDate()}</span>${on(
        d,
      )
        .slice(0, 3)
        .map(
          (t) =>
            `<button class="task-chip" data-task="${t.id}">${esc(t.title)}</button>`,
        )
        .join("")}</div>`;
    }
    c.innerHTML = h + "</div>";
  } else {
    const base = new Date(state.selected),
      start = new Date(base);
    if (state.view === "week")
      start.setUTCDate(base.getUTCDate() - base.getUTCDay());
    const days =
      state.view === "week"
        ? Array.from({ length: 7 }, (_, i) => {
            const d = new Date(start);
            d.setUTCDate(start.getUTCDate() + i);
            return d;
          })
        : [base];
    title.textContent =
      state.view === "week"
        ? `Week of ${start.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`
        : base.toLocaleDateString(undefined, {
            weekday: "long",
            month: "long",
            day: "numeric",
          });
    if (state.view === "week") {
      c.innerHTML = `<div class="week-grid">${days
        .map(
          (d) =>
            `<section class="week-column"><header><span>${d.toLocaleDateString(undefined, { weekday: "short" })}</span><strong>${d.getUTCDate()}</strong></header><div class="week-items">${
              on(d)
                .map(
                  (t) =>
                    `<button class="week-item" data-task="${t.id}"><time>${date(t).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</time><strong>${esc(t.title)}</strong><small>${esc(t.course)}</small></button>`,
                )
                .join("") || '<p class="empty-slot">No deadlines</p>'
            }</div></section>`,
        )
        .join("")}</div>`;
    } else {
      c.innerHTML = `<div class="day-view"><div class="day-summary"><span class="day-number-large">${base.getDate()}</span><div><strong>${base.toLocaleDateString(undefined, { weekday: "long" })}</strong><small>${on(base).length} deadline${on(base).length === 1 ? "" : "s"} scheduled</small></div></div><div class="day-items">${
        on(base)
          .map(
            (t) =>
              `<button class="day-item" data-task="${t.id}"><time>${date(t).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</time><span><strong>${esc(t.title)}</strong><small>${esc(t.course)} · ${esc(t.difficulty)}</small></span></button>`,
          )
          .join("") ||
        '<p class="empty-slot">No deadlines scheduled for this day.</p>'
      }</div></div>`;
    }
  }
  document
    .querySelectorAll("[data-task]")
    .forEach((b) => (b.onclick = () => openTask(+b.dataset.task)));
}
function budget() {
  const dep = state.entries
      .filter((e) => e.type === "deposit")
      .reduce((s, e) => s + e.amount, 0),
    wit = state.entries
      .filter((e) => e.type === "withdraw")
      .reduce((s, e) => s + e.amount, 0),
    total = dep + wit;
  $("#balanceValue").textContent = money(state.balance);
  $("#entryCount").textContent = `${state.entries.length} entries`;
  $("#pieLabel").textContent = total
    ? `${Math.round((dep / total) * 100)}% in`
    : "No entries";
  $("#budgetPie").style.background = total
    ? `conic-gradient(var(--lime) ${(dep / total) * 100}%,var(--coral) 0)`
    : "var(--line)";
  $("#budgetEntries").innerHTML =
    state.entries
      .map(
        (e) =>
          `<div class="budget-entry"><span class="entry-icon ${e.type}">${e.type === "deposit" ? "+" : "−"}</span><span><strong>${esc(e.reason)}</strong><small>${e.type} · ${e.status}</small></span><b class="${e.type}">${e.type === "deposit" ? "+" : "−"}${money(e.amount)}</b>${e.type === "withdraw" && e.status === "pending" ? `<span class="entry-actions"><button class="button button-quiet" data-budget-action="cancel" data-budget-id="${e.id}">Cancel</button><button class="button button-primary" data-budget-action="spent" data-budget-id="${e.id}">Spent</button></span>` : ""}</div>`,
      )
      .join("") || '<p class="result-empty">No audits yet.</p>';
}
function close(id) {
  $(`#${id}`).hidden = true;
}
function tab(t) {
  state.tab = t;
  const tasks = t === "tasks";
  $("#taskWorkspace").hidden = !tasks;
  $("#budgetWorkspace").hidden = tasks;
  $("#openAction").textContent = tasks ? "+ Add task" : "Audit";
  document
    .querySelectorAll("[data-tab]")
    .forEach((b) => b.classList.toggle("active", b.dataset.tab === t));
  render();
}
function openTask(id) {
  const t = state.tasks.find((x) => x.id === id);
  if (!t) return;
  $("#taskModalContent").innerHTML =
    `<h2>${esc(t.title)}</h2><p>${esc(t.description)}</p><p><strong>Due</strong><br>${date(t).toLocaleString()}</p>`;
  $("#taskModal").hidden = false;
}
document
  .querySelectorAll("[data-close]")
  .forEach((b) => (b.onclick = () => close(b.dataset.close)));
document
  .querySelectorAll("[data-tab]")
  .forEach((b) => (b.onclick = () => tab(b.dataset.tab)));
$("#openAction").onclick = () => {
  state.auditUnlock = state.tab === "budget";
  $("#pinInput").value = "";
  $("#pinError").hidden = true;
  $("#pinModal").hidden = false;
};
$("#unlockButton").onclick = () => {
  if ($("#pinInput").value === "313131") {
    close("pinModal");
    if (state.auditUnlock) {
      $("#auditForm").reset();
      $("#auditModal").hidden = false;
    } else {
      state.editingId = null;
      $("#taskForm").reset();
      $("#taskFormModal").hidden = false;
    }
  } else $("#pinError").hidden = false;
};
document.querySelectorAll("[data-view]").forEach(
  (b) =>
    (b.onclick = () => {
      state.view = b.dataset.view;
      document
        .querySelectorAll("[data-view]")
        .forEach((x) => x.classList.toggle("active", x === b));
      render();
    }),
);
$("#calendar").onclick = (e) => {
  const c = e.target.closest(".day-cell");
  if (c) {
    state.selected = new Date(`${c.dataset.date}T00:00:00Z`);
    render();
  }
};
$("#taskForm").onsubmit = async (e) => {
  e.preventDefault();
  const body = new FormData(e.currentTarget);
  try {
    body.append("pin", "313131");
    await api("/api/tasks", { method: "POST", body });
    close("taskFormModal");
    load();
  } catch (x) {
    $("#formError").textContent = x.message;
    $("#formError").hidden = false;
  }
};
$("#auditForm").onsubmit = async (e) => {
  e.preventDefault();
  const body = Object.fromEntries(new FormData(e.currentTarget));
  body.pin = "313131";
  try {
    await api("/api/budget", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    close("auditModal");
    load();
  } catch (x) {
    $("#auditError").textContent = x.message;
    $("#auditError").hidden = false;
  }
};
load().catch(
  (x) =>
    ($("#calendar").innerHTML =
      `<p class="result-empty">${esc(x.message)}</p>`),
);
let searchTimer;
$("#searchInput").oninput = (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(async () => {
    const term = e.target.value.trim();
    if (!term) {
      $("#searchResults").hidden = true;
      return;
    }
    const tasks = (await api(`/api/tasks?search=${encodeURIComponent(term)}`))
      .tasks;
    $("#searchResults").innerHTML =
      tasks
        .slice(0, 6)
        .map(
          (t) =>
            `<button class="search-item" data-task="${t.id}">${esc(t.title)}<small>${esc(t.course)}</small></button>`,
        )
        .join("") || '<p class="result-empty">No matching tasks.</p>';
    $("#searchResults").hidden = false;
  }, 180);
};
$("#queryForm").onsubmit = async (e) => {
  e.preventDefault();
  const q = $("#queryInput").value.trim().toLowerCase();
  if (
    q.startsWith("class fund used today") ||
    q.startsWith("class fund used this week") ||
    q.startsWith("class fund use this month")
  ) {
    const result = await api(`/api/query?q=${encodeURIComponent(q)}`);
    $("#queryTitle").textContent = result.label;
    $("#queryResults").innerHTML = result.entries.length
      ? result.entries
          .map(
            (entry) =>
              `<div class="query-result"><strong>${esc(entry.reason)}</strong><small>${money(entry.amount)} · spent</small></div>`,
          )
          .join("")
      : `<p class="result-empty">No class fund spending found. Total: ${money(result.total)}</p>`;
    $("#overlay").hidden = false;
    return;
  }
  const tasks = q.includes("today") ? on(new Date()) : state.tasks;
  $("#queryTitle").textContent = "Planner results";
  $("#queryResults").innerHTML =
    tasks
      .map(
        (t) =>
          `<button class="query-result" data-task="${t.id}"><strong>${esc(t.title)}</strong><small>${esc(t.course)}</small></button>`,
      )
      .join("") || '<p class="result-empty">No tasks matched that query.</p>';
  $("#overlay").hidden = false;
};
document.addEventListener("click", (e) => {
  const button = e.target.closest("[data-task]");
  if (button) openTask(Number(button.dataset.task));
});
$("#previousMonth").onclick = () => {
  const n = state.view === "week" ? 7 : state.view === "day" ? 1 : 0;
  if (n) state.selected.setUTCDate(state.selected.getUTCDate() - n);
  else state.cursor.setUTCMonth(state.cursor.getUTCMonth() - 1);
  render();
};
$("#nextMonth").onclick = () => {
  const n = state.view === "week" ? 7 : state.view === "day" ? 1 : 0;
  if (n) state.selected.setUTCDate(state.selected.getUTCDate() + n);
  else state.cursor.setUTCMonth(state.cursor.getUTCMonth() + 1);
  render();
};
$("#todayButton").onclick = () => {
  state.cursor = new Date();
  state.selected = new Date();
  render();
};
document.addEventListener("click", async (e) => {
  const action = e.target.closest("[data-budget-action]");
  if (!action) return;
  try {
    await api(`/api/budget/${action.dataset.budgetId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: action.dataset.budgetAction,
        pin: "313131",
      }),
    });
    await load();
  } catch (x) {
    alert(x.message);
  }
});
