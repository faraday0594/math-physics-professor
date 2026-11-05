let conversationHistory = [];
let attachedImageFile = null;
let attachedAudioBlob = null;
let attachedAudioFilename = "grabacion.webm";
let lastSubmittedPrompt = "";
let classroomRecords = [];
let activeClassroomDeck = null;
let activeSlideIndex = 0;

function addClassroomRecord(prompt, answer) {
  const id = classroomRecords.length;
  classroomRecords.push({ prompt, answer, cachedDeck: null });
  return id;
}

// Audio recording state
let mediaRecorder = null;
let audioChunks = [];
let recordingInterval = null;
let recordingSeconds = 0;

document.addEventListener("DOMContentLoaded", () => {
  // Limpiar cualquier clave vieja en caché si es la key antigua sk-api-dmD...
  const cachedKey = localStorage.getItem("minimax_api_key");
  if (cachedKey && cachedKey.startsWith("sk-api-dmD")) {
    localStorage.removeItem("minimax_api_key");
  }

  // Restore saved API Key and Base URL from localStorage if present
  const savedKey = localStorage.getItem("minimax_api_key");
  const savedBaseUrl = localStorage.getItem("minimax_base_url");
  if (savedKey) {
    const keyInput = document.getElementById("customApiKey");
    if (keyInput) keyInput.value = savedKey;
  }
  if (savedBaseUrl) {
    const baseInput = document.getElementById("customBaseUrl");
    if (baseInput) baseInput.value = savedBaseUrl;
  }

  fetchConfigStatus();
  if (typeof renderMathInElement === "function") {
    renderMathInElement(document.body, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
      ],
      throwOnError: false,
    });
  }

  // Support Ctrl+V image pasting anywhere
  window.addEventListener("paste", (e) => {
    const items = (e.clipboardData || e.originalEvent.clipboardData).items;
    for (const item of items) {
      if (item.type.indexOf("image") === 0) {
        const file = item.getAsFile();
        if (file) {
          setImageAttachment(file);
        }
      }
    }
  });
});

async function fetchConfigStatus() {
  try {
    const res = await fetch("/api/config-status");
    const data = await res.json();
    const statusEl = document.getElementById("currentKeyStatus");
    if (statusEl) {
      statusEl.textContent = `Clave activa en .env: ${data.masked_key} | Endpoint: ${data.base_url}`;
    }
  } catch (err) {
    console.error("Error fetching config:", err);
  }
}

function toggleModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle("hidden");
}

window.toggleModal = toggleModal;
window.saveAndCloseSettings = saveAndCloseSettings;

async function saveAndCloseSettings() {
  const keyInput = document.getElementById("customApiKey");
  const baseInput = document.getElementById("customBaseUrl");
  const notice = document.getElementById("saveConfigNotice");

  const apiKey = keyInput ? keyInput.value.trim() : "";
  const baseUrl = baseInput ? baseInput.value.trim() : "https://api.minimax.io/v1";

  if (apiKey) {
    localStorage.setItem("minimax_api_key", apiKey);
    localStorage.setItem("minimax_base_url", baseUrl);

    try {
      const res = await fetch("/api/save-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey, base_url: baseUrl }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        if (notice) {
          notice.classList.remove("hidden");
          setTimeout(() => notice.classList.add("hidden"), 3000);
        }
        await fetchConfigStatus();
      }
    } catch (e) {
      console.error("Error saving config to server:", e);
    }
  }

  toggleModal("settingsModal");
}

// --- Attachments handling ---
function handleImageSelected(event) {
  const file = event.target.files[0];
  if (file) setImageAttachment(file);
}

function setImageAttachment(file) {
  attachedImageFile = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    document.getElementById("imagePreviewThumb").src = e.target.result;
    document.getElementById("imagePreviewName").textContent = file.name || "imagen_pegada.png";
    document.getElementById("imagePreviewBadge").classList.remove("hidden");
    document.getElementById("attachmentBar").classList.remove("hidden");
  };
  reader.readAsDataURL(file);
}

function clearImageAttachment() {
  attachedImageFile = null;
  document.getElementById("imageInput").value = "";
  document.getElementById("imagePreviewBadge").classList.add("hidden");
  updateAttachmentBarVisibility();
}

function handleAudioFileSelected(event) {
  const file = event.target.files[0];
  if (file) {
    setAudioAttachment(file, file.name);
  }
}

function setAudioAttachment(blob, filename) {
  attachedAudioBlob = blob;
  attachedAudioFilename = filename || "audio.webm";
  const url = URL.createObjectURL(blob);
  const player = document.getElementById("audioPreviewPlayer");
  player.src = url;
  document.getElementById("audioPreviewName").textContent = attachedAudioFilename;
  document.getElementById("audioPreviewBadge").classList.remove("hidden");
  document.getElementById("attachmentBar").classList.remove("hidden");
}

function clearAudioAttachment() {
  attachedAudioBlob = null;
  document.getElementById("audioFileInput").value = "";
  document.getElementById("audioPreviewBadge").classList.add("hidden");
  updateAttachmentBarVisibility();
}

function updateAttachmentBarVisibility() {
  if (!attachedImageFile && !attachedAudioBlob) {
    document.getElementById("attachmentBar").classList.add("hidden");
  }
}

// --- Microphone Recording ---
async function toggleRecording() {
  const micBtn = document.getElementById("micButton");
  const micIcon = document.getElementById("micIcon");
  const micTimer = document.getElementById("micTimer");

  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
    clearInterval(recordingInterval);
    micBtn.classList.remove("border-rose-500", "bg-rose-950/60");
    micIcon.textContent = "🎙️";
    micTimer.classList.add("hidden");
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
      setAudioAttachment(audioBlob, "pregunta_voz.webm");
      stream.getTracks().forEach((track) => track.stop());
    };

    mediaRecorder.start();
    recordingSeconds = 0;
    micBtn.classList.add("border-rose-500", "bg-rose-950/60");
    micIcon.textContent = "⏹️";
    micTimer.textContent = "00:00";
    micTimer.classList.remove("hidden");

    recordingInterval = setInterval(() => {
      recordingSeconds++;
      const mins = String(Math.floor(recordingSeconds / 60)).padStart(2, "0");
      const secs = String(recordingSeconds % 60).padStart(2, "0");
      micTimer.textContent = `${mins}:${secs}`;
    }, 1000);
  } catch (err) {
    alert("No se pudo acceder al micrófono: " + err.message);
  }
}

// --- Presets ---
function loadPreset(type) {
  const input = document.getElementById("promptInput");
  if (type === "linear") {
    input.value = "Explícame paso a paso cómo resolver la ecuación 2x - 1 = 5 y genera su gráfica mostrando el punto de intersección.";
  } else if (type === "projectile") {
    input.value = "Un proyectil se lanza desde el suelo con velocidad inicial v0 = 25 m/s y un ángulo de 40 grados. Calcula paso a paso el tiempo de vuelo, la altura máxima, el alcance horizontal y grafica la trayectoria y(x) marcando el punto más alto.";
  } else if (type === "calculus") {
    input.value = "Dada la función f(x) = x^3 - 3x + 1, encuentra analíticamente su derivada, sus puntos críticos (máximo y mínimo local), y grafica la curva junto con sus puntos críticos.";
  } else if (type === "harmonic") {
    input.value = "Explica la ecuación de un oscilador armónico amortiguado x(t) = A * exp(-gamma * t) * cos(omega * t) con A=2 m, gamma=0.3 s^-1 y omega=4 rad/s. Calcula la posición en t=2 s y grafica x(t) junto con sus curvas envolventes.";
  } else if (type === "integral") {
    input.value = "Calcula paso a paso la integral definida y el área bajo la curva de f(x) = x^3 - 4*x^2 + 3*x + 2 entre 0 y 3, y sombrea la región integrada en la gráfica.";
  } else if (type === "ode") {
    input.value = "Resuelve paso a paso la ecuación diferencial de segundo orden y'' + 2y' + 10y = 0 con condiciones iniciales y(0)=2, y'(0)=0 y grafica su solución temporal y su espacio de fases.";
  }
  input.focus();
}

// --- Render Message Helpers ---
function renderMarkdownWithMath(rawMarkdown) {
  // Protect LaTeX blocks before Marked parses markdown
  const mathBlocks = [];
  let protectedText = rawMarkdown.replace(/\$\$([\s\S]*?)\$\$/g, (match) => {
    mathBlocks.push(match);
    return `@@MATH_BLOCK_${mathBlocks.length - 1}@@`;
  });
  protectedText = protectedText.replace(/\$([^\$\n]+?)\$/g, (match) => {
    mathBlocks.push(match);
    return `@@MATH_BLOCK_${mathBlocks.length - 1}@@`;
  });

  let html = typeof marked !== "undefined" ? marked.parse(protectedText) : protectedText.replace(/\n/g, "<br/>");

  html = html.replace(/@@MATH_BLOCK_(\d+)@@/g, (_, idx) => mathBlocks[Number(idx)]);
  return html;
}

