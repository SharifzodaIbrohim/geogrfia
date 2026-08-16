/* Professional student registration — no page reload */
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
    s.textContent =
      ".student-reg-form.grid-form{grid-template-columns:1fr 1fr;gap:.75rem 1rem}" +
      ".student-reg-form .full-row{grid-column:1/-1}" +
      "@media(max-width:700px){.student-reg-form.grid-form{grid-template-columns:1fr}}";
    document.head.appendChild(s);
  }

  function stopCamera() {
    /* camera handled by inline script in admin.html */
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
      var box = document.getElementById("newIdBox");
      if (box) box.classList.remove("hidden");
      var nn = document.getElementById("newIdName");
      var nv = document.getElementById("newIdValue");
      if (nn) nn.textContent = s.fullName || fullName;
      if (nv) nv.textContent = s.id || "";
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
