(() => {
  "use strict";

  const PERIOD_LABELS = { daily: "日榜", weekly: "周榜", monthly: "月榜" };
  const CARD_LABELS = { portrait: "竖版", square: "方形", og: "横版" };
  const STORAGE = { theme: "trending-radar-theme", favorites: "trending-radar-favorites" };
  const state = { data: null, period: "daily", query: "", language: "all", favorites: new Set(), newsCategory: "all", newsSource: "all", card: "portrait" };
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];

  function escapeHtml(value) { const element = document.createElement("span"); element.textContent = String(value ?? ""); return element.innerHTML; }
  function readData() { try { return JSON.parse($("#initial-data").textContent); } catch (error) { console.error("无法读取榜单数据", error); return null; } }
  function readFavorites() { try { return new Set(JSON.parse(localStorage.getItem(STORAGE.favorites) || "[]")); } catch (_) { return new Set(); } }
  function saveFavorites() { localStorage.setItem(STORAGE.favorites, JSON.stringify([...state.favorites].sort())); }
  function allRepos() { return Object.values(state.data.periods).flat(); }
  function uniqueRepos() { const map = new Map(); allRepos().forEach((repo) => map.set(repo.title.toLowerCase(), repo)); return [...map.values()]; }
  function currentRepos() {
    let repos = state.period === "favorites" ? uniqueRepos().filter((repo) => state.favorites.has(repo.title)) : state.data.periods[state.period] || [];
    const query = state.query.trim().toLowerCase();
    if (query) repos = repos.filter((repo) => [repo.title, repo.author, repo.description, repo.summary, repo.language].some((value) => String(value || "").toLowerCase().includes(query)));
    if (state.language !== "all") repos = repos.filter((repo) => repo.language === state.language);
    return repos;
  }
  function movementMarkup(movement) { const direction = movement?.direction || "new"; const icons = { up: "↑", down: "↓", same: "→", new: "+" }; return `<span class="movement movement-${direction}">${icons[direction]} ${escapeHtml(movement?.label || "新上榜")}</span>`; }
  function periodsMarkup(periods) { if (!periods || periods.length < 2) return ""; return `<span class="cross-badge">${periods.map((period) => PERIOD_LABELS[period]).join(" · ")}均上榜</span>`; }
  function repoCard(repo) {
    const favorite = state.favorites.has(repo.title);
    const shareUrl = `${location.origin}${location.pathname}#repo-${encodeURIComponent(repo.title)}`;
    return `<article class="repo-card" id="repo-${escapeHtml(repo.title)}" data-repo="${escapeHtml(repo.title)}"><div class="rank-column"><span class="rank">${String(repo.rank).padStart(2, "0")}</span>${movementMarkup(repo.movement)}</div><div class="repo-content"><div class="repo-title-row"><div><p class="repo-author">${escapeHtml(repo.author)}</p><h3><a href="${escapeHtml(repo.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(repo.title)}</a></h3></div>${periodsMarkup(repo.periods)}</div><p class="repo-description">${escapeHtml(repo.description)}</p><p class="repo-summary"><span>中文速览</span>${escapeHtml(repo.summary)}</p><div class="repo-meta"><span><i class="language-dot"></i>${escapeHtml(repo.language || "未知")}</span><span>★ ${escapeHtml(repo.stars)}</span><span>⑂ ${escapeHtml(repo.forks)}</span></div></div><div class="repo-actions"><button class="card-action favorite-button${favorite ? " is-favorite" : ""}" type="button" data-action="favorite" data-repo="${escapeHtml(repo.title)}" aria-pressed="${favorite}" aria-label="${favorite ? "取消收藏" : "收藏"} ${escapeHtml(repo.title)}">${favorite ? "★" : "☆"}</button><button class="card-action" type="button" data-action="share" data-title="${escapeHtml(repo.title)}" data-url="${escapeHtml(shareUrl)}" aria-label="分享 ${escapeHtml(repo.title)}">↗</button></div></article>`;
  }
  function renderRepos() {
    const repos = currentRepos(); $("#repo-list").innerHTML = repos.map(repoCard).join(""); $("#empty-state").hidden = repos.length > 0; $("#result-count").textContent = `显示 ${repos.length} 个项目`;
    $$(".tab").forEach((button) => { const active = button.dataset.period === state.period; button.classList.toggle("is-active", active); button.setAttribute("aria-selected", String(active)); });
    if (location.hash.startsWith("#repo-")) document.getElementById(decodeURIComponent(location.hash.slice(1)))?.classList.add("is-linked");
  }
  function relativeTime(value) {
    const date = new Date(value); if (Number.isNaN(date.getTime())) return "最近更新";
    const minutes = Math.max(0, Math.round((Date.now() - date.getTime()) / 60000));
    if (minutes < 60) return `${Math.max(1, minutes)} 分钟前`;
    if (minutes < 1440) return `${Math.floor(minutes / 60)} 小时前`;
    return `${Math.floor(minutes / 1440)} 天前`;
  }
  function newsItems() {
    return (Array.isArray(state.data.news) ? state.data.news : []).filter((item) => (state.newsCategory === "all" || item.category === state.newsCategory) && (state.newsSource === "all" || item.source_id === state.newsSource));
  }
  function renderNews() {
    const news = newsItems(); $("#news-count").textContent = news.length ? `${news.length} 条 · 更新于 ${relativeTime(state.data.news_generated_at)}` : "资讯源暂不可用";
    $("#news-list").innerHTML = news.length ? news.map((item, index) => `<article class="news-item${index === 0 ? " is-featured" : ""}"><div class="news-item-top"><button class="news-category" type="button" data-news-category="${escapeHtml(item.category || "资讯")}">${escapeHtml(item.category || "资讯")}</button><span>${escapeHtml(item.source || "公开 RSS")}</span>${item.stale ? `<span class="stale-badge">上一版</span>` : ""}</div><h3><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title || item.original_title)}</a></h3>${item.summary ? `<p>${escapeHtml(item.summary)}</p>` : ""}<div class="news-tags">${(item.tags || []).slice(0, 3).map((tag) => `<span>#${escapeHtml(tag)}</span>`).join("")}</div><div class="news-item-meta"><time datetime="${escapeHtml(item.published_at || "")}">${relativeTime(item.published_at || item.fetched_at)}</time><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">阅读原文 ↗</a></div></article>`).join("") : `<div class="empty-state"><strong>今日资讯暂不可用</strong><p>单个来源限流不会影响榜单；稍后刷新即可看到最新内容。</p></div>`;
  }
  function populateNewsFilters() {
    const items = state.data.news || []; const categories = [...new Set(items.map((item) => item.category).filter(Boolean))]; const sources = [...new Map(items.map((item) => [item.source_id, item.source])).entries()];
    $("#news-categories").innerHTML = ["all", ...categories].map((category) => `<button class="chip${state.newsCategory === category ? " is-active" : ""}" type="button" data-news-category="${escapeHtml(category)}">${category === "all" ? "全部" : escapeHtml(category)}</button>`).join("");
    $("#news-source-filter").innerHTML = `<option value="all">全部来源</option>${sources.map(([id, source]) => `<option value="${escapeHtml(id)}">${escapeHtml(source)}</option>`).join("")}`; $("#news-source-filter").value = state.newsSource;
  }
  function updateOverview() {
    const repos = uniqueRepos(); $("#stat-total").textContent = allRepos().length; $("#stat-unique").textContent = repos.length; $("#stat-cross").textContent = repos.filter((repo) => repo.periods?.length > 1).length; $("#stat-languages").textContent = new Set(repos.map((repo) => repo.language).filter((x) => x && x !== "未知")).size; $("#overview-date").textContent = `${state.data.date} · ${state.data.news?.length || 0} 条资讯`;
    const featured = state.data.periods.daily[0]; if (featured) { $("#featured-link").textContent = featured.title; $("#featured-link").href = featured.url; $("#featured-summary").textContent = featured.summary; $("#featured-meta").innerHTML = `<span>★ ${escapeHtml(featured.stars)}</span><span>${escapeHtml(featured.language)}</span>${periodsMarkup(featured.periods)}`; }
    const lead = state.data.news?.[0]; if (lead) { $("#featured-news-link").textContent = lead.title || lead.original_title; $("#featured-news-link").href = lead.url; $("#featured-news-summary").textContent = lead.summary || lead.original_summary || "查看今日科技与开源资讯"; $("#featured-news-meta").innerHTML = `<span>${escapeHtml(lead.source || "公开资讯")}</span><span>${relativeTime(lead.published_at)}</span>`; }
  }
  function populateLanguages() { const languages = [...new Set(uniqueRepos().map((repo) => repo.language).filter(Boolean))].sort((a, b) => a.localeCompare(b)); $("#language-filter").insertAdjacentHTML("beforeend", languages.map((language) => `<option value="${escapeHtml(language)}">${escapeHtml(language)}</option>`).join("")); }
  function toast(message) { const element = $("#toast"); element.textContent = message; element.classList.add("is-visible"); clearTimeout(toast.timer); toast.timer = setTimeout(() => element.classList.remove("is-visible"), 2200); }
  async function share(title, url) { try { if (navigator.share) await navigator.share({ title, text: `在 GitHub 趋势雷达查看 ${title}`, url }); else if (navigator.clipboard) { await navigator.clipboard.writeText(url); toast("链接已复制"); } else toast(url); } catch (error) { if (error.name !== "AbortError") toast("分享失败，请手动复制地址"); } }
  function applyTheme(theme) { document.documentElement.dataset.theme = theme; localStorage.setItem(STORAGE.theme, theme); }
  function setCardVariant(variant) { state.card = variant; const suffix = CARD_LABELS[variant]; const svg = `cards/latest-${variant}.svg`; const png = `cards/latest-${variant}.png`; $("#trend-card-image").src = svg; $("#trend-card-image").alt = `今日开源趋势${suffix}卡片`; $("#download-card-svg").href = svg; $("#download-card-svg").download = `github-trending-${variant}.svg`; $("#download-card-png").href = png; $("#download-card-png").download = `github-trending-${variant}.png`; $$(".card-tab").forEach((button) => { const active = button.dataset.card === variant; button.classList.toggle("is-active", active); button.setAttribute("aria-selected", String(active)); }); }
  async function loadNewsEndpoint() { try { const response = await fetch("data/news/latest.json", { cache: "no-store" }); if (!response.ok) throw new Error(`HTTP ${response.status}`); const bundle = await response.json(); if (Array.isArray(bundle.items)) { state.data.news = bundle.items; state.data.news_generated_at = bundle.generated_at; state.data.news_sources = bundle.sources || []; populateNewsFilters(); updateOverview(); renderNews(); } } catch (_) { /* 内嵌数据是兼容回退 */ } }
  function bindEvents() {
    $$(".tab").forEach((button) => button.addEventListener("click", () => { state.period = button.dataset.period; renderRepos(); })); $("#search-input").addEventListener("input", (event) => { state.query = event.target.value; renderRepos(); }); $("#language-filter").addEventListener("change", (event) => { state.language = event.target.value; renderRepos(); });
    $("#repo-list").addEventListener("click", (event) => { const button = event.target.closest("button[data-action]"); if (!button) return; if (button.dataset.action === "favorite") { const name = button.dataset.repo; state.favorites.has(name) ? state.favorites.delete(name) : state.favorites.add(name); saveFavorites(); renderRepos(); toast(state.favorites.has(name) ? "已收藏" : "已取消收藏"); } else share(button.dataset.title, button.dataset.url); });
    $("#news-categories").addEventListener("click", (event) => { const button = event.target.closest("[data-news-category]"); if (!button) return; state.newsCategory = button.dataset.newsCategory; populateNewsFilters(); renderNews(); }); $("#news-list").addEventListener("click", (event) => { const button = event.target.closest("[data-news-category]"); if (!button) return; state.newsCategory = button.dataset.newsCategory; populateNewsFilters(); renderNews(); }); $("#news-source-filter").addEventListener("change", (event) => { state.newsSource = event.target.value; renderNews(); });
    $("#reset-filters").addEventListener("click", () => { state.query = ""; state.language = "all"; $("#search-input").value = ""; $("#language-filter").value = "all"; renderRepos(); }); $("#share-page").addEventListener("click", () => share("GitHub 趋势雷达", location.href)); $("#share-card").addEventListener("click", () => share("今日开源趋势卡片", new URL(`cards/latest-${state.card}.png`, location.href).href)); $("#theme-toggle").addEventListener("click", () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark")); $$(".card-tab").forEach((button) => button.addEventListener("click", () => setCardVariant(button.dataset.card))); document.addEventListener("keydown", (event) => { if (event.key === "/" && document.activeElement.tagName !== "INPUT") { event.preventDefault(); $("#search-input").focus(); } });
  }
  function init() {
    state.data = readData(); if (!state.data?.periods) { $("#empty-state").hidden = false; $("#empty-state strong").textContent = "榜单数据加载失败"; return; } state.favorites = readFavorites(); const preferred = localStorage.getItem(STORAGE.theme) || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"); applyTheme(preferred); updateOverview(); populateLanguages(); populateNewsFilters(); renderRepos(); renderNews(); setCardVariant("portrait"); bindEvents(); loadNewsEndpoint();
  }
  document.addEventListener("DOMContentLoaded", init);
})();
