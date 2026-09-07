(function () {
  const body = document.body;
  const toggle = document.querySelector("[data-nav-toggle]");
  const backdrop = document.querySelector("[data-nav-backdrop]");
  if (toggle) {
    toggle.addEventListener("click", function () {
      body.classList.toggle("nav-open");
    });
  }
  if (backdrop) {
    backdrop.addEventListener("click", function () {
      body.classList.remove("nav-open");
    });
  }

  document.querySelectorAll("[data-dismiss]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const flash = btn.closest(".flash");
      if (flash) flash.remove();
    });
  });

  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("submit", function (event) {
      const message = el.getAttribute("data-confirm");
      if (message && !window.confirm(message)) event.preventDefault();
    });
  });

  document.querySelectorAll("[data-toggle-password]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const input = document.getElementById(btn.getAttribute("data-toggle-password"));
      if (!input) return;
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.textContent = show ? "Hide" : "Show";
    });
  });

  document.querySelectorAll("[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const text = btn.getAttribute("data-copy");
      if (!text) return;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () {
          const previous = btn.textContent;
          btn.textContent = "Copied";
          setTimeout(function () { btn.textContent = previous; }, 1500);
        });
      } else {
        window.prompt("Copy this link", text);
      }
    });
  });

  const idleSeconds = parseInt(body.getAttribute("data-idle-timeout") || "0", 10);
  const logoutUrl = body.getAttribute("data-logout-url");
  if (idleSeconds > 0 && logoutUrl) {
    let idleTimer;
    const idleLogout = function () {
      const form = document.createElement("form");
      form.method = "post";
      form.action = logoutUrl;
      form.style.display = "none";
      const csrf = document.querySelector("[name=csrfmiddlewaretoken]");
      if (csrf) {
        const token = document.createElement("input");
        token.type = "hidden";
        token.name = "csrfmiddlewaretoken";
        token.value = csrf.value;
        form.appendChild(token);
      }
      const reason = document.createElement("input");
      reason.type = "hidden";
      reason.name = "reason";
      reason.value = "inactivity";
      form.appendChild(reason);
      document.body.appendChild(form);
      form.submit();
    };
    const bumpIdle = function () {
      window.clearTimeout(idleTimer);
      idleTimer = window.setTimeout(idleLogout, idleSeconds * 1000);
    };
    ["click", "keydown", "mousemove", "scroll", "touchstart"].forEach(function (eventName) {
      document.addEventListener(eventName, bumpIdle, { passive: true });
    });
    bumpIdle();
  }

  const dirtyForms = document.querySelectorAll("form[data-dirty-guard]");
  dirtyForms.forEach(function (form) {
    let dirty = false;
    form.addEventListener("input", function () {
      dirty = true;
    });
    form.addEventListener("submit", function () {
      dirty = false;
    });
    window.addEventListener("beforeunload", function (event) {
      if (dirty) {
        event.preventDefault();
        event.returnValue = "";
      }
    });
  });
})();
