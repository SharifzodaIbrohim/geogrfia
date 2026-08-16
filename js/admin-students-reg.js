/* Student registration: API create + local folder card + structured CSV */
(function () {
  const TOKEN_KEY = "geo_admin_token";
  const DIR_DB = "geografia_admin_fs";
  const DIR_STORE = "handles";
  const DIR_KEY = "students_info_dir";
  const FOLDER_HINT = "Малумотхои хонандагон";

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
    s.textContent =
      ".student-reg-form.grid-form{grid-template-columns:1fr 1fr;gap:.75rem 1rem}" +
      ".student-reg-form .full-row{grid-column:1/-1}" +
      "@media(max-width:700px){.student-reg-form.grid-form{grid-template-columns:1fr}}";
    document.head.appendChild(s);
  }

  function clearPhoto() {
    var hidden = document.getElementById("stPhotoData");
    var preview = document.getElementById("photoPreview");
    var ph = document.getElementById("photoPlaceholder");
    var file = document.getElementById("photoFileInput");
    if (hidden) hidden.value = "";
    if (preview) {
      preview.removeAttribute("src");
      preview.style.display = "none";
    }
    if (ph) ph.style.display = "";
    if (file) file.value = "";
  }

  /* ---------- IndexedDB for directory handle (Chrome/Edge) ---------- */
  function idbOpen() {
    return new Promise(function (resolve, reject) {
      var req = indexedDB.open(DIR_DB, 1);
      req.onupgradeneeded = function () {
        var db = req.result;
        if (!db.objectStoreNames.contains(DIR_STORE)) db.createObjectStore(DIR_STORE);
      };
      req.onsuccess = function () {
        resolve(req.result);
      };
      req.onerror = function () {
        reject(req.error);
      };
    });
  }

  async function idbGet(key) {
    try {
      var db = await idbOpen();
      return await new Promise(function (resolve, reject) {
        var tx = db.transaction(DIR_STORE, "readonly");
        var r = tx.objectStore(DIR_STORE).get(key);
        r.onsuccess = function () {
          resolve(r.result || null);
        };
        r.onerror = function () {
          reject(r.error);
        };
      });
    } catch (_) {
      return null;
    }
  }

  async function idbSet(key, val) {
    try {
      var db = await idbOpen();
      await new Promise(function (resolve, reject) {
        var tx = db.transaction(DIR_STORE, "readwrite");
        tx.objectStore(DIR_STORE).put(val, key);
        tx.oncomplete = function () {
          resolve();
        };
        tx.onerror = function () {
          reject(tx.error);
        };
      });
    } catch (_) {}
  }

  async function ensureStudentsDir() {
    if (!window.showDirectoryPicker) return null;
    var handle = await idbGet(DIR_KEY);
    if (handle) {
      try {
        var q = await handle.queryPermission({ mode: "readwrite" });
        if (q === "granted") return handle;
        var r = await handle.requestPermission({ mode: "readwrite" });
        if (r === "granted") return handle;
      } catch (_) {
        handle = null;
      }
    }
    alert(
      "Лутфан папкаи «" +
        FOLDER_HINT +
        "»-ро интихоб кунед.\n\nАгар нест: дар равзана New folder созед, ном гузоред «" +
        FOLDER_HINT +
        "», сипас интихоб кунед.\n\nИн фақат дар компютери шумо нигоҳ дошта мешавад (на дар сервер)."
    );
    handle = await window.showDirectoryPicker({
      id: "geografia-students-info",
      mode: "readwrite",
      startIn: "documents",
    });
    await idbSet(DIR_KEY, handle);
    return handle;
  }

  function safeFileName(s) {
    return String(s || "student")
      .replace(/[\\/:*?"<>|]+/g, "_")
      .replace(/\s+/g, "_")
      .slice(0, 80);
  }

  function buildStudentCardHtml(st) {
    var id = st.id || "";
    var full = st.fullName || [st.lastName, st.firstName, st.patronymic].filter(Boolean).join(" ");
    var photo = st.photoData || "";
    var photoBlock = photo
      ? '<img src="' + photo + '" alt="photo" style="width:140px;height:140px;object-fit:cover;border-radius:8px;border:1px solid #ccc"/>'
      : '<div style="width:140px;height:140px;border:1px dashed #aaa;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#888">Без сурат</div>';
    var rows = [
      ["ID (барои воридшавӣ)", id],
      ["Насаб", st.lastName || ""],
      ["Ном", st.firstName || ""],
      ["Номи падар", st.patronymic || ""],
      ["Таваллуд", st.birthDate || ""],
      ["Суроға", st.address || ""],
      ["Муассиса / Мактаб", st.school || ""],
      ["Синф", st.className || ""],
      ["Омӯзгор", st.teacher || ""],
      ["Санаи бақайдгирӣ", new Date().toLocaleString("tg-TJ")],
    ];
    var table = rows
      .map(function (r) {
        return (
          "<tr><td style=\"padding:6px 10px;border:1px solid #ddd;width:40%;background:#f7f7f7\"><b>" +
          esc(r[0]) +
          "</b></td><td style=\"padding:6px 10px;border:1px solid #ddd\">" +
          esc(r[1]) +
          "</td></tr>"
        );
      })
      .join("");
    return (
      "<!DOCTYPE html><html lang=\"tg\"><head><meta charset=\"utf-8\"/>" +
      "<title>Хонанда — " +
      esc(full) +
      "</title>" +
      "<style>body{font-family:Segoe UI,Tahoma,sans-serif;max-width:720px;margin:24px auto;padding:0 16px;color:#111}" +
      "h1{font-size:1.25rem;margin:0 0 8px}.idbox{font-size:1.35rem;letter-spacing:1px;font-family:Consolas,monospace;background:#111;color:#fff;padding:10px 14px;border-radius:8px;display:inline-block;margin:12px 0}" +
      "@media print{button{display:none!important}body{margin:0}}</style></head><body>" +
      "<button onclick=\"window.print()\" style=\"padding:8px 14px;margin-bottom:12px;cursor:pointer\">Чоп / Save as PDF</button>" +
      "<h1>Маълумоти хонанда — Geografia</h1>" +
      "<p style=\"color:#555;margin:0 0 12px\">Ин варақро чоп кунед ё «Save as PDF» интихоб кунед.</p>" +
      "<div style=\"display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap\">" +
      photoBlock +
      "<div><div class=\"idbox\">" +
      esc(id) +
      "</div><div style=\"font-size:1.1rem;font-weight:600\">" +
      esc(full) +
      "</div></div></div>" +
      "<table style=\"width:100%;border-collapse:collapse;margin-top:18px\">" +
      table +
      "</table>" +
      "<p style=\"margin-top:24px;font-size:0.85rem;color:#666\">Папка: " +
      esc(FOLDER_HINT) +
      " · Фақат дар компютери админ</p>" +
      "</body></html>"
    );
  }

  async function writeFileToDir(dirHandle, fileName, contents, mime) {
    var fh = await dirHandle.getFileHandle(fileName, { create: true });
    var w = await fh.createWritable();
    await w.write(new Blob([contents], { type: mime || "text/html;charset=utf-8" }));
    await w.close();
  }

  async function saveStudentLocalCopy(st) {
    var html = buildStudentCardHtml(st);
    var base =
      safeFileName((st.lastName || "") + "_" + (st.firstName || "") + "_" + (st.id || "")) ||
      safeFileName(st.id || "student");
    var htmlName = base + ".html";
    var txtName = base + ".txt";
    var txt =
      "ID: " +
      (st.id || "") +
      "\nНасаб: " +
      (st.lastName || "") +
      "\nНом: " +
      (st.firstName || "") +
      "\nНоми падар: " +
      (st.patronymic || "") +
      "\nТаваллуд: " +
      (st.birthDate || "") +
      "\nСуроға: " +
      (st.address || "") +
      "\nМактаб: " +
      (st.school || "") +
      "\nСинф: " +
      (st.className || "") +
      "\nОмӯзгор: " +
      (st.teacher || "") +
      "\nСана: " +
      new Date().toISOString() +
      "\n";

    try {
      var dir = await ensureStudentsDir();
      if (dir) {
        await writeFileToDir(dir, htmlName, html, "text/html;charset=utf-8");
        await writeFileToDir(dir, txtName, txt, "text/plain;charset=utf-8");
        return { ok: true, mode: "folder", name: htmlName };
      }
    } catch (e) {
      console.warn("local folder save", e);
    }

    // Fallback: download to Downloads (browser cannot create arbitrary folders without permission)
    try {
      var a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([html], { type: "text/html;charset=utf-8" }));
      a.download = htmlName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      return { ok: true, mode: "download", name: htmlName };
    } catch (e2) {
      return { ok: false, error: String(e2) };
    }
  }

  function csvEscape(v) {
    var s = String(v == null ? "" : v);
    if (/[",\n\r]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  }

  async function exportStudentsCsv() {
    var data = await api("/api/admin/students");
    var list = data.students || [];
    var headers = [
      "ID",
      "Насаб",
      "Ном",
      "Номи падар",
      "Номи пурра",
      "Таваллуд",
      "Суроға",
      "Мактаб",
      "Синф",
      "Омӯзгор",
      "Сурат",
      "Сана",
    ];
    var lines = [headers.join(",")];
    list.forEach(function (s) {
      lines.push(
        [
          s.id,
          s.lastName,
          s.firstName,
          s.patronymic,
          s.fullName,
          s.birthDate,
          s.address,
          s.school,
          s.className,
          s.teacher,
          s.hasPhoto ? "ҳа" : "не",
          (s.createdAt || "").toString().slice(0, 19).replace("T", " "),
        ]
          .map(csvEscape)
          .join(",")
      );
    });
    var bom = "\ufeff";
    var blob = new Blob([bom + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "students_" + new Date().toISOString().slice(0, 10) + ".csv";
    a.click();

    // Also try save into local folder
    try {
      var dir = await ensureStudentsDir();
      if (dir) {
        await writeFileToDir(
          dir,
          "рӯйхат_хонандагон_" + new Date().toISOString().slice(0, 10) + ".csv",
          bom + lines.join("\r\n"),
          "text/csv;charset=utf-8"
        );
      }
    } catch (_) {}
  }

  async function registerStudent(e) {
    if (e && e.preventDefault) e.preventDefault();
    if (e && e.stopImmediatePropagation) e.stopImmediatePropagation();
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
    if (!lastName || !firstName) {
      var m1 = "Насаб ва Ном ҳатмӣ мебошанд.";
      if (msg) {
        msg.textContent = m1;
        msg.classList.remove("hidden");
        msg.classList.add("error");
      } else alert(m1);
      return false;
    }
    if (!className || !school) {
      var m2 = "Синф ва Мактаб ҳатмӣ мебошанд.";
      if (msg) {
        msg.textContent = m2;
        msg.classList.remove("hidden");
        msg.classList.add("error");
      } else alert(m2);
      return false;
    }
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
      s.lastName = s.lastName || lastName;
      s.firstName = s.firstName || firstName;
      s.patronymic = s.patronymic || patronymic;
      s.birthDate = s.birthDate || birthDate;
      s.address = s.address || address;
      s.school = s.school || school;
      s.className = s.className || className;
      s.teacher = s.teacher || teacher;
      s.photoData = photoData || s.photoData || "";
      s.fullName = s.fullName || fullName;

      var box = document.getElementById("newIdBox");
      if (box) box.classList.remove("hidden");
      var nn = document.getElementById("newIdName");
      var nv = document.getElementById("newIdValue");
      if (nn) nn.textContent = s.fullName || fullName;
      if (nv) nv.textContent = s.id || "";

      var saveRes = await saveStudentLocalCopy(s);
      if (saveRes && saveRes.ok) {
        if (msg) {
          msg.textContent =
            saveRes.mode === "folder"
              ? "Сабт шуд. Нусха дар папкаи «" + FOLDER_HINT + "»: " + saveRes.name
              : "Сабт шуд. Нусхаи HTML зеркашӣ шуд (" + saveRes.name + "). Барои папка Chrome/Edge истифода баред.";
          msg.classList.remove("hidden", "error");
          msg.classList.add("ok");
        }
      }

      var formEl = document.getElementById("studentForm");
      if (formEl) formEl.reset();
      clearPhoto();
      loadStudentsLocal();
    } catch (err) {
      if (msg) {
        msg.textContent = err.message || String(err);
        msg.classList.remove("hidden");
        msg.classList.add("error");
      } else alert(err.message || String(err));
    }
    return false;
  }
  window.__geoRegisterStudent = registerStudent;

  function bind() {
    var form = document.getElementById("studentForm");
    if (form) {
      form.setAttribute("action", "javascript:void(0)");
      form.setAttribute("onsubmit", "return false;");
      form.addEventListener(
        "submit",
        function (e) {
          e.preventDefault();
          e.stopImmediatePropagation();
          registerStudent(e);
          return false;
        },
        true
      );
    }
    var btnReg = document.getElementById("btnRegisterStudent");
    if (btnReg) {
      btnReg.type = "button";
      btnReg.addEventListener("click", function (e) {
        e.preventDefault();
        registerStudent(e);
      });
    }

    document.querySelectorAll(".tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (btn.dataset.tab === "students") loadStudentsLocal();
      });
    });

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
          await exportStudentsCsv();
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