function appendUserMessage(text, imgUrl, hasAudio) {
  const container = document.getElementById("chatContainer");
  const wrapper = document.createElement("div");
  wrapper.className = "max-w-3xl mx-auto flex justify-end";

  let mediaHtml = "";
  if (imgUrl) {
    mediaHtml += `<img src="${imgUrl}" class="max-h-48 rounded-xl border border-sky-400/30 mb-2 object-contain" />`;
  }
  if (hasAudio) {
    mediaHtml += `<div class="inline-flex items-center gap-1.5 text-xs bg-amber-500/20 text-amber-200 border border-amber-400/30 px-2.5 py-1 rounded-lg mb-2">🎙️ Nota de voz enviada</div>`;
  }

  wrapper.innerHTML = `
    <div class="bg-gradient-to-br from-sky-600/30 to-indigo-600/30 border border-sky-500/30 rounded-2xl rounded-tr-sm px-5 py-3.5 max-w-xl text-sm text-slate-100 shadow-lg">
      ${mediaHtml}
      <div class="whitespace-pre-wrap">${escapeHtml(text || "(Archivo multimedia adjunto)")}</div>
    </div>
  `;
  container.appendChild(wrapper);
  container.scrollTop = container.scrollHeight;
}

function appendTeacherResponse(data) {
  const container = document.getElementById("chatContainer");
  const wrapper = document.createElement("div");
  wrapper.className = "max-w-3xl mx-auto";

  // API fallback notice badge (if MiniMax returned 402 insufficient balance)
  let apiWarningHtml = "";
  if (data.api_warning) {
    apiWarningHtml = `
      <div class="mb-3 p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200 flex items-center justify-between gap-2">
        <span>⚡ ${escapeHtml(data.api_warning)}</span>
        <button onclick="toggleModal('settingsModal')" class="shrink-0 px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700">Configurar API</button>
      </div>
    `;
  }

  // Transcribed audio badge
  let transcriptionHtml = "";
  if (data.transcribed_audio) {
    transcriptionHtml = `
      <div class="mb-3 p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200">
        <span class="font-semibold">🎙️ Audio transcrito (asr-1.0):</span> "${escapeHtml(data.transcribed_audio)}"
      </div>
    `;
  }

  // Thinking accordion
  let thinkingHtml = "";
  if (data.thinking) {
    thinkingHtml = `
      <details class="mb-4 bg-slate-950/80 border border-slate-800 rounded-xl overflow-hidden text-xs">
        <summary class="px-3.5 py-2 cursor-pointer text-slate-400 hover:text-sky-400 font-medium select-none flex items-center gap-2">
          <span>🧠</span> Ver razonamiento interno del Profesor (${escapeHtml(data.model_used || "MiniMax")})
        </summary>
        <div class="p-3.5 border-t border-slate-800 text-slate-400 whitespace-pre-wrap font-mono text-[11px] leading-relaxed">${escapeHtml(data.thinking)}</div>
      </details>
    `;
  }

  // Plots gallery
  let plotsHtml = "";
  if (data.plots && data.plots.length > 0) {
    const imgs = data.plots
      .map(
        (b64, i) => `
        <div class="bg-white rounded-xl p-2 shadow-md border border-slate-700">
          <img src="${b64}" alt="Gráfica generada ${i + 1}" class="w-full max-h-[420px] object-contain mx-auto rounded-lg" />
        </div>`
      )
      .join("");
    plotsHtml = `
      <div class="mt-4 space-y-3">
        <div class="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
          <span>📊</span> Gráfica Generada por el Profesor (Matplotlib / SymPy)
        </div>
        ${imgs}
      </div>
    `;
  }

  // Scripts accordion
  let scriptsHtml = "";
  if (data.scripts && data.scripts.length > 0) {
    const items = data.scripts
      .map(
        (s, idx) => `
        <div class="space-y-2">
          <div class="text-[11px] text-sky-400 font-semibold"># Script ${idx + 1}: ${escapeHtml(s.description || "Verificación científica")}</div>
          <pre class="bg-slate-950 p-3 rounded-lg border border-slate-800 overflow-x-auto text-xs text-emerald-300"><code>${escapeHtml(s.code)}</code></pre>
          ${
            s.stdout
              ? `<div class="bg-slate-950/90 p-2.5 rounded-lg border border-emerald-500/30 text-xs font-mono text-emerald-200"><span class="text-emerald-400 font-bold">Salida Exacta:</span>\n${escapeHtml(s.stdout)}</div>`
              : ""
          }
          ${
            s.error
              ? `<div class="bg-rose-950/50 p-2.5 rounded-lg border border-rose-500/30 text-xs font-mono text-rose-300">${escapeHtml(s.error)}</div>`
              : ""
          }
        </div>`
      )
      .join('<hr class="border-slate-800 my-3" />');

    scriptsHtml = `
      <details class="mt-4 bg-slate-950/70 border border-slate-800 rounded-xl overflow-hidden text-xs">
        <summary class="px-3.5 py-2.5 cursor-pointer text-emerald-400 hover:text-emerald-300 font-medium select-none flex items-center justify-between">
          <span>🐍 Ver Script Científico Ejecutado (${data.scripts.length})</span>
          <span class="text-[11px] text-slate-500">SymPy • NumPy • Matplotlib</span>
        </summary>
        <div class="p-3.5 border-t border-slate-800 space-y-3">${items}</div>
      </details>
    `;
  }

  const renderedAnswer = renderMarkdownWithMath(data.answer || "");
  const lessonId = addClassroomRecord(data.user_prompt || lastSubmittedPrompt || "2x - 1 = 5", data.answer || "");

  wrapper.innerHTML = `
    <div class="bg-slate-900/95 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-xl">
      <div class="flex items-center justify-between border-b border-slate-800/80 pb-3 mb-3.5 flex-wrap gap-2.5">
        <div class="flex items-center gap-2.5 min-w-0">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center text-sm font-bold shrink-0">∑</div>
          <div class="min-w-0">
            <div class="text-sm font-bold text-white truncate">Profesor MiniMax</div>
            <div class="text-[11px] text-slate-400 truncate">Modelo: ${escapeHtml(data.model_used || "MiniMax")}</div>
          </div>
        </div>
        <div class="flex items-center gap-2 w-full sm:w-auto justify-between sm:justify-end">
          <button id="classroomBtn_${lessonId}" onclick="openClassroomExplanation(${lessonId})"
            class="flex-1 sm:flex-initial justify-center text-xs px-3.5 py-2 sm:py-1.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-white font-semibold shadow-md shadow-amber-500/20 transition flex items-center gap-1.5">
            <span>🎓</span>
            <span>Explicación en Clase (Slides)</span>
          </button>
          <span class="hidden sm:inline-block text-[11px] px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0">
            ✓ Verificado
          </span>
        </div>
      </div>

      ${apiWarningHtml}
      ${transcriptionHtml}
      ${thinkingHtml}
      <div class="prose-math text-sm text-slate-200 leading-relaxed">${renderedAnswer}</div>
      ${plotsHtml}
      ${scriptsHtml}

      <div class="mt-5 pt-4 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="text-xs text-slate-400">
          💡 ¿Quieres entender <strong>cómo se intuye cada paso</strong> con diapositivas interactivas?
        </div>
        <button onclick="openClassroomExplanation(${lessonId})"
          class="w-full sm:w-auto justify-center text-xs px-4 py-2.5 sm:py-2 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/30 font-semibold transition flex items-center gap-2 shrink-0">
          <span>🎓</span>
          <span>Abrir Clase Magistral (Paso a Paso)</span>
        </button>
      </div>
    </div>
  `;

  container.appendChild(wrapper);

  // Render KaTeX equations and highlight code blocks
  if (typeof renderMathInElement === "function") {
    renderMathInElement(wrapper, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\[", right: "\\]", display: true },
        { left: "\\(", right: "\\)", display: false },
      ],
      throwOnError: false,
    });
  }

  if (typeof hljs !== "undefined") {
    wrapper.querySelectorAll("pre code").forEach((block) => {
      hljs.highlightElement(block);
    });
  }

  container.scrollTop = container.scrollHeight;
}

function appendErrorCard(message) {
  const container = document.getElementById("chatContainer");
  const wrapper = document.createElement("div");
  wrapper.className = "max-w-3xl mx-auto";
  wrapper.innerHTML = `
    <div class="bg-rose-950/40 border border-rose-500/40 rounded-2xl p-5 text-xs text-rose-200 space-y-3">
      <div class="font-bold text-sm text-rose-300 flex items-center gap-2">
        <span>⚠️</span> Aviso de Conexión con MiniMax API
      </div>
      <p class="leading-relaxed">${escapeHtml(message)}</p>
      <div class="flex flex-wrap gap-2 pt-1">
        <button onclick="runInteractiveTeacherDemo('2x-1=5')" class="px-3 py-1.5 rounded-lg bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 border border-sky-500/30 font-semibold transition">
          ▶️ Ver Explicación + Gráfica Real en Modo Demo ("2x - 1 = 5")
        </button>
        <button onclick="toggleModal('settingsModal')" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition">
          ⚙️ Cambiar API Key
        </button>
      </div>
    </div>
  `;
  container.appendChild(wrapper);
  container.scrollTop = container.scrollHeight;
}

