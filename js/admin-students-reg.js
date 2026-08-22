/* Student reg + camera + CSV + local folder + Даватнома */
(function () {
  const TOKEN_KEY = "geo_admin_token";
  const DIR_DB = "geografia_admin_fs";
  const DIR_STORE = "handles";
  const DIR_KEY = "students_info_dir";
  var _regLock = false;
  var _dirMemory = null;
  var _camStream = null;

  const esc = window.esc || function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&", "<": "<", ">": ">", '"': """, "'": "&#39;" })[c];
    });
  };

  function getToken() {
    return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem("adminToken") || "";
  }

  async function api(path, options) {
    options = options || {};
    const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
    const token = getToken();
    if (token) {
      headers["X-Admin-Token"] = token;
      headers["Authorization"] = "Bearer " + token;
    }
    const res = await fetch(path, Object.assign({}, options, { headers: headers, credentials: "include" }));
    const data = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(data.error || data.message || ("Хато " + res.status));
    return data;
  }

  function val(id) {
    var el = document.getElementById(id);
    return el && el.value != null ? String(el.value).trim() : "";
  }

  function formatTgDate(v) {
    if (!v) return "—";
    var s = String(v).trim();
    var m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!m) return s;
    var months = ["январ","феврал","март","апрел","май","июн","июл","август","сентябр","октябр","ноябр","декабр"];
    return parseInt(m[3], 10) + " " + (months[parseInt(m[2], 10) - 1] || m[2]) + "и соли " + m[1];
  }

  function applyPhoto(dataUrl) {
    var hidden = document.getElementById("stPhotoData");
    var img = document.getElementById("photoImg");
    var ph = document.getElementById("photoPlaceholder");
    if (hidden) hidden.value = dataUrl || "";
    if (img && dataUrl) {
      img.src = dataUrl;
      img.style.display = "block";
    } else if (img) {
      img.removeAttribute("src");
      img.style.display = "none";
    }
    if (ph) ph.style.display = dataUrl ? "none" : "";
  }

  function clearPhoto() {
    applyPhoto("");
    var f = document.getElementById("photoFileInput");
    if (f) f.value = "";
  }

  function setCamStatus(msg) {
    var el = document.getElementById("cameraStatus");
    if (el) el.textContent = msg || "";
  }

  async function listCameras() {
    var sel = document.getElementById("cameraSelect");
    if (!sel || !navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
    try {
      var devices = await navigator.mediaDevices.enumerateDevices();
      var cams = devices.filter(function (d) { return d.kind === "videoinput"; });
      var cur = sel.value;
      sel.innerHTML = "";
      if (!cams.length) {
        sel.innerHTML = '<option value="">Камера ёфт нашуд</option>';
        return;
      }
      cams.forEach(function (d, i) {
        var o = document.createElement("option");
        o.value = d.deviceId || "";
        o.textContent = d.label || ("Камера " + (i + 1));
        sel.appendChild(o);
      });
      if (cur) sel.value = cur;
    } catch (e) {
      setCamStatus("Рӯйхати камера: " + (e.message || e));
    }
  }

  async function startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCamStatus("Камера дастгирӣ намешавад (HTTPS лозим)");
      return;
    }
    stopCamera();
    var sel = document.getElementById("cameraSelect");
    var video = document.getElementById("cameraVideo");
    if (!video) return;
    var constraints = { video: { facingMode: "user" }, audio: false };
    if (sel && sel.value) {
      constraints.video = { deviceId: { exact: sel.value } };
    }
    try {
      setCamStatus("Кушода истодааст…");
      _camStream = await navigator.mediaDevices.getUserMedia(constraints);
      video.srcObject = _camStream;
      video.style.display = "block";
      await video.play().catch(function () {});
      setCamStatus("Камера фаъол");
      await listCameras();
    } catch (e) {
      setCamStatus("Хато: " + (e.message || e));
      _camStream = null;
    }
  }

  function stopCamera() {
    if (_camStream) {
      try {
        _camStream.getTracks().forEach(function (t) { t.stop(); });
      } catch (_) {}
      _camStream = null;
    }
    var video = document.getElementById("cameraVideo");
    if (video) {
      video.srcObject = null;
      video.style.display = "none";
    }
    setCamStatus("");
  }

  function capturePhoto() {
    var video = document.getElementById("cameraVideo");
    var canvas = document.getElementById("cameraCanvas");
    if (!video || !canvas || !video.srcObject || video.videoWidth < 2) {
      setCamStatus("Аввал камераро кушоед");
      return;
    }
    var w = video.videoWidth;
    var h = video.videoHeight;
    canvas.width = w;
    canvas.height = h;
    var ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, w, h);
    var dataUrl = canvas.toDataURL("image/jpeg", 0.88);
    applyPhoto(dataUrl);
    setCamStatus("Акс гирифта шуд");
  }

  function idbOpen() {
    return new Promise(function (resolve, reject) {
      var req = indexedDB.open(DIR_DB, 1);
      req.onupgradeneeded = function () {
        var db = req.result;
        if (!db.objectStoreNames.contains(DIR_STORE)) db.createObjectStore(DIR_STORE);
      };
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error); };
    });
  }

  async function idbSet(key, val) {
    var db = await idbOpen();
    return new Promise(function (resolve, reject) {
      var tx = db.transaction(DIR_STORE, "readwrite");
      tx.objectStore(DIR_STORE).put(val, key);
      tx.oncomplete = function () { resolve(); };
      tx.onerror = function () { reject(tx.error); };
    });
  }

  async function idbGet(key) {
    var db = await idbOpen();
    return new Promise(function (resolve, reject) {
      var tx = db.transaction(DIR_STORE, "readonly");
      var req = tx.objectStore(DIR_STORE).get(key);
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error); };
    });
  }

  function updateFolderStatus(ok, name) {
    var el = document.getElementById("localFolderStatus");
    if (!el) return;
    if (ok) {
      el.textContent = "📁 " + (name || "папка");
      el.style.color = "var(--accent, #70db97)";
    } else {
      el.textContent = name || "";
      el.style.color = "";
    }
  }

  async function tryRestoreDir() {
    try {
      if (!window.showDirectoryPicker) return null;
      var handle = await idbGet(DIR_KEY);
      if (!handle) return null;
      if (handle.queryPermission) {
        var perm = await handle.queryPermission({ mode: "readwrite" });
        if (perm !== "granted") {
          perm = await handle.requestPermission({ mode: "readwrite" });
          if (perm !== "granted") return null;
        }
      }
      _dirMemory = handle;
      updateFolderStatus(true, handle.name || "папка");
      return handle;
    } catch (_) {
      return null;
    }
  }

  async function pickStudentsFolder() {
    if (!window.showDirectoryPicker) {
      alert("Браузери шумо папкаи маҳаллиро дастгирӣ намекунад (Chrome/Edge лозим).");
      return;
    }
    try {
      var handle = await window.showDirectoryPicker({ mode: "readwrite" });
      _dirMemory = handle;
      await idbSet(DIR_KEY, handle);
      updateFolderStatus(true, handle.name || "папка");
    } catch (e) {
      if (e && e.name === "AbortError") return;
      alert("Папка интихоб нашуд: " + (e.message || e));
    }
  }

  async function saveStudentLocalCopy(st) {
    try {
      var dir = _dirMemory || (await tryRestoreDir());
      if (!dir) return { ok: false };
      var name = (st.fullName || st.id || "student").replace(/[\\/:*?"<>|]+/g, "_").slice(0, 60);
      var fileName = (st.id || Date.now()) + "_" + name + ".html";
      var html = buildStudentCardHtml(st);
      var fh = await dir.getFileHandle(fileName, { create: true });
      var w = await fh.createWritable();
      await w.write(html);
      await w.close();
      return { ok: true, fileName: fileName };
    } catch (e) {
      return { ok: false, error: e.message || String(e) };
    }
  }

  function buildStudentCardHtml(st) {
    var id = st.id || "";
    var full = st.fullName || [st.lastName, st.firstName, st.patronymic].filter(Boolean).join(" ");
    var photo = st.photoData || "";
    var genderLabel = st.gender === "male" ? "Мард" : (st.gender === "female" ? "Зан" : (st.gender || "—"));
    var olyTitle = st.olympiadTitle || "—";
    var olyStart = st.olympiadStart ? formatTgDate(st.olympiadStart) : "—";
    var birthFmt = st.birthDate ? formatTgDate(st.birthDate) : "—";
    var webUrl = "https://geografia-19tf.onrender.com";
    var igUrl = "https://www.instagram.com/geografia.tj/";
    var webQr = "https://api.qrserver.com/v1/create-qr-code/?size=160x160&margin=10&color=0b3d2e&bgcolor=ffffff&data=" + encodeURIComponent(webUrl);
    var igQr = "https://api.qrserver.com/v1/create-qr-code/?size=160x160&margin=10&color=c13584&bgcolor=ffffff&data=" + encodeURIComponent(igUrl);
    var photoBlock = photo
      ? '<div class="photo-wrap"><img src="' + photo + '" alt="photo"/></div>'
      : '<div class="photo-wrap placeholder"><span>Бе сурат</span></div>';
    var rows = [
      ["ID (барои воридшавӣ)", id],
      ["Насаб", st.lastName || ""],
      ["Ном", st.firstName || ""],
      ["Номи падар", st.patronymic || ""],
      ["Ҷинс", genderLabel],
      ["Таваллуд", birthFmt],
      ["Суроға", st.address || ""],
      ["Муассиса / Мактаб", st.school || ""],
      ["Синф", st.className || ""],
      ["Омӯзгор", st.teacher || ""],
      ["Унвони олимпиада", olyTitle],
      ["Санаи оғози олимпиада", olyStart],
      ["Санаи бақайдгирӣ", st.createdAt || st.registeredAt || new Date().toLocaleString()]
    ];
    var table = rows.map(function (r) {
      return "<tr><th>" + esc(r[0]) + "</th><td>" + esc(r[1] || "—") + "</td></tr>";
    }).join("");
    var subLine = olyTitle !== "—" ? olyTitle : "Иштирокчӣ · Geografia.tj";
    var chips = "";
    if (genderLabel !== "—") chips += '<span class="chip">' + esc(genderLabel) + "</span>";
    if (olyStart !== "—") chips += '<span class="chip">Санаи оғоз: ' + esc(olyStart) + "</span>";
    return "<!DOCTYPE html><html lang=\"tg\"><head><meta charset=\"utf-8\"/>" +
      "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"/>" +
      "<title>Даватнома — " + esc(full) + " | Geografia.tj</title><style>" +
      "@page{size:A4;margin:10mm}:root{--g1:#0a3328;--g2:#157a58;--g3:#d4f0e4;--gold:#c9a227;--gold2:#f0d78c;--ink:#132019;--muted:#5a6b62;--line:#cfe0d6;--paper:#fffcf7}" +
      "*{box-sizing:border-box;margin:0;padding:0}body{font-family:'Segoe UI',system-ui,sans-serif;background:#e8f0eb;color:var(--ink);line-height:1.45}" +
      ".page{max-width:210mm;margin:16px auto;padding:10px}.toolbar{display:flex;gap:8px;margin-bottom:14px;justify-content:center}" +
      ".toolbar button{border:0;background:var(--g2);color:#fff;padding:11px 20px;border-radius:10px;font-weight:700;cursor:pointer}" +
      ".pass{background:var(--paper);border:2.5px solid var(--g1);border-radius:8px;overflow:hidden;box-shadow:0 10px 36px rgba(10,51,40,.14);position:relative}" +
      ".pass::before{content:'';position:absolute;inset:7px;border:1.5px solid var(--gold);border-radius:4px;pointer-events:none;z-index:0}" +
      ".head{background:linear-gradient(135deg,var(--g1),#0f4d3a 45%,var(--g2));color:#fff;padding:22px 28px 18px;text-align:center;position:relative;z-index:1}" +
      ".brand{font-size:1.15rem;letter-spacing:.32em;font-weight:800}.badge{display:inline-block;margin-top:12px;background:linear-gradient(90deg,var(--gold),var(--gold2),var(--gold));color:var(--g1);padding:6px 20px;border-radius:999px;font-weight:800;letter-spacing:.14em;font-size:.8rem}" +
      ".head h1{margin:14px 0 4px;font-size:1.9rem;font-weight:800}.head .tagline{opacity:.9;font-size:.92rem}" +
      ".gold-line{height:5px;background:linear-gradient(90deg,transparent,var(--gold),var(--gold2),var(--gold),transparent)}.body{padding:24px 28px 12px;position:relative;z-index:1}" +
      ".top{display:flex;gap:24px;align-items:flex-start;flex-wrap:wrap}.photo-wrap{width:152px;height:152px;border-radius:10px;overflow:hidden;border:3px solid var(--g2);background:#f0f7f3;flex-shrink:0}" +
      ".photo-wrap img{width:100%;height:100%;object-fit:cover;display:block}.photo-wrap.placeholder{display:flex;align-items:center;justify-content:center;color:var(--muted);font-weight:600}" +
      ".meta{flex:1;min-width:220px}.id-label{font-size:.72rem;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);font-weight:700;margin-bottom:5px}" +
      ".idbox{display:inline-block;font-family:ui-monospace,Consolas,monospace;font-size:1.22rem;letter-spacing:1.6px;background:var(--g1);color:#fff;padding:11px 18px;border-radius:9px;margin-bottom:12px}" +
      ".name{font-size:1.45rem;font-weight:800;margin:0 0 6px;color:var(--g1)}.sub{color:var(--g2);font-size:1rem;font-weight:700;margin:0 0 8px}" +
      ".chips{display:flex;flex-wrap:wrap;gap:8px}.chip{display:inline-block;background:var(--g3);color:var(--g1);padding:5px 12px;border-radius:6px;font-size:.84rem;font-weight:700;border:1px solid #b8dcc9}" +
      "table{width:100%;border-collapse:collapse;margin:18px 0 6px;font-size:13.5px}th,td{padding:9px 12px;border:1px solid var(--line);text-align:left}th{width:36%;background:#f0f7f3;color:var(--g1);font-weight:700}tr:nth-child(even) td{background:#fafdfb}" +
      ".foot{margin-top:8px;padding:18px 28px 22px;border-top:1px dashed var(--line);background:linear-gradient(180deg,#fbfefc,#f2f8f5);position:relative;z-index:1}" +
      ".qr-title{text-align:center;font-size:.82rem;font-weight:700;color:var(--muted);letter-spacing:.1em;text-transform:uppercase;margin-bottom:14px}.qr-row{display:flex;gap:40px;flex-wrap:wrap;justify-content:center}.qr{text-align:center;width:172px}" +
      ".qr img{width:150px;height:150px;border-radius:12px;border:2px solid var(--line);background:#fff;padding:8px}.qr .lbl{margin-top:9px;font-size:.9rem;font-weight:800;color:var(--g1)}.qr .url{font-size:.72rem;color:var(--muted);word-break:break-all}" +
      ".seal{text-align:center;margin-top:16px;font-weight:800;color:var(--g1);letter-spacing:.12em;font-size:1rem}.seal span{color:var(--gold);margin:0 8px}.note{text-align:center;margin:10px auto 0;color:var(--muted);font-size:.82rem;max-width:540px}" +
      "@media print{body{background:#fff}.toolbar{display:none!important}.page{margin:0;padding:0;max-width:none}.pass{box-shadow:none;border-radius:0}}</style></head><body><div class=\"page\">" +
      "<div class=\"toolbar\"><button type=\"button\" onclick=\"window.print()\">🖨 Чоп / Save as PDF</button></div><article class=\"pass\">" +
      "<header class=\"head\"><div class=\"brand\">GEOGRAFIA.TJ</div><div class=\"badge\">ДАВАТНОМА · ИҶОЗАТНОМА</div><h1>Даватнома</h1>" +
      "<p class=\"tagline\">Ҳуҷҷати расмии иштирок дар олимпиада / викторина</p></header><div class=\"gold-line\"></div><div class=\"body\"><div class=\"top\">" + photoBlock +
      "<div class=\"meta\"><div class=\"id-label\">ID барои воридшавӣ</div><div class=\"idbox\">" + esc(id) + "</div>" +
      "<p class=\"name\">" + esc(full) + "</p><p class=\"sub\">" + esc(subLine) + "</p><div class=\"chips\">" + chips + "</div></div></div>" +
      "<table>" + table + "</table></div><footer class=\"foot\"><div class=\"qr-title\">Пайвандҳо · QR-код</div><div class=\"qr-row\">" +
      "<div class=\"qr\"><img src=\"" + igQr + "\" alt=\"IG\"/><div class=\"lbl\">📷 Instagram</div><div class=\"url\">instagram.com/geografia.tj</div></div>" +
      "<div class=\"qr\"><img src=\"" + webQr + "\" alt=\"Web\"/><div class=\"lbl\">🌐 Веб-саҳифа</div><div class=\"url\">" + esc(webUrl) + "</div></div>" +
      "</div><p class=\"seal\">GEOGRAFIA.TJ <span>·</span> Платформаи география</p>" +
      "<p class=\"note\">Ин даватнома ҳуҷҷати расмии иштирок аст. ID-ро нигоҳ доред ва барои воридшавӣ ба платформа истифода баред.</p>" +
      "</footer></article></div></body></html>";
  }

  function csvEscape(v) {
    var s = String(v == null ? "" : v);
    if (/[",\n\r]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  }

  async function exportStudentsCsv() {
    try {
      var data = await api("/api/admin/students");
      var list = data.students || [];
      var headers = ["ID", "Насаб", "Ном", "Номи падар", "Ҷинс", "Таваллуд", "Суроға", "Мактаб", "Синф", "Омӯзгор", "Олимпиада", "Санаи оғоз", "Сурат"];
      var lines = [headers.join(",")];
      list.forEach(function (s) {
        var g = s.gender === "male" ? "Мард" : (s.gender === "female" ? "Зан" : (s.gender || ""));
        lines.push([
          s.id, s.lastName, s.firstName, s.patronymic, g, s.birthDate, s.address,
          s.school, s.className, s.teacher, s.olympiadTitle, s.olympiadStart,
          (s.hasPhoto || s.photoData) ? "ҳа" : "не"
        ].map(csvEscape).join(","));
      });
      var bom = "\uFEFF";
      var blob = new Blob([bom + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url;
      a.download = "students_" + new Date().toISOString().slice(0, 10) + ".csv";
      a.style.display = "none";
      document.body.appendChild(a);
      a.click();
      setTimeout(function () { try { URL.revokeObjectURL(url); } catch (_) {} a.remove(); }, 1500);
    } catch (e) {
      alert("Export нашуд: " + (e.message || e));
    }
  }

  async function registerStudent(e) {
    if (e && e.preventDefault) e.preventDefault();
    if (_regLock) return false;
    _regLock = true;
    var msg = document.getElementById("studentFormMsg");
    if (msg) msg.classList.add("hidden");
    var lastName = val("stLastName"), firstName = val("stFirstName");
    var patronymic = val("stFatherName"), birthDate = val("stBirthDate");
    var address = val("stAddress"), className = val("stClass"), school = val("stSchool");
    var teacher = val("stTeacher"), gender = val("stGender");
    var olympiadTitle = val("stOlympiadTitle"), olympiadStart = val("stOlympiadStart");
    var photoData = val("stPhotoData");
    var fullName = [lastName, firstName, patronymic].filter(Boolean).join(" ");
    try {
      if (!lastName || !firstName) throw new Error("Насаб ва Ном ҳатмӣ.");
      if (!className || !school) throw new Error("Синф ва Мактаб ҳатмӣ.");
      var data = await api("/api/admin/students", {
        method: "POST",
        body: JSON.stringify({
          lastName: lastName, firstName: firstName, patronymic: patronymic,
          birthDate: birthDate, address: address, className: className,
          school: school, teacher: teacher, gender: gender,
          olympiadTitle: olympiadTitle, olympiadStart: olympiadStart,
          photoData: photoData, fullName: fullName
        })
      });
      var s = data.student || data;
      Object.assign(s, {
        lastName: lastName, firstName: firstName, patronymic: patronymic,
        birthDate: birthDate, address: address, school: school, className: className,
        teacher: teacher, gender: gender, olympiadTitle: olympiadTitle,
        olympiadStart: olympiadStart, photoData: photoData,
        fullName: s.fullName || fullName, createdAt: s.createdAt || new Date().toLocaleString()
      });
      var box = document.getElementById("newIdBox");
      if (box) box.classList.remove("hidden");
      var nv = document.getElementById("newIdValue");
      if (nv) nv.textContent = s.id || "";
      var saved = await saveStudentLocalCopy(s);
      var extra = "";
      if (saved && saved.ok) extra = " · файл: " + (saved.fileName || "OK");
      else if (saved && saved.error) extra = " · папка: " + saved.error;
      try {
        var htmlUrl = URL.createObjectURL(new Blob([buildStudentCardHtml(s)], { type: "text/html;charset=utf-8" }));
        window.open(htmlUrl, "_blank");
        setTimeout(function () { try { URL.revokeObjectURL(htmlUrl); } catch (_) {} }, 60000);
      } catch (_) {}
      if (msg) {
        msg.textContent = "ID: " + (s.id || "") + " · Даватнома кушода шуд" + extra;
        msg.classList.remove("hidden", "error");
        msg.classList.add("ok");
      }
      var formEl = document.getElementById("studentForm");
      if (formEl) formEl.reset();
      clearPhoto();
      stopCamera();
      loadStudentsLocal();
    } catch (err) {
      if (msg) {
        msg.textContent = err.message || String(err);
        msg.classList.remove("hidden");
        msg.classList.add("error");
      } else alert(err.message || String(err));
    } finally { _regLock = false; }
    return false;
  }

  async function loadStudentsLocal() {
    try {
      var data = await api("/api/admin/students");
      var body = document.getElementById("studentsBody");
      if (!body) return;
      var list = data.students || [];
      body.innerHTML = list.length ? list.map(function (s) {
        var id = s.id || "";
        var g = s.gender === "male" ? "Мард" : (s.gender === "female" ? "Зан" : (s.gender || "—"));
        return "<tr><td><code>" + esc(id) + "</code></td><td>" + esc(s.fullName || "") + "</td><td>" + esc(g) +
          "</td><td>" + esc(s.className || "") + "</td><td>" + esc(s.school || "") +
          "</td><td>" + esc(s.olympiadTitle || "—") + "</td><td>" + (s.hasPhoto || s.photoData ? "+" : "-") +
          "</td><td><button type=\"button\" class=\"btn small danger\" data-del-student=\"" + esc(id) + "\">Нест</button></td></tr>";
      }).join("") : '<tr><td colspan="8">Хонанда нест</td></tr>';
    } catch (e) {
      var body = document.getElementById("studentsBody");
      if (body) body.innerHTML = '<tr><td colspan="8">Хато: ' + esc(e.message || e) + "</td></tr>";
    }
  }

  async function deleteStudent(id) {
    id = String(id || "").trim();
    if (!id || !confirm("Нест кунем?\n" + id)) return;
    try {
      await api("/api/admin/students/" + encodeURIComponent(id), { method: "DELETE" });
      loadStudentsLocal();
    } catch (err) { alert("Нест нашуд: " + (err.message || err)); }
  }

  function bind() {
    var form = document.getElementById("studentForm");
    if (form) {
      form.onsubmit = function (e) { e.preventDefault(); registerStudent(e); return false; };
    }
    var btnReg = document.getElementById("btnRegisterStudent");
    if (btnReg) btnReg.onclick = function (e) { e.preventDefault(); registerStudent(e); };
    var btnExport = document.getElementById("exportStudentsBtn");
    if (btnExport) btnExport.onclick = function (e) { e.preventDefault(); exportStudentsCsv(); };
    var btnFolder = document.getElementById("btnPickStudentsFolder");
    if (btnFolder) btnFolder.onclick = function (e) { e.preventDefault(); pickStudentsFolder(); };
    var btnStart = document.getElementById("btnStartCamera");
    if (btnStart) btnStart.onclick = function (e) { e.preventDefault(); startCamera(); };
    var btnCap = document.getElementById("btnCapturePhoto");
    if (btnCap) btnCap.onclick = function (e) { e.preventDefault(); capturePhoto(); };
    var btnStop = document.getElementById("btnStopCamera");
    if (btnStop) btnStop.onclick = function (e) { e.preventDefault(); stopCamera(); };
    var btnClr = document.getElementById("btnClearPhoto");
    if (btnClr) btnClr.onclick = function (e) { e.preventDefault(); clearPhoto(); };
    var copyBtn = document.getElementById("copyIdBtn");
    if (copyBtn) {
      copyBtn.onclick = async function () {
        var v = (document.getElementById("newIdValue") || {}).textContent || "";
        if (!v) return;
        try { await navigator.clipboard.writeText(v); alert("ID нусха шуд"); }
        catch (_) { prompt("Нусха:", v); }
      };
    }
    var body = document.getElementById("studentsBody");
    if (body && !body._geoDelBound) {
      body._geoDelBound = true;
      body.addEventListener("click", function (ev) {
        var btn = ev.target && ev.target.closest && ev.target.closest("[data-del-student]");
        if (!btn) return;
        deleteStudent(btn.getAttribute("data-del-student"));
      });
    }
    var f = document.getElementById("photoFileInput");
    if (f) {
      f.onchange = function (ev) {
        var file = ev.target.files && ev.target.files[0];
        if (!file) return;
        var r = new FileReader();
        r.onload = function () { applyPhoto(r.result); };
        r.readAsDataURL(file);
      };
    }
    document.querySelectorAll(".tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (btn.dataset.tab === "students") loadStudentsLocal();
      });
    });
    listCameras();
    tryRestoreDir().then(function (d) { updateFolderStatus(!!d, d && d.name); });
    loadStudentsLocal();
  }

  window.__geoRegisterStudent = registerStudent;
  window.__geoExportStudents = exportStudentsCsv;
  window.__geoPickStudentsFolder = pickStudentsFolder;
  window.loadStudents = loadStudentsLocal;

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind);
  else bind();
})();
