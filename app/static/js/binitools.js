(function () {
  "use strict";

  var MAX_UPLOAD_FILES = 20;

  function biniToast(msg) {
    var el = document.getElementById("bini-toast");
    if (!el) {
      window.alert(msg);
      return;
    }
    el.textContent = msg;
    el.removeAttribute("hidden");
    el.classList.add("bini-toast--on");
    window.clearTimeout(el._biniTid);
    el._biniTid = window.setTimeout(function () {
      el.classList.remove("bini-toast--on");
    }, 1800);
  }

  function biniCopyAllTextarea() {
    var t = document.getElementById("text-content");
    if (!t) return;
    if (!t.value) {
      biniToast("Nada para copiar");
      return;
    }
    if (!navigator.clipboard) {
      biniToast("Não dá para copiar neste browser");
      return;
    }
    navigator.clipboard.writeText(t.value).then(
      function () {
        biniToast("Tudo copiado");
      },
      function () {
        biniToast("Falhou ao copiar");
      }
    );
  }

  function biniCopyImageUrl(url) {
    if (!url) {
      biniToast("Cópia indisponível");
      return;
    }
    if (!navigator.clipboard || !window.ClipboardItem) {
      biniToast("Este browser não copia imagens (precisa de contexto seguro e suporte).");
      return;
    }
    fetch(url, { method: "GET", credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("http");
        return r.blob();
      })
      .then(function (blob) {
        var t = blob.type;
        if (!t || t === "application/octet-stream") t = "image/png";
        var m = {};
        m[t] = blob;
        return navigator.clipboard.write([new ClipboardItem(m)]);
      })
      .then(
        function () {
          biniToast("Imagem copiada");
        },
        function () {
          biniToast("Falhou ao copiar imagem");
        }
      );
  }

  function biniCopyTextFallback(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    var ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (e) {
      ok = false;
    }
    document.body.removeChild(ta);
    return ok;
  }

  function biniCopyPublicUrl(url) {
    if (!url) {
      biniToast("Link indisponível");
      return;
    }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(url).then(
        function () {
          biniToast("Link copiado");
        },
        function () {
          if (biniCopyTextFallback(url)) return;
          biniToast("Falhou ao copiar o link");
        }
      );
      return;
    }
    if (biniCopyTextFallback(url)) return;
    biniToast("Não foi possível copiar neste navegador");
  }

  function biniCopyTextId(id) {
    if (!id || !navigator.clipboard) {
      biniToast("Cópia indisponível");
      return;
    }
    fetch("/t/" + id + "/raw", { method: "GET", credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("http");
        return r.json();
      })
      .then(function (j) {
        if (!j || !j.ok) throw new Error("bad");
        return navigator.clipboard.writeText(j.text || "");
      })
      .then(
        function () {
          biniToast("Texto copiado");
        },
        function () {
          biniToast("Falhou ao copiar");
        }
      );
  }

  function biniTextQuickDelete() {
    var hid = document.getElementById("text-id");
    var tid = hid && String(hid.value).trim();
    if (tid) {
      if (!window.confirm("Apagar este texto guardado?")) return;
      var f = document.createElement("form");
      f.method = "POST";
      f.action = "/t/" + encodeURIComponent(tid) + "/delete";
      document.body.appendChild(f);
      f.submit();
      return;
    }
    var t = document.getElementById("text-content");
    if (t) t.value = "";
  }

  document.addEventListener("click", function (e) {
    var copyImg = e.target && e.target.closest
      ? e.target.closest("[data-bini-copy-image]")
      : null;
    if (copyImg) {
      e.preventDefault();
      biniCopyImageUrl(copyImg.getAttribute("data-bini-copy-image"));
      return;
    }
    var copyPub = e.target && e.target.closest
      ? e.target.closest("[data-bini-copy-public]")
      : null;
    if (copyPub) {
      e.preventDefault();
      biniCopyPublicUrl(copyPub.getAttribute("data-bini-copy-public"));
      return;
    }
    var btn = e.target && e.target.closest
      ? e.target.closest("[data-copy-text-id]")
      : null;
    if (!btn) return;
    e.preventDefault();
    var id = parseInt(btn.getAttribute("data-copy-text-id"), 10);
    biniCopyTextId(id);
  });

  function bindClicks() {
    ["bini-copy-all", "bini-copy-all-m"].forEach(function (id) {
      var a = document.getElementById(id);
      if (a) a.addEventListener("click", biniCopyAllTextarea);
    });
    ["bini-text-quick-del", "bini-text-quick-del-m"].forEach(function (id) {
      var a = document.getElementById(id);
      if (a) a.addEventListener("click", biniTextQuickDelete);
    });
  }

  document.addEventListener("DOMContentLoaded", bindClicks);
  document.body.addEventListener("htmx:afterSettle", function (e) {
    var ac = document.getElementById("bini-hx-autocopy");
    if (ac && ac.dataset.url) {
      var u = ac.dataset.url;
      if (navigator.clipboard && u) {
        navigator.clipboard.writeText(u).then(
          function () {
            biniToast("Link copiado para a área de transferência");
          },
          function () {
            biniToast("Guardado. Copia o link no cartão se precisares.");
          }
        );
      }
      ac.remove();
    }
    if (!e.detail || !e.detail.elt) return;
    if (e.detail.elt.id === "bini-img-form" || e.detail.elt.id === "bini-doc-form") {
      e.detail.elt.reset();
      var prog = e.detail.elt.querySelector(".bini-progress");
      if (prog) prog.style.display = "none";
    }
  });
  document.body.addEventListener("htmx:beforeRequest", function (e) {
    if (!e.detail || !e.detail.elt) return;
    if (e.detail.elt.id === "bini-img-form" || e.detail.elt.id === "bini-doc-form") {
      var inp = e.detail.elt.querySelector('input[type="file"]');
      if (inp && inp.files && inp.files.length > MAX_UPLOAD_FILES) {
        e.preventDefault();
        var p = e.detail.elt.querySelector("#bini-up-msg");
        var msg = "Máximo de " + MAX_UPLOAD_FILES + " ficheiros por envio.";
        if (p) {
          p.textContent = msg;
          p.classList.add("bini-msg-err");
        } else {
          biniToast(msg);
        }
        return;
      }
      var p = e.detail.elt.querySelector("#bini-up-msg");
      if (p) {
        p.textContent = "A enviar…";
        p.classList.remove("bini-msg-err");
      }
      var prog = e.detail.elt.querySelector(".bini-progress");
      if (prog) {
        prog.value = 0;
        prog.style.display = "block";
      }
    }
  });
  document.body.addEventListener("htmx:xhr:progress", function(e) {
    if (!e.detail || !e.detail.elt) return;
    var prog = e.detail.elt.querySelector(".bini-progress");
    if (prog && e.detail.lengthComputable) {
      prog.style.display = "block";
      prog.value = (e.detail.loaded / e.detail.total) * 100;
    }
  });
  window.biniToast = biniToast;
  window.biniCopyPublicUrl = biniCopyPublicUrl;
})();
