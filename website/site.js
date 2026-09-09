"use strict";

(() => {
  const originals = {
    horizon: { title: "Glass Horizon", stage: "master", description: "Late-night textures. A brighter finish.", meta: "126 BPM · A minor", artwork: "", checklist: { master: true, artwork: true, rights: false } },
    lanterns: { title: "Paper Lanterns", stage: "mix", description: "Warm chords. A little room to breathe.", meta: "112 BPM · C major", artwork: "art-pink", checklist: { master: false, artwork: true, rights: false } },
    tide: { title: "Low Tide", stage: "production", description: "Slow movement. Something taking shape.", meta: "90 BPM · D minor", artwork: "art-purple", checklist: { master: false, artwork: false, rights: false } }
  };
  const freshProjects = () => JSON.parse(JSON.stringify(originals));
  let projects = freshProjects();
  let selected = "horizon";
  const title = document.querySelector("#demo-title");
  const titleInput = document.querySelector("#demo-title-input");
  const stageSelect = document.querySelector("#demo-stage");
  const stageBadge = document.querySelector("#demo-stage-badge");
  const choices = [...document.querySelectorAll("button[data-project]")];
  const checks = [...document.querySelectorAll("#demo-checklist input")];
  const status = document.querySelector("#demo-status");
  const reset = document.querySelector("#demo-reset");
  const audio = document.querySelector("#demo-audio");
  const stageNames = { idea: "Idea", production: "Production", mix: "Mix", master: "Master", released: "Released" };
  const stepNames = { master: "final master", artwork: "cover artwork", rights: "rights & credits" };

  function updateReadiness() {
    const project = projects[selected];
    const completed = Object.values(project.checklist).filter(Boolean).length;
    const count = document.querySelector("#readiness-count");
    count.replaceChildren(document.createTextNode(String(completed)));
    const denominator = document.createElement("span");
    denominator.textContent = "/3";
    count.append(denominator);
    const progress = document.querySelector("#readiness-progress");
    progress.value = completed;
    progress.textContent = `${completed} of 3 complete`;
    const next = Object.keys(project.checklist).find(key => !project.checklist[key]);
    const note = document.querySelector("#readiness-note");
    note.textContent = next ? `Next up: ${stepNames[next]}.` : "All sample steps checked. Nice work.";
    note.classList.toggle("is-ready", completed === 3);
  }

  function updateTitle() {
    const visibleTitle = projects[selected].title.trim() || "Untitled project";
    title.textContent = visibleTitle;
    document.querySelector(`[data-project-label="${selected}"]`).textContent = visibleTitle;
  }

  function render() {
    const project = projects[selected];
    choices.forEach(choice => {
      const active = choice.dataset.project === selected;
      choice.classList.toggle("is-selected", active);
      choice.setAttribute("aria-pressed", String(active));
      const visibleTitle = projects[choice.dataset.project].title.trim() || "Untitled project";
      choice.querySelector("strong").textContent = visibleTitle;
    });
    titleInput.value = project.title;
    updateTitle();
    document.querySelector("#demo-description").textContent = project.description;
    document.querySelector("#demo-meta").textContent = project.meta;
    document.querySelector("#demo-art").className = project.artwork;
    stageSelect.value = project.stage;
    stageBadge.className = `stage stage-${project.stage}`;
    stageBadge.textContent = stageNames[project.stage].toUpperCase();
    checks.forEach(check => { check.checked = project.checklist[check.name]; });
    updateReadiness();
  }

  choices.forEach(choice => {
    choice.disabled = false;
    choice.addEventListener("click", () => {
      selected = choice.dataset.project;
      render();
      status.textContent = `${projects[selected].title.trim() || "Untitled project"} selected. Try changing its title, stage or release checklist.`;
    });
  });
  titleInput.disabled = false;
  titleInput.addEventListener("input", () => {
    projects[selected].title = titleInput.value;
    updateTitle();
  });
  titleInput.addEventListener("change", () => {
    status.textContent = "Sample title updated. These changes stay in this page only.";
  });
  stageSelect.disabled = false;
  stageSelect.addEventListener("change", () => {
    if (!Object.hasOwn(stageNames, stageSelect.value)) return;
    projects[selected].stage = stageSelect.value;
    stageBadge.className = `stage stage-${stageSelect.value}`;
    stageBadge.textContent = stageNames[stageSelect.value].toUpperCase();
    status.textContent = `Sample project moved to ${stageNames[stageSelect.value]}. The checklist is yours to review separately.`;
  });
  checks.forEach(check => {
    check.disabled = false;
    check.addEventListener("change", () => {
      projects[selected].checklist[check.name] = check.checked;
      updateReadiness();
      const completed = Object.values(projects[selected].checklist).filter(Boolean).length;
      status.textContent = `${completed} of 3 sample release steps complete. This demo does not validate a real release.`;
    });
  });
  reset.hidden = false;
  reset.addEventListener("click", () => {
    projects = freshProjects();
    selected = "horizon";
    audio.pause();
    if (audio.readyState > 0) audio.currentTime = 0;
    render();
    status.textContent = "Demo reset. All three sample projects are back to their starting point.";
  });
  status.textContent = "Your sandbox is ready. Choose a project and make it your own — nothing is saved or uploaded.";

  const shareButton = document.querySelector("#share-button");
  const shareInput = document.querySelector("#share-link");
  const shareStatus = document.querySelector("#share-status");
  shareButton.hidden = false;
  shareInput.addEventListener("click", () => shareInput.select());
  shareButton.addEventListener("click", async () => {
    const url = shareInput.value;
    const shareData = { title: "ProducerOS — Your studio, in focus", text: "A local Windows workspace for music projects, versions and release preparation. Try the demo.", url };
    if (typeof navigator.share === "function") {
      try {
        await navigator.share(shareData);
        shareStatus.textContent = "Share dialog completed.";
        return;
      } catch (error) {
        if (error && error.name === "AbortError") {
          shareStatus.textContent = "Sharing cancelled. The link is here whenever you need it.";
          return;
        }
      }
    }
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      try {
        await navigator.clipboard.writeText(url);
        shareStatus.textContent = "Link copied. Paste it into a message to your producer friend.";
        return;
      } catch (_) {
        // Clipboard permission is optional. The link remains visible and selectable.
      }
    }
    shareInput.focus();
    shareInput.select();
    shareStatus.textContent = "Select and copy the link above, then paste it into your message.";
  });
})();
