// ─── DOM refs ────────────────────────────────────────────────────────────────
const state      = document.getElementById("state");
const substate   = document.getElementById("substate");
const orb        = document.getElementById("orb");
const micButton  = document.getElementById("micButton");
const modeLabel  = document.getElementById("modeLabel");

const chatPanel  = document.getElementById("chatPanel");
const chatButton = document.getElementById("chatButton");
const closeChat  = document.getElementById("closeChat");
const messages   = document.getElementById("messages");
const textInput  = document.getElementById("textInput");
const sendButton = document.getElementById("sendButton");

const weatherCard  = document.getElementById("weatherCard");
const sysCard      = document.getElementById("sysCard");
const quickActions = document.getElementById("quickActions");

// Status bar elements
const sysCpu     = document.getElementById("sysCpu");
const sysRam     = document.getElementById("sysRam");
const sysBat     = document.getElementById("sysBat");
const sysTime    = document.getElementById("sysTime");

let socket    = null;
let listening = false;
let currentMode = "NORMAL";  // NORMAL | CODING | STUDY

// ─── WebSocket ───────────────────────────────────────────────────────────────

function connect() {
    socket = new WebSocket("ws://127.0.0.1:8000/ws");

    socket.onopen = () => {
        console.log("✅ Connected to Tommy");
    };

    socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleEvent(message.event, message.data);
    };

    socket.onclose = () => {
        setState("OFFLINE", "Tommy backend is not running.");
        setTimeout(connect, 1500);
    };

    socket.onerror = (error) => {
        console.error("WebSocket error:", error);
    };
}

// ─── Event dispatcher ────────────────────────────────────────────────────────

function handleEvent(event, data) {
    switch (event) {
        case "ready":        setReady();                         break;
        case "listening":    setListening();                     break;
        case "thinking":     setThinking();                      break;
        case "user_message": if (data?.text) addMessage(data.text, "user"); break;
        case "answer":       handleAnswer(data);                 break;
        case "speaking_start": startSpeaking();                  break;
        case "speaking_end":   stopSpeaking();                   break;
        case "error":        if (data?.text) addMessage(data.text, "tommy", "NORMAL"); break;
        case "weather_data": renderWeatherCard(data);            break;
        case "system_status": renderSystemStatus(data);          break;
    }
}

// ─── State setters ───────────────────────────────────────────────────────────

function setState(title, subtitle) {
    state.textContent  = title;
    substate.innerHTML = subtitle;
}

function setReady() {
    listening = false;
    setState("TOMMY READY", 'Click <b>🎤</b> and talk to me');
    orb.classList.remove("listening", "speaking");
    micButton.classList.remove("active");
    micButton.disabled = false;
}

function setListening() {
    listening = true;
    setState("LISTENING...", "Speak now 🎤");
    orb.classList.add("listening");
    orb.classList.remove("speaking");
    micButton.classList.add("active");
    micButton.disabled = true;
}

function setThinking() {
    setState("THINKING...", "Tommy is processing 🧠");
    orb.classList.remove("listening");
}

function startSpeaking() {
    setState("TOMMY SPEAKING", "🔊 Tommy is talking...");
    orb.classList.remove("listening");
    orb.classList.add("speaking");
}

function stopSpeaking() {
    orb.classList.remove("speaking");
}

// ─── Mode management ─────────────────────────────────────────────────────────

const MODE_CONFIG = {
    CODING: {
        label: "⌨️ CODING MODE",
        cls: "mode-coding",
        orbClass: "orb-coding",
    },
    STUDY: {
        label: "📚 STUDY MODE",
        cls: "mode-study",
        orbClass: "orb-study",
    },
    NORMAL: {
        label: "💬 NORMAL MODE",
        cls: "mode-normal",
        orbClass: "",
    },
};

function setMode(mode) {
    currentMode = mode || "NORMAL";
    const cfg = MODE_CONFIG[currentMode] || MODE_CONFIG.NORMAL;

    modeLabel.textContent = cfg.label;
    modeLabel.className   = "mode-badge " + cfg.cls;

    orb.classList.remove("orb-coding", "orb-study");
    if (cfg.orbClass) orb.classList.add(cfg.orbClass);
}

// ─── Answer handler ──────────────────────────────────────────────────────────

function handleAnswer(data) {
    if (!data?.text) return;
    const mode = data.mode || "NORMAL";
    setMode(mode);
    addMessage(data.text, "tommy", mode);
    chatPanel.classList.add("open");
}

