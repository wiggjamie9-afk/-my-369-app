/* 48 AI Crew Quoting: put a business's quote page on its own website.
   <script src="https://your-domain/embed.js" data-business="your-link-name" async></script>
   It adds an iframe where the script tag is, and grows it to fit. It reads nothing from your page. */
(function () {
  "use strict";
  var script = document.currentScript;
  if (!script || !script.src) return;
  var slug = script.getAttribute("data-business");
  if (!slug || !/^[a-z0-9-]{3,40}$/.test(slug)) return;
  var origin = new URL(script.src).origin;

  var frame = document.createElement("iframe");
  frame.src = origin + "/q/" + slug + "/?embed=1";
  frame.title = script.getAttribute("data-title") || "Get an instant price";
  frame.setAttribute("scrolling", "no");
  frame.setAttribute("loading", "lazy");
  frame.style.cssText = "display:block;width:100%;max-width:640px;margin:0 auto;border:0;border-radius:16px;min-height:520px;color-scheme:dark";
  script.parentNode.insertBefore(frame, script.nextSibling);

  window.addEventListener("message", function (e) {
    // only listen to our own frame, on our own origin
    if (e.origin !== origin || e.source !== frame.contentWindow || !e.data || typeof e.data !== "object") return;
    if (e.data.qm === "height" && typeof e.data.h === "number" && e.data.h > 100 && e.data.h < 20000) {
      frame.style.height = Math.ceil(e.data.h) + "px";
    } else if (e.data.qm === "top") {                         // a new step opened: bring the top of the widget into view
      var top = frame.getBoundingClientRect().top;
      if (top < 0) window.scrollTo({ top: window.pageYOffset + top - 8, behavior: "smooth" });
    }
  });
})();
