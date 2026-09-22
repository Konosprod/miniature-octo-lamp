const input = document.getElementById("search");
const suggestionsList = document.getElementById("suggestions");
const emptyState = document.getElementById("empty-state");
const loadingState = document.getElementById("loading-state");
const content = document.getElementById("content");
const sourceCard = document.getElementById("source-card");
const summary = document.getElementById("summary");
const resultsOurs = document.getElementById("results-ours");
const resultsAnilist = document.getElementById("results-anilist");

let debounceTimeout;
let activeIndex = -1;
let currentSuggestions = [];

function animeTitle(anime) {
    return anime.title_romaji || anime.title_english || anime.title_native || "Sans titre";
}

function openAnime(anime) {
    if (anime.siteUrl) {
        window.open(anime.siteUrl, "_blank", "noopener,noreferrer");
    }
}

function renderSourceCard(anime) {
    sourceCard.innerHTML = "";

    const img = document.createElement("img");
    img.src = anime.cover || "";
    img.alt = animeTitle(anime);

    const info = document.createElement("div");
    info.className = "source-info";

    const title = document.createElement("h2");
    title.textContent = animeTitle(anime);

    const description = document.createElement("p");
    description.textContent = (anime.description || "").replace(/<[^>]*>/g, "");

    const badgeRow = document.createElement("div");
    badgeRow.className = "badge-row";
    (anime.genres || []).forEach((genre) => {
        const badge = document.createElement("span");
        badge.className = "badge";
        badge.textContent = genre;
        badgeRow.appendChild(badge);
    });

    info.appendChild(title);
    info.appendChild(description);
    info.appendChild(badgeRow);

    sourceCard.appendChild(img);
    sourceCard.appendChild(info);
}

function renderCard(anime, isCommon) {
    const card = document.createElement("div");
    card.classList.add("card");
    if (isCommon) {
        card.classList.add("is-common");
    }
    card.addEventListener("click", () => openAnime(anime));

    if (isCommon) {
        const badge = document.createElement("span");
        badge.className = "common-badge";
        badge.textContent = "Commun";
        card.appendChild(badge);
    }

    const img = document.createElement("img");
    img.src = anime.cover || "";
    img.alt = animeTitle(anime);
    img.loading = "lazy";

    const titleEl = document.createElement("h3");
    titleEl.textContent = animeTitle(anime);

    card.appendChild(img);
    card.appendChild(titleEl);
    return card;
}

function renderComparison(data) {
    renderSourceCard(data.source);

    const oursIds = new Set(data.ours.map((a) => a.id));
    const anilistIds = new Set(data.anilist.map((a) => a.id));
    const commonCount = data.ours.filter((a) => anilistIds.has(a.id)).length;

    summary.innerHTML =
        `<strong>${commonCount}</strong> titre(s) en commun entre notre algo et les ` +
        `recommandations AniList (sur ${data.ours.length} vs ${data.anilist.length}).`;

    resultsOurs.innerHTML = "";
    data.ours.forEach((anime) => {
        resultsOurs.appendChild(renderCard(anime, anilistIds.has(anime.id)));
    });

    resultsAnilist.innerHTML = "";
    data.anilist.forEach((anime) => {
        resultsAnilist.appendChild(renderCard(anime, oursIds.has(anime.id)));
    });

    emptyState.hidden = true;
    loadingState.hidden = true;
    content.hidden = false;
}

function fetchAnimeListAndDisplay(id) {
    emptyState.hidden = true;
    content.hidden = true;
    loadingState.hidden = false;

    fetch(`/anime/${encodeURIComponent(id)}/recommendations`)
        .then((response) => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(renderComparison)
        .catch((error) => {
            loadingState.hidden = true;
            emptyState.hidden = false;
            emptyState.textContent = "Erreur lors du chargement des recommandations.";
            console.error("Erreur lors du chargement des animes :", error);
        });
}

function clearSuggestions() {
    suggestionsList.innerHTML = "";
    activeIndex = -1;
    currentSuggestions = [];
}

function renderSuggestions(suggestions) {
    clearSuggestions();
    currentSuggestions = suggestions;

    suggestions.forEach((item, index) => {
        const li = document.createElement("li");
        li.textContent = item.title_romaji || item.title_native || item.title_english;
        li.setAttribute("data-index", index);

        li.addEventListener("click", () => {
            input.value = li.textContent;
            clearSuggestions();
            fetchAnimeListAndDisplay(item.anime_id);
        });

        suggestionsList.appendChild(li);
    });
}

function updateActiveItem() {
    const items = suggestionsList.querySelectorAll("li");
    items.forEach((item, index) => {
        item.classList.toggle("active", index === activeIndex);
    });
}

input.addEventListener("input", () => {
    clearTimeout(debounceTimeout);

    const query = input.value;

    if (query.length < 3) {
        clearSuggestions();
        return;
    }

    debounceTimeout = setTimeout(() => {
        fetch(`/anime/autocomplete?search=${encodeURIComponent(query)}`)
            .then((response) => response.json())
            .then((suggestions) => {
                renderSuggestions(suggestions);
            })
            .catch((error) => {
                console.error("Erreur lors de l'autocomplétion :", error);
            });
    }, 300);
});

input.addEventListener("keydown", (e) => {
    const items = suggestionsList.querySelectorAll("li");

    if (e.key === "ArrowDown") {
        e.preventDefault();
        if (activeIndex < items.length - 1) {
            activeIndex++;
            updateActiveItem();
        }
    } else if (e.key === "ArrowUp") {
        e.preventDefault();
        if (activeIndex > 0) {
            activeIndex--;
            updateActiveItem();
        }
    } else if (e.key === "Enter") {
        if (activeIndex >= 0 && activeIndex < currentSuggestions.length) {
            const item = currentSuggestions[activeIndex];
            input.value = item.title_romaji || item.title_native || item.title_english;
            clearSuggestions();
            fetchAnimeListAndDisplay(item.anime_id);
        }
    } else if (e.key === "Escape") {
        clearSuggestions();
    }
});

document.addEventListener("click", (e) => {
    if (!document.querySelector(".search-container").contains(e.target)) {
        clearSuggestions();
    }
});
