/* Student registration + ALWAYS local download + optional folder */
(function () {
  const TOKEN_KEY = "geo_admin_token";
  const DIR_DB = "geografia_admin_fs";
  const DIR_STORE = "handles";
  const DIR_KEY = "students_info_dir";
  const FOLDER_HINT = "Малумотхои хонандагон";

  var _regLock = false;
  var _dirMemory = null; // FileSystemDirectoryHandle when granted

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

  function forceDownload(filename, text, mime) {
    try {
      var blob = new Blob([text], { type: mime || "text/plain;charset=utf-8" });
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.style.display = "none";
      document.body.appendChild(a);
      a.click();
      setTimeout(function () {
        try {
          URL.revokeObjectURL(url);
        } catch (_) {}
        a.remove();
      }, 1500);
      return true;
    } catch (e) {
      console.error("forceDownload", e);
      return false;
    }
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
      ? '<img src="' +
        photo +
        '" alt="photo" style="width:140px;height:140px;object-fit:cover;border-radius:8px;border:1px solid #ccc"/>'
      : '<div style="width:140px;height:140px;border:1px dashed #aaa;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#888">Бе сурат</div>';
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
      ["Санаи бақайдгирӣ", new Date().toLocaleString()],
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
      "<p style=\"color:#555\">Чоп кунед ё Save as PDF.</p>" +
      "<div style=\"display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap\">" +
      photoBlock +
      "<div><div class=\"idbox\">" +
      esc(id) +
      "</div><div style=\"font-size:1.1rem;font-weight:600\">" +
      esc(full) +
      "</div></div></div>" +
      "<table style=\"width:100%;border-collapse:collapse;margin-top:18px\">" +
      table +
      "</table></body></html>"
    );
  }

  function buildStudentTxt(st) {
    return (
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
      "\n"
    );
  }

  async function writeFileToDir(dirHandle, fileName, contents, mime) {
    var fh = await dirHandle.getFileHandle(fileName, { create: true });
    var w = await fh.createWritable();
    await w.write(new Blob([contents], { type: mime || "text/plain;charset=utf-8" }));
    await w.close();
  }

  async function tryRestoreDir() {
    if (_dirMemory) return _dirMemory;
    if (!window.showDirectoryPicker) return null;
    try {
      var handle = await idbGet(DIR_KEY);
      if (!handle) return null;
      var q = await handle.queryPermission({ mode: "readwrite" });
      if (q === "granted") {
        _dirMemory = handle;
        return handle;
      }
    } catch (_) {}
    return null;
  }

  /** Must be called from a click handler (user gesture). */
  async function pickStudentsFolder() {
    if (!window.showDirectoryPicker) {
      alert(
        "Браузери шумо интихоби папкаро дастгирӣ намекунад.\nChrome ё Edge истифода баред.\nҲоло файлҳо ба Downloads зеркашӣ мешаванд."
      );
      updateFolderStatus(false);
      return null;
    }
    try {
      alert(
        "Папкаи «" +
          FOLDER_HINT +
          "»-ро интихоб кунед.\nАгар нест: New folder → ном «" +
          FOLDER_HINT +
          "» → Select."
      );
      var handle = await window.showDirectoryPicker({
        id: "geografia-students-info",
        mode: "readwrite",
        startIn: "documents",
      });
      _dirMemory = handle;
      await idbSet(DIR_KEY, handle);
      updateFolderStatus(true);
      alert("Папка пайваст шуд: «" + FOLDER_HINT + "». Акнун ҳар бақайдгирӣ он ҷо низ захира мешавад.");
      return handle;
    } catch (e) {
      if (e && e.name === "AbortError") {
        alert("Интихоби папка бекор шуд.");
      } else {
        alert("Папка: " + (e && e.message ? e.message : e));
      }
      updateFolderStatus(!!_dirMemory);
      return null;
    }
  }

  function updateFolderStatus(ok) {
    var el = document.getElementById("localFolderStatus");
    if (!el) return;
    el.textContent = ok
      ? "Папка пайваст: «" + FOLDER_HINT + "» ✓"
      : "Папка ҳанӯз интихоб нашудааст — файлҳо ба Downloads мераванд. Тугмаи «Папкаи маҳаллӣ»-ро пахш кунед.";
    el.style.color = ok ? "#0a7a4c" : "#a60";
  }

  async function saveStudentLocalCopy(st) {
    var html = buildStudentCardHtml(st);
    var txt = buildStudentTxt(st);
    var base =
      safeFileName((st.lastName || "") + "_" + (st.firstName || "") + "_" + (st.id || "")) ||
      safeFileName(st.id || "student");
    var htmlName = base + ".html";
    var txtName = base + ".txt";

    // 1) ALWAYS download (works in all browsers after async)
    var d1 = forceDownload(htmlName, html, "text/html;charset=utf-8");
    var d2 = forceDownload(txtName, txt, "text/plain;charset=utf-8");

    // 2) Also write to folder if already connected
    var folderOk = false;
    try {
      var dir = _dirMemory || (await tryRestoreDir());
      if (dir) {
        await writeFileToDir(dir, htmlName, html, "text/html;charset=utf-8");
        await writeFileToDir(dir, txtName, txt, "text/plain;charset=utf-8");
        folderOk = true;
        _dirMemory = dir;
      }
    } catch (e) {
      console.warn("folder write", e);
      folderOk = false;
    }

    return {
      ok: d1 || d2 || folderOk,
      mode: folderOk ? "folder+download" : "download",
      name: htmlName,
    };
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
    var body = bom + lines.join("\r\n");
    var fname = "students_" + new Date().toISOString().slice(0, 10) + ".csv";
    forceDownload(fname, body, "text/csv;charset=utf-8");

    try {
      var dir = _dirMemory || (await tryRestoreDir());
      if (dir) {
        await writeFileToDir(dir, fname, body, "text/csv;charset=utf-8");
      }
    } catch (_) {}

    alert("CSV зеркашӣ шуд: " + fname + " (" + list.length + " хонанда, сохтори нав).");
  }
  window.__geoExportStudents = exportStudentsCsv;
  window.__geoPickStudentsFolder = pickStudentsFolder;

  async function registerStudent(e) {
    if (e && e.preventDefault) e.preventDefault();
    if (e && e.stopImmediatePropagation) e.stopImmediatePropagation();
    if (_regLock) return false;
    _regLock = true;

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
      if (!lastName || !firstName) throw new Error("Насаб ва Ном ҳатмӣ мебошанд.");
      if (!className || !school) throw new Error("Синф ва Мактаб ҳатмӣ мебошанд.");

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
      var info =
        "ID сохта шуд. Файлҳои .html ва .txt ба Downloads зеркашӣ шуданд" +
        (saveRes && saveRes.mode === "folder+download"
          ? " ва ба папкаи «" + FOLDER_HINT + "» ҳам навишта шуданд."
          : ". Барои папка: тугмаи «Папкаи маҳаллӣ».");
      if (msg) {
        msg.textContent = info;
        msg.classList.remove("hidden", "error");
        msg.classList.add("ok");
      } else {
        alert(info);
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
    } finally {
      _regLock = false;
    }
    return false;
  }
  window.__geoRegisterStudent = registerStudent;

  function bind() {
    var form = document.getElementById("studentForm");
    if (form) {
      form.setAttribute("action", "javascript:void(0)");
      form.onsubmit = function (e) {
        e.preventDefault();
        registerStudent(e);
        return false;
      };
    }
    var btnReg = document.getElementById("btnRegisterStudent");
    if (btnReg) {
      btnReg.type = "button";
      btnReg.onclick = function (e) {
        e.preventDefault();
        registerStudent(e);
      };
    }
    var exportBtn = document.getElementById("exportStudentsBtn");
    if (exportBtn) {
      exportBtn.type = "button";
      exportBtn.onclick = function (e) {
        e.preventDefault();
        exportStudentsCsv().catch(function (err) {
          alert(err.message || String(err));
        });
      };
    }
    var pickBtn = document.getElementById("btnPickStudentsFolder");
    if (pickBtn) {
      pickBtn.onclick = function (e) {
        e.preventDefault();
        pickStudentsFolder();
      };
    }

    var copyBtn = document.getElementById("copyIdBtn");
    if (copyBtn) {
      copyBtn.onclick = async function () {
        var v = (document.getElementById("newIdValue") || {}).textContent || "";
        if (!v) return;
        try {
          await navigator.clipboard.writeText(v);
          alert("ID нусха шуд");
        } catch (_) {
          prompt("Нусха кунед:", v);
        }
      };
    }

    document.querySelectorAll(".tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (btn.dataset.tab === "students") {
          loadStudentsLocal();
          tryRestoreDir().then(function (d) {
            updateFolderStatus(!!d);
          });
        }
      });
    });

    tryRestoreDir().then(function (d) {
      updateFolderStatus(!!d);
    });
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
                "<tr><td><code>" +
                esc(s.id) +
                "</code></td><td>" +
                esc(s.fullName || "") +
                "</td><td>" +
                esc(s.className) +
                "</td><td>" +
                esc(s.school) +
                "</td><td>" +
                esc(s.teacher || "") +
                "</td><td>" +
                (s.hasPhoto ? "✓" : "—") +
                '</td><td><button type="button" class="btn small danger" data-del-student="' +
                esc(s.id) +
                '">Нест</button></td></tr>'
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
