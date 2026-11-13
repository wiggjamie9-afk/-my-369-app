/* Roof Quote Mate - FULL tier add-ons: roof photos, and the buyer's own branding.
   The lite package is this same folder with this one file left out. Without it the
   app runs as lite whatever config.js says, so the tiers can't be swapped by editing a word. */
(function () {
  "use strict";
  var RQM = window.RQM = window.RQM || {};

  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === "text") n.textContent = attrs[k];
      else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), attrs[k]);
      else if (k in n) n[k] = attrs[k];
      else n.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (kid) { if (kid) n.appendChild(kid); });
    return n;
  }

  /* The business's name and logo in the header, on every screen. */
  function brand(header, config) {
    header.textContent = "";
    var b = config.business;
    if (b.logoPath) {
      var img = el("img", { src: b.logoPath, alt: "", className: "brand-logo" });
      img.addEventListener("error", function () { img.remove(); });      // no logo file? name only
      header.appendChild(img);
    }
    header.appendChild(el("span", { className: "brand-name", text: b.name }));
    document.title = b.name + " | Instant ballpark";
  }

  /* Shrink a phone photo before it is sent, so four photos upload on patchy reception. */
  function shrink(file, maxEdge, quality) {
    return new Promise(function (resolve) {
      var url = URL.createObjectURL(file), img = new Image();
      img.onload = function () {
        var scale = Math.min(1, maxEdge / Math.max(img.width, img.height));
        var canvas = document.createElement("canvas");
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
        URL.revokeObjectURL(url);
        canvas.toBlob(function (blob) {
          if (!blob) return resolve(file);
          resolve(new File([blob], file.name.replace(/\.[^.]+$/, "") + ".jpg", { type: "image/jpeg" }));
        }, "image/jpeg", quality);
      };
      img.onerror = function () { URL.revokeObjectURL(url); resolve(file); };   // can't read it: send it as it is
      img.src = url;
    });
  }

  /* The photo picker. Returns { node, files() } where files() gives the shrunk photos. */
  function photos(config) {
    var max = config.photos.max, words = config.words, chosen = [];
    var grid = el("div", { className: "photo-grid" });
    var note = el("p", { className: "small", role: "status" });
    var input = el("input", { type: "file", accept: "image/*", multiple: true, id: "photoInput", className: "visually-hidden" });
    var pick = el("label", { className: "btn btn-outline", htmlFor: "photoInput", text: "Add photos" });

    function draw() {
      grid.textContent = "";
      chosen.forEach(function (item, i) {
        grid.appendChild(el("div", { className: "photo" }, [
          el("img", { src: item.url, alt: "Roof photo " + (i + 1) }),
          el("button", { type: "button", className: "photo-x", "aria-label": "Remove photo " + (i + 1), text: "×",
            onclick: function () { URL.revokeObjectURL(item.url); chosen.splice(i, 1); note.textContent = ""; draw(); } })
        ]));
      });
      pick.textContent = chosen.length ? "Add another (" + chosen.length + " of " + max + ")" : "Add photos";
      pick.hidden = chosen.length >= max;
    }

    input.addEventListener("change", function () {
      var extra = 0;
      Array.prototype.forEach.call(input.files, function (file) {
        if (!/^image\//.test(file.type)) return;
        if (chosen.length >= max) { extra++; return; }
        chosen.push({ file: file, url: URL.createObjectURL(file) });
      });
      note.textContent = extra ? "Only " + max + " photos fit. Left out the last " + extra + "." : "";
      input.value = "";
      draw();
    });

    draw();
    return {
      node: el("div", { className: "photos" }, [
        el("h3", { text: words.photosTitle.replace("4", String(max)) }), el("p", { className: "small", text: words.photosSub }),
        grid, input, pick, note]),
      files: function () {
        return Promise.all(chosen.map(function (item) { return shrink(item.file, config.photos.maxEdgePx, config.photos.quality); }));
      }
    };
  }

  RQM.full = { brand: brand, photos: photos };
})();
