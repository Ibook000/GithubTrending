(() => {
  "use strict";

  const PERIOD_LABELS = { daily: "日榜", weekly: "周榜", monthly: "月榜" };
  const STORAGE = { theme: "trending-radar-theme", favorites: "trending-radar-favorites" };
  const state = { data: null, period: "daily", query: "", language: "all", favorites: new Set() };
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];

  function readData() {
    try {
      return JSON.parse($("#initial-data").textContent);
    } catch (error) {
      console.error("无法读取榜单数据", error);
      return null;
    }
  }

  function readFavorites() {
    try {
      return new Set(JSON.parse(localStorage.getItem(STORAGE.favorites) || "[]"));
    } catch (_error) {
      return new Set();
    }
  }

  function saveFavorites() {
    localStorage.setItem(STORAGE.favorites, JSON.stringify([...state.favorites].sort()));
  }

  function escapeHtml(value) {
    const element = document.createElement("span");
    element.textContent = String(value ?? "");
    return element.innerHTML;
  }

  function allRepos() {
    return Object.values(state.data.periods).flat();
  }

  function uniqueRepos() {
    const byName = new Map();
    allRepos().forEach((repo) => byName.set(repo.title.toLowerCase(), repo));
    return [...byName.values()];
  }

  function currentRepos() {
    let repos = state.period === "favorites"
      ? uniqueRepos().filter((repo) => state.favorites.has(repo.title))
      : state.data.periods[state.period] || [];
    const query = state.query.trim().toLowerCase();
    if (query) {
      repos = repos.filter((repo) => [repo.title, repo.author, repo.description, repo.summary, repo.language]
        .some((value) => String(value || "").toLowerCase().includes(query)));
    }
    if (state.language !== "all") repos = repos.filter((repo) => repo.language === state.language);
    return repos;
  }

  function renderNews() {
    const news = Array.isArray(state.data.news) ? state.data.news : [];
    $("#news-count").textContent = news.length ? `${news.length} 条公开资讯` : "资讯源暂不可用";
    $("#news-list").innerHTML = news.length
      ? news.map((item) => `<article class="news-item">
          <div class="news-item-top"><span class="news-category">${escapeHtml(item.category || "资讯")}</span><span>${escapeHtml(item.source || "公开 RSS")}</span></div>
          <h3><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)}</a></h3>
          ${item.summary ? `<p>${escapeHtml(item.summary)}</p>` : ""}
          <div class="news-item-meta">${escapeHtml(item.published || "今日更新")}</div>
        </article>`).join("")
      : `<div class="empty-state"><strong>今日资讯暂不可用</strong><p>新闻源偶尔会限流，榜单和趋势卡片仍可正常使用。</p></div>`;
  }

  function movementMarkup(movement) {
    const direction = movement?.direction || "new";
    const icons = { up: "↑", down: "↓", same: "→", new: "+" };
    return `<span class="movement movement-${direction}">${icons[direction]} ${escapeHtml(movement?.label || "新上榜")}</span>`;
  }

  function periodsMarkup(periods) {
    if (!periods || periods.length < 2) return "";
    return `<span class="cross-badge">${periods.map((period) => PERIOD_LABELS[period]).join(" · ")}均上榜</span>`;
  }

  function repoCard(repo) {
    const favorite = state.favorites.has(repo.title);
    const shareUrl = `${location.origin}${location.pathname}#repo-${encodeURIComponent(repo.title)}`;
    return `<article class="repo-card" id="repo-${escapeHtml(repo.title)}" data-repo="${escapeHtml(repo.title)}">
      <div class="rank-column"><span class="rank">${String(repo.rank).padStart(2, "0")}</span>${movementMarkup(repo.movement)}</div>
      <div class="repo-content">
        <div class="repo-title-row">
          <div><p class="repo-author">${escapeHtml(repo.author)}</p><h3><a href="${escapeHtml(repo.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(repo.title)}</a></h3></div>
          ${periodsMarkup(repo.periods)}
        </div>
        <p class="repo-description">${escapeHtml(repo.description)}</p>
        <p class="repo-summary"><span>中文速览</span>${escapeHtml(repo.summary)}</p>
        <div class="repo-meta">
          <span><i class="language-dot"></i>${escapeHtml(repo.language || "未知")}</span>
          <span>★ ${escapeHtml(repo.stars)}</span><span>⑂ ${escapeHtml(repo.forks)}</span>
        </div>
      </div>
      <div class="repo-actions">
        <button class="card-action favorite-button${favorite ? " is-favorite" : ""}" type="button" data-action="favorite" data-repo="${escapeHtml(repo.title)}" aria-pressed="${favorite}" aria-label="${favorite ? "取消收藏" : "收藏"} ${escapeHtml(repo.title)}">${favorite ? "★" : "☆"}</button>
        <button class="card-action" type="button" data-action="share" data-title="${escapeHtml(repo.title)}" data-url="${escapeHtml(shareUrl)}" aria-label="分享 ${escapeHtml(repo.title)}">↗</button>
      </div>
    </article>`;
  }

  function render() {
    const repos = currentRepos();
    $("#repo-list").innerHTML = repos.map(repoCard).join("");
    $("#empty-state").hidden = repos.length > 0;
    $("#result-count").textContent = `显示 ${repos.length} 个项目`;
    $$(".tab").forEach((button) => {
      const active = button.dataset.period === state.period;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", String(active));
    });
    if (location.hash.startsWith("#repo-")) {
      const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      target?.classList.add("is-linked");
    }
  }

  function updateStats() {
    const repos = uniqueRepos();
    $("#stat-total").textContent = allRepos().length;
    $("#stat-unique").textContent = repos.length;
    $("#stat-cross").textContent = repos.filter((repo) => repo.periods?.length > 1).length;
    $("#stat-languages").textContent = new Set(repos.map((repo) => repo.language).filter((x) => x && x !== "未知")).size;
    const featured = state.data.periods.daily[0];
    if (featured) {
      $("#featured-link").textContent = featured.title;
      $("#featured-link").href = featured.url;
      $("#featured-summary").textContent = featured.summary;
      $("#featured-meta").innerHTML = `<span>★ ${escapeHtml(featured.stars)}</span><span>${escapeHtml(featured.language)}</span>${periodsMarkup(featured.periods)}`;
    }
  }

  function populateLanguages() {
    const languages = [...new Set(uniqueRepos().map((repo) => repo.language).filter(Boolean))].sort((a, b) => a.localeCompare(b));
    $("#language-filter").insertAdjacentHTML("beforeend", languages.map((language) => `<option value="${escapeHtml(language)}">${escapeHtml(language)}</option>`).join(""));
  }

  function toast(message) {
    const element = $("#toast");
    element.textContent = message;
    element.classList.add("is-visible");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => element.classList.remove("is-visible"), 2200);
  }

  async function share(title, url) {
    try {
      if (navigator.share) await navigator.share({ title, text: `在 GitHub 趋势雷达查看 ${title}`, url });
      else { await navigator.clipboard.writeText(url); toast("链接已复制"); }
    } catch (error) {
      if (error.name !== "AbortError") toast("分享失败，请手动复制地址");
    }
  }

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(STORAGE.theme, theme);
  }

  function bindEvents() {
    $$(".tab").forEach((button) => button.addEventListener("click", () => { state.period = button.dataset.period; render(); }));
    $("#search-input").addEventListener("input", (event) => { state.query = event.target.value; render(); });
    $("#language-filter").addEventListener("change", (event) => { state.language = event.target.value; render(); });
    $("#repo-list").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-action]");
      if (!button) return;
      if (button.dataset.action === "favorite") {
        const name = button.dataset.repo;
        state.favorites.has(name) ? state.favorites.delete(name) : state.favorites.add(name);
        saveFavorites(); render(); toast(state.favorites.has(name) ? "已收藏" : "已取消收藏");
      } else share(button.dataset.title, button.dataset.url);
    });
    $("#reset-filters").addEventListener("click", () => { state.query = ""; state.language = "all"; $("#search-input").value = ""; $("#language-filter").value = "all"; render(); });
    $("#share-page").addEventListener("click", () => share("GitHub 趋势雷达", location.href));
    $("#share-card").addEventListener("click", () => share("今日开源趋势卡片", new URL("today-card.svg", location.href).href));
    $("#theme-toggle").addEventListener("click", () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));
    document.addEventListener("keydown", (event) => { if (event.key === "/" && document.activeElement.tagName !== "INPUT") { event.preventDefault(); $("#search-input").focus(); } });
  }

  function init() {
    state.data = readData();
    if (!state.data?.periods) { $("#empty-state").hidden = false; $("#empty-state strong").textContent = "榜单数据加载失败"; return; }
    state.favorites = readFavorites();
    const preferred = localStorage.getItem(STORAGE.theme) || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    applyTheme(preferred); updateStats(); populateLanguages(); renderNews(); bindEvents(); render();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
