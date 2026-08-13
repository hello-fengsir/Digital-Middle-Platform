(() => {
  "use strict";
  const directoryPath = "/";
  function safeDirectoryTarget(raw) {
    if (!raw) return null;
    try {
      const target = new URL(raw, window.location.origin);
      if (target.origin !== window.location.origin || target.pathname !== directoryPath) return null;
      return `${target.pathname}${target.search}${target.hash}`;
    } catch {
      return null;
    }
  }
  function resolveReturnTarget() {
    const explicit = new URLSearchParams(window.location.search).get("return");
    return safeDirectoryTarget(explicit) || safeDirectoryTarget(document.referrer) || directoryPath;
  }
  window.TianCangReturn = Object.freeze({ safeDirectoryTarget, resolveReturnTarget });
  document.getElementById("tiancangReturnButton")?.addEventListener("click", () => {
    window.location.assign(resolveReturnTarget());
  });

  // Mobile-visible proxy for PDF.js' own clockwise-rotation command.
  const right = document.getElementById("toolbarViewerRight");
  const secondaryRotate = document.getElementById("pageRotateCw");
  if (right && secondaryRotate && !document.getElementById("tiancangRotateButton")) {
    const rotate = document.createElement("button");
    rotate.id = "tiancangRotateButton";
    rotate.type = "button";
    rotate.tabIndex = 0;
    rotate.title = "顺时针旋转";
    rotate.setAttribute("aria-label", "顺时针旋转");
    rotate.textContent = "↻";
    rotate.addEventListener("click", () => secondaryRotate.click());
    right.prepend(rotate);
  }
})();