// --- Main Send Problem Function ---
async function sendProblem() {
  const promptInput = document.getElementById("promptInput");
  const text = promptInput.value.trim();

  if (!text && !attachedImageFile && !attachedAudioBlob) {
    alert("Escribe un problema, sube una foto o graba un audio primero.");
    return;
  }

  const sendBtn = document.getElementById("sendBtn");
  sendBtn.disabled = true;
  sendBtn.innerHTML = `<span>Calculando...</span>`;
  lastSubmittedPrompt = text;

  const imgPreviewUrl = attachedImageFile ? document.getElementById("imagePreviewThumb").src : null;
  appendUserMessage(text, imgPreviewUrl, Boolean(attachedAudioBlob));

  const formData = new FormData();
  formData.append("prompt", text);
  formData.append("history", JSON.stringify(conversationHistory));
  formData.append("model", document.getElementById("modelSelect").value);
  formData.append("reasoning_effort", document.getElementById("effortSelect").value);
  formData.append("api_key", document.getElementById("customApiKey").value || "");
  formData.append("base_url", document.getElementById("customBaseUrl").value || "");

  if (attachedImageFile) {
    formData.append("image", attachedImageFile);
  }
  if (attachedAudioBlob) {
    formData.append("audio", attachedAudioBlob, attachedAudioFilename);
  }

  // Clear inputs
  promptInput.value = "";
  clearImageAttachment();
  clearAudioAttachment();

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minutos máximo

    const res = await fetch("/api/solve", {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    const data = await res.json();

    if (!res.ok) {
      appendErrorCard(data.detail || "Error desconocido al procesar la solicitud.");
    } else {
      data.user_prompt = text;
      appendTeacherResponse(data);
      conversationHistory.push({ role: "user", content: text || "[Problema multimodal]" });
      conversationHistory.push({ role: "assistant", content: data.answer });
    }
  } catch (err) {
    if (err.name === 'AbortError') {
      appendErrorCard("El servidor o MiniMax tardó más de 2 minutos en responder. Se canceló la espera. Por favor intenta de nuevo.");
    } else {
      appendErrorCard("Error al conectar con el servidor: " + err.message);
    }
  } finally {
    sendBtn.disabled = false;
    sendBtn.innerHTML = `<span>Resolver</span><span>➔</span>`;
  }
}

// --- Direct Python Sandbox Execution ---
async function executeDirectSandbox() {
  const code = document.getElementById("directSandboxCode").value;
  const outDiv = document.getElementById("directSandboxOutput");
  outDiv.classList.remove("hidden");
  outDiv.innerHTML = `<div class="text-xs text-slate-400">Ejecutando script en SymPy / Matplotlib...</div>`;

  try {
    const res = await fetch("/api/run-sandbox", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    const data = await res.json();

    let html = "";
    if (data.stdout) {
      html += `<pre class="bg-slate-950 p-3 rounded-xl border border-emerald-500/30 text-xs text-emerald-300 font-mono">${escapeHtml(data.stdout)}</pre>`;
    }
    if (data.error) {
      html += `<pre class="bg-rose-950/50 p-3 rounded-xl border border-rose-500/30 text-xs text-rose-300 font-mono">${escapeHtml(data.error)}</pre>`;
    }
    if (data.plots && data.plots.length > 0) {
      html += data.plots
        .map((p) => `<div class="bg-white p-2 rounded-xl"><img src="${p}" class="max-h-72 mx-auto object-contain" /></div>`)
        .join("");
    }
    outDiv.innerHTML = html || `<div class="text-xs text-slate-400">Script ejecutado sin salida.</div>`;
  } catch (err) {
    outDiv.innerHTML = `<div class="text-xs text-rose-400">Error: ${escapeHtml(err.message)}</div>`;
  }
}

// --- Interactive Teacher Demo (Runs real Python Sandbox on backend!) ---
async function runInteractiveTeacherDemo(demoType) {
  let userPrompt = "";
  let pythonScript = "";
  let teacherExplanation = "";
  let thinkingProcess = "";

  if (demoType === "2x-1=5") {
    userPrompt = "Profesor, ¿cómo resuelvo la ecuación 2x - 1 = 5 paso a paso y cómo se ve su gráfica?";
    thinkingProcess =
      "1. El estudiante plantea la ecuación lineal de primer grado: 2x - 1 = 5.\n" +
      "2. Ejecutaré `run_python_solver` con SymPy para resolver simbólicamente la ecuación y Matplotlib para graficar la recta y = 2x - 1 intersectando con y = 5.\n" +
      "3. Estructuraré la explicación didáctica paso a paso despejando la incógnita x.";
    pythonScript = `import sympy as sp
import numpy as np
import matplotlib.pyplot as plt

x = sp.Symbol('x')
eq = sp.Eq(2*x - 1, 5)
sol = sp.solve(eq, x)[0]
print(f"Solución simbólica con SymPy: x = {sol}")
print(f"Comprobación: 2*({sol}) - 1 = {2*sol - 1}")

x_vals = np.linspace(-1, 5, 200)
y_vals = 2 * x_vals - 1

plt.figure(figsize=(7.5, 4.5))
plt.plot(x_vals, y_vals, label='Función lineal: y = 2x - 1', color='#0284c7', linewidth=2.5)
plt.axhline(5, color='#f59e0b', linestyle='--', linewidth=1.8, label='Valor objetivo: y = 5')
plt.axvline(float(sol), color='#10b981', linestyle=':', linewidth=1.5)
plt.scatter([float(sol)], [5], color='#ef4444', s=100, zorder=5, label=f'Punto solución ({sol}, 5)')
plt.annotate(f'Intersección: x = {sol}', xy=(float(sol), 5), xytext=(float(sol)-1.5, 6.2),
             arrowprops=dict(arrowstyle='->', color='#ef4444', lw=1.5), fontweight='bold')
plt.title('Interpretación Geométrica de 2x - 1 = 5')
plt.xlabel('Eje X')
plt.ylabel('Eje Y')
plt.legend()
plt.grid(True, alpha=0.3)`;

    teacherExplanation = `### 1. Planteamiento del Problema
Queremos encontrar el valor de la incógnita $x$ que hace verdadera la igualdad en la siguiente **ecuación lineal de primer grado**:

$$2x - 1 = 5$$

Nuestro objetivo es **despejar $x$** (dejarla completamente sola de un lado del signo igual) aplicando operaciones inversas en ambos miembros de la ecuación para mantener el equilibrio.

---

### 2. Resolución Paso a Paso

* **Paso 1: Eliminar el término constante ($-1$)**
  Sumamos $1$ en ambos lados de la igualdad para cancelar el $-1$ que acompaña a $2x$:
  $$2x - 1 + 1 = 5 + 1$$
  $$2x = 6$$

* **Paso 2: Despejar el coeficiente ($2$)**
  Como el $2$ está multiplicando a la $x$, dividimos ambos lados de la ecuación entre $2$:
  $$\\frac{2x}{2} = \\frac{6}{2}$$
  $$x = 3$$

* **Paso 3: Comprobación**
  Sustituimos $x = 3$ en la ecuación original para verificar:
  $$2(3) - 1 = 6 - 1 = 5 \\quad \\checkmark$$

---

### 3. Resultado Final e Interpretación Gráfica
* **Resultado Exacto:** $$x = 3$$
* **¿Qué vemos en la gráfica?** Geométricamente, resolver $2x - 1 = 5$ equivale a encontrar el punto donde la recta $y = 2x - 1$ (línea azul) cruza la línea horizontal $y = 5$ (línea naranja punteada). Como observas en la gráfica inferior generada por el motor, ambas rectas se cortan exactamente en las coordenadas **$(3, 5)$**.`;
  } else {
    userPrompt = "Un proyectil se lanza con velocidad inicial v0 = 25 m/s y ángulo de 40°. Calcula su altura máxima, alcance horizontal y grafica su trayectoria.";
    thinkingProcess =
      "1. Problema clásico de cinemática en 2 dimensiones (tiro parabólico sin rozamiento, g = 9.81 m/s²).\n" +
      "2. Usaré NumPy y Matplotlib en el sandbox para calcular v0x, v0y, tiempo de vuelo, altura máxima H y alcance R, graficando la parábola y(x).";
    pythonScript = `import numpy as np
import matplotlib.pyplot as plt

v0 = 25.0          # m/s
theta_deg = 40.0   # grados
g = 9.81           # m/s^2
theta = np.radians(theta_deg)

v0x = v0 * np.cos(theta)
v0y = v0 * np.sin(theta)

t_vuelo = (2 * v0y) / g
h_max = (v0y**2) / (2 * g)
alcance = v0x * t_vuelo
x_hmax = v0x * (t_vuelo / 2)

print(f"v0x = {v0x:.2f} m/s | v0y = {v0y:.2f} m/s")
print(f"Tiempo total de vuelo: T = {t_vuelo:.2f} s")
print(f"Altura máxima: H_max = {h_max:.2f} m (en x = {x_hmax:.2f} m)")
print(f"Alcance horizontal máximo: R = {alcance:.2f} m")

t = np.linspace(0, t_vuelo, 250)
x = v0x * t
y = v0y * t - 0.5 * g * t**2

plt.figure(figsize=(8, 4.5))
plt.plot(x, y, color='#4f46e5', linewidth=2.5, label='Trayectoria del proyectil y(x)')
plt.scatter([x_hmax], [h_max], color='#ef4444', s=90, zorder=5, label=f'Altura Máx ({x_hmax:.1f} m, {h_max:.2f} m)')
plt.scatter([alcance], [0], color='#10b981', s=90, zorder=5, label=f'Impacto R = {alcance:.2f} m')
plt.axhline(0, color='#334155', linewidth=1.2)
plt.title(f'Física: Tiro Parabólico (v0 = {v0} m/s, θ = {theta_deg}°)')
plt.xlabel('Distancia Horizontal x (m)')
plt.ylabel('Altura y (m)')
plt.legend()
plt.grid(True, alpha=0.3)`;

    teacherExplanation = `### 1. Planteamiento Físico (Cinemática en 2D)
En el **movimiento parabólico**, descomponemos la velocidad inicial $\\vec{v}_0$ en dos ejes independientes (con gravedad $g = 9.81\\text{ m/s}^2$):
* **Eje Horizontal ($X$ - MRU):** $$v_{0x} = v_0 \\cos(\\theta) = 25 \\cos(40^\\circ) \\approx 19.15\\text{ m/s}$$
* **Eje Vertical ($Y$ - MRUA):** $$v_{0y} = v_0 \\sin(\\theta) = 25 \\sin(40^\\circ) \\approx 16.07\\text{ m/s}$$

---

### 2. Cálculo Paso a Paso

1. **Tiempo de vuelo ($T$):** En el punto más alto $v_y = 0$, por lo que el tiempo en subir es $t_{\\text{subida}} = \\frac{v_{0y}}{g}$ y el tiempo total es el doble:
   $$T = \\frac{2 v_{0y}}{g} = \\frac{2(16.07)}{9.81} \\approx 3.28\\text{ s}$$

2. **Altura máxima ($H_{\\max}$):**
   $$H_{\\max} = \\frac{v_{0y}^2}{2g} = \\frac{(16.07)^2}{2(9.81)} \\approx 13.16\\text{ m}$$

3. **Alcance horizontal ($R$):**
   $$R = v_{0x} \\cdot T = 19.15 \\times 3.28 \\approx 62.75\\text{ m}$$`;
  }

  appendUserMessage(userPrompt, null, false);

  const res = await fetch("/api/run-sandbox", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code: pythonScript }),
  });
  const sandboxResult = await res.json();
  sandboxResult.description = "Script ejecutado en tiempo real por el Sandbox Python";

  appendTeacherResponse({
    user_prompt: userPrompt,
    answer: teacherExplanation,
    thinking: thinkingProcess,
    transcribed_audio: "",
    scripts: [sandboxResult],
    plots: sandboxResult.plots || [],
    model_used: "MiniMax-M3.1-Flash + Python Sandbox",
  });
}

