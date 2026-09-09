// Local progressive enhancements; all music files remain on the local server.
(function () {
  "use strict";
  document.documentElement.classList.add("js-ready");
  function registerServiceWorker() {
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("/service-worker.js", {scope:"/"}).catch(function () {});
  }
  function initFilterDrawer() {
    var drawer = document.querySelector("[data-filter-drawer]");
    var toggle = document.querySelector("[data-filter-toggle]");
    if (!drawer || !toggle) return;
    var previousFocus;
    toggle.setAttribute("aria-expanded", "false");
    drawer.id = "project-filters";
    toggle.setAttribute("aria-controls", drawer.id);
    function close() { drawer.classList.remove("open"); toggle.setAttribute("aria-expanded", "false"); if (previousFocus) previousFocus.focus(); }
    toggle.addEventListener("click", function () {
      if (drawer.classList.contains("open")) { close(); return; }
      previousFocus = document.activeElement;
      drawer.classList.add("open"); toggle.setAttribute("aria-expanded", "true");
      var first = drawer.querySelector("input:not([type=hidden]), select, button"); if (first) first.focus();
    });
    var closeBtn = drawer.querySelector("[data-filter-close]");
    if (closeBtn) closeBtn.addEventListener("click", close);
    drawer.addEventListener("click", function (event) { if (event.target === drawer) close(); });
    drawer.addEventListener("keydown", function (event) {
      if (!drawer.classList.contains("open")) return;
      if (event.key === "Escape") { event.preventDefault(); close(); }
      if (event.key === "Tab") {
        var controls = drawer.querySelectorAll("button, input:not([type=hidden]), select, a[href]");
        var first = controls[0], last = controls[controls.length-1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    });
  }
  function initForms() {
    document.querySelectorAll("[data-backup-dry-run]").forEach(function(form) {
      form.addEventListener("submit",async function(event) {
        event.preventDefault();
        var target=document.getElementById("dry-run-"+form.getAttribute("data-backup-dry-run"));
        var button=form.querySelector("button");
        target.hidden=false; target.textContent="Checking backup…"; button.disabled=true;
        try {
          var response=await fetch(form.action,{method:"POST",body:new FormData(form)});
          if(!response.ok || !(response.headers.get("content-type")||"").includes("application/json")) throw new Error("Backup check unavailable");
          var result=await response.json();
          target.textContent=(result.ok?"Backup is valid. No data has been changed.":"Backup cannot be restored.")+"\n"+JSON.stringify(result,null,2);
        } catch(error) { target.textContent="Could not check this backup. Reconnect or sign in, then try again."; }
        finally { button.disabled=false; }
      });
    });
    document.querySelectorAll("[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (event) { if (!window.confirm(form.getAttribute("data-confirm"))) event.preventDefault(); });
    });
    document.querySelectorAll("[data-expand-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () { var target=document.getElementById(btn.getAttribute("data-expand-toggle")); if(target) btn.setAttribute("aria-expanded", target.classList.toggle("open") ? "true" : "false"); });
    });
  }
  function initDashboardCache() {
    try {
      // Migrate away from cached HTML: store only inert text, never forms or audio.
      localStorage.removeItem("produceros:last-dashboard");
      localStorage.removeItem("produceros:last-dashboard-at");
      if (document.querySelector("form[action='/login']")) localStorage.removeItem("produceros:summary-v2");
      var dashboard=document.querySelector("[data-dashboard-summary]");
      if (!dashboard) return;
      var summary={at:new Date().toISOString(),stats:[],projects:[]};
      dashboard.querySelectorAll(".stat-tile").forEach(function (tile) { summary.stats.push(tile.textContent.trim().replace(/\s+/g," ")); });
      dashboard.querySelectorAll(".project-row .row-title strong").forEach(function (title) { summary.projects.push(title.textContent.trim()); });
      localStorage.setItem("produceros:summary-v2",JSON.stringify(summary));
    } catch (e) { /* Storage may be disabled. */ }
  }
  function initPlayers() {
    document.querySelectorAll("[data-audio-player]").forEach(function (player) {
      var audio=player.querySelector("audio"), button=player.querySelector("[data-audio-play]"), controls=player.querySelector(".player-controls"), canvas=player.querySelector("canvas"), status=player.querySelector("[data-audio-status]");
      var ctx=canvas.getContext("2d"), audioContext, analyser, bins, animation;
      var reduced=window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      var initialStatus=status.textContent;
      controls.hidden=false;
      // Native controls remain available for seeking, volume and unsupported Web Audio.
      function draw() {
        if (!ctx) return;
        ctx.clearRect(0,0,canvas.width,canvas.height);
        var gradient=ctx.createLinearGradient(0,0,canvas.width,0); gradient.addColorStop(0,"#009dce"); gradient.addColorStop(.55,"#8764ee"); gradient.addColorStop(1,"#df4bbb"); ctx.fillStyle=gradient;
        if (analyser && !audio.paused && !reduced) {
          analyser.getByteFrequencyData(bins);
          for(var i=0;i<64;i++) { var height=Math.max(3,bins[i]/255*90); ctx.fillRect(i*10+2,(100-height)/2,5,height); }
        } else { ctx.fillRect(0,49,canvas.width,2); }
        if (!audio.paused && !reduced) animation=requestAnimationFrame(draw);
      }
      function setButton() { var playing=!audio.paused; button.setAttribute("aria-label",playing?"Pause audio preview":"Play audio preview"); button.querySelector("use").setAttribute("href","/static/svg/icons.svg#icon-"+(playing?"pause":"play")); }
      button.addEventListener("click",async function () {
        if (!audio.paused) { audio.pause(); return; }
        try {
          document.querySelectorAll("audio").forEach(function (other) { if(other!==audio) other.pause(); });
          try {
            var Context=window.AudioContext || window.webkitAudioContext;
            if (Context && !audioContext) { audioContext=new Context(); analyser=audioContext.createAnalyser(); analyser.fftSize=256; bins=new Uint8Array(analyser.frequencyBinCount); audioContext.createMediaElementSource(audio).connect(analyser); analyser.connect(audioContext.destination); }
            if(audioContext) await audioContext.resume();
          } catch (e) { /* Native playback remains available without visualization. */ }
          await audio.play(); status.textContent=initialStatus;
        } catch(e) { status.textContent="Preview unavailable. Check the file, approved folder, and your browser's audio format support."; setButton(); }
      });
      audio.addEventListener("play",function () { document.querySelectorAll("audio").forEach(function(other){if(other!==audio) other.pause();}); setButton(); cancelAnimationFrame(animation); draw(); });
      audio.addEventListener("pause",function () { setButton(); cancelAnimationFrame(animation); draw(); });
      audio.addEventListener("ended",setButton);
      audio.addEventListener("error",function () { status.textContent="Preview unavailable. Check the file, approved folder, and your browser's audio format support."; setButton(); });
      player.querySelectorAll("[data-audio-skip]").forEach(function (skip) { skip.addEventListener("click",function () { if(Number.isFinite(audio.duration)) audio.currentTime=Math.max(0,Math.min(audio.duration,audio.currentTime+Number(skip.getAttribute("data-audio-skip")))); }); });
      draw();
    });
  }
  document.addEventListener("DOMContentLoaded",function () {
    registerServiceWorker(); initFilterDrawer(); initForms(); initDashboardCache(); initPlayers();
  });
})();
