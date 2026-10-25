"use strict";

var repository = "Rohanbramhankar/rohgpt-local-llm-chatbot";
var versionLabel = document.getElementById("releaseVersion");
var statusLabel = document.getElementById("downloadStatus");
var links = document.querySelectorAll("[data-asset]");

fetch("https://api.github.com/repos/" + repository + "/releases/latest", {
    headers: { Accept: "application/vnd.github+json" }
}).then(function (response) {
    if (!response.ok) throw new Error("No published release yet.");
    return response.json();
}).then(function (release) {
    var assets = new Map(release.assets.map(function (asset) {
        return [asset.name, asset.browser_download_url];
    }));
    var available = 0;
    links.forEach(function (link) {
        var url = assets.get(link.dataset.asset);
        if (url) {
            link.href = url;
            link.classList.remove("disabled");
            link.removeAttribute("aria-disabled");
            link.textContent = "Download";
            available += 1;
        } else {
            link.textContent = "Not available yet";
        }
    });
    versionLabel.textContent = release.tag_name;
    statusLabel.textContent = available
        ? "Downloads are served from GitHub Releases. RohGPT chat itself runs locally on your device."
        : "The latest release does not include desktop packages yet.";
}).catch(function () {
    versionLabel.textContent = "Coming soon";
    links.forEach(function (link) {
        link.textContent = "Coming soon";
    });
    statusLabel.textContent = "Desktop downloads will appear here after the first release build succeeds.";
});