// --- Interactive Classroom Slide Deck ("Ver Explicación en Clase") ---
async function openClassroomExplanation(recordId) {
  const record = classroomRecords[recordId];
  if (!record) return;

  const modal = document.getElementById("classroomModal");
  const container = document.getElementById("classroomSlideContainer");
  const stepper = document.getElementById("classroomStepper");

  modal.classList.remove("hidden");

  if (record.cachedDeck) {
    activeClassroomDeck = record.cachedDeck;
    activeSlideIndex = 0;
    renderCurrentClassroomSlide();
    return;
  }

  // Show loading state while MiniMax / SymPy prepares the slides and per-slide plots
  document.getElementById("classroomCourseTitle").textContent = "Preparando tu Clase Magistral Interactiva...";
  document.getElementById("classroomCourseSubtitle").textContent =
    "El Profesor está diseñando las diapositivas de intuición y generando las gráficas paso a paso con Python";
  stepper.innerHTML = "";
  container.innerHTML = `
    <div class="h-full flex flex-col items-center justify-center text-center py-16 space-y-4">
      <div class="w-16 h-16 rounded-2xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-3xl animate-pulse">
        🎓
      </div>
      <div class="text-base font-bold text-white">Construyendo Diapositivas Didácticas y Gráficas...</div>
      <p class="text-xs text-slate-400 max-w-md leading-relaxed">
        Dividiendo el problema en intuición visual, estrategia matemática, desarrollo paso a paso y verificación gráfica con SymPy + Matplotlib.
      </p>
    </div>
  `;

  try {
    const res = await fetch("/api/classroom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: record.prompt,
        answer: record.answer,
        model: document.getElementById("modelSelect").value,
        api_key: document.getElementById("customApiKey").value || "",
        base_url: document.getElementById("customBaseUrl").value || "",
      }),
    });
    const deck = await res.json();
    record.cachedDeck = deck;
    activeClassroomDeck = deck;
    activeSlideIndex = 0;
    renderCurrentClassroomSlide();
  } catch (err) {
    container.innerHTML = `<div class="p-6 text-rose-400 text-sm">Error al generar la clase: ${escapeHtml(err.message)}</div>`;
  }
}

function closeClassroomModal() {
  document.getElementById("classroomModal").classList.add("hidden");
}

function goToClassroomSlide(idx) {
  if (!activeClassroomDeck || !activeClassroomDeck.slides) return;
  if (idx < 0 || idx >= activeClassroomDeck.slides.length) return;
  activeSlideIndex = idx;
  renderCurrentClassroomSlide();
}

function changeClassroomSlide(delta) {
  goToClassroomSlide(activeSlideIndex + delta);
}

