/* 센터 운영 비서 프론트 — 바닐라 JS.
   구성: 1 설정·fetch 래퍼 · 2 다크 모드 · 3 요약 카드 + 스파크라인 · 4 데이터 CRUD + CSV 내보내기 · 5 채팅 · 6 대화 기록 */
(() => {
  "use strict";

  // ---------- 1. 설정·공통 ----------
  const CFG = window.APP_CONFIG || {};
  const API = (CFG.API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
  const TIMEOUT = CFG.REQUEST_TIMEOUT_MS || 25000;
  const $ = (id) => document.getElementById(id);
  const fmt = (n) => (n === null || n === undefined ? "—" : Number(n).toLocaleString("ko-KR", { maximumFractionDigits: 1 }));
  let UNIT = "kWh";

  async function api(path, { method = "GET", body, timeout = TIMEOUT } = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
      const res = await fetch(API + path, {
        method, signal: controller.signal,
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      if (res.status === 204) return null;
      let data = null;
      try { data = await res.json(); } catch (_) { /* 본문 없음 */ }
      if (!res.ok) {
        const msg = (data && (data.message || data.error)) || `서버 오류 (${res.status})`;
        const err = new Error(msg); err.status = res.status; err.code = data && data.error; throw err;
      }
      return data;
    } catch (e) {
      if (e.name === "AbortError") { const err = new Error("응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요."); err.code = "timeout"; throw err; }
      if (e instanceof TypeError) { const err = new Error("서버에 연결할 수 없습니다. 백엔드가 켜져 있는지, API 주소가 맞는지 확인하세요."); err.code = "network"; throw err; }
      throw e;
    } finally { clearTimeout(timer); }
  }

  function setMsg(el, text, kind) { el.textContent = text || ""; el.className = "form-msg" + (kind ? " " + kind : ""); }

  // ---------- 2. 다크 모드 ----------
  const root = document.documentElement;
  let savedTheme = null;
  try { savedTheme = localStorage.getItem("theme"); } catch (_) {}
  if (savedTheme) root.setAttribute("data-theme", savedTheme);
  $("themeToggle").addEventListener("click", () => {
    const dark = root.getAttribute("data-theme") === "dark" || (!root.getAttribute("data-theme") && matchMedia("(prefers-color-scheme: dark)").matches);
    const next = dark ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("theme", next); } catch (_) {}
  });

  // ---------- 3. 서버 상태·요약 ----------
  $("docsLink").href = API + "/docs";

  async function loadHealth() {
    const badge = $("serverBadge");
    try {
      const h = await api("/api/health", { timeout: 60000 });
      UNIT = h.unit || UNIT; $("unitLabel").textContent = `(${UNIT})`;
      badge.textContent = `서버 연결됨 · ${h.storage}${h.llm_configured ? "" : " · LLM 미설정"}`;
      badge.className = "badge " + (h.llm_configured ? "badge-ok" : "badge-warn");
    } catch (e) {
      badge.textContent = "서버 연결 실패"; badge.className = "badge badge-err";
    }
  }

  const TREND_KO = { increasing: ["증가", "up"], decreasing: ["감소", "down"], stable: ["유지", "flat"], not_enough_data: ["데이터 부족", ""] };

  async function loadSummary() {
    try {
      const s = await api("/api/data/summary");
      $("sumPeriod").textContent = s.count ? `${s.period.start} ~ ${s.period.end}` : "—";
      $("sumCount").textContent = `${s.count}건`;
      $("sumAvg").textContent = s.metrics ? `${fmt(s.metrics.average)} ${s.unit}` : "—";
      $("sumMaxMin").textContent = s.metrics ? `${fmt(s.metrics.max)} / ${fmt(s.metrics.min)}` : "—";
      $("sumRecent").textContent = s.recent_7_days ? `${fmt(s.recent_7_days.average)} ${s.unit}` : "—";
      const [label, cls] = TREND_KO[s.trend] || ["—", ""];
      const trendEl = $("sumTrend");
      trendEl.textContent = label + (s.trend_change_pct !== null && s.trend_change_pct !== undefined ? ` (${s.trend_change_pct > 0 ? "+" : ""}${s.trend_change_pct}%)` : "");
      trendEl.className = cls;
      $("sumLatest").textContent = s.latest ? `마지막 기록 ${s.latest.date} · ${fmt(s.latest.value)} ${s.unit}${s.latest.memo ? " · " + s.latest.memo : ""}` : "데이터가 없습니다. 아래에서 추가하거나 시드 스크립트를 실행하세요.";
    } catch (e) {
      $("sumLatest").textContent = "요약을 불러오지 못했습니다: " + e.message;
    }
  }

  function drawSparkline(rows) {
    const canvas = $("sparkline");
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height, pad = 8;
    ctx.clearRect(0, 0, W, H);
    const data = rows.slice(-60);
    if (data.length < 2) return;
    const vals = data.map((r) => Number(r.value));
    const min = Math.min(...vals), max = Math.max(...vals), span = max - min || 1;
    const x = (i) => pad + (i / (data.length - 1)) * (W - pad * 2);
    const y = (v) => H - pad - ((v - min) / span) * (H - pad * 2);
    const styles = getComputedStyle(root);
    ctx.strokeStyle = styles.getPropertyValue("--line").trim(); ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(pad, y(vals.reduce((a, b) => a + b, 0) / vals.length)); ctx.lineTo(W - pad, y(vals.reduce((a, b) => a + b, 0) / vals.length)); ctx.setLineDash([4, 4]); ctx.stroke(); ctx.setLineDash([]);
    ctx.strokeStyle = styles.getPropertyValue("--primary").trim(); ctx.lineWidth = 2;
    ctx.beginPath(); vals.forEach((v, i) => (i ? ctx.lineTo(x(i), y(v)) : ctx.moveTo(x(i), y(v)))); ctx.stroke();
    ctx.fillStyle = styles.getPropertyValue("--accent").trim();
    ctx.beginPath(); ctx.arc(x(vals.length - 1), y(vals[vals.length - 1]), 3.5, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = styles.getPropertyValue("--muted").trim(); ctx.font = "11px sans-serif";
    ctx.fillText(`최근 ${data.length}일 · 점선 = 평균`, pad + 2, 12);
  }

  // ---------- 4. 데이터 CRUD ----------
  let editingId = null;
  let rowsCache = [];

  async function loadData() {
    const body = $("dataBody");
    try {
      rowsCache = await api("/api/data");
      $("dataCountBadge").textContent = `${rowsCache.length}건`;
      drawSparkline(rowsCache);
      const recent = rowsCache.slice().reverse().slice(0, 30);
      if (!recent.length) { body.innerHTML = '<tr><td colspan="4" class="empty">데이터가 없습니다. 위 폼으로 추가하세요.</td></tr>'; return; }
      body.innerHTML = "";
      for (const r of recent) {
        const tr = document.createElement("tr");
        tr.dataset.id = r.id;
        if (r.id === editingId) tr.classList.add("editing");
        tr.innerHTML = `<td>${r.date}</td><td class="num">${fmt(r.value)}</td><td></td>
          <td class="actions"><button class="row-btn edit" title="수정" aria-label="수정">✎</button><button class="row-btn del" title="삭제" aria-label="삭제">✕</button></td>`;
        tr.children[2].textContent = r.memo || "";
        tr.querySelector(".edit").addEventListener("click", () => startEdit(r));
        tr.querySelector(".del").addEventListener("click", () => removeRow(r));
        body.appendChild(tr);
      }
    } catch (e) {
      body.innerHTML = `<tr><td colspan="4" class="empty">${e.message}</td></tr>`;
    }
  }

  function startEdit(r) {
    editingId = r.id;
    $("dataDate").value = r.date; $("dataValue").value = r.value; $("dataMemo").value = r.memo || "";
    $("dataSubmit").textContent = "수정 저장"; $("dataCancel").classList.remove("hidden");
    setMsg($("dataMsg"), `${r.date} 기록을 수정합니다.`);
    document.querySelectorAll("#dataBody tr").forEach((tr) => tr.classList.toggle("editing", tr.dataset.id === r.id));
    $("dataDate").focus();
  }
  function cancelEdit() {
    editingId = null; $("dataForm").reset();
    $("dataSubmit").textContent = "추가"; $("dataCancel").classList.add("hidden"); setMsg($("dataMsg"), "");
    document.querySelectorAll("#dataBody tr.editing").forEach((tr) => tr.classList.remove("editing"));
  }
  $("dataCancel").addEventListener("click", cancelEdit);

  async function removeRow(r) {
    if (!confirm(`${r.date} (${fmt(r.value)} ${UNIT}) 기록을 삭제할까요?`)) return;
    try {
      await api(`/api/data/${r.id}`, { method: "DELETE" });
      setMsg($("dataMsg"), "삭제했습니다.", "ok");
      if (editingId === r.id) cancelEdit();
      await Promise.all([loadData(), loadSummary()]);
    } catch (e) { setMsg($("dataMsg"), e.message, "err"); }
  }

  $("dataForm").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const date = $("dataDate").value, value = $("dataValue").value.trim(), memo = $("dataMemo").value.trim();
    if (!date) return setMsg($("dataMsg"), "날짜를 선택하세요.", "err");
    if (value === "" || Number(value) < 0) return setMsg($("dataMsg"), "값은 0 이상의 숫자여야 합니다.", "err");
    const btn = $("dataSubmit"); btn.disabled = true;
    try {
      if (editingId) {
        await api(`/api/data/${editingId}`, { method: "PUT", body: { date, value: Number(value), memo } });
        setMsg($("dataMsg"), "수정했습니다. 요약이 다시 계산됩니다.", "ok");
        cancelEdit();
      } else {
        await api("/api/data", { method: "POST", body: { date, value: Number(value), memo } });
        setMsg($("dataMsg"), `${date} 기록을 추가했습니다.`, "ok");
        $("dataForm").reset();
      }
      await Promise.all([loadData(), loadSummary()]);
    } catch (e) { setMsg($("dataMsg"), e.message, "err"); }
    finally { btn.disabled = false; }
  });

  // CSV 내보내기(보너스): 서버 호출 없이 이미 받아 둔 전체 목록(rowsCache)으로 파일을 만든다. BOM 을 붙여 Excel 에서 한글이 깨지지 않게 한다
  $("exportCsv").addEventListener("click", () => {
    if (!rowsCache.length) return setMsg($("dataMsg"), "내보낼 데이터가 없습니다.", "err");
    const esc = (v) => `"${String(v === null || v === undefined ? "" : v).replace(/"/g, '""')}"`;
    const lines = ["date,value,memo", ...rowsCache.map((r) => [esc(r.date), r.value, esc(r.memo || "")].join(","))];
    const blob = new Blob(["\uFEFF" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `center_power_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setMsg($("dataMsg"), `${rowsCache.length}건을 CSV로 내보냈습니다.`, "ok");
  });

  // ---------- 5. 채팅 ----------
  let conversationId = null;
  const messagesEl = $("messages");

  function addMessage(role, text, meta) {
    const wrap = document.createElement("div");
    wrap.className = `msg msg-${role}`;
    const bubble = document.createElement("div");
    bubble.className = "msg-bubble"; bubble.textContent = text;
    const inner = document.createElement("div");
    inner.appendChild(bubble);
    if (meta) { const m = document.createElement("div"); m.className = "msg-meta"; m.textContent = meta; inner.appendChild(m); }
    wrap.appendChild(inner);
    messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return wrap;
  }
  function addTyping() {
    const wrap = document.createElement("div");
    wrap.className = "msg msg-assistant";
    wrap.innerHTML = '<div class="msg-bubble"><span class="typing"><i></i><i></i><i></i></span> 데이터 요약을 참고해 답을 작성하고 있습니다…</div>';
    messagesEl.appendChild(wrap); messagesEl.scrollTop = messagesEl.scrollHeight;
    return wrap;
  }
  function resetChat(greeting = true) {
    conversationId = null;
    $("convBadge").textContent = "새 대화"; $("convBadge").className = "badge badge-muted";
    messagesEl.innerHTML = "";
    if (greeting) addMessage("assistant", "새 대화를 시작합니다. 데이터 요약을 바탕으로 답하겠습니다.");
    document.querySelectorAll(".history-item.active").forEach((b) => b.classList.remove("active"));
  }
  $("newChat").addEventListener("click", () => resetChat());

  const chatInput = $("chatInput");
  chatInput.addEventListener("input", () => { $("chatCount").textContent = chatInput.value.length; });
  chatInput.addEventListener("keydown", (ev) => { if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); $("chatForm").requestSubmit(); } });

  $("chatForm").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return setMsg($("chatMsg"), "질문을 입력하세요.", "err");
    if (text.length > 1000) return setMsg($("chatMsg"), "1,000자 이내로 입력하세요.", "err");
    setMsg($("chatMsg"), "");
    const btn = $("chatSend"); btn.disabled = true; chatInput.disabled = true;
    addMessage("user", text);
    chatInput.value = ""; $("chatCount").textContent = "0";
    const typing = addTyping();
    try {
      const res = await api("/api/chat", { method: "POST", body: { message: text, conversation_id: conversationId }, timeout: TIMEOUT * 2 });
      typing.remove();
      conversationId = res.conversation_id;
      $("convBadge").textContent = "저장됨 · " + conversationId.slice(0, 8); $("convBadge").className = "badge badge-ok";
      const s = res.summary_used;
      addMessage("assistant", res.answer, `모델 ${res.model} · 참고한 요약: ${s.count}건, 추세 ${TREND_KO[s.trend] ? TREND_KO[s.trend][0] : s.trend}`);
      loadHistory();
    } catch (e) {
      typing.remove();
      let msg = e.message;
      if (e.code === "llm_not_configured") msg = "서버에 LLM API 키가 설정되지 않았습니다. 관리자가 환경변수를 등록해야 합니다.";
      addMessage("error", msg);
      if (e.status === 404) resetChat(false);
    } finally { btn.disabled = false; chatInput.disabled = false; chatInput.focus(); }
  });

  // ---------- 6. 대화 기록 ----------
  async function loadHistory() {
    const list = $("historyList");
    try {
      const items = await api("/api/conversations?limit=50");
      if (!items.length) { list.innerHTML = '<li class="empty">저장된 대화가 없습니다. 비서에게 질문하면 자동으로 저장됩니다.</li>'; return; }
      list.innerHTML = "";
      for (const c of items) {
        const li = document.createElement("li");
        const btn = document.createElement("button");
        btn.type = "button"; btn.className = "history-item" + (c.id === conversationId ? " active" : "");
        const when = (c.updated_at || "").replace("T", " ").slice(0, 16);
        btn.innerHTML = `<span class="history-title"></span><span class="history-sub"></span>`;
        btn.querySelector(".history-title").textContent = c.title || "(제목 없음)";
        btn.querySelector(".history-sub").textContent = `${c.message_count}개 메시지 · ${when} · ${c.preview || ""}`;
        btn.addEventListener("click", () => openConversation(c.id));
        const del = document.createElement("button");
        del.type = "button"; del.className = "row-btn del"; del.title = "삭제"; del.textContent = "✕";
        del.addEventListener("click", async () => {
          if (!confirm(`대화 "${c.title}" 를 삭제할까요?`)) return;
          try { await api(`/api/conversations/${c.id}`, { method: "DELETE" }); if (conversationId === c.id) resetChat(); loadHistory(); }
          catch (e) { alert(e.message); }
        });
        li.append(btn, del); list.appendChild(li);
      }
    } catch (e) { list.innerHTML = `<li class="empty">${e.message}</li>`; }
  }

  async function openConversation(id) {
    try {
      const c = await api(`/api/conversations/${id}`);
      conversationId = c.id;
      messagesEl.innerHTML = "";
      for (const m of c.messages) addMessage(m.role === "user" ? "user" : "assistant", m.content, (m.created_at || "").replace("T", " ").slice(0, 16));
      $("convBadge").textContent = "불러옴 · " + c.title.slice(0, 18); $("convBadge").className = "badge badge-ok";
      document.querySelectorAll(".history-item").forEach((b) => b.classList.toggle("active", b.textContent.startsWith(c.title)));
      chatInput.focus();
    } catch (e) { alert(e.message); }
  }
  $("refreshHistory").addEventListener("click", loadHistory);
  $("refreshSummary").addEventListener("click", () => Promise.all([loadSummary(), loadData()]));

  // ---------- 시작 ----------
  (async () => {
    await loadHealth();
    await Promise.all([loadSummary(), loadData(), loadHistory()]);
  })();
})();
