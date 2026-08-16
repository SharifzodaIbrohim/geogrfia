/* Professional student registration: 9 fields + device camera */
(function () {
  const TOKEN_KEY = "geo_admin_token";

  const esc = window.esc || function (s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&", "<": "<", ">": ">", '"': """, "'": "&#39;" }[c])
    );
  };

  function getToken() {
    return (
      localStorage.getItem(TOKEN_KEY) ||
      sessionStorage.getItem(TOKEN_KEY) ||
      localStorage.getItem("adminToken") ||
      ""
    );
  }

  async function api(path, options = {}) {
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    const token = getToken();
    if (token) headers["X-Admin-Token"] = token;
    const res = await fetch(path, { ...options, headers, credentials: "include" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || data.message || "Хато");
    return data;
  }

  function injectStyle() {
    if (document.getElementById("student-reg-style")) return;
    const s = document.createElement("style");
    s.id = "student-reg-style";
    s.textContent = `
.student-reg-form.grid-form{grid-template-columns:1fr 1fr;gap:.75rem 1rem}
.student-reg-form .full-row{grid-column:1/-1}
.photo-capture{display:flex;flex-wrap:wrap;gap:1rem;align-items:flex-start}
.photo-frame{width:160px;height:160px;border:2px dashed #888;border-radius:12px;display:flex;align-items:center;justify-content:center;overflow:hidden;cursor:pointer;background:rgba(0,0,0,.04)}
.photo-frame img{width:100%;height:100%;object-fit:cover}
.camera-video{width:240px;max-width:100%;border-radius:8px;background:#000}
.photo-controls{display:flex;flex-direction:column;gap:.4rem;min-width:200px}
.photo-btns{display:flex;flex-wrap:wrap;gap:.35rem}
@media(max-width:700px){.student-reg-form.grid-form{grid-template-columns:1fr}}
`;
    document.head.appendChild(s);
  }

  function injectForm() {
    const sec = document.getElementById("tab-students");
    if (!sec) return;
    sec.innerHTML = `
        <h2>Хонандагон — Бақайдгирӣ</h2>
        <form id="studentForm" class="card grid-form student-reg-form">
          <div><label>1. Насаб *</label>
            <input id="stLastName" required autocomplete="family-name" placeholder="Ҳасанов" /></div>
          <div><label>2. Ном *</label>
            <input id="stFirstName" required autocomplete="given-name" placeholder="Ойбек" /></div>
          <div><label>3. Номи падар</label>
            <input id="stPatronymic" placeholder="Алиевич" /></div>
          <div><label>4. Рӯз.Моҳ.Сол таваллуд</label>
            <input id="stBirthDate" type="date" /></div>
          <div class="full-row"><label>5. Суроға</label>
            <input id="stAddress" placeholder="ш. Душанбе, кӯчаи …" /></div>
          <div class="full-row"><label>6. Муассиса / Мактаб *</label>
            <input id="stSchool" required placeholder="Литсейи … / Мактаби №…" /></div>
          <div><label>7. Синф *</label>
            <input id="stClassName" required placeholder="10Б" /></div>
          <div><label>8. Омӯзгор</label>
            <input id="stTeacher" placeholder="Номи омӯзгор" /></div>
          <div class="full-row photo-block">
            <label>9. Сурат (.JPG) — аз камераи дастгоҳ</label>
            <div class="photo-capture">
              <div id="photoFrame" class="photo-frame" title="Барои аксгирӣ клик кунед">
                <img id="photoPreview" alt="" class="hidden" />
                <span id="photoPlaceholder">📷 Аксгирӣ</span>
              </div>
              <div class="photo-controls">
                <label class="muted">Камера</label>
                <select id="cameraSelect"><option value="">— интихоб —</option></select>
                <div class="photo-btns">
                  <button type="button" id="btnStartCamera" class="btn small">Кушодани камера</button>
                  <button type="button" id="btnCapturePhoto" class="btn small primary" disabled>Гирифтани акс</button>
                  <button type="button" id="btnClearPhoto" class="btn small">Пок</button>
                </div>
                <video id="cameraVideo" class="camera-video hidden" playsinline autoplay muted></video>
                <canvas id="photoCanvas" class="hidden"></canvas>
              </div>
            </div>
            <input type="hidden" id="stPhotoData" value="" />
          </div>
          <div class="form-actions full-row">
            <button type="submit" class="btn primary">Бақайдгирӣ + Сохтани ID</button>
            <button type="button" id="exportStudentsBtn" class="btn">Export CSV</button>
          </div>
          <p id="studentMsg" class="msg hidden full-row"></p>
          <p id="studentFormMsg" class="msg hidden full-row"></p>
        </form>
        <div id="newIdBox" class="card hidden" style="margin-top:0.75rem">
          <p><strong id="newIdName"></strong></p>
          <p class="muted">ID-и нав (ба хонанда диҳед):</p>
          <code id="newIdValue" style="user-select:all;font-size:1.05rem"></code>
          <button type="button" id="copyIdBtn" class="btn" style="margin-top:0.5rem">Нусхабардорӣ</button>
        </div>
        <div class="table-wrap" style="margin-top:1rem"><table><thead><tr>
          <th>ID</th><th>Насаб Ном</th><th>Синф</th><th>Мактаб</th><th>Омӯзгор</th><th>Сурат</th><th></th>
        </tr></thead><tbody id="studentsBody"></tbody></table></div>
    `;
  }

  injectStyle();
  injectForm();

  let _camStream = null;

  async function listCameras() {
    const sel = document.getElementById("cameraSelect");
    if (!sel || !navigator.mediaDevices?.enumerateDevices) return;
    try {
      const tmp = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      tmp.getTracks().forEach((t) => t.stop());
    } catch (_) {}
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const cams = devices.filter((d) => d.kind === "videoinput");
      sel.innerHTML = "";
      if (!cams.length) {
        sel.innerHTML = '<option value="">Камера ёфт нашуд</option>';
        return;
      }
      cams.forEach((d, i) => {
        const opt = document.createElement("option");
        opt.value = d.deviceId;
        opt.textContent = d.label || "Камера " + (i + 1);
        sel.appendChild(opt);
      });
    } catch (e) {
      console.warn("enumerateDevices", e);
    }
  }

  function stopCamera() {
    if (_camStream) {
      _camStream.getTracks().forEach((t) => t.stop());
      _camStream = null;
    }
    const video = document.getElementById("cameraVideo");
    if (video) {
      video.srcObject = null;
      video.classList.add("hidden");
    }
    const btnCap = document.getElementById("btnCapturePhoto");
    if (btnCap) btnCap.disabled = true;
  }

  async function startCamera() {
    const video = document.getElementById("cameraVideo");
    const sel = document.getElementById("cameraSelect");
    const btnCap = document.getElementById("btnCapturePhoto");
    if (!video) return;
    stopCamera();
    const deviceId = sel?.value || undefined;
    const constraints = {
      audio: false,
      video: deviceId
        ? { deviceId: { exact: deviceId }, width: { ideal: 1280 }, height: { ideal: 720 } }
        : { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
    };
    try {
      _camStream = await navigator.mediaDevices.getUserMedia(constraints);
      video.srcObject = _camStream;
      video.classList.remove("hidden");
      if (btnCap) btnCap.disabled = false;
      await listCameras();
      if (deviceId && sel) sel.value = deviceId;
    } catch (e) {
      alert("Камера кушода нашуд: " + (e.message || e));
    }
  }

  function capturePhoto() {
    const video = document.getElementById("cameraVideo");
    const canvas = document.getElementById("photoCanvas");
    const preview = document.getElementById("photoPreview");
    const ph = document.getElementById("photoPlaceholder");
    const hidden = document.getElementById("stPhotoData");
    if (!video || !canvas || !video.videoWidth) {
      alert("Аввал камераро кушоед.");
      return;
    }
    const w = video.videoWidth;
    const h = video.videoHeight;
    const scale = Math.min(1, 800 / Math.max(w, h));
    canvas.width = Math.round(w * scale);
    canvas.height = Math.round(h * scale);
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
    if (hidden) hidden.value = dataUrl;
    if (preview) {
      preview.src = dataUrl;
      preview.classList.remove("hidden");
    }
    if (ph) ph.classList.add("hidden");
    stopCamera();
  }

  function clearPhoto() {
    const hidden = document.getElementById("stPhotoData");
    const preview = document.getElementById("photoPreview");
    const ph = document.getElementById("photoPlaceholder");
    if (hidden) hidden.value = "";
    if (preview) {
      preview.removeAttribute("src");
      preview.classList.add("hidden");
    }
    if (ph) ph.classList.remove("hidden");
  }

  document.getElementById("btnStartCamera")?.addEventListener("click", () => startCamera());
  document.getElementById("btnCapturePhoto")?.addEventListener("click", () => capturePhoto());
  document.getElementById("btnClearPhoto")?.addEventListener("click", () => clearPhoto());
  document.getElementById("photoFrame")?.addEventListener("click", () => {
    if (!_camStream) startCamera();
    else capturePhoto();
  });
  document.getElementById("cameraSelect")?.addEventListener("change", () => {
    if (_camStream) startCamera();
  });

  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.tab === "students") {
        listCameras();
        loadStudentsLocal();
      }
    });
  });

  document.getElementById("studentForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    e.stopImmediatePropagation();
    const msg = document.getElementById("studentFormMsg") || document.getElementById("studentMsg");
    msg?.classList.add("hidden");
    const lastName = document.getElementById("stLastName")?.value.trim() || "";
    const firstName = document.getElementById("stFirstName")?.value.trim() || "";
    const patronymic = document.getElementById("stPatronymic")?.value.trim() || "";
    const birthDate = document.getElementById("stBirthDate")?.value.trim() || "";
    const address = document.getElementById("stAddress")?.value.trim() || "";
    const className = document.getElementById("stClassName")?.value.trim() || "";
    const school = document.getElementById("stSchool")?.value.trim() || "";
    const teacher = document.getElementById("stTeacher")?.value.trim() || "";
    const photoData = document.getElementById("stPhotoData")?.value || "";
    const fullName = [lastName, firstName, patronymic].filter(Boolean).join(" ");
    try {
      const data = await api("/api/admin/students", {
        method: "POST",
        body: JSON.stringify({
          lastName, firstName, patronymic, birthDate, address,
          className, school, teacher, photoData, fullName,
        }),
      });
      const s = data.student || data;
      document.getElementById("newIdBox")?.classList.remove("hidden");
      const nn = document.getElementById("newIdName");
      const nv = document.getElementById("newIdValue");
      if (nn) nn.textContent = s.fullName || fullName;
      if (nv) nv.textContent = s.id || "";
      e.target.reset();
      clearPhoto();
      stopCamera();
      loadStudentsLocal();
    } catch (err) {
      if (msg) {
        msg.textContent = err.message || String(err);
        msg.classList.remove("hidden");
        msg.classList.add("error");
      } else alert(err.message || String(err));
    }
  });

  document.getElementById("copyIdBtn")?.addEventListener("click", async () => {
    const v = document.getElementById("newIdValue")?.textContent || "";
    if (!v) return;
    try {
      await navigator.clipboard.writeText(v);
      alert("ID нусха шуд");
    } catch (_) {
      prompt("Нусха кунед:", v);
    }
  });

  document.getElementById("exportStudentsBtn")?.addEventListener("click", async () => {
    try {
      const token = getToken();
      const res = await fetch("/api/admin/students/export", {
        headers: token ? { "X-Admin-Token": token } : {},
        credentials: "include",
      });
      if (!res.ok) throw new Error("Export хато");
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "students.csv";
      a.click();
    } catch (e) {
      alert(e.message || String(e));
    }
  });

  async function loadStudentsLocal() {
    try {
      const data = await api("/api/admin/students");
      const body = document.getElementById("studentsBody");
      if (!body) return;
      const list = data.students || [];
      body.innerHTML = list.length
        ? list
            .map(
              (s) => `
        <tr>
          <td><code>${esc(s.id)}</code></td>
          <td>${esc(s.fullName || ((s.lastName || "") + " " + (s.firstName || "")).trim())}</td>
          <td>${esc(s.className)}</td>
          <td>${esc(s.school)}</td>
          <td>${esc(s.teacher || "")}</td>
          <td>${s.hasPhoto ? "✓" : "—"}</td>
          <td><button type="button" class="btn small danger" data-del-student="${esc(s.id)}">Нест</button></td>
        </tr>`
            )
            .join("")
        : '<tr><td colspan="7">Хонанда нест</td></tr>';
      body.querySelectorAll("[data-del-student]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (!confirm("Хонанда нест карда шавад?")) return;
          await api("/api/admin/students/" + btn.dataset.delStudent, { method: "DELETE" });
          loadStudentsLocal();
        });
      });
    } catch (e) {
      console.warn("loadStudentsLocal", e);
    }
  }

  window.loadStudents = loadStudentsLocal;
})();