function renderCurrentClassroomSlide() {
  if (!activeClassroomDeck || !activeClassroomDeck.slides) return;
  const slides = activeClassroomDeck.slides;
  const slide = slides[activeSlideIndex];

  document.getElementById("classroomCourseTitle").textContent = activeClassroomDeck.course_title || "Clase Magistral Interactiva";
  document.getElementById("classroomCourseSubtitle").textContent = activeClassroomDeck.subtitle || "";
  document.getElementById("classroomModelBadge").textContent = activeClassroomDeck.model_used || "Modo Aula";

  // Render stepper pills
  const stepper = document.getElementById("classroomStepper");
  stepper.innerHTML = slides
    .map((s, idx) => {
      const active = idx === activeSlideIndex;
      const cls = active
        ? "bg-amber-500 text-slate-950 font-bold shadow-md shadow-amber-500/20"
        : "bg-slate-800/90 text-slate-400 hover:bg-slate-800 hover:text-slate-200";
      return `
        <button onclick="goToClassroomSlide(${idx})"
          class="px-3.5 py-1.5 rounded-xl text-xs transition shrink-0 flex items-center gap-1.5 ${cls}">
          <span>${idx + 1}.</span>
          <span>${escapeHtml(s.badge || s.title || "Paso " + (idx + 1))}</span>
        </button>
      `;
    })
    .join("");

  // Key formula box
  let formulaBoxHtml = "";
  if (slide.key_formula) {
    formulaBoxHtml = `
      <div class="p-4 rounded-2xl bg-slate-950/90 border border-sky-500/30 shadow-inner">
        <div class="text-[11px] font-semibold uppercase tracking-wider text-sky-400 mb-1">📌 Fórmula / Concepto Clave del Paso</div>
        <div class="text-base text-white overflow-x-auto">$$${slide.key_formula}$$</div>
      </div>
    `;
  }

  // Mini interactive check box
  let miniCheckHtml = "";
  if (slide.mini_check && slide.mini_check.question) {
    miniCheckHtml = `
      <details class="group bg-emerald-950/25 border border-emerald-500/30 rounded-2xl p-4 text-xs transition">
        <summary class="cursor-pointer font-semibold text-emerald-300 flex items-center justify-between select-none">
          <span>🤔 Pregunta de Intuición: ${escapeHtml(slide.mini_check.question)}</span>
          <span class="text-[11px] px-2.5 py-0.5 rounded-lg bg-emerald-500/20 text-emerald-300 group-open:hidden">Ver Respuesta</span>
        </summary>
        <div class="mt-3 pt-3 border-t border-emerald-500/20 text-slate-200 leading-relaxed">
          <strong class="text-emerald-400">Respuesta del Profesor:</strong> ${escapeHtml(slide.mini_check.answer || "")}
        </div>
      </details>
    `;
  }

  // Right column: Visual Plot or Blackboard Summary
  let visualColumnHtml = "";
  if (slide.plots && slide.plots.length > 0) {
    const plotImgs = slide.plots
      .map(
        (b64) => `
        <div class="bg-white rounded-2xl p-3 shadow-xl border border-slate-700">
          <img src="${b64}" class="w-full max-h-[360px] object-contain mx-auto rounded-lg" />
        </div>`
      )
      .join("");

    const codeToggle = slide.python_plot_code
      ? `<details class="text-xs bg-slate-950/80 border border-slate-800 rounded-xl overflow-hidden">
           <summary class="px-3 py-2 cursor-pointer text-slate-400 hover:text-emerald-400 font-mono text-[11px]">🐍 Ver script de esta diapositiva</summary>
           <pre class="p-3 text-[11px] text-emerald-300 overflow-x-auto"><code>${escapeHtml(slide.python_plot_code)}</code></pre>
         </details>`
      : "";

    visualColumnHtml = `
      <div class="space-y-3">
        <div class="text-xs font-semibold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
          <span>📊</span> Pizarrón Gráfico — Diapositiva ${activeSlideIndex + 1}
        </div>
        ${plotImgs}
        ${codeToggle}
      </div>
    `;
  } else {
    visualColumnHtml = `
      <div class="h-full flex flex-col justify-center p-6 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-4">
        <div class="text-xs font-semibold uppercase tracking-wider text-amber-400">💡 Resumen de Pizarrón</div>
        <div class="text-sm text-slate-300 leading-relaxed">${escapeHtml(slide.intuition_callout || "")}</div>
        ${formulaBoxHtml}
      </div>
    `;
  }

  const hasPlots = slide.plots && slide.plots.length > 0;
  const renderedContent = renderMarkdownWithMath(slide.content_markdown || "");

  const container = document.getElementById("classroomSlideContainer");
  container.innerHTML = `
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6 items-start">
      <!-- Left Pedagogical Column -->
      <div class="lg:col-span-7 space-y-3.5 sm:space-y-4 min-w-0">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs font-semibold">
          <span>Paso ${activeSlideIndex + 1} de ${slides.length}</span>
          <span>•</span>
          <span class="truncate">${escapeHtml(slide.badge || "Explicación Guiada")}</span>
        </div>

        <h2 class="text-lg sm:text-xl md:text-2xl font-bold text-white leading-snug">${escapeHtml(slide.title || "")}</h2>

        ${
          slide.intuition_callout
            ? `<div class="p-3.5 sm:p-4 rounded-2xl bg-gradient-to-r from-amber-500/15 to-orange-500/10 border-l-4 border-amber-400 text-xs sm:text-sm text-amber-100 leading-relaxed">
                 <strong class="text-amber-300 block text-xs uppercase tracking-wider mb-1">💡 ¿Cómo intuirlo?</strong>
                 ${escapeHtml(slide.intuition_callout)}
               </div>`
            : ""
        }

        <div class="prose-math text-sm text-slate-200 leading-relaxed bg-slate-950/50 border border-slate-800/80 rounded-2xl p-3.5 sm:p-5">
          ${renderedContent}
        </div>

        ${hasPlots ? formulaBoxHtml : ""}
        ${miniCheckHtml}
      </div>

      <!-- Right Visual Column -->
      <div class="lg:col-span-5 lg:sticky lg:top-2 min-w-0">
        ${visualColumnHtml}
      </div>
    </div>
  `;

  container.scrollTop = 0;

  if (typeof renderMathInElement === "function") {
    renderMathInElement(container, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\[", right: "\\]", display: true },
        { left: "\\(", right: "\\)", display: false },
      ],
      throwOnError: false,
    });
  }

  // Update footer navigation buttons
  document.getElementById("slideCounterText").textContent = `${activeSlideIndex + 1} / ${slides.length}`;
  document.getElementById("prevSlideBtn").disabled = activeSlideIndex === 0;
  document.getElementById("nextSlideBtn").disabled = activeSlideIndex === slides.length - 1;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ============================================================================
// ACADEMY COURSE: 30-DAY CALENDAR & AI MASTERCLASS ENGINE
// ============================================================================
let academyCurriculumData = null;
let activeModuleFilter = 0; // 0 = all modules
let cachedAcademyLessons = {};
let currentAcademyDay = 1;

