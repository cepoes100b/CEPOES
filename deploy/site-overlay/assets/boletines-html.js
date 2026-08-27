/* CEPOES · Boletín — comportamiento mínimo.
   Sin dependencias. Degrada bien: si el JS no carga, la página se lee igual. */
(function () {
  "use strict";

  var root = document.querySelector(".bol");
  if (!root) return;
  root.classList.add("bol-js");

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* --- 1. Barra de progreso de lectura ------------------------------------ */
  var bar = root.querySelector(".bol-progress__bar");
  var ticking = false;

  function progreso() {
    if (!bar) return;
    var alto = document.documentElement.scrollHeight - window.innerHeight;
    var pct = alto > 0 ? (window.scrollY / alto) * 100 : 0;
    bar.style.width = Math.min(100, Math.max(0, pct)).toFixed(2) + "%";
  }

  /* --- 2. Scrollspy del riel de ejes -------------------------------------- */
  var links = Array.prototype.slice.call(root.querySelectorAll(".bol-riel__link"));
  var secciones = links
    .map(function (a) {
      var id = a.getAttribute("href");
      return id && id.charAt(0) === "#" ? document.getElementById(id.slice(1)) : null;
    })
    .filter(Boolean);

  var progressWrap = root.querySelector(".bol-progress");

  function marcarActiva() {
    var y = window.scrollY + window.innerHeight * 0.28;
    var activa = -1;
    for (var i = 0; i < secciones.length; i++) {
      if (secciones[i].offsetTop <= y) activa = i;
    }
    links.forEach(function (a, i) {
      if (i === activa) a.setAttribute("aria-current", "true");
      else a.removeAttribute("aria-current");
    });
    // El progreso toma el color del eje que se está leyendo
    if (progressWrap) {
      var eje = activa >= 0 ? secciones[activa].getAttribute("data-eje") : null;
      if (eje) progressWrap.setAttribute("data-eje", eje);
      else progressWrap.removeAttribute("data-eje");
    }
    // Mantener visible la píldora activa en el scroller horizontal
    if (activa >= 0 && links[activa].scrollIntoView) {
      var lista = links[activa].parentNode;
      if (lista && lista.scrollWidth > lista.clientWidth) {
        var l = links[activa];
        var izq = l.offsetLeft - lista.clientWidth / 2 + l.clientWidth / 2;
        lista.scrollTo({ left: izq, behavior: reduce ? "auto" : "smooth" });
      }
    }
  }

  function onScroll() {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(function () {
      progreso();
      marcarActiva();
      ticking = false;
    });
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  onScroll();

  /* --- 3. Aparición progresiva -------------------------------------------- */
  var revelables = root.querySelectorAll("[data-reveal]");
  if (reduce || !("IntersectionObserver" in window)) {
    Array.prototype.forEach.call(revelables, function (el) { el.classList.add("is-visible"); });
  } else {
    var io = new IntersectionObserver(
      function (entradas) {
        entradas.forEach(function (e) {
          if (e.isIntersecting) {
            e.target.classList.add("is-visible");
            io.unobserve(e.target);
          }
        });
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.06 }
    );
    Array.prototype.forEach.call(revelables, function (el) { io.observe(el); });
  }

  /* --- 4. Copiar la cita sugerida ----------------------------------------- */
  var btnCita = root.querySelector("[data-copiar-cita]");
  if (btnCita && navigator.clipboard) {
    btnCita.addEventListener("click", function () {
      var texto = root.querySelector(".bol-cita");
      if (!texto) return;
      navigator.clipboard.writeText(texto.textContent.trim()).then(function () {
        var original = btnCita.textContent;
        btnCita.textContent = "Cita copiada";
        setTimeout(function () { btnCita.textContent = original; }, 2200);
      });
    });
  }
})();
