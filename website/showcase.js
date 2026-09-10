"use strict";

// Native audio controls remain usable without JavaScript.
const demoPlayers = [...document.querySelectorAll(".demo-beat audio")];
for (const player of demoPlayers) {
  player.addEventListener("play", () => {
    for (const other of demoPlayers) {
      if (other !== player) other.pause();
    }
  });
}