function getCompletedDays() {
  try {
    const raw = localStorage.getItem("minimax_academy_completed_days");
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function saveCompletedDays(daysArr) {
  localStorage.setItem("minimax_academy_completed_days", JSON.stringify(daysArr));
}

function toggleDayComplete(dayNumber) {
  const completed = getCompletedDays();
  const idx = completed.indexOf(dayNumber);
  if (idx === -1) {
    completed.push(dayNumber);
  } else {
    completed.splice(idx, 1);
  }
  saveCompletedDays(completed);
  updateAcademyProgressUI();

  const btn = document.getElementById("markDayCompleteBtn");
  if (btn) {
    const isDone = completed.includes(dayNumber);
    btn.className = isDone
      ? "px-4 py-2 rounded-xl bg-emerald-600 text-white text-xs font-bold shadow-md transition flex items-center gap-1.5"
      : "px-4 py-2 rounded-xl bg-slate-800 hover:bg-emerald-600/80 text-slate-200 hover:text-white border border-slate-700 text-xs font-bold transition flex items-center gap-1.5";
    btn.innerHTML = isDone ? `<span>✓</span><span>Día ${dayNumber} Completado</span>` : `<span>○</span><span>Marcar Día ${dayNumber} como Completado</span>`;
  }
}

async function openAcademyModal() {
  const modal = document.getElementById("academyModal");
  modal.classList.remove("hidden");
  showAcademyCalendarView();

  if (!academyCurriculumData) {
    try {
      const res = await fetch("/api/academy/curriculum");
      academyCurriculumData = await res.json();
    } catch (e) {
      console.error("Error loading curriculum:", e);
      return;
    }
  }
  renderAcademyCalendar(activeModuleFilter);
}

function closeAcademyModal() {
  document.getElementById("academyModal").classList.add("hidden");
}

function showAcademyCalendarView() {
  document.getElementById("academyCalendarView").classList.remove("hidden");
  document.getElementById("academyLessonView").classList.add("hidden");
  document.getElementById("backToCalendarBtn").classList.add("hidden");
  document.getElementById("academyHeaderTitle").textContent = "Academia de Ingeniería: Calendario de 30 Días";
  document.getElementById("academyHeaderSubtitle").textContent =
    "De cero absoluto en matemáticas hasta ecuaciones diferenciales y control en ingeniería";
  if (academyCurriculumData) {
    renderAcademyCalendar(activeModuleFilter);
  }
}

function updateAcademyProgressUI() {
  if (!academyCurriculumData) return;
  const completed = getCompletedDays();
  const total = academyCurriculumData.total_days || 30;
  const count = completed.length;
  const pct = Math.min(100, Math.round((count / total) * 100));

  const badge = document.getElementById("academyProgressBadge");
  if (badge) badge.textContent = `${count} / ${total} Completados (${pct}%)`;

  const mobText = document.getElementById("mobileProgressText");
  if (mobText) mobText.textContent = `${count} / ${total} días (${pct}%)`;

  const bar = document.getElementById("academyProgressBar");
  if (bar) bar.style.width = `${pct}%`;

  // Find next unfinished day
  let nextDayObj = null;
  for (const mod of academyCurriculumData.modules) {
    for (const d of mod.days) {
      if (!completed.includes(d.day)) {
        nextDayObj = d;
        break;
      }
    }
    if (nextDayObj) break;
  }
  if (!nextDayObj && academyCurriculumData.modules.length > 0) {
    nextDayObj = academyCurriculumData.modules[0].days[0];
  }

  if (nextDayObj) {
    const titleEl = document.getElementById("nextRecommendedTitle");
    if (titleEl) {
      titleEl.textContent = `Día ${nextDayObj.day}: ${nextDayObj.title}`;
    }
    const btnText = document.getElementById("startNextDayBtnText");
    if (btnText) {
      btnText.textContent = `Iniciar Clase del Día ${nextDayObj.day}`;
    }
  }
}

function openNextUnfinishedDay() {
  if (!academyCurriculumData) return;
  const completed = getCompletedDays();
  for (const mod of academyCurriculumData.modules) {
    for (const d of mod.days) {
      if (!completed.includes(d.day)) {
        openAcademyDayLesson(d.day);
        return;
      }
    }
  }
  openAcademyDayLesson(1);
}

function renderAcademyCalendar(filterModId = 0) {
  activeModuleFilter = filterModId;
  if (!academyCurriculumData) return;

  updateAcademyProgressUI();
  const completed = getCompletedDays();

  // Render filter tabs
  const filterBar = document.getElementById("moduleFilterBar");
  const allActive = filterModId === 0;
  let tabsHtml = `
    <button onclick="renderAcademyCalendar(0)"
      class="px-3.5 py-2 rounded-xl text-xs font-bold shrink-0 transition ${
        allActive
          ? "bg-amber-500 text-slate-950 shadow-md"
          : "bg-slate-900 text-slate-300 border border-slate-800 hover:bg-slate-800"
      }">
      🗓️ Todas las Fases (30 Días)
    </button>
  `;
  for (const mod of academyCurriculumData.modules) {
    const isAct = filterModId === mod.module_id;
    tabsHtml += `
      <button onclick="renderAcademyCalendar(${mod.module_id})"
        class="px-3.5 py-2 rounded-xl text-xs font-semibold shrink-0 transition ${
          isAct
            ? "bg-sky-500 text-slate-950 font-bold shadow-md"
            : "bg-slate-900 text-slate-300 border border-slate-800 hover:bg-slate-800"
        }">
        Fase ${mod.module_id}: ${escapeHtml(mod.module_badge.split("•")[1] || mod.module_badge)}
      </button>
    `;
  }
  filterBar.innerHTML = tabsHtml;

  // Render module sections and day cards
  const container = document.getElementById("curriculumModulesContainer");
  const modulesToRender =
    filterModId === 0
      ? academyCurriculumData.modules
      : academyCurriculumData.modules.filter((m) => m.module_id === filterModId);

  container.innerHTML = modulesToRender
    .map((mod) => {
      const daysCards = mod.days
        .map((d) => {
          const isDone = completed.includes(d.day);
          const statusBadge = isDone
            ? `<span class="text-[11px] px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold">✓ Completado</span>`
            : `<span class="text-[11px] px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700 font-medium">Pendiente</span>`;

          return `
            <div onclick="openAcademyDayLesson(${d.day})"
              class="cursor-pointer group bg-slate-900 hover:bg-slate-800/90 border ${
                isDone ? "border-emerald-500/40" : "border-slate-800 hover:border-amber-500/50"
              } rounded-2xl p-4 sm:p-5 transition flex flex-col justify-between gap-3 shadow-lg">
              <div class="space-y-2.5">
                <div class="flex items-center justify-between gap-2">
                  <span class="px-2.5 py-1 rounded-lg bg-amber-500/15 text-amber-300 border border-amber-500/30 text-xs font-bold">
                    Día ${d.day}
                  </span>
                  ${statusBadge}
                </div>

                <h4 class="font-bold text-sm sm:text-base text-white group-hover:text-amber-300 transition leading-snug">
                  ${escapeHtml(d.title)}
                </h4>

                <p class="text-xs text-slate-400 leading-relaxed">
                  ${escapeHtml(d.subtitle)}
                </p>

                <div class="p-2.5 rounded-xl bg-slate-950 border border-slate-800/90 text-xs text-sky-300 overflow-x-auto">
                  $$${d.formula_preview}$$
                </div>
              </div>

              <div class="space-y-2.5 pt-2 border-t border-slate-800/80">
                <div class="text-[11px] text-slate-400">
                  <strong class="text-emerald-400">⚙️ Ingeniería:</strong> ${escapeHtml(d.engineering_link)}
                </div>

                <div class="w-full py-2 px-3 rounded-xl bg-slate-800 group-hover:bg-gradient-to-r group-hover:from-amber-500 group-hover:to-orange-600 text-slate-200 group-hover:text-white text-xs font-bold text-center transition flex items-center justify-center gap-1.5">
                  <span>🎓 Entrar a la Clase del Día ${d.day}</span>
                  <span>➔</span>
                </div>
              </div>
            </div>
          `;
        })
        .join("");

      return `
        <div class="space-y-3.5">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-slate-800 pb-2.5">
            <div>
              <span class="text-[11px] font-bold uppercase tracking-wider text-sky-400">${escapeHtml(mod.module_badge)}</span>
              <h3 class="text-base sm:text-lg font-bold text-white">${escapeHtml(mod.module_title)}</h3>
            </div>
            <p class="text-xs text-slate-400 max-w-xl">${escapeHtml(mod.description)}</p>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5 sm:gap-4">
            ${daysCards}
          </div>
        </div>
      `;
    })
    .join("");

  if (typeof renderMathInElement === "function") {
    renderMathInElement(container, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
      ],
      throwOnError: false,
    });
  }
}

async function openAcademyDayLesson(dayNumber) {
  currentAcademyDay = dayNumber;
  document.getElementById("academyCalendarView").classList.add("hidden");
  const lessonView = document.getElementById("academyLessonView");
  const contentEl = document.getElementById("academyLessonContent");
  lessonView.classList.remove("hidden");
  document.getElementById("backToCalendarBtn").classList.remove("hidden");

  document.getElementById("academyHeaderTitle").textContent = `Clase Magistral — Día ${dayNumber} de 30`;
  lessonView.scrollTop = 0;

  if (cachedAcademyLessons[dayNumber]) {
    renderAcademyDayLesson(cachedAcademyLessons[dayNumber]);
    return;
  }

  contentEl.innerHTML = `
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-8 sm:p-12 text-center space-y-4 my-6 shadow-xl">
      <div class="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-amber-500/20 to-orange-600/20 border border-amber-500/40 flex items-center justify-center text-3xl animate-pulse">
        🧠
      </div>
      <h3 class="text-base sm:text-xl font-bold text-white">
        El Profesor MiniMax está preparando tu Clase del Día ${dayNumber}...
      </h3>
      <p class="text-xs sm:text-sm text-slate-400 max-w-lg mx-auto leading-relaxed">
        Redactando la explicación con tips mentales, construyendo la <strong>demostración matemática paso a paso</strong>, ejecutando el script científico en <strong>SymPy + Matplotlib</strong> y generando la ilustración conceptual con <strong>MiniMax Image-01</strong>.
      </p>
    </div>
  `;

  try {
    const res = await fetch("/api/academy/lesson", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        day: dayNumber,
        model: document.getElementById("modelSelect") ? document.getElementById("modelSelect").value : "MiniMax-M3.1-Flash",
        api_key: document.getElementById("customApiKey") ? document.getElementById("customApiKey").value : "",
        base_url: document.getElementById("customBaseUrl") ? document.getElementById("customBaseUrl").value : "",
        generate_ai_image: false,
      }),
    });
    const rawText = await res.text();
    if (!res.ok || !rawText) {
      throw new Error(`El servidor respondió con estado ${res.status}. Por favor intenta de nuevo.`);
    }
    const lesson = JSON.parse(rawText);
    cachedAcademyLessons[dayNumber] = lesson;
    renderAcademyDayLesson(lesson);

    // Trigger MiniMax image-01 asynchronously in background without blocking the lesson!
    setTimeout(() => {
      if (currentAcademyDay === dayNumber) {
        regenerateConceptImage(dayNumber);
      }
    }, 150);
  } catch (err) {
    contentEl.innerHTML = `
      <div class="bg-rose-950/40 border border-rose-500/40 rounded-2xl p-6 text-xs text-rose-200 space-y-3">
        <div class="font-bold text-sm">Error al cargar la clase del Día ${dayNumber}</div>
        <p>${escapeHtml(err.message)}</p>
        <button onclick="openAcademyDayLesson(${dayNumber})" class="px-4 py-2 rounded-xl bg-sky-600 text-white font-semibold">Reintentar</button>
      </div>
    `;
  }
}

