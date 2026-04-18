// AubeStatus - auto refresh leger
(function () {
  const REFRESH_MS = 60 * 1000;

  function scheduleReload() {
    setTimeout(function () {
      if (document.visibilityState === "visible") {
        window.location.reload();
      } else {
        document.addEventListener(
          "visibilitychange",
          function onVis() {
            if (document.visibilityState === "visible") {
              document.removeEventListener("visibilitychange", onVis);
              window.location.reload();
            }
          }
        );
      }
    }, REFRESH_MS);
  }

  scheduleReload();
})();
