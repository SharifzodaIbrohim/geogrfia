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
    s.textContent = [
      ".student-reg-form.grid-form{grid-template-columns:1fr 1fr;gap:.75rem 1rem}",
      ".student-reg-form .full-row{grid-column:1/-1}",
      ".photo-capture{display:flex;flex-wrap:wrap;gap:1rem;align-items:flex-start}",
      ".photo-frame{width:160px;height:160px;border:2px dashed #888;border-radius:12px;display:flex;align-items:center;justify-content:center;overflow:hidden;cursor:pointer;background:rgba(0,0,0,.04)}",
      ".photo-frame img{width:100%;height:100%;object-fit:cover}",
      ".camera-video{width:240px;max-width:100%;border-radius:8px;background:#000}",
      ".photo-controls{display:flex;flex-direction:column;gap:.4rem;min-width:200px}",
      ".photo-btns{display:flex;flex-wrap:wrap;gap:.35rem}",
      "@media(max-width:700px){.student-reg-form.grid-form{grid-template-columns:1fr}}",
    ].join("\n");
    document.head.appendChild(s);
  }

  // Static HTML in admin.html is preferred; only inject if missing
  function injectForm() {
    if (document.getElementById("stLastName")) return;
    const sec = document.getElementById("tab-students");
    if (!sec) return;
    sec.innerHTML = "<p class=\"error\">Форма бор нашуд. Саҳифаро нав кунед (Ctrl+F5).</p>";
  }

  injectStyle();
  injectForm();

  let _camStream = null;

  async function listCameras() {
    const sel = document.getElementById("cameraSelect");
    if (!sel || !navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
    try {
      const tmp = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      tmp.getTracks().forEach(function (t) { t.stop(); });
    } catch (_) {}
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const cams = devices.filter(function (d) { return d.kind === "videoinput"; });
      sel.innerHTML = "";
      if (!cams.length) {
        sel.innerHTML = "<option value=\"\">Камера ёфт нашуд</option>";
        return;
      }
      cams.forEach(function (d, i) {
        const opt = document.createElement("option");
        opt.value = d.deviceId;
        opt.textContent = d.label || ("Камера " + (i + 1));
        sel.appendChild(opt);
      });
    } catch (e) {
      console.warn("enumerateDevices", e);
    }
  }

  function stopCamera() {
    if (_camStream) {
      _camStream.getTracks().forEach(function (t) { t.stop(); });
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
    const deviceId = sel && sel.value ? sel.value : undefined;
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

  function bind() {
    var btnStart = document.getElementById("btnStartCamera");
    var btnCap = document.getElementById("btnCapturePhoto");
    var btnClear = document.getElementById("btnClearPhoto");
    var frame = document.getElementById("photoFrame");
    var camSel = document.getElementById("cameraSelect");
    var form = document.getElementById("studentForm");

    if (btnStart) btnStart.addEventListener("click", function () { startCamera(); });
    if (btnCap) btnCap.addEventListener("click", function () { capturePhoto(); });
    if (btnClear) btnClear.addEventListener("click", function () { clearPhoto(); });
    if (frame) frame.addEventListener("click", function () {
      if (!_camStream) startCamera();
      else capturePhoto();
    });
    if (camSel) camSel.addEventListener("change", function () {
      if (_camStream) startCamera();
    });

    document.querySelectorAll(".tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (btn.dataset.tab === "students") {
          listCameras();
          loadStudentsLocal();
        }
      });
    });

    if (form) {
      form.addEventListener("submit", async function (e) {
        e.preventDefault();
        e.stopImmediatePropagation();
        var msg = document.getElementById("studentFormMsg") || document.getElementById("studentMsg");
        if (msg) msg.classList.add("hidden");
        var lastName = (document.getElementById("stLastName") || {}).value || "";
        var firstName = (document.getElementById("stFirstName") || {}).value || "";
        var patronymic = (document.getElementById("stPatronymic") || {}).value || "";
        var birthDate = (document.getElementById("stBirthDate") || {}).value || "";
        var address = (document.getElementById("stAddress") || {}).value || "";
        var className = (document.getElementById("stClassName") || {}).value || "";
        var school = (document.getElementById("stSchool") || {}).value || "";
        var teacher = (document.getElementById("stTeacher") || {}).value || "";
        var photoData = (document.getElementById("stPhotoData") || {}).value || "";
        lastName = String(lastName).trim();
        firstName = String(firstName).trim();
        patronymic = String(patronymic).trim();
        birthDate = String(birthDate).trim();
        address = String(address).trim();
        className = String(className).trim();
        school = String(school).trim();
        teacher = String(teacher).trim();
        var fullName = [lastName, firstName, patronymic].filter(Boolean).join(" ");
        try {
          var data = await api("/api/admin/students", {
            method: "POST",
            body: JSON.stringify({
              lastName: lastName,
              firstName: firstName,
              patronymic: patronymic,
              birthDate: birthDate,
              address: address,
              className: className,
              school: school,
              teacher: teacher,
              photoData: photoData,
              fullName: fullName,
            }),
          });
          var s = data.student || data;
          var box = document.getElementById("newIdBox");
          if (box) box.classList.remove("hidden");
          var nn = document.getElementById("newIdName");
          var nv = document.getElementById("newIdValue");
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
    }

    var copyBtn = document.getElementById("copyIdBtn");
    if (copyBtn) {
      copyBtn.addEventListener("click", async function () {
        var v = (document.getElementById("newIdValue") || {}).textContent || "";
        if (!v) return;
        try {
          await navigator.clipboard.writeText(v);
          alert("ID нусха шуд");
        } catch (_) {
          prompt("Нусха кунед:", v);
        }
      });
    }

    var exportBtn = document.getElementById("exportStudentsBtn");
    if (exportBtn) {
      exportBtn.addEventListener("click", async function () {
        try {
          var token = getToken();
          var res = await fetch("/api/admin/students/export", {
            headers: token ? { "X-Admin-Token": token } : {},
            credentials: "include",
          });
          if (!res.ok) throw new Error("Export хато");
          var blob = await res.blob();
          var a = document.createElement("a");
          a.href = URL.createObjectURL(blob);
          a.download = "students.csv";
          a.click();
        } catch (e) {
          alert(e.message || String(e));
        }
      });
    }
  }

  async function loadStudentsLocal() {
    try {
      var data = await api("/api/admin/students");
      var body = document.getElementById("studentsBody");
      if (!body) return;
      var list = data.students || [];
      body.innerHTML = list.length
        ? list
            .map(function (s) {
              return (
                "<tr>" +
                "<td><code>" + esc(s.id) + "</code></td>" +
                "<td>" + esc(s.fullName || ((s.lastName || "") + " " + (s.firstName || "")).trim()) + "</td>" +
                "<td>" + esc(s.className) + "</td>" +
                "<td>" + esc(s.school) + "</td>" +
                "<td>" + esc(s.teacher || "") + "</td>" +
                "<td>" + (s.hasPhoto ? "✓" : "—") + "</td>" +
                "<td><button type=\"button\" class=\"btn small danger\" data-del-student=\"" + esc(s.id) + "\">Нест</button></td>" +
                "</tr>"
              );
            })
            .join("")
        : '<tr><td colspan="7">Хонанда нест</td></tr>';
      body.querySelectorAll("[data-del-student]").forEach(function (btn) {
        btn.addEventListener("click", async function () {
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
  bind();
})();
