/**
 * Google Gemini AI Fleet Commander UI Controller
 * Manages API configuration, natural language command dispatching, and response presentation.
 */

window.GeminiCommander = (function () {
  let isConfigured = false;

  function init() {
    const sendBtn = document.getElementById("btn-send-ai-main") || document.getElementById("btn-ai-send");
    const inputField = document.getElementById("ai-main-input") || document.getElementById("ai-prompt-input");
    const saveKeyBtn = document.getElementById("btn-save-gemini-key") || document.getElementById("btn-save-key");
    const apiKeyInput = document.getElementById("gemini-key-input") || document.getElementById("gemini-api-key");
    const chips = document.querySelectorAll(".quick-ai-chip, .prompt-chips .chip");

    if (sendBtn && inputField) {
      sendBtn.addEventListener("click", () => sendPrompt(inputField.value));
      inputField.addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendPrompt(inputField.value);
      });
    }

    if (saveKeyBtn && apiKeyInput) {
      saveKeyBtn.addEventListener("click", () => {
        const key = apiKeyInput.value.trim();
        if (key) {
          saveApiKey(key);
        }
      });
    }

    chips.forEach(chip => {
      chip.addEventListener("click", () => {
        if (inputField) {
          inputField.value = chip.innerText.replace(/^[^\w]+/, "").trim();
          sendPrompt(inputField.value);
        }
      });
    });
  }

  function appendMessage(sender, text, isAi = false, meta = null) {
    const chatLog = document.getElementById("ai-chat-log-main") || document.getElementById("ai-chat-log");
    if (!chatLog) return;

    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${isAi ? "ai" : "user"}`;
    
    let html = `<strong>${sender}:</strong> ${text}`;
    if (meta && meta.reasoning) {
      html += `<div style="margin-top:6px; font-size:0.75rem; color:#d8b4fe; border-top:1px dashed rgba(216,180,254,0.3); padding-top:4px;">
        💡 <em>Reasoning:</em> ${meta.reasoning}
      </div>`;
    }
    bubble.innerHTML = html;
    chatLog.appendChild(bubble);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  async function sendPrompt(promptText) {
    if (!promptText || promptText.trim() === "") return;

    const inputField = document.getElementById("ai-main-input") || document.getElementById("ai-prompt-input");
    if (inputField) inputField.value = "";

    appendMessage("Supervisor", promptText, false);

    try {
      const resp = await fetch("/api/ai/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: promptText })
      });
      const data = await resp.json();

      if (data.success && data.result) {
        const res = data.result;
        const msg = res.reply_message || "Command executed successfully.";
        appendMessage("Gemini Commander", msg, true, res);

        // Update anomaly diagnostic feed if available
        const feed = document.getElementById("ai-anomaly-feed");
        if (feed && res.reasoning) {
          feed.innerHTML = `[AI Analysis] Target: <strong>${res.assigned_amr || 'Fleet'}</strong><br>${res.reasoning}`;
        }
      } else {
        appendMessage("System", data.error || "Failed to process AI command.", true);
      }
    } catch (err) {
      appendMessage("Error", "Network error communicating with AI agent.", true);
    }
  }

  async function saveApiKey(key) {
    try {
      const resp = await fetch("/api/ai/configure", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: key })
      });
      const data = await resp.json();
      if (data.success) {
        isConfigured = data.is_configured;
        updateBadgeStatus(isConfigured);
        appendMessage("System", `Gemini API Key configured! Model: ${data.model}`, true);
      }
    } catch (e) {
      appendMessage("System", "Could not save API key.", true);
    }
  }

  function updateBadgeStatus(configured) {
    isConfigured = configured;
    const badge = document.getElementById("ai-status-badge");
    if (badge) {
      badge.innerText = configured ? "GEMINI ONLINE" : "LOCAL HYBRID";
      badge.style.color = configured ? "var(--accent-green)" : "var(--accent-purple)";
    }
  }

  return {
    init,
    updateBadgeStatus,
    appendMessage
  };
})();