// ─── Message renderer ─────────────────────────────────────────────────────────
// Renders plain text AND fenced code blocks for CODING mode.

function renderMessageContent(text, mode) {
    if (mode !== "CODING") {
        // For STUDY: render **bold** and bullet points.
        if (mode === "STUDY") {
            return renderStudyContent(text);
        }
        const safe = escapeHtml(text);
        return `<span>${safe}</span>`;
    }

    // CODING mode: parse code blocks
    const parts = text.split(/(```[\s\S]*?```)/g);
    let html = "";

    parts.forEach(part => {
        const fenceMatch = part.match(/^```(\w*)\n?([\s\S]*?)```$/);
        if (fenceMatch) {
            const lang    = fenceMatch[1] || "code";
            const code    = fenceMatch[2];
            const escaped = escapeHtml(code);
            html += `
<div class="code-block">
  <div class="code-header">
    <span class="code-lang">${lang.toUpperCase()}</span>
    <button class="copy-btn" onclick="copyCode(this)">📋 Copy</button>
  </div>
  <pre><code>${escaped}</code></pre>
</div>`;
        } else if (part.trim()) {
            html += `<span>${escapeHtml(part)}</span>`;
        }
    });

    return html;
}

function renderStudyContent(text) {
    let html = escapeHtml(text);
    // **bold**
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    // bullet points starting with - or *
    html = html.replace(/\n[-*] (.+)/g, "\n<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>");
    return `<div class="study-content">${html}</div>`;
}

function escapeHtml(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function copyCode(btn) {
    const code = btn.closest(".code-block").querySelector("code").textContent;
    navigator.clipboard.writeText(code).then(() => {
        btn.textContent = "✅ Copied!";
        setTimeout(() => { btn.textContent = "📋 Copy"; }, 1800);
    });
}

function addMessage(text, type, mode = "NORMAL") {
    const wrapper = document.createElement("div");
    wrapper.classList.add("message", type);

    if (type === "tommy") {
        const modeClass = mode.toLowerCase();
        wrapper.innerHTML = `
            <div class="avatar ${modeClass}-avatar">T</div>
            <div class="bubble ${modeClass}-bubble">
              <div class="mode-pill mode-${modeClass}">${MODE_CONFIG[mode]?.label || "💬 NORMAL"}</div>
              <div class="msg-body"></div>
            </div>`;
        wrapper.querySelector(".msg-body").innerHTML = renderMessageContent(text, mode);
    } else {
        wrapper.innerHTML = `<div class="bubble user-bubble"></div>`;
        wrapper.querySelector(".bubble").textContent = text;
    }

    messages.appendChild(wrapper);
    messages.scrollTop = messages.scrollHeight;

    if (type === "tommy") {
        chatPanel.classList.add("open");
    }
}

// ─── Weather card ─────────────────────────────────────────────────────────────

const WX_ICONS = {
    "Clear Sky": "☀️", "Mainly Clear": "🌤️", "Partly Cloudy": "⛅",
    "Overcast": "☁️", "Foggy": "🌫️", "Icy Fog": "🌫️",
    "Light Drizzle": "🌦️", "Slight Rain": "🌧️", "Moderate Rain": "🌧️",
    "Heavy Rain": "⛈️", "Slight Snow": "❄️", "Showers": "🌦️",
    "Thunderstorm": "⛈️",
};

function renderWeatherCard(d) {
    if (d.error) {
        weatherCard.innerHTML = `<div class="card-error">⚠️ ${d.error}</div>`;
        weatherCard.classList.add("visible");
        return;
    }

    const icon = WX_ICONS[d.condition] || "🌡️";

    weatherCard.innerHTML = `
      <div class="wx-header">
        <span class="wx-icon">${icon}</span>
        <div>
          <div class="wx-city">${d.city}</div>
          <div class="wx-condition">${d.condition}</div>
        </div>
        <button class="card-close" onclick="weatherCard.classList.remove('visible')">×</button>
      </div>
      <div class="wx-temp">${d.temp}°C</div>
      <div class="wx-meta">
        <span>🌡️ Feels ${d.feels_like}°C</span>
        <span>💧 ${d.humidity}%</span>
        <span>💨 ${d.wind} km/h</span>
      </div>`;

    weatherCard.classList.add("visible");
    addMessage(`Weather in ${d.city}: ${d.temp}°C, ${d.condition}. Feels like ${d.feels_like}°C, humidity ${d.humidity}%.`, "tommy", "NORMAL");
}

// ─── System status card ───────────────────────────────────────────────────────

function renderSystemStatus(d) {
    // Update top status bar
    if (sysCpu) sysCpu.textContent = `CPU ${d.cpu}%`;
    if (sysRam) sysRam.textContent = `RAM ${d.ram}%`;
    if (sysBat) {
        if (d.battery !== null) {
            sysBat.textContent = `🔋 ${d.battery}%${d.charging ? "⚡" : ""}`;
        } else {
            sysBat.textContent = "🔋 N/A";
        }
    }
    if (sysTime) sysTime.textContent = d.time;

    // Full status card
    const batLine = d.battery !== null
        ? `<div class="sys-row"><span>Battery</span><span>${d.battery}% ${d.charging ? "⚡ Charging" : "🔋 On Battery"}</span></div>`
        : "";

    sysCard.innerHTML = `
      <div class="sys-header">
        <span>🖥️ System Status</span>
        <button class="card-close" onclick="sysCard.classList.remove('visible')">×</button>
      </div>
      <div class="sys-grid">
        <div class="sys-stat">
          <div class="sys-val">${d.cpu}%</div>
          <div class="sys-key">CPU</div>
          <div class="sys-bar"><div style="width:${d.cpu}%"></div></div>
        </div>
        <div class="sys-stat">
          <div class="sys-val">${d.ram}%</div>
          <div class="sys-key">RAM</div>
          <div class="sys-bar"><div style="width:${d.ram}%"></div></div>
        </div>
      </div>
      <div class="sys-details">
        <div class="sys-row"><span>Disk</span><span>${d.disk_used} / ${d.disk_total} GB</span></div>
        ${batLine}
        <div class="sys-row"><span>OS</span><span>${d.os}</span></div>
        <div class="sys-row"><span>Date</span><span>${d.date}</span></div>
      </div>`;

    sysCard.classList.add("visible");
}

// ─── Status bar auto-refresh ──────────────────────────────────────────────────

function refreshStatusBar() {
    if (sysTime) {
        const now = new Date();
        sysTime.textContent = now.toLocaleTimeString("en-IN", {
            hour: "2-digit", minute: "2-digit", hour12: true
        });
    }
}

setInterval(refreshStatusBar, 30000);

// ─── Quick action buttons ────────────────────────────────────────────────────

function sendAction(eventName, extraData = {}) {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify({ event: eventName, ...extraData }));
}

