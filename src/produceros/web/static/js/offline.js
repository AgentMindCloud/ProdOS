(function () {
  "use strict";
  var retry=document.querySelector("[data-offline-retry]");
  if(retry) retry.addEventListener("click",function(){ window.location.assign("/"); });
  try {
    var raw=localStorage.getItem("produceros:summary-v2");
    if (!raw || raw.length>16000) return;
    var cached=JSON.parse(raw), target=document.getElementById("last-summary-content");
    if(!Array.isArray(cached.stats) || !Array.isArray(cached.projects)) return;
    cached.stats.concat(cached.projects).slice(0,16).forEach(function(value) { if(typeof value!=="string") return; var line=document.createElement("p"); line.textContent=value.slice(0,400); target.appendChild(line); });
    document.getElementById("last-summary-at").textContent="Captured: "+String(cached.at||"unknown").slice(0,50);
    document.getElementById("last-summary").hidden=false;
  } catch(e) { /* Corrupt or disabled local storage must not break the retry link. */ }
})();
