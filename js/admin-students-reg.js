/* Professional student registration: 9 fields + camera + file fallback */
(function () {
  const TOKEN_KEY = "geo_admin_token";

  const esc =
    window.esc ||
    function (s) {
      return String(s ?? "").replace(/[&<>"']/g, function (c) {
        return { "&": "&", "<": "<", ">": ">", '"': """, "'": "&#39;" }[c];
      });
    };

  function getToken() {
    return (
      localStorage.getItem(TOKEN_KEY) ||
      sessionStorage.getItem(TOKEN_KEY) ||
      localStorage.getItem("adminToken") ||
      ""
    );
  }

  async function api(path, options) {
    options = options || {};
    const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
    const token = getToken();
    if (token) headers["X-Admin-Token"] = token;
    const res = await fetch(path, Object.assign({}, options, { headers: headers, credentials: "include" }));
    const data = await res.json().catch(function () {
      return {};
    });
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
      ".camera-video{width:min(320px,100%);max-width:100%;border-radius:8px;background:#111;min-height:180px;display:block}",
      ".photo-controls{display:flex;flex-direction:column;gap:.5rem;min-width:220px;flex:1}",
      ".photo-btns{display:flex;flex-wrap:wrap;gap:.35rem}",
      "#cameraStatus{font-size:.9rem;color:#666;min-height:1.2em}",
      "#cameraStatus.err{color:#b00020}",
      "#cameraStatus.ok{color:#0a7}",
      "@media(max-width:700px){.student-reg-form.grid-form{grid-template-columns:1fr}}",
    ].join("\n");
    document.head.appendChild(s);
  }

  function setCamStatus(text, kind) {
    var el = document.getElementById("cameraStatus");
    if (!el) return;
    el.textContent = text || "";
    el.className = kind || "";
  }

  function ensureExtraControls() {
    var controls = document.querySelector(".photo-controls");
    if (!controls) return;
    if (!document.getElementById("cameraStatus")) {
      var st = document.createElement("p");
      st.id = "cameraStatus";
      st.textContent = "Барои рӯйхати камераҳо «Кушодани камера»-ро пахш кунед.";
      controls.appendChild(st);
    }
    if (!document.getElementById("photoFileInput")) {
      var lab = document.createElement("label");
      lab.style.marginTop = "0.25rem";
      lab.innerHTML =
        'Ё файл / камераи телефон: <input type="file" id="photoFileInput" accept="image/*" capture="environment" />';
      controls.appendChild(lab);
    }
    var video = document.getElementById("cameraVideo");
    if (video) {
      video.setAttribute("playsinline", "");
      video.setAttribute("muted", "");
      video.setAttribute("autoplay", "");
    }
  }

  let _camStream = null;

  async function fillCameraSelect(preferId) {
    var sel = document.getElementById("cameraSelect");
    if (!sel) return;
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
      sel.innerHTML = '<option value="">API дастгирӣ намешавад</option>';
      setCamStatus("Ин браузер камераро дастгирӣ намекунад.", "err");
      return;
    }
    try {
      var devices = await navigator.mediaDevices.enumerateDevices();
      var cams = devices.filter(function (d) {
        return d.kind === "videoinput";
      });
      sel.innerHTML = "";
      if (!cams.length) {
        sel.innerHTML = '<option value="">Камера ёфт нашуд</option>';
        setCamStatus("Камера ёфт нашуд. Иҷозат ё дастгоҳро санҷед.", "err");
        return;
      }
      cams.forEach(function (d, i) {
        var opt = document.createElement("option");
        opt.value = d.deviceId || "";
        opt.textContent = d.label && d.label.trim() ? d.label : "Камера " + (i + 1);
        sel.appendChild(opt);
      });
      if (preferId) {
        for (var i = 0; i < sel.options.length; i++) {
          if (sel.options[i].value === preferId) {
            sel.selectedIndex = i;
            break;
          }
        }
      }
      setCamStatus("Ёфт шуд: " + cams.length + " камера. Интихоб кунед ё акс гиред.", "ok");
    } catch (e) {
      console.warn("enumerateDevices", e);
      setCamStatus("Рӯйхати камераҳо: " + (e.message || e), "err");
    }
  }

  function stopCamera() {
    if (_camStream) {
      _camStream.getTracks().forEach(function (t) {
        try {
          t.stop();
        } catch (_) {}
      });
      _camStream = null;
    }
    var video = document.getElementById("cameraVideo");
    if (video) {
      try {
        video.srcObject = null;
      } catch (_) {}
      video.classList.add("hidden");
      video.style.display = "none";
    }
    var btnCap = document.getElementById("btnCapturePhoto");
    if (btnCap) btnCap.disabled = true;
  }

  async function startCamera() {
    var video = document.getElementById("cameraVideo");
    var sel = document.getElementById("cameraSelect");
    var btnCap = document.getElementById("btnCapturePhoto");
    if (!video) {
      setCamStatus("Элементи video дар саҳифа нест.", "err");
      return;
    }
    if (!window.isSecureContext) {
      setCamStatus("Камера фақат дар HTTPS кор мекунад.", "err");
      alert("Камера фақат дар HTTPS кор мекунад.");
      return;
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCamStatus("Браузер getUserMedia надорад. Аз «файл» истифода баред.", "err");
      return;
    }

    stopCamera();
    setCamStatus("Камера кушода мешавад… (иҷозатро тасдиқ кунед)", "");

    var deviceId = sel && sel.value ? sel.value : "";
    var attempts = [];
    if (deviceId) {
      attempts.push({ audio: false, video: { deviceId: { ideal: deviceId } } });
    }
    attempts.push({ audio: false, video: { facingMode: "user" } });
    attempts.push({ audio: false, video: true });

    var lastErr = null;
    for (var i = 0; i < attempts.length; i++) {
      try {
        _camStream = await navigator.mediaDevices.getUserMedia(attempts[i]);
        lastErr = null;
        break;
      } catch (e) {
        lastErr = e;
        _camStream = null;
      }
    }

    if (!_camStream) {
      var msg =
        "Камера кушода нашуд: " +
        (lastErr && (lastErr.name || lastErr.message) ? lastErr.name + " — " + lastErr.message : lastErr || "номаълум");
      setCamStatus(msg + " · Аз «файл» акс интихоб кунед.", "err");
      alert(msg);
      return;
    }

    video.srcObject = _camStream;
    video.classList.remove("hidden");
    video.style.display = "block";
    try {
      await video.play();
    } catch (_) {}

    if (btnCap) btnCap.disabled = false;

    var track = _camStream.getVideoTracks()[0];
    var settings = track && track.getSettings ? track.getSettings() : {};
    var activeId = settings.deviceId || deviceId || "";
    await fillCameraSelect(activeId);
    setCamStatus("Камера фаъол · «Гирифтани акс»-ро пахш кунед", "ok");
  }

  function capturePhoto() {
    var video = document.getElementById("cameraVideo");
    var canvas = document.getElementById("photoCanvas");
    var preview = document.getElementById("photoPreview");
    var ph = document.getElementById("photoPlaceholder");
    var hidden = document.getElementById("stPhotoData");
    if (!video || !canvas) {
      alert("Элементҳои аксгирӣ нестанд.");
      return;
    }
    if (!video.videoWidth) {
      alert("Аввал камераро кушоед ва интизор шавед то тасвир пайдо шавад.");
      return;
    }
    var w = video.videoWidth;
    var h = video.videoHeight;
    var scale = Math.min(1, 800 / Math.max(w, h));
    canvas.width = Math.round(w * scale);
    canvas.height = Math.round(h * scale);
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    var dataUrl = canvas.toDataURL("image/jpeg", 0.85);
    applyPhotoData(dataUrl);
    stopCamera();
    setCamStatus("Акс гирифта шуд ✓", "ok");
  }

  function applyPhotoData(dataUrl) {
    var hidden = document.getElementById("stPhotoData");
    var preview = document.getElementById("photoPreview");
    var ph = document.getElementById("photoPlaceholder");
    if (hidden) hidden.value = dataUrl || "";
    if (preview && dataUrl) {
      preview.src = dataUrl;
      preview.classList.remove("hidden");
      preview.style.display = "block";
    }
    if (ph && dataUrl) ph.classList.add("hidden");
  }

  function clearPhoto() {
    var hidden = document.getElementById("stPhotoData");
    var preview = document.getElementById("photoPreview");
    var ph = document.getElementById("photoPlaceholder");
    var file = document.getElementById("photoFileInput");
    if (hidden) hidden.value = "";
    if (preview) {
      preview.removeAttribute("src");
      preview.classList.add("hidden");
      preview.style.display = "";
    }
    if (ph) ph.classList.remove("hidden");
    if (file) file.value = "";
    setCamStatus("Акс пок шуд.", "");
  }

  function onFileSelected(ev) {
    var f = ev.target && ev.target.files && ev.target.files[0];
    if (!f) return;
    if (!/^image\//.test(f.type)) {
      alert("Фақат файли расм (JPG/PNG).");
      return;
    }
    var reader = new FileReader();
    reader.onload = function () {
      var dataUrl = reader.result;
      if (typeof dataUrl === "string" && dataUrl.length > 2_500_000) {
        // compress via canvas
        var img = new Image();
        img.onload = function () {
          var c = document.createElement("canvas");
          var scale = Math.min(1, 800 / Math.max(img.width, img.height));
          c.width = Math.round(img.width * scale);
          c.height = Math.round(img.height * scale);
          c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
          applyPhotoData(c.toDataURL("image/jpeg", 0.85));
          setCamStatus("Аз файл бор шуд ✓", "ok");
        };
        img.src = dataUrl;
      } else {
        applyPhotoData(dataUrl);
        setCamStatus("Аз файл бор шуд ✓", "ok");
      }
    };
    reader.readAsDataURL(f);
  }

  function bind() {
    ensureExtraControls();

    var btnStart = document.getElementById("btnStartCamera");
    var btnCap = document.getElementById("btnCapturePhoto");
    var btnClear = document.getElementById("btnClearPhoto");
    var frame = document.getElementById("photoFrame");
    var camSel = document.getElementById("cameraSelect");
    var form = document.getElementById("studentForm");
    var fileIn = document.getElementById("photoFileInput");

    if (btnStart) {
      btnStart.addEventListener("click", function (e) {
        e.preventDefault();
        startCamera();
      });
    }
    if (btnCap) {
      btnCap.addEventListener("click", function (e) {
        e.preventDefault();
        capturePhoto();
      });
    }
    if (btnClear) {
      btnClear.addEventListener("click", function (e) {
        e.preventDefault();
        clearPhoto();
        stopCamera();
      });
    }
    if (frame) {
      frame.addEventListener("click", function () {
        if (!_camStream) startCamera();
        else capturePhoto();
      });
    }
    if (camSel) {
      camSel.addEventListener("change", function () {
        if (_camStream) startCamera();
      });
    }
    if (fileIn) {
      fileIn.addEventListener("change", onFileSelected);
    }

    document.querySelectorAll(".tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (btn.dataset.tab === "students") {
          ensureExtraControls();
          loadStudentsLocal();
          setCamStatus('Барои камера «Кушодани камера» ё файл интихоб кунед.', "");
        }
      });
    });

    if (form) {
      form.addEventListener(
        "submit",
        async function (e) {
          e.preventDefault();
          e.stopImmediatePropagation();
          var msg = document.getElementById("studentFormMsg") || document.getElementById("studentMsg");
          if (msg) msg.classList.add("hidden");
          function val(id) {
            var el = document.getElementById(id);
            return el && el.value != null ? String(el.value).trim() : "";
          }
          var lastName = val("stLastName");
          var firstName = val("stFirstName");
          var patronymic = val("stPatronymic");
          var birthDate = val("stBirthDate");
          var address = val("stAddress");
          var className = val("stClassName");
          var school = val("stSchool");
          var teacher = val("stTeacher");
          var photoData = val("stPhotoData");
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
        },
        true
      );
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
                "<td><code>" +
                esc(s.id) +
                "</code></td>" +
                "<td>" +
                esc(s.fullName || ((s.lastName || "") + " " + (s.firstName || "")).trim()) +
                "</td>" +
                "<td>" +
                esc(s.className) +
                "</td>" +
                "<td>" +
                esc(s.school) +
                "</td>" +
                "<td>" +
                esc(s.teacher || "") +
                "</td>" +
                "<td>" +
                (s.hasPhoto ? "✓" : "—") +
                "</td>" +
                '<td><button type="button" class="btn small danger" data-del-student="' +
                esc(s.id) +
                '">Нест</button></td>' +
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
  injectStyle();
  bind();
})();
