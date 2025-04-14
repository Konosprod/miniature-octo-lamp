const input = document.getElementById("search");
const suggestionsList = document.getElementById("suggestions");

let debounceTimeout;
let activeIndex = -1;
let currentSuggestions = [];

function fetchAnimeListAndDisplay(id) {
    fetch(`/anime/${encodeURIComponent(id)}/recommendations`)
        .then(response => response.json())
        .then(animeList => {
            const grid = document.getElementById("results-grid");
            grid.innerHTML = ""; // clear previous results

            animeList.forEach(anime => {
                const card = document.createElement("div");
                
                card.addEventListener("click", () => {
                    window.open(anime['siteUrl'], "_blank", 'noopener,noreferrer');
                });

                card.classList.add("card");

                const img = document.createElement("img");
                img.src = anime['cover'];
                img.alt = anime['title_romaji'] || anime['title_english'] || anime['title_native'];

                const titleEl = document.createElement("h3");
                titleEl.textContent = anime['title_romaji'] || anime['title_english'] || anime['title_native'];

                card.appendChild(img);
                card.appendChild(titleEl);
                grid.appendChild(card);
            });
        })
        .catch(error => console.error("Erreur lors du chargement des animes :", error));
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
        if(item["title_romaji"] !== null) {
            li.textContent = item["title_romaji"]
        } else if(item["title_native"] !== null) {
            li.textContent = item["title_native"]
        } else {
            li.textContent = item["title_english"]
        }
        suggestionsList.appendChild(li);
        li.setAttribute("data-index", index);

        li.addEventListener("click", () => {
            input.value = item["title_romaji"];
            clearSuggestions();
            fetchAnimeListAndDisplay(item["anime_id"]);
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
            .then(response => response.json())
            .then(suggestions => {
                renderSuggestions(suggestions);
            })
            .catch(error => {
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
            input.value = currentSuggestions[activeIndex]["title_romaji"];
            clearSuggestions();
            fetchAnimeListAndDisplay(currentSuggestions[activeIndex]["anime_id"]);
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
