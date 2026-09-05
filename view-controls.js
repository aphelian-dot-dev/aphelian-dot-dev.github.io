    // Presentation selection is session-only; it creates no storage or new run.
    const stage3D = document.createElement("canvas");
    stage3D.id = "stage3D";
    stage3D.setAttribute("aria-hidden", "true");
    stage3D.style.cssText = "position:fixed;inset:0;width:100%;height:100%;pointer-events:none";
    canvas.before(stage3D);
    const view2DButton = document.getElementById("view2D");
    const view3DButton = document.getElementById("view3D");
    const graphicsNotice = document.getElementById("graphicsError");
    let selectedView = "3d";
    let lastImpactOffset = { x: 0, y: 0 };
    let view3D = null;
    let graphicsLost = false;
    let graphicsSubtitle = "";
    try { view3D = createOrrery3D(stage3D); }
    catch (error) {
      console.warn("Aphelian: WebGL unavailable; using 2D", error);
      selectedView = "2d";
      graphicsNotice.textContent = "WebGL is unavailable. You can still play in 2D; enable graphics acceleration and reopen this file to try 3D.";
    }

    function updateViewControls() {
      const is3D = selectedView === "3d";
      stage3D.hidden = !is3D;
      // The upstream canvas rule sets display:block, so set display explicitly.
      stage3D.style.display = is3D ? "block" : "none";
      view2DButton.setAttribute("aria-pressed", String(!is3D));
      view3DButton.setAttribute("aria-pressed", String(is3D));
      view3DButton.disabled = !view3D || graphicsLost;
      document.getElementById("riteButton").disabled = is3D && graphicsLost;
      graphicsNotice.hidden = !!view3D && !graphicsLost;
      document.getElementById("viewDescription").textContent = is3D
        ? "Sculpted cosmos / perspective field"
        : "Archival canvas / original field";
      if (game.mode === "title") document.getElementById("eyebrow").textContent = `${selectedView.toUpperCase()} / A rite in three movements`;
    }

    function selectView(view) {
      if (game.mode !== "title" || !["2d", "3d"].includes(view)) return;
      if (view === "3d" && (!view3D || graphicsLost)) return;
      selectedView = view;
      lastImpactOffset = { x: 0, y: 0 };
      clearInputs(true);
      pointer.x = game.player.x + baseOrbit;
      pointer.y = game.player.y - baseOrbit * .3;
      pointer.active = false;
      renderScale = 1;
      lowFpsTime = 0;
      resize();
      updateViewControls();
      document.getElementById("announcer").textContent = `${view.toUpperCase()} view selected. Same rite, same rules.`;
    }
    view2DButton.addEventListener("click", () => selectView("2d"));
    view3DButton.addEventListener("click", () => selectView("3d"));
    stage3D.addEventListener("webglcontextlost", event => {
      event.preventDefault();
      graphicsLost = true;
      graphicsNotice.textContent = "WebGL is recovering. 2D is still available from the home screen.";
      if (selectedView === "3d") {
        pauseGame();
        if (game.mode === "paused") {
          graphicsSubtitle = document.getElementById("subtitle").textContent;
          document.getElementById("subtitle").textContent = "3D graphics interrupted. Combat is paused while WebGL recovers. If this persists, reopen this file.";
        }
        document.getElementById("announcer").textContent = "3D graphics interrupted. Combat is paused.";
        document.getElementById("riteButton").disabled = true;
      }
      updateViewControls();
    });
    stage3D.addEventListener("webglcontextrestored", () => {
      graphicsLost = false;
      if (selectedView === "3d") {
        if (game.mode === "paused") document.getElementById("subtitle").textContent = graphicsSubtitle;
        document.getElementById("announcer").textContent = "3D graphics restored. Resume when ready.";
      }
      graphicsSubtitle = "";
      document.getElementById("riteButton").disabled = false;
      updateViewControls();
    });
    window.addEventListener("keydown", event => {
      if (!graphicsLost || selectedView !== "3d" || ["KeyM", "Tab"].includes(event.code)) return;
      const control = event.target.closest?.("button, input, select, textarea, a, summary");
      const nativeActivation = ["Enter", "NumpadEnter", "Space"].includes(event.code) && control && !control.matches(":disabled");
      // Native activation must reach its target; the bubble handler also gates play.
      if (nativeActivation) return;
      event.preventDefault();
      event.stopImmediatePropagation();
    }, true);