function quickSearch() {
    const q = prompt("Search Google for:");
    if (q) {
        addMessage(`Search: ${q}`, "user");
        sendChat(`search for ${q}`);
    }
}

function quickYouTube() {
    const q = prompt("YouTube search (leave empty to just open):");
    addMessage(q ? `YouTube: ${q}` : "Open YouTube", "user");
    sendChat(q ? `youtube ${q}` : "open youtube");
}

function quickWeather() {
    const city = prompt("City name:", "Meerut") || "Meerut";
    sendAction("get_weather", { city });
}

function quickSysStatus() {
    sendAction("get_system_status");
}

// ─── Chat input ───────────────────────────────────────────────────────────────

function sendChat(text) {
    text = text || textInput.value.trim();
    if (!text) return;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    addMessage(text, "user");
    socket.send(JSON.stringify({ event: "chat", text }));
    if (textInput) textInput.value = "";
}

if (sendButton) sendButton.onclick = () => sendChat();
if (textInput) {
    textInput.addEventListener("keydown", e => {
        if (e.key === "Enter") sendChat();
    });
}

// ─── Mic button ───────────────────────────────────────────────────────────────

micButton.onclick = () => {
    if (listening) return;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        setState("OFFLINE", "Start Tommy backend first.");
        return;
    }
    socket.send(JSON.stringify({ event: "start_listening" }));
};

// ─── Panel toggles ───────────────────────────────────────────────────────────

if (chatButton) chatButton.onclick  = () => chatPanel.classList.add("open");
if (closeChat)  closeChat.onclick   = () => chatPanel.classList.remove("open");

// Quick-action wiring (buttons in HTML call these directly as onclick)
window.quickSearch    = quickSearch;
window.quickYouTube   = quickYouTube;
window.quickWeather   = quickWeather;
window.quickSysStatus = quickSysStatus;
window.copyCode       = copyCode;

// ─── Boot ─────────────────────────────────────────────────────────────────────
connect();
setMode("NORMAL");
refreshStatusBar();