function renderAcademyDayLesson(lesson) {
  const contentEl = document.getElementById("academyLessonContent");
  const day = lesson.day || currentAcademyDay;
  const completed = getCompletedDays();
  const isDone = completed.includes(day);

  document.getElementById("academyHeaderTitle").textContent = `Día ${day}: ${lesson.title || ""}`;
  document.getElementById("academyHeaderSubtitle").textContent = lesson.module_title || "";

  // 1. Mental Tips Cards
  const tipsHtml = (lesson.mental_tips || [])
    .map(
      (tip, i) => `
      <div class="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-2.5">
        <span class="text-amber-400 font-bold text-sm shrink-0">💡 Tip ${i + 1}:</span>
        <span class="text-xs sm:text-sm text-amber-100 leading-relaxed">${renderMarkdownWithMath(tip)}</span>
      </div>
    `
    )
    .join("");

  // 2. Mathematical Proof ("¿De dónde sale la fórmula?")
  const proof = lesson.mathematical_proof || {};
  const proofHtml = `
    <div class="bg-slate-900 border-2 border-indigo-500/40 rounded-2xl p-4 sm:p-6 shadow-xl space-y-3">
      <div class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-indigo-400">
        <span>🏛️</span>
        <span>Demostración Matemática (Para que tu cerebro entienda el origen)</span>
      </div>
      <h3 class="text-base sm:text-lg font-bold text-white">${renderMarkdownWithMath(proof.title || "¿De dónde sale esta fórmula?")}</h3>
      ${
        proof.intuition
          ? `<div class="p-3 rounded-xl bg-indigo-950/50 border border-indigo-500/30 text-xs sm:text-sm text-indigo-200">
               <strong>Intuición clave:</strong> ${escapeHtml(proof.intuition)}
             </div>`
          : ""
      }
      <div class="prose-math text-xs sm:text-sm text-slate-200 leading-relaxed bg-slate-950/80 border border-slate-800 rounded-xl p-4">
        ${renderMarkdownWithMath(proof.steps_markdown || "")}
      </div>
    </div>
  `;

  // 3. Dual Visual Lab: Matplotlib Scientific Plot + MiniMax Image-01 Concept Illustration
  const plots = lesson.plots || [];
  const plotImgHtml =
    plots.length > 0
      ? plots
          .map(
            (b64) => `
          <div class="bg-white rounded-xl p-2 shadow-md border border-slate-700">
            <img src="${b64}" class="w-full max-h-[360px] object-contain mx-auto rounded-lg" />
          </div>
        `
          )
          .join("")
      : `<div class="text-xs text-slate-400 p-4">Sin gráfica adicional.</div>`;

  const conceptImgUrl = lesson.concept_image || "";
  const conceptImgSource = lesson.concept_image_source || "MiniMax image-01";
  const defaultImgPrompt =
    lesson.image_prompt ||
    `Educational 3D scientific diagram of ${lesson.title}, glowing geometric labels, dark slate background`;

  // 4. Worked Examples
  const examplesHtml = (lesson.worked_examples || [])
    .map(
      (ex, i) => `
      <div class="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 sm:p-5 space-y-2.5">
        <div class="text-xs font-bold uppercase tracking-wider text-sky-400">
          📘 ${escapeHtml(ex.title || `Ejemplo Resuelto ${i + 1}`)}
        </div>
        <div class="text-xs sm:text-sm font-semibold text-white bg-slate-900 p-3 rounded-xl border border-slate-800">
          ${renderMarkdownWithMath(ex.problem || "")}
        </div>
        <div class="prose-math text-xs sm:text-sm text-slate-300 leading-relaxed pt-1">
          ${renderMarkdownWithMath(ex.step_by_step || "")}
        </div>
        ${
          ex.final_result
            ? `<div class="p-2.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-xs sm:text-sm text-emerald-300 font-semibold">
                 ✓ Resultado: ${renderMarkdownWithMath(ex.final_result)}
               </div>`
            : ""
        }
      </div>
    `
    )
    .join("");

  // 5. Common Mistakes
  const mistakesHtml = (lesson.common_mistakes || [])
    .map(
      (m) => `
      <li class="text-xs sm:text-sm text-rose-200 leading-relaxed">${renderMarkdownWithMath(m)}</li>
    `
    )
    .join("");

  // 6. Graduated Exercises (with Hint, Step-by-Step Solution, and "Practice on Board" button)
  const exercisesHtml = (lesson.exercises || [])
    .map((ex, i) => {
      const safePractice = escapeHtml(ex.practice_prompt || ex.question || "");
      return `
        <div class="bg-slate-950 border border-slate-800 rounded-2xl p-4 sm:p-5 space-y-3">
          <div class="flex items-center justify-between gap-2 flex-wrap">
            <span class="px-2.5 py-1 rounded-lg bg-purple-500/15 text-purple-300 border border-purple-500/30 text-xs font-bold">
              🏋️ ${escapeHtml(ex.level || `Ejercicio ${i + 1}`)}
            </span>
            <button onclick="practiceExerciseInBoard('${safePractice.replace(/'/g, "\\'")}')"
              class="text-xs px-3 py-1.5 rounded-xl bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 border border-sky-500/30 font-semibold transition">
              🧑‍🏫 Resolver en el Pizarrón con IA
            </button>
          </div>

          <div class="prose-math text-xs sm:text-sm text-white font-medium leading-relaxed">
            ${renderMarkdownWithMath(ex.question || "")}
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
            <details class="bg-slate-900 border border-amber-500/30 rounded-xl p-3 text-xs">
              <summary class="cursor-pointer font-semibold text-amber-300 select-none">💡 Ver Pista (Hint)</summary>
              <div class="mt-2 pt-2 border-t border-slate-800 text-slate-300 leading-relaxed">
                ${renderMarkdownWithMath(ex.hint || "")}
              </div>
            </details>

            <details class="bg-slate-900 border border-emerald-500/30 rounded-xl p-3 text-xs">
              <summary class="cursor-pointer font-semibold text-emerald-300 select-none">✅ Ver Solución Paso a Paso</summary>
              <div class="mt-2 pt-2 border-t border-slate-800 text-slate-200 leading-relaxed">
                ${renderMarkdownWithMath(ex.solution || "")}
              </div>
            </details>
          </div>
        </div>
      `;
    })
    .join("");

  contentEl.innerHTML = `
    <div class="space-y-6">
      <!-- Top Lesson Banner -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-xl space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-bold">
              Día ${day} de 30
            </span>
            <span class="text-xs text-slate-400">• ⏱️ ${escapeHtml(lesson.estimated_time || "25 min")}</span>
            <span class="text-xs text-sky-400">• ${escapeHtml(lesson.model_used || "MiniMax")}</span>
          </div>

          <button id="markDayCompleteBtn" onclick="toggleDayComplete(${day})"
            class="${
              isDone
                ? "px-4 py-2 rounded-xl bg-emerald-600 text-white text-xs font-bold shadow-md transition flex items-center gap-1.5"
                : "px-4 py-2 rounded-xl bg-slate-800 hover:bg-emerald-600/80 text-slate-200 hover:text-white border border-slate-700 text-xs font-bold transition flex items-center gap-1.5"
            }">
            <span>${isDone ? "✓" : "○"}</span>
            <span>${isDone ? `Día ${day} Completado` : `Marcar Día ${day} como Completado`}</span>
          </button>
        </div>

        <div>
          <h1 class="text-lg sm:text-2xl font-bold text-white leading-snug">${escapeHtml(lesson.title || "")}</h1>
          <p class="text-xs sm:text-sm text-slate-400 mt-1">${escapeHtml(lesson.subtitle || "")}</p>
        </div>

        <div class="p-3.5 rounded-xl bg-sky-950/40 border border-sky-500/30 text-xs sm:text-sm text-sky-100 leading-relaxed">
          <strong class="text-sky-400 block text-xs uppercase tracking-wider mb-1">⚙️ ¿Por qué es vital en Ingeniería y Ciencias?</strong>
          ${renderMarkdownWithMath(lesson.why_it_matters || "")}
        </div>
      </div>

      <!-- Detailed Explanation + Mental Tips -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-xl space-y-4">
        <div class="flex items-center justify-between gap-2 flex-wrap">
          <div class="text-xs font-bold uppercase tracking-wider text-sky-400 flex items-center gap-1.5">
            <span>📖</span>
            <span>1. Explicación Detallada y Conceptos Clave</span>
          </div>
          <button id="deepDiveBtn" onclick="loadLiveDeepDive(${day})"
            class="text-xs px-3 py-1.5 rounded-xl bg-sky-500/15 hover:bg-sky-500/25 text-sky-300 border border-sky-500/30 font-semibold transition flex items-center gap-1.5">
            <span>✨</span>
            <span>Ampliar Clase en Vivo con MiniMax IA</span>
          </button>
        </div>
        <div class="prose-math text-xs sm:text-sm text-slate-200 leading-relaxed">
          ${renderMarkdownWithMath(lesson.detailed_explanation || "")}
        </div>
        <div id="liveDeepDiveContainer" class="hidden p-4 rounded-2xl bg-slate-950 border border-sky-500/40 space-y-2"></div>

        <div class="space-y-2.5 pt-2">
          <div class="text-xs font-bold uppercase tracking-wider text-amber-400">
            🧠 Tips Mentales y Trucos de Experto para Recordar Siempre
          </div>
          ${tipsHtml}
        </div>
      </div>

      <!-- Mathematical Proof Section -->
      ${proofHtml}

      <!-- Dual Visual Lab: Matplotlib Scientific Graph + MiniMax image-01 AI Illustration -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        <!-- Left: Exact Matplotlib Graph -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-xl space-y-3 flex flex-col justify-between">
          <div class="space-y-3">
            <div class="flex items-center justify-between gap-2">
              <span class="text-xs font-bold uppercase tracking-wider text-emerald-400">
                📊 Gráfica Científica Exacta (SymPy + Matplotlib)
              </span>
            </div>
            ${plotImgHtml}
          </div>

          ${
            lesson.python_plot_code
              ? `<details class="bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs mt-2">
                   <summary class="cursor-pointer text-slate-400 hover:text-emerald-300 font-mono text-[11px]">🐍 Ver código Python que generó esta gráfica</summary>
                   <pre class="mt-2 text-[11px] text-emerald-300 overflow-x-auto"><code>${escapeHtml(lesson.python_plot_code)}</code></pre>
                 </details>`
              : ""
          }
        </div>

        <!-- Right: MiniMax image-01 AI Concept Illustration -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-xl space-y-3 flex flex-col justify-between">
          <div class="space-y-3">
            <div class="flex items-center justify-between gap-2 flex-wrap">
              <span class="text-xs font-bold uppercase tracking-wider text-amber-400">
                🎨 Ilustración Conceptual (${escapeHtml(conceptImgSource)})
              </span>
            </div>

            <div id="conceptImageContainer" class="bg-slate-950 rounded-xl p-2 border border-slate-800 flex items-center justify-center min-h-[220px]">
              ${
                conceptImgUrl
                  ? `<img id="conceptImageEl" src="${conceptImgUrl}" alt="Ilustración Conceptual" class="w-full max-h-[340px] object-contain rounded-lg" />`
                  : `<div class="text-xs text-slate-400">Genera una ilustración visual con MiniMax image-01</div>`
              }
            </div>
          </div>

          <!-- Custom MiniMax image-01 Prompt Box -->
          <div class="space-y-2 pt-2 border-t border-slate-800">
            <label class="block text-[11px] text-slate-400">
              ¿Quieres visualizar otra escena de este tema con el modelo <strong class="text-amber-300">MiniMax image-01</strong>?
            </label>
            <div class="flex gap-2">
              <input id="customImagePromptInput" type="text" value="${escapeHtml(defaultImgPrompt)}"
                class="flex-1 rounded-xl bg-slate-950 border border-slate-700 px-3 py-2 text-xs text-white focus:border-amber-500 focus:outline-none" />
              <button id="regenImageBtn" onclick="regenerateConceptImage(${day})"
                class="px-3.5 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-white text-xs font-bold shrink-0 transition">
                🎨 Generar IA
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Worked Examples -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-xl space-y-4">
        <div class="text-xs font-bold uppercase tracking-wider text-sky-400">
          ✏️ 2. Ejemplos Resueltos Paso a Paso
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          ${examplesHtml}
        </div>

        ${
          mistakesHtml
            ? `<div class="p-4 rounded-2xl bg-rose-950/30 border border-rose-500/30 space-y-2 mt-4">
                 <div class="text-xs font-bold uppercase tracking-wider text-rose-400">
                   ⚠️ Errores Típicos en Exámenes (¡Evítalos!)
                 </div>
                 <ul class="list-disc ml-5 space-y-1">
                   ${mistakesHtml}
                 </ul>
               </div>`
            : ""
        }
      </div>

      <!-- Graduated Exercises -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-xl space-y-4">
        <div>
          <div class="text-xs font-bold uppercase tracking-wider text-purple-400">
            🏋️ 3. Laboratorio de Ejercicios Graduados (Con Pistas y Solución)
          </div>
          <p class="text-xs text-slate-400 mt-0.5">
            Intenta resolverlos primero en papel. Si te atascas, abre la pista o llévalo al pizarrón interactivo.
          </p>
        </div>
        <div class="space-y-3.5">
          ${exercisesHtml}
        </div>
      </div>

      <!-- Bottom Day Navigation Bar -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-3 shadow-xl">
        <button onclick="${day > 1 ? `openAcademyDayLesson(${day - 1})` : "showAcademyCalendarView()"}"
          class="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition">
          ${day > 1 ? `← Ir al Día ${day - 1}` : "← Volver al Calendario"}
        </button>

        <button onclick="completeAndAdvanceDay(${day})"
          class="w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-sky-600 hover:from-emerald-400 hover:to-sky-500 text-white text-xs sm:text-sm font-bold shadow-lg transition flex items-center justify-center gap-2">
          <span>✓ Completar Día ${day} y Avanzar al Día ${day < 30 ? day + 1 : 1}</span>
          <span>➔</span>
        </button>
      </div>
    </div>
  `;

  if (typeof renderMathInElement === "function") {
    renderMathInElement(contentEl, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\[", right: "\\]", display: true },
        { left: "\\(", right: "\\)", display: false },
      ],
      throwOnError: false,
    });
  }
}

