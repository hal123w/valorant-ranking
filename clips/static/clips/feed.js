(function () {
  function getCsrfToken() {
    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function recordView(card) {
    var url = card.getAttribute("data-view-url");
    if (!url || card.dataset.viewSent === "1") return;
    card.dataset.viewSent = "1";

    fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCsrfToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
    })
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        if (!data || typeof data.view_count === "undefined") return;
        var el = card.querySelector(".view-count");
        if (el) el.textContent = data.view_count;
      })
      .catch(function () {
        card.dataset.viewSent = "0";
      });
  }

  // --- Report panels ---
  document.querySelectorAll(".report-toggle").forEach(function (btn) {
    btn.addEventListener("click", function (event) {
      event.stopPropagation();
      var panelId = btn.getAttribute("aria-controls");
      var panel = document.getElementById(panelId);
      if (!panel) return;
      var willOpen = panel.hasAttribute("hidden");
      document.querySelectorAll(".report-panel").forEach(function (p) {
        p.setAttribute("hidden", "");
      });
      document.querySelectorAll(".report-toggle").forEach(function (b) {
        b.setAttribute("aria-expanded", "false");
      });
      if (willOpen) {
        panel.removeAttribute("hidden");
        btn.setAttribute("aria-expanded", "true");
      }
    });
  });

  document.addEventListener("click", function () {
    document.querySelectorAll(".report-panel").forEach(function (p) {
      p.setAttribute("hidden", "");
    });
    document.querySelectorAll(".report-toggle").forEach(function (b) {
      b.setAttribute("aria-expanded", "false");
    });
  });

  document.querySelectorAll(".report-panel").forEach(function (panel) {
    panel.addEventListener("click", function (event) {
      event.stopPropagation();
    });
  });

  // First click on embed area: count view, then unlock X embed for play
  document.querySelectorAll(".clip-card").forEach(function (card) {
    var catcher = card.querySelector(".embed-click-catcher");
    if (!catcher) return;
    catcher.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      recordView(card);
      catcher.remove();
    });
  });

  // Keep embeds inside the viewport (no fixed px card widths that overflow on phones)
  function constrainEmbeds() {
    document.querySelectorAll(".clip-card").forEach(function (card) {
      card.style.width = "";
      card.style.maxWidth = "100%";
      var iframe = card.querySelector(".embed-wrap iframe");
      if (!iframe) return;
      iframe.style.width = "100%";
      iframe.style.maxWidth = "100%";
      iframe.removeAttribute("width");
    });
  }

  function whenTwitterReady(cb) {
    if (window.twttr && window.twttr.ready) {
      window.twttr.ready(cb);
      return;
    }
    var tries = 0;
    var timer = setInterval(function () {
      tries += 1;
      if (window.twttr && window.twttr.ready) {
        clearInterval(timer);
        window.twttr.ready(cb);
      } else if (tries > 40) {
        clearInterval(timer);
      }
    }, 250);
  }

  whenTwitterReady(function (twttr) {
    constrainEmbeds();
    if (twttr.events && twttr.events.bind) {
      twttr.events.bind("rendered", function () {
        constrainEmbeds();
      });
    }
    setTimeout(constrainEmbeds, 400);
    setTimeout(constrainEmbeds, 1200);
  });

  var resizeTimer = null;
  window.addEventListener("resize", function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(constrainEmbeds, 180);
  });
})();
