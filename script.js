// frontend/script.js
const API_BASE = "http://127.0.0.1:8000";

document.getElementById("tab-chat").onclick = () => switchTab("chat");
document.getElementById("tab-vitals").onclick = () => switchTab("vitals");
document.getElementById("tab-reminders").onclick = () => switchTab("reminders");

function switchTab(name) {
  document.querySelectorAll(".tabs button").forEach(b => b.classList.remove("active"));
  document.getElementById("tab-" + name).classList.add("active");
  document.getElementById("chat-panel").classList.toggle("hidden", name !== "chat");
  document.getElementById("vitals-panel").classList.toggle("hidden", name !== "vitals");
  document.getElementById("reminders-panel").classList.toggle("hidden", name !== "reminders");
}

// Chat
document.getElementById("send-btn").addEventListener("click", sendMessage);
document.getElementById("user-input").addEventListener("keydown", (e) => { if (e.key === "Enter") sendMessage(); });

async function sendMessage() {
  const input = document.getElementById("user-input");
  const message = input.value.trim();
  if (!message) return;
  appendChat("You", message, "user");
  input.value = "";
  appendChat("AI", "Thinking...", "bot", true);
  try {
    const res = await fetch(API_BASE + "/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });
    const data = await res.json();
    replaceLastBot(data.reply);
  } catch (err) {
    replaceLastBot("Error contacting backend: " + err.message);
  }
}

function appendChat(who, text, cls, isTemp=false) {
  const box = document.getElementById("chat-box");
  const p = document.createElement("div");
  p.className = "msg " + cls + (isTemp ? " temp" : "");
  p.innerHTML = `<strong>${who}:</strong> <span>${text}</span>`;
  box.appendChild(p);
  box.scrollTop = box.scrollHeight;
}

function replaceLastBot(text) {
  const box = document.getElementById("chat-box");
  const temps = box.querySelectorAll(".msg.bot.temp");
  if (temps.length) {
    temps[temps.length - 1].innerHTML = `<strong>AI:</strong> <span>${text}</span>`;
    temps[temps.length - 1].classList.remove("temp");
  } else {
    appendChat("AI", text, "bot");
  }
}

// Vitals
document.getElementById("save-vitals").addEventListener("click", async () => {
  const bp = document.getElementById("bp").value;
  const sugar = document.getElementById("sugar").value;
  const pulse = document.getElementById("pulse").value;
  const notes = document.getElementById("v-notes").value;
  const payload = { blood_pressure: bp, blood_sugar: sugar, pulse, notes, timestamp: new Date().toISOString() };
  const res = await fetch(API_BASE + "/vitals", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (data.ok) {
    loadVitals();
    alert("Vitals saved.");
  }
});

async function loadVitals() {
  const res = await fetch(API_BASE + "/vitals");
  const data = await res.json();
  const el = document.getElementById("vitals-list");
  el.innerHTML = "";
  (data.vitals || []).slice().reverse().forEach(v => {
    const d = document.createElement("div");
    d.innerText = `${v.timestamp || ''} — BP:${v.blood_pressure || '-'} Sugar:${v.blood_sugar || '-'} Pulse:${v.pulse || '-' } Notes:${v.notes || ''}`;
    el.appendChild(d);
  });
}

// Reminders
document.getElementById("add-reminder").addEventListener("click", async () => {
  const title = document.getElementById("rem-title").value;
  const time = document.getElementById("rem-time").value;
  const notes = document.getElementById("rem-notes").value;
  if (!title || !time) { alert("Title and time needed"); return; }
  const res = await fetch(API_BASE + "/reminder", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title, time, notes })
  });
  const data = await res.json();
  if (data.ok) {
    loadReminders();
    alert("Reminder added.");
  } else {
    alert("Error adding reminder");
  }
});

async function loadReminders() {
  const res = await fetch(API_BASE + "/reminders");
  const data = await res.json();
  const el = document.getElementById("reminders-list");
  el.innerHTML = "";
  (data.reminders || []).forEach(r => {
    const d = document.createElement("div");
    d.innerText = `${r.time} — ${r.title} ${r.notes ? "(" + r.notes + ")" : ""}`;
    el.appendChild(d);
  });
}

// initial load
loadVitals();
loadReminders();