async function regenerateConceptImage(dayNumber) {
  const input = document.getElementById("customImagePromptInput");
  const btn = document.getElementById("regenImageBtn");
  const container = document.getElementById("conceptImageContainer");
  if (!input || !container) return;

  const prompt = input.value.trim();
  if (!prompt) return;

  btn.disabled = true;
  btn.textContent = "⏳ Generando...";
  container.innerHTML = `<div class="text-xs text-amber-300 animate-pulse py-12">🎨 Creando imagen con MiniMax image-01...</div>`;

  try {
    const res = await fetch("/api/academy/generate-image", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        day: dayNumber,
        api_key: document.getElementById("customApiKey") ? document.getElementById("customApiKey").value : "",
        base_url: document.getElementById("customBaseUrl") ? document.getElementById("customBaseUrl").value : "",
      }),
    });
    const data = await res.json();
    if (data.image_url) {
      container.innerHTML = `<img src="${data.image_url}" alt="Ilustración IA" class="w-full max-h-[340px] object-contain rounded-lg" />`;
      if (cachedAcademyLessons[dayNumber]) {
        cachedAcademyLessons[dayNumber].concept_image = data.image_url;
        cachedAcademyLessons[dayNumber].concept_image_source = data.source || "MiniMax image-01";
      }
    }
  } catch (e) {
    container.innerHTML = `<div class="text-xs text-rose-400 p-4">Error al generar imagen: ${escapeHtml(e.message)}</div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "🎨 Generar IA";
  }
}

function completeAndAdvanceDay(dayNumber) {
  const completed = getCompletedDays();
  if (!completed.includes(dayNumber)) {
    completed.push(dayNumber);
    saveCompletedDays(completed);
    updateAcademyProgressUI();
  }
  if (dayNumber < 30) {
    openAcademyDayLesson(dayNumber + 1);
  } else {
    showAcademyCalendarView();
  }
}

function practiceExerciseInBoard(promptText) {
  closeAcademyModal();
  const input = document.getElementById("promptInput");
  if (input) {
    input.value = promptText;
    input.focus();
    sendProblem();
  }
}

async function loadLiveDeepDive(dayNumber) {
  const btn = document.getElementById("deepDiveBtn");
  const box = document.getElementById("liveDeepDiveContainer");
  if (!box) return;

  box.classList.remove("hidden");
  box.innerHTML = `<div class="text-xs text-sky-300 animate-pulse">🧠 El Profesor MiniMax está redactando una cátedra avanzada en vivo para el Día ${dayNumber}...</div>`;
  if (btn) {
    btn.disabled = true;
    btn.textContent = "⏳ Generando con MiniMax...";
  }

  try {
    const res = await fetch("/api/academy/deep-dive", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        day: dayNumber,
        model: document.getElementById("modelSelect") ? document.getElementById("modelSelect").value : "MiniMax-M3.1-Flash",
        api_key: document.getElementById("customApiKey") ? document.getElementById("customApiKey").value : "",
        base_url: document.getElementById("customBaseUrl") ? document.getElementById("customBaseUrl").value : "",
      }),
    });
    const data = await res.json();
    box.innerHTML = `
      <div class="text-xs font-bold uppercase tracking-wider text-sky-400 mb-2">✨ Cápsula Magistral en Vivo (${escapeHtml(data.model_used || "MiniMax")})</div>
      <div class="prose-math text-xs sm:text-sm text-slate-200 leading-relaxed">${renderMarkdownWithMath(data.content_markdown || "")}</div>
    `;
    if (typeof renderMathInElement === "function") {
      renderMathInElement(box, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
          { left: "\\[", right: "\\]", display: true },
          { left: "\\(", right: "\\)", display: false },
        ],
        throwOnError: false,
      });
    }
  } catch (e) {
    box.innerHTML = `<div class="text-xs text-rose-400">No se pudo cargar la ampliación en vivo: ${escapeHtml(e.message)}</div>`;
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<span>✨</span><span>Ampliar Clase en Vivo con MiniMax IA</span>`;
    }
  }
}

window.loadLiveDeepDive = loadLiveDeepDive;

window.openAcademyModal = openAcademyModal;
window.closeAcademyModal = closeAcademyModal;
window.showAcademyCalendarView = showAcademyCalendarView;
window.renderAcademyCalendar = renderAcademyCalendar;
window.openAcademyDayLesson = openAcademyDayLesson;
window.openNextUnfinishedDay = openNextUnfinishedDay;
window.toggleDayComplete = toggleDayComplete;
window.regenerateConceptImage = regenerateConceptImage;
window.completeAndAdvanceDay = completeAndAdvanceDay;
window.practiceExerciseInBoard = practiceExerciseInBoard;

