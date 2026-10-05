// MediAssist AI - Chatbot front-end logic
// Core chat + NLP debug panel, plus: speech-to-text input, text-to-speech
// replies, English <-> Tamil translation, and a chat-history panel.

(function () {
  const form = document.getElementById("chatForm");
  const input = document.getElementById("chatInput");
  const messages = document.getElementById("chatMessages");
  const sendBtn = document.getElementById("sendBtn");
  const resetBtn = document.getElementById("resetBtn");
  const micBtn = document.getElementById("micBtn");
  const ttsToggle = document.getElementById("ttsToggle");
  const langSelect = document.getElementById("langSelect");
  const historyToggle = document.getElementById("historyToggle");
  const historyCloseBtn = document.getElementById("historyCloseBtn");
  const historyPanel = document.getElementById("historyPanel");
  const historyList = document.getElementById("historyList");
  const emergencyBtn = document.getElementById("emergencyBtn");
  const chips = document.querySelectorAll(".chip");
  const emergencyAlert = document.getElementById("emergencyAlert");
  const emergencyAlertClose = document.getElementById("emergencyAlertClose");
  const emergencyAlertCall = document.getElementById("emergencyAlertCall");
  const emergencyAlertLocation = document.getElementById("emergencyAlertLocation");

  let ttsEnabled = false;
  let currentLang = "en"; // 'en' or 'ta'

  // -----------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------
  function escapeHtml(str) {
    const div = document.createElement("div");
    div.innerText = str;
    return div.innerHTML;
  }

  function renderMarkdownLite(text) {
    // Minimal markdown: **bold** and line breaks - keeps the bot
    // response safe (escaped) while still readable.
    let safe = escapeHtml(text);
    safe = safe.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    safe = safe.replace(/\n/g, "<br>");
    return safe;
  }

  function addMessage(role, text, isEmergency, originalText) {
    const wrap = document.createElement("div");
    wrap.className = "msg " + (role === "user" ? "msg-user" : "msg-bot") + (isEmergency ? " msg-emergency" : "");
    wrap.innerHTML = renderMarkdownLite(text);
    if (originalText && originalText !== text) {
      const orig = document.createElement("span");
      orig.className = "msg-original";
      orig.textContent = (role === "user" ? "Sent as: " : "Original (EN): ") + originalText;
      wrap.appendChild(orig);
    }
    messages.appendChild(wrap);
    messages.scrollTop = messages.scrollHeight;
    return wrap;
  }

  function addTyping() {
    const wrap = document.createElement("div");
    wrap.className = "msg msg-bot";
    wrap.id = "typingIndicator";
    wrap.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
    messages.appendChild(wrap);
    messages.scrollTop = messages.scrollHeight;
  }

  function removeTyping() {
    const el = document.getElementById("typingIndicator");
    if (el) el.remove();
  }

  function updateDebugPanel(data) {
    document.getElementById("dbgIntent").textContent = data.intent || "-";
    document.getElementById("dbgAgent").textContent = data.agent || "-";
    document.getElementById("dbgSentiment").textContent = (data.sentiment && data.sentiment.label) || "-";
    document.getElementById("dbgConfidence").textContent = (data.confidence !== undefined ? data.confidence.toFixed(1) : "0") + "%";
    document.getElementById("confidenceFill").style.width = (data.confidence || 0) + "%";

    // Entities
    const entBox = document.getElementById("dbgEntities");
    entBox.innerHTML = "";
    const ents = data.entities || {};
    const allTags = [];
    (ents.doctors || []).forEach(d => allTags.push("Doctor: " + d.full_name));
    (ents.departments || []).forEach(d => allTags.push("Dept: " + d.name));
    (ents.medicines || []).forEach(d => allTags.push("Medicine: " + d.name));
    (ents.symptoms || []).forEach(s => allTags.push("Symptom: " + s));
    (ents.dates || []).forEach(d => allTags.push("Date: " + (d.resolved_date || d.text)));
    (ents.times || []).forEach(t => allTags.push("Time: " + t));
    if (ents.emergency_signals && ents.emergency_signals.length) {
      ents.emergency_signals.forEach(s => allTags.push("⚠ " + s));
    }
    if (allTags.length === 0) {
      entBox.innerHTML = '<span class="text-muted" style="font-size:12.5px;">No entities detected</span>';
    } else {
      allTags.forEach(t => {
        const tag = document.createElement("span");
        tag.className = "entity-tag";
        tag.textContent = t;
        entBox.appendChild(tag);
      });
    }
  }

  // -----------------------------------------------------------------
  // Translation (English <-> Tamil) via the free MyMemory endpoint.
  // No API key / paid service required. Fails gracefully (falls back
  // to the original text) if the network call doesn't succeed.
  // -----------------------------------------------------------------
  async function translateText(text, fromLang, toLang) {
    if (!text || fromLang === toLang) return text;
    try {
      const url = `https://api.mymemory.translated.net/get?q=${encodeURIComponent(text)}&langpair=${fromLang}|${toLang}`;
      const resp = await fetch(url);
      const data = await resp.json();
      const translated = data && data.responseData && data.responseData.translatedText;
      return translated || text;
    } catch (err) {
      console.warn("Translation unavailable, using original text.", err);
      return text;
    }
  }

  // -----------------------------------------------------------------
  // Text-to-Speech
  // -----------------------------------------------------------------
  function speak(text, lang) {
    if (!ttsEnabled || !("speechSynthesis" in window)) return;
    // Strip markdown bold markers before reading aloud.
    const clean = text.replace(/\*\*/g, "").replace(/[#_`]/g, "");
    const utter = new SpeechSynthesisUtterance(clean);
    utter.lang = lang === "ta" ? "ta-IN" : "en-US";
    utter.rate = 1;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utter);
  }

  ttsToggle.addEventListener("click", function () {
    ttsEnabled = !ttsEnabled;
    ttsToggle.textContent = ttsEnabled ? "🔊 Voice Reply: On" : "🔊 Voice Reply: Off";
    ttsToggle.classList.toggle("active", ttsEnabled);
    if (!ttsEnabled && "speechSynthesis" in window) window.speechSynthesis.cancel();
  });

  langSelect.addEventListener("change", function () {
    currentLang = langSelect.value;
    input.placeholder = currentLang === "ta"
      ? "உங்கள் செய்தியை தட்டச்சு செய்யவும்..."
      : "Type your message... e.g. 'I need a heart doctor'";
  });

  // -----------------------------------------------------------------
  // Speech-to-Text (Dual-Mode: Web Speech API + MediaRecorder Server Backup)
  // -----------------------------------------------------------------
  const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
  const micStatus = document.getElementById("micStatus");
  const micStatusText = document.getElementById("micStatusText");

  let recognizer = null;
  let mediaRecorder = null;
  let audioChunks = [];
  let isRecording = false;
  let mediaStream = null;
  let sttGotText = false;

  function showMicStatus(msg) {
    if (micStatus) {
      micStatus.style.display = "flex";
      if (micStatusText) micStatusText.textContent = msg || "Listening... Speak clearly into your microphone";
    }
  }

  function hideMicStatus() {
    if (micStatus) micStatus.style.display = "none";
  }

  function resetMic() {
    isRecording = false;
    sttGotText = false;
    micBtn.classList.remove("recording");
    micBtn.textContent = "🎤";
    micBtn.title = "Click to speak";
    hideMicStatus();
    input.placeholder = currentLang === "ta"
      ? "உங்கள் செய்தியை தட்டச்சு செய்யவும்..."
      : "Type your message... e.g. 'I need a heart doctor'";

    if (mediaStream) {
      try {
        mediaStream.getTracks().forEach(track => track.stop());
      } catch (e) {}
      mediaStream = null;
    }
  }

  async function startRecordingFlow() {
    if (isRecording) {
      stopRecordingFlow();
      return;
    }

    try {
      // 1. Request microphone permissions explicitly from the browser
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      console.warn("Microphone access denied or error:", err);
      alert("Microphone access is required for voice input. Please allow microphone permissions in your browser address bar.");
      resetMic();
      return;
    }

    isRecording = true;
    sttGotText = false;
    micBtn.classList.add("recording");
    micBtn.textContent = "⏹";
    micBtn.title = "Click to stop listening";
    showMicStatus("Listening... Speak clearly into your microphone now");
    input.placeholder = "Listening... Speak now...";

    const reqLang = currentLang === "ta" ? "ta-IN" : "en-US";

    // 2. Setup MediaRecorder as server fallback
    audioChunks = [];
    try {
      mediaRecorder = new MediaRecorder(mediaStream);
      mediaRecorder.ondataavailable = function (e) {
        if (e.data && e.data.size > 0) {
          audioChunks.push(e.data);
        }
      };
      mediaRecorder.onstop = async function () {
        // If Web Speech API already got text, no need for server fallback
        if (sttGotText || !audioChunks.length) return;
        const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
        if (audioBlob.size < 500) return; // empty noise

        showMicStatus("Processing voice input...");
        const formData = new FormData();
        formData.append("audio", audioBlob, "speech.wav");
        formData.append("lang", reqLang);

        try {
          const resp = await fetch("/api/voice-recognize", { method: "POST", body: formData });
          const resData = await resp.json();
          if (resData && resData.status === "success" && resData.transcript) {
            input.value = resData.transcript;
            input.focus();
          }
        } catch (e) {
          console.warn("Server voice recognition error:", e);
        } finally {
          hideMicStatus();
        }
      };
      mediaRecorder.start();
    } catch (mrErr) {
      console.warn("MediaRecorder setup failed:", mrErr);
    }

    // 3. Setup Web Speech API for instant client-side transcription
    if (SpeechRecognitionCtor) {
      try {
        if (recognizer) {
          try { recognizer.abort(); } catch (e) {}
        }
        recognizer = new SpeechRecognitionCtor();
        recognizer.continuous = false;
        recognizer.interimResults = true;
        recognizer.maxAlternatives = 1;
        recognizer.lang = reqLang;

        recognizer.onresult = function (event) {
          let interimTranscript = "";
          let finalTranscript = "";

          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              finalTranscript += event.results[i][0].transcript;
            } else {
              interimTranscript += event.results[i][0].transcript;
            }
          }

          const txt = (finalTranscript || interimTranscript).trim();
          if (txt) {
            input.value = txt;
            sttGotText = true;
          }

          if (finalTranscript.trim()) {
            fetch("/api/voice-log", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ transcript: finalTranscript.trim(), recognition_lang: reqLang }),
            }).catch(() => {});
          }
        };

        recognizer.onerror = function (event) {
          console.warn("Web Speech API error:", event.error);
          // If Web Speech fails (e.g. no-speech/network), let MediaRecorder fallback run!
        };

        recognizer.onend = function () {
          if (input.value.trim()) {
            input.focus();
          }
          stopRecordingFlow();
        };

        recognizer.start();
      } catch (recErr) {
        console.warn("SpeechRecognition start failed:", recErr);
      }
    }
  }

  function stopRecordingFlow() {
    if (!isRecording) return;
    if (recognizer) {
      try { recognizer.stop(); } catch (e) {}
    }
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      try { mediaRecorder.stop(); } catch (e) {}
    }
    resetMic();
  }

  micBtn.addEventListener("click", function (e) {
    e.preventDefault();
    startRecordingFlow();
  });

  // -----------------------------------------------------------------
  // Emergency Alert banner - shown in addition to the (already
  // red-tinted) chat bubble whenever the backend flags is_emergency,
  // so a real emergency is impossible to miss even if someone skims
  // past the chat text.
  // -----------------------------------------------------------------
  function showEmergencyAlert(data) {
    if (!emergencyAlert) return;
    const info = (data && data.data) || {};
    if (info.helpline) {
      emergencyAlertCall.href = "tel:" + info.helpline.replace(/[^+\d]/g, "");
      emergencyAlertCall.textContent = "📞 Call " + info.helpline;
    }
    if (info.location) {
      emergencyAlertLocation.textContent = "📍 " + info.location;
    }
    emergencyAlert.style.display = "block";
    emergencyAlert.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  if (emergencyAlertClose) {
    emergencyAlertClose.addEventListener("click", function () {
      emergencyAlert.style.display = "none";
    });
  }

  // -----------------------------------------------------------------
  // Sending a message
  // -----------------------------------------------------------------
  async function sendMessage(text, fromVoice) {
    if (!text.trim()) return;
    const displayedUserText = text;
    input.value = "";
    sendBtn.disabled = true;

    // If chatting in Tamil, translate to English first since the NLP
    // pipeline (intent classifier, NER, sentiment) is English-based.
    let englishText = text;
    if (currentLang === "ta") {
      englishText = await translateText(text, "ta", "en");
    }
    addMessage("user", displayedUserText, false, currentLang === "ta" ? englishText : null);
    addTyping();

    try {
      const resp = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: englishText,
          input_mode: fromVoice ? "voice" : "text",
          lang: currentLang,
        }),
      });
      const data = await resp.json();
      removeTyping();

      let displayedBotText = data.response;
      if (currentLang === "ta") {
        displayedBotText = await translateText(data.response, "en", "ta");
      }
      addMessage("bot", displayedBotText, data.is_emergency, currentLang === "ta" ? data.response : null);
      updateDebugPanel(data);
      speak(displayedBotText, currentLang);

      if (data.is_emergency) {
        showEmergencyAlert(data);
      }

      if (data.requires_login) {
        const loginPrompt = document.createElement("div");
        loginPrompt.className = "msg msg-bot";
        loginPrompt.innerHTML = '<a href="/login" class="btn btn-primary btn-sm">Log In</a>';
        messages.appendChild(loginPrompt);
        messages.scrollTop = messages.scrollHeight;
      }
    } catch (err) {
      removeTyping();
      addMessage("bot", "Sorry, something went wrong connecting to the server. Please try again.", false);
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      sendMessage(input.value, false);
    });
  }

  if (emergencyBtn) {
    emergencyBtn.addEventListener("click", function () {
      const emergencyMessage = "I am having severe chest pain and difficulty breathing";
      sendMessage(emergencyMessage, false);
    });
  }

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      sendMessage(chip.getAttribute("data-message"), false);
    });
  });

  if (resetBtn) {
    resetBtn.addEventListener("click", async function () {
      await fetch("/api/chat/reset", { method: "POST" });
      messages.innerHTML = "";
      if (emergencyAlert) emergencyAlert.style.display = "none";
      addMessage("bot", "Conversation reset. Hi again! 👋 How can I help you today?", false);
    });
  }

  // -----------------------------------------------------------------
  // Chat History panel
  // -----------------------------------------------------------------
  async function loadHistory() {
    historyList.innerHTML = '<span class="history-empty">Loading...</span>';
    try {
      const resp = await fetch("/api/chat/history");
      const data = await resp.json();
      const rows = data.history || [];
      if (rows.length === 0) {
        historyList.innerHTML = '<span class="history-empty">No past conversations yet.</span>';
        return;
      }
      historyList.innerHTML = "";
      rows.forEach(function (row) {
        const item = document.createElement("div");
        item.className = "history-item";
        const modeTag = row.input_mode === "voice" ? " 🎤" : "";
        item.innerHTML = `<span class="h-user">You${modeTag}: ${escapeHtml(row.user_message)}</span>` +
          `<span class="h-bot">${escapeHtml((row.bot_response || "").slice(0, 140))}${(row.bot_response || "").length > 140 ? "…" : ""}</span>` +
          `<span class="h-meta">${row.agent || ""} · ${row.created_at || ""}</span>`;
        item.addEventListener("click", function () {
          input.value = row.user_message;
          historyPanel.style.display = "none";
          input.focus();
        });
        historyList.appendChild(item);
      });
    } catch (err) {
      historyList.innerHTML = '<span class="history-empty">Couldn\'t load history right now.</span>';
    }
  }

  historyToggle.addEventListener("click", function () {
    const showing = historyPanel.style.display !== "none";
    historyPanel.style.display = showing ? "none" : "block";
    if (!showing) loadHistory();
  });

  historyCloseBtn.addEventListener("click", function () {
    historyPanel.style.display = "none";
  });
})();
