'use strict';
/* Presentation only. Financial values, qualification and exports come from one snapshot. */
(() => {
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? 'Unavailable').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
  const valid = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
  const number = (value, digits = 2) => valid(value) ? Number(value).toLocaleString('en-US', {minimumFractionDigits:digits, maximumFractionDigits:digits}) : '—';
  const percent = (value, scale = 1, signed = false) => valid(value) ? `${signed && Number(value) > 0 ? '+' : ''}${number(Number(value) * scale)}%` : '—';
  const points = value => valid(value) ? `${Number(value) > 0 ? '+' : ''}${number(Number(value) * 100)} pp` : '—';
  const money = value => valid(value) ? `$${number(value)}` : '—';
  const iconPaths = {up:'M6 18 18 6M6 6h12v12',down:'M6 6l12 12M6 18h12V6',flat:'M4 12h16m-4-4 4 4-4 4M8 8l-4 4 4 4',overview:'M4 4h16v16H4zM4 10h16M12 10v10',themes:'m12 3 9 9-9 9-9-9 9-9zM8 12l4-4 4 4-4 4-4-4z',primary:'M10 17a7 7 0 1 0 0-14 7 7 0 0 0 0 14zm5-2 6 6',saved:'m12 3 2.8 5.8 6.4.9-4.6 4.5 1.1 6.4-5.7-3-5.7 3 1.1-6.4L2.8 9.7l6.4-.9L12 3z',methodology:'M5 5h14M5 10h14M5 15h9M5 20h9',orbit:'M20 12a8 8 0 1 1-8-8M12 4v8h8'};
  const icon = key => `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${iconPaths[key] || iconPaths.flat}"/></svg>`;
  const tone = value => /bullish|positive|long/i.test(value || '') ? 'positive' : /bearish|negative|short/i.test(value || '') ? 'negative' : /mixed/i.test(value || '') ? 'mixed' : 'neutral';
  const signTone = value => !valid(value) || Number(value) === 0 ? 'neutral' : Number(value) > 0 ? 'positive' : 'negative';
  const symbol = value => icon(tone(value) === 'positive' ? 'up' : tone(value) === 'negative' ? 'down' : 'flat');
  const state = value => `<span class="state ${tone(value)}"><span aria-hidden="true">${symbol(value)}</span>${esc(value || 'Unavailable')}</span>`;
  const priority = value => `<span class="priority ${tone(value)}">${esc(value || 'Watch')}</span>`;
  const publicSnapshot = window.THEMESCOPE_STATIC_SOURCE?.mode === 'public_snapshot';
  const preview = publicSnapshot || Boolean(window.FIXTURE_SNAPSHOT);
  const savedKey = 'themescope-vnext-watchlist';
  let snapshot = null, snapshotSignature = '', currentStatus = {}, route = '', origin = '#themes', feedbackTimer, requestError = '';
  let watched = [];
  try { const values = JSON.parse(localStorage.getItem(savedKey) || '[]'); if (Array.isArray(values)) watched = [...new Set(values.filter(s => typeof s === 'string' && s.trim()))]; } catch { /* A blocked or malformed browser store must not stop research. */ }
  const ui = {universe:'active', themeSort:'score', themeDescending:true, selectedTheme:'', candidateMode:'unique', memberSearch:'', memberRole:'', memberEligibility:'', memberSort:'ticker'};
  const positions = new Map(), blobUrls = new Map();
  let inspector = null, inspectorTrigger = '', inspectorOrigin = '', inspectorScroll = 0;
  const inspectorViews = new Map();
  let mapSelected = '', mapResizeTimer;
  let mapWidth = 800;
  const mapHeight = 280, mapPadding = {left:66,right:24,top:24,bottom:50};
  const name = id => snapshot?.themes?.find(t => t.theme_id === id)?.name || id || 'Unavailable';
  const themeHref = id => '#themes/' + encodeURIComponent(id);
  const chevron = '<span class="chevron" aria-hidden="true">›</span>';
  const tickerLink = ticker => `<a class="ticker ticker-link" href="#primary?ticker=${encodeURIComponent(ticker)}" data-inspect-ticker="${esc(ticker)}" data-focus-key="ticker:${esc(ticker)}">${esc(ticker)}${chevron}</a>`;
  const themeLink = id => `<a class="theme-link" href="${themeHref(id)}" data-inspect-theme="${esc(id)}" data-focus-key="theme:${esc(id)}">${esc(name(id))}${chevron}</a>`;
  const saveButton = (ticker, location) => `<button class="save-button" data-save="${esc(ticker)}" data-focus-key="${esc(location + ':' + ticker)}" aria-pressed="${watched.includes(ticker)}" aria-label="${watched.includes(ticker) ? 'Saved ' + esc(ticker) + '; remove from Saved' : 'Save ' + esc(ticker)}"><span aria-hidden="true">${watched.includes(ticker) ? '★' : '☆'}</span><span class="sr-only">${watched.includes(ticker) ? 'Saved' : 'Save'}</span></button>`;
  const empty = (title, message, action = '') => `<div class="empty-state"><span class="quiet-orbit" aria-hidden="true">◌</span><h3>${esc(title)}</h3><p>${esc(message)}</p>${action}</div>`;
  const displayKey = 'themescope-vnext-display';
  let display = {density:'compact', text:100, motion:false, contrast:false};
  try {
    const stored = JSON.parse(localStorage.getItem(displayKey) || '{}');
    display = {density:stored.density === 'comfortable' ? 'comfortable' : 'compact', text:[100,125,150,175,200].includes(stored.text) ? stored.text : 100, motion:stored.motion === true, contrast:stored.contrast === true};
  } catch { /* Independent, optional browser preference. */ }
  function applyDisplay(persist = false) {
    const root = document.documentElement;
    root.dataset.density = display.density; root.dataset.motion = display.motion ? 'reduce' : 'system'; root.dataset.contrast = display.contrast ? 'high' : 'standard';
    root.style.fontSize = display.text + '%';
    $('text-size').textContent = display.text + '%';
    $('display-motion').checked = display.motion; $('display-contrast').checked = display.contrast;
    document.querySelectorAll('button[data-density]').forEach(b => b.setAttribute('aria-pressed',String(b.dataset.density === display.density)));
    document.querySelector('[data-text-step="-25"]').disabled = display.text === 100;
    document.querySelector('[data-text-step="25"]').disabled = display.text === 200;
    if ($('theme-map-panel').open) renderThemeMap();
    if (persist) try { localStorage.setItem(displayKey,JSON.stringify(display)); } catch { announce('Display settings apply for this visit; browser storage is unavailable.'); }
  }
  function closeDisplay() { $('display-panel').hidden = true; $('display-toggle').setAttribute('aria-expanded','false'); }
  function focusKey() { return document.activeElement?.dataset?.focusKey; }
  function restoreFocus(key) { if (key) [...(inspector ? $('research-inspector') : document).querySelectorAll(`[data-focus-key="${CSS.escape(key)}"]`)].find(node => !node.closest('[hidden]'))?.focus({preventScroll:true}); }
  function announce(text) {
    clearTimeout(feedbackTimer); $('feedback').textContent = text; $('feedback').classList.add('visible');
    feedbackTimer = setTimeout(() => $('feedback').classList.remove('visible'), 3200);
  }
  function earningsDates(ticker) { return snapshot?.earnings?.[ticker]?.dates || []; }
  // All-unavailable cannot distinguish disabled, failed, or an empty calendar in this contract.
  function earningsEnabled() { return Object.values(snapshot?.earnings || {}).some(e=>(e?.dates?.length || 0)>0 || e?.status === 'Available'); }
  function earnings(ticker) { const dates = earningsDates(ticker); return dates.length ? dates.map(esc).join('<br>') : `<span class="muted">${snapshot?.earnings?.[ticker]?.status === 'Available' ? 'No reported date' : 'Unavailable'}</span>`; }
  function themeBreadth(metric) {
    if (valid(metric?.value)) return percent(metric.value);
    if (!valid(metric?.valid) || !valid(metric?.configured)) return '—';
    const detail = `${metric.valid}/${metric.configured} valid${valid(metric.coverage) ? ' · ' + percent(metric.coverage,100) + ' coverage' : ''}`;
    return `<span title="${esc(detail)}">—<span class="sr-only"> breadth unavailable; ${esc(detail)}</span></span>`;
  }
  function comparison(theme) { const value = theme.transition?.priority_change; return value == null ? 'Comparison unavailable' : value === '—' ? 'Continuing' : value; }
  function prelaunch() { return snapshot?.theme_layer?.state === 'pre_launch_research'; }
  function download(themeId) {
    const text = themeId ? snapshot?.exports?.individual?.[themeId] : snapshot?.exports?.combined;
    if (text === undefined || text === null) return null;
    if (!preview) return themeId ? `/api/exports/${encodeURIComponent(themeId)}.txt` : '/api/exports/combined.txt';
    const key = themeId || '__combined';
    if (!blobUrls.has(key)) blobUrls.set(key, URL.createObjectURL(new Blob([text], {type:'text/plain'})));
    return blobUrls.get(key);
  }
  function themeDownload(themeId) {
    const url = download(themeId);
    return url ? `<a class="button secondary small" href="${esc(url)}" download="Theme.txt">Theme Primary TXT <span aria-hidden="true">↓</span></a>` : '<span class="muted table-note">No published Primary TXT for this theme</span>';
  }
  function table(headers, rows, caption, className = '') {
    return `<table class="${className}"><caption class="sr-only">${esc(caption)}</caption><thead><tr>${headers.map(h => `<th scope="col"${h.numeric ? ' class="numeric"' : ''}>${h.label || h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table>`;
  }
  function renderLayer() {
    $('fixture-banner').hidden = publicSnapshot || !snapshot?.synthetic_fixture;
    $('public-banner').hidden = !publicSnapshot;
    if (publicSnapshot) $('public-banner').textContent = `Public snapshot · Completed US session ${snapshot.session} · Read-only`;
    $('refresh').hidden = publicSnapshot;
    if (publicSnapshot) document.querySelector('.diagnostics summary').textContent = 'Snapshot details';
    const layer = snapshot?.theme_layer || {}, session = snapshot?.session;
    const messages = {
      pre_launch_research:`Pre-launch research · Completed session ${session} · Approved launch membership universe. Official index history begins at the ${layer.launch_rebalance_session} close; first earned session ${layer.first_earned_session}.`,
      pre_launch:'Pre-launch · Official theme indices have not yet initialized.',
      initialized:`Launch close: index initialized at 100 · First earned session ${layer.first_earned_session}. Historical comparisons are not yet available.`,
      live:'Official theme history · Completed-session research',
      activation_blocked:'Theme activation blocked · Market context remains available. See Configuration & activation status in Methodology.'
    };
    const routine = ['initialized','live'].includes(layer.state);
    $('lifecycle-detail').hidden = !messages[layer.state];
    $('lifecycle-detail').textContent = messages[layer.state] || '';
    $('theme-layer').hidden = routine || !messages[layer.state];
    $('theme-layer').textContent = messages[layer.state] || '';
    $('blockers').innerHTML = (snapshot?.production_blockers || []).map(b => `<li>${esc(b)}</li>`).join('') || '<li>No activation blockers recorded.</li>';
  }
  function primaryThemes() {
    return (snapshot?.themes || []).filter(t => t.priority && t.priority !== 'Watch').sort((a, b) => {
      const direction = /short/i.test(snapshot?.market_direction) ? 1 : -1;
      return direction * ((Number(a.score) || 0) - (Number(b.score) || 0)) || a.theme_id.localeCompare(b.theme_id);
    });
  }
  function qualifiedRows() { return (snapshot?.relationships || []).filter(r => r.qualifies); }
  function uniqueRows(rows) {
    // Choose the server's assigned relationship BEFORE view filtering. Never synthesize an aggregate W.
    const tickers = new Map();
    for (const row of rows) if (!tickers.has(row.ticker) || row.theme_id === row.assigned_section) tickers.set(row.ticker, row);
    return [...tickers.values()];
  }
  // Display transforms only: all breadth, returns, scores and trend come from the snapshot.
  function breadthBar(label,value,coverage = '') {
    const available = valid(value), bounded = available ? Math.max(0,Math.min(100,Number(value))) : 0;
    return `<div class="breadth-bar"><span class="breadth-label">${esc(label)}</span><svg viewBox="0 0 100 6" preserveAspectRatio="none" aria-hidden="true" focusable="false"><rect class="breadth-track" width="100" height="6" rx="2"/>${available ? `<rect class="breadth-fill" width="${bounded}" height="6" rx="2"/>` : ''}</svg><strong>${percent(value)}</strong>${coverage ? `<small>${esc(coverage)}</small>` : ''}</div>`;
  }
  function mapThemes() { return (snapshot?.themes || []).filter(t=>t.status === 'active' && valid(t.returns?.[0]?.value) && valid(t.returns?.[1]?.value)); }
  function mapDescription(t) { return `${t.name || t.theme_id} · Score ${number(t.score)} · 1M ${percent(t.returns?.[0]?.value,100,true)} · 3M ${percent(t.returns?.[1]?.value,100,true)} · ${t.index?.trend || 'Unavailable'} · ${t.priority || 'Watch'}`; }
  function renderThemeMap() {
    const fontScale = parseFloat(getComputedStyle(document.documentElement).fontSize) / 16;
    mapPadding.left=66*fontScale; mapPadding.right=24*fontScale; mapPadding.top=24; mapPadding.bottom=50*fontScale;
    const panelWidth = $('theme-map').clientWidth;
    mapWidth = Math.max(240,panelWidth ? (window.innerWidth <= 800 ? panelWidth : panelWidth * .78 - 20) : 800);
    const rows = mapThemes().sort((a,b)=>name(a.theme_id).localeCompare(name(b.theme_id))), active = (snapshot?.themes || []).filter(t=>t.status === 'active').length;
    if (!rows.length) { $('theme-map').innerHTML = empty('Theme Map unavailable','No Active themes with both supplied returns.'); return; }
    // Linear raw-return axes include zero and every finite supplied observation. Never trim outliers.
    const domain = index=>{
      const values=rows.map(t=>Number(t.returns[index].value)), low=Math.min(0,...values), high=Math.max(0,...values);
      const padding=Math.max((high-low)*.07,.005);
      return [low-padding,high+padding];
    };
    const [xmin,xmax]=domain(0), [ymin,ymax]=domain(1), width=mapWidth-mapPadding.left-mapPadding.right, height=mapHeight-mapPadding.top-mapPadding.bottom;
    const x=v=>mapPadding.left+(v-xmin)/(xmax-xmin)*width, y=v=>mapPadding.top+(ymax-v)/(ymax-ymin)*height;
    const tickCount=mapWidth<500 ? 3 : 5;
    const ticks=(low,high)=>Array.from({length:tickCount},(_,i)=>low+(high-low)*i/(tickCount-1));
    const xTicks=ticks(xmin,xmax).map((v,i)=>`<g class="map-tick"><line x1="${x(v)}" y1="${mapHeight-mapPadding.bottom}" x2="${x(v)}" y2="${mapHeight-mapPadding.bottom+4}"/><text x="${x(v)}" y="${mapHeight-mapPadding.bottom+21*fontScale}" text-anchor="${i === 0 ? 'start' : i === tickCount-1 ? 'end' : 'middle'}">${percent(v,100)}</text></g>`).join('');
    const yTicks=ticks(ymin,ymax).map(v=>`<g class="map-tick"><line x1="${mapPadding.left-4}" y1="${y(v)}" x2="${mapPadding.left}" y2="${y(v)}"/><text x="${mapPadding.left-9}" y="${y(v)+4}" text-anchor="end">${percent(v,100)}</text></g>`).join('');
    const point=t=>{
      const cx=x(Number(t.returns[0].value)),cy=y(Number(t.returns[1].value)), cls=tone(t.index?.trend);
      const shape=cls === 'negative' ? `<path d="M${cx-5} ${cy-4}h10l-5 9z"/>` : cls === 'mixed' ? `<path d="M${cx} ${cy-6}l6 6-6 6-6-6z"/>` : `<circle cx="${cx}" cy="${cy}" r="4.5"/>`;
      return `<a href="${themeHref(t.theme_id)}" data-inspect-theme="${esc(t.theme_id)}" data-map-theme="${esc(t.theme_id)}" data-focus-key="map:${esc(t.theme_id)}" class="map-point ${cls}" aria-label="${esc(mapDescription(t))}"><title>${esc(mapDescription(t))}</title><circle class="point-hit" cx="${cx}" cy="${cy}" r="12"/><circle class="point-ring" cx="${cx}" cy="${cy}" r="9"/>${shape}</a>`;
    };
    $('theme-map').innerHTML = `<div class="map-toolbar"><p class="table-note">Raw returns · linear axes · ${rows.length}/${active} Active themes</p><label class="inline-label">Focus theme<select id="map-selection" data-focus-key="map-selection"><option value="">Select a theme</option>${rows.map(t=>`<option value="${esc(t.theme_id)}">${esc(t.name || t.theme_id)}</option>`).join('')}</select></label></div><div class="map-layout"><div class="map-chart"><div class="map-axis-label">3M return ↑</div><svg id="theme-map-svg" viewBox="0 0 ${mapWidth} ${mapHeight}" role="group" aria-label="Theme Map: raw 1M return horizontally, raw 3M return vertically. Each link opens theme research." data-xmin="${xmin}" data-xmax="${xmax}" data-ymin="${ymin}" data-ymax="${ymax}"><rect class="map-field" x="${mapPadding.left}" y="${mapPadding.top}" width="${width}" height="${height}"/><line class="map-zero" x1="${x(0)}" y1="${mapPadding.top}" x2="${x(0)}" y2="${mapHeight-mapPadding.bottom}"/><line class="map-zero" x1="${mapPadding.left}" y1="${y(0)}" x2="${mapWidth-mapPadding.right}" y2="${y(0)}"/>${xTicks}${yTicks}${rows.map(point).join('')}</svg><div class="map-axis-label map-x-label">1M return →</div></div><div id="map-readout" class="map-readout" aria-live="polite"></div></div><div class="map-footer"><span class="map-legend"><span class="positive">● Bullish</span><span class="negative">▼ Bearish</span><span class="mixed">◆ Mixed</span><span class="neutral">○ Unavailable</span></span><a class="text-link" href="#themes">Theme table ${chevron}</a></div>`;
    if (!rows.some(t=>t.theme_id === mapSelected)) mapSelected = rows[0].theme_id;
    $('map-selection').value = mapSelected;
    showMapReadout(mapSelected);
  }
  function showMapReadout(id) {
    const t=mapThemes().find(t=>t.theme_id === id);
    if (!t || !$('map-readout')) return;
    mapSelected=id;
    $('map-selection').value=id;
    document.querySelectorAll('[data-map-theme]').forEach(node=>node.classList.toggle('map-selected',node.dataset.mapTheme === id));
    $('map-readout').innerHTML=`<h3>${themeLink(id)}</h3><dl><div><dt>Score</dt><dd>${number(t.score)}</dd></div><div><dt>1M</dt><dd class="${signTone(t.returns[0].value)}">${percent(t.returns[0].value,100,true)}</dd></div><div><dt>3M</dt><dd class="${signTone(t.returns[1].value)}">${percent(t.returns[1].value,100,true)}</dd></div></dl>${state(t.index?.trend)}<p>${priority(t.priority)}</p>`;
  }
  function marketEMA(label,close,value) {
    const available = valid(close) && valid(value), relation = !available ? 'Unavailable' : Number(close) > Number(value) ? 'Above' : Number(close) < Number(value) ? 'Below' : 'At';
    const cls = relation === 'Above' ? 'positive' : relation === 'Below' ? 'negative' : 'neutral';
    return `<div class="ema-context ${cls}"><span>${icon(relation === 'Above' ? 'up' : relation === 'Below' ? 'down' : 'flat')} ${relation} ${label}</span><b>${money(value)}</b></div>`;
  }
  function renderOverview() {
    const market = snapshot?.market || {}, decision = market.decision || {}, direction = snapshot?.market_direction || decision.direction || 'Unclassified';
    $('market-direction').innerHTML = `<div class="direction-row"><div><span class="metric-label">Market</span><h2 class="direction-name ${tone(direction)}"><span class="direction-symbol" aria-hidden="true">${symbol(direction)}</span>${esc(direction)}</h2></div><details class="decision-details"><summary>Market Matrix</summary><p id="decision-path">${esc(decision.reason || 'Unavailable until a successful refresh.')}</p><p id="today-plan">${esc(snapshot?.today_plan || '')}</p><p>Breadth: ${esc(market.breadth_consensus || 'Unavailable')}${decision.breadth_qualifier ? ' · ' + esc(decision.breadth_qualifier) : ''}</p></details></div>`;
    $('market-cards').innerHTML = ['SPY','QQQ','IWM'].map(ticker => {
      const row = market.context?.[ticker] || {}, b = row.breadth || {};
      return `<article class="market-card ${ticker === 'IWM' ? 'context' : ''}" aria-label="${ticker} market context"><div class="market-card-head"><span class="market-ticker">${ticker}</span><span class="market-price">${money(row.close)}</span>${state(row.price_state)}</div>${ticker === 'IWM' ? `<span class="muted">Context only</span><div class="market-emas">${marketEMA('EMA21',row.close,row.ema21)}${marketEMA('EMA50',row.close,row.ema50)}</div>` : `<div class="market-emas">${marketEMA('EMA21',row.close,row.ema21)}${marketEMA('EMA50',row.close,row.ema50)}</div><div class="market-breadth">${breadthBar('Breadth 21',b.above_ema21)}${breadthBar('Breadth 50',b.above_ema50)}</div><span class="breadth-state ${tone(b.state)}" title="${esc(b.valid ?? 0)}/${esc(b.configured ?? 0)} valid">${symbol(b.state)} ${esc(b.state || 'Unavailable')} breadth</span>`}</article>`;
    }).join('');
    $('market-data-details').innerHTML = ['SPY','QQQ'].map(ticker=>{
      const row=market.context?.[ticker] || {}, b=row.breadth || {};
      return `<p>${ticker} breadth · ${esc(b.valid ?? 0)}/${esc(b.configured ?? 0)} valid · ${esc(b.state || 'Unavailable')}<br>${esc(row.roster_source || 'Roster unavailable')}<br>${esc((row.roster_warnings || []).join(' ') || 'No roster advisories.')}</p>`;
    }).join('');
    renderThemeMap();
    const themes = primaryThemes().slice(0, 5);
    $('primary-themes').innerHTML = themes.length ? themes.map((t, i) => `<div class="preview-row"><span class="position">${String(i + 1).padStart(2,'0')}</span><div>${themeLink(t.theme_id)}<small>${esc(t.family)}</small></div><div class="preview-value">${number(t.score)}<small>${priority(t.priority)}</small></div></div>`).join('') : empty('No Primary themes today', 'No themes qualify in this snapshot.', '<a href="#themes" class="text-link">Explore themes →</a>');
    const stocks = uniqueRows(qualifiedRows()).sort((a, b) => a.ticker.localeCompare(b.ticker)).slice(0, 5);
    $('candidate-preview').innerHTML = stocks.length ? stocks.map(r => `<div class="preview-row stock-row"><div>${tickerLink(r.ticker)}<small>${themeLink(r.theme_id)} · ${esc(r.role)}</small></div><div class="preview-value ${signTone(r.relative?.w)}">${points(r.relative?.w)}</div>${saveButton(r.ticker, 'overview')}</div>`).join('') : empty('No Primary stocks', 'No qualifying stocks in this snapshot.', '<a href="#primary" class="text-link">Open Primary →</a>');
  }
  function setOptions(id, options) {
    const select = $(id), first = select.options[0].outerHTML, previous = select.value;
    const html = first + options.map(([value, text]) => `<option value="${esc(value)}">${esc(text)}</option>`).join('');
    if (select.innerHTML !== html) { select.innerHTML = html; select.value = options.some(([value]) => value === previous) ? previous : ''; }
  }
  function themeValue(theme, key) {
    if (key === 'name') return theme.name || theme.theme_id;
    if (key === 'score') return valid(theme.score) ? Number(theme.score) : null;
    if (key === 'return1' || key === 'return3') { const v = theme.returns?.[key === 'return1' ? 0 : 1]?.value; return valid(v) ? Number(v) : null; }
    if (key === 'breadth') { const v = theme.breadth?.[0]?.value; return valid(v) ? Number(v) : null; }
    if (key === 'trend') return theme.index?.trend || 'Unavailable';
    if (key === 'change') return comparison(theme);
    return theme[key] || '';
  }
  function compareValues(a, b, descending = false) {
    if (a == null) return b == null ? 0 : 1;
    if (b == null) return -1;
    const order = typeof a === 'number' ? a - b : String(a).localeCompare(String(b));
    return descending ? -order : order;
  }
  function themeRows() {
    const query = $('theme-search').value.trim().toLowerCase();
    return (snapshot?.themes || []).filter(t => (ui.universe === 'active' ? t.status === 'active' : t.status !== 'active') && (!query || `${t.name} ${t.theme_id} ${t.family}`.toLowerCase().includes(query)) && (!$('theme-family').value || t.family === $('theme-family').value) && (!$('theme-priority').value || t.priority === $('theme-priority').value) && (!$('theme-trend').value || (t.index?.trend || 'Unavailable') === $('theme-trend').value)).sort((a, b) => compareValues(themeValue(a, ui.themeSort), themeValue(b, ui.themeSort), ui.themeDescending) || a.theme_id.localeCompare(b.theme_id));
  }
  function sortHeading(label, key, numeric = false) {
    const selected = ui.themeSort === key;
    return `<th scope="col"${numeric ? ' class="numeric"' : ''}${selected ? ` aria-sort="${ui.themeDescending ? 'descending' : 'ascending'}"` : ''}><button class="sort-button" data-theme-sort="${key}" data-focus-key="sort:${key}">${label}<span aria-hidden="true">${selected ? ui.themeDescending ? '↓' : '↑' : '↕'}</span><span class="sr-only">, sort ${selected && !ui.themeDescending ? 'descending' : 'ascending'}</span></button></th>`;
  }
  function renderThemes() {
    const active = (snapshot?.themes || []).filter(t => t.status === 'active').length;
    $('active-count').textContent = active; $('watch-count').textContent = (snapshot?.themes?.length || 0) - active;
    document.querySelectorAll('[data-universe]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.universe === ui.universe)));
    const rows = themeRows();
    $('theme-results').textContent = `${rows.length} ${ui.universe === 'active' ? 'Active themes' : 'Watch-only concepts'} · ${snapshot?.session || 'No snapshot'} · Sort: ${({'score':'Score','name':'Theme','return1':'1M','return3':'3M','trend':'Trend','breadth':'Breadth EMA21','priority':'Priority','change':'Comparison'})[ui.themeSort]} ${ui.themeDescending ? 'high → low' : 'low → high'}`;
    if (!rows.length) { $('theme-table').innerHTML = empty(snapshot ? 'No themes match this view' : 'Your theme universe is waiting', snapshot ? 'Try another search or reset the filters. Watch-only concepts have no live calculation membership.' : 'Refresh Data to load a completed-session snapshot.', '<button class="button secondary" data-reset="themes">Reset filters</button>'); return; }
    const heading = `<thead><tr><th scope="col" title="Position in this sorted and filtered list, not an official canonical rank">#</th>${sortHeading('Theme','name')}${sortHeading('Score','score',true)}${sortHeading('1M %','return1',true)}${sortHeading('3M %','return3',true)}${sortHeading('Trend','trend')}${sortHeading('B21 / B50','breadth',true)}${sortHeading('Priority','priority')}</tr></thead>`;
    const body = rows.map((t, i) => {
      const tie = valid(t.score) && rows.some((x, j) => j !== i && valid(x.score) && Number(x.score) === Number(t.score));
      return `<tr data-theme-row="${esc(t.theme_id)}" class="${ui.selectedTheme === t.theme_id ? 'selected-row' : ''}"><td class="list-position">${String(i+1).padStart(2,'0')}</td><td class="theme-name" data-label="Theme">${themeLink(t.theme_id)}${ui.selectedTheme === t.theme_id ? '<span class="sr-only"> · Last opened theme</span>' : ''}<small class="theme-family">${esc(t.family)}</small>${tie ? '<small class="tie-label">equal Score</small>' : ''}</td><td class="numeric" data-label="Score">${number(t.score)}</td><td class="numeric ${signTone(t.returns?.[0]?.value)}" data-label="1M">${percent(t.returns?.[0]?.value,100,true)}</td><td class="numeric ${signTone(t.returns?.[1]?.value)}" data-label="3M">${percent(t.returns?.[1]?.value,100,true)}</td><td data-label="${prelaunch() ? 'Research trend' : 'Trend'}">${state(t.index?.trend)}</td><td class="numeric" data-label="Breadth >21 / >50"><span class="breadth-values"><span>${themeBreadth(t.breadth?.[0])}</span><span>${themeBreadth(t.breadth?.[1])}</span></span></td><td data-label="Priority">${priority(t.priority)}</td></tr>`;
    }).join('');
    const sortControl = `<label class="theme-mobile-sort inline-label">Sort themes<select id="theme-mobile-sort"><option value="score:desc">Score high to low</option><option value="score:asc">Score low to high</option><option value="name:asc">Theme A–Z</option><option value="return1:desc">1M high to low</option><option value="return3:desc">3M high to low</option><option value="priority:asc">Priority</option></select></label>`;
    $('theme-table').innerHTML = sortControl + `<table role="table"><caption class="sr-only">Custom theme research · financial metrics from the published snapshot. 1M and 3M are median member returns. Breadth is context only.</caption>${heading}<tbody role="rowgroup">${body}</tbody></table>`;
    const mobile = $('theme-mobile-sort'); if ([...mobile.options].some(o => o.value === `${ui.themeSort}:${ui.themeDescending ? 'desc' : 'asc'}`)) mobile.value = `${ui.themeSort}:${ui.themeDescending ? 'desc' : 'asc'}`;
  }
  function eligibility(row) { return !row.eligibility?.available ? 'Unavailable' : row.eligibility.eligible ? 'Eligible' : 'Ineligible'; }
  function candidateRow(row, location) {
    return `<tr><td data-label="Ticker">${tickerLink(row.ticker)}</td><td data-label="Theme">${themeLink(row.theme_id)}</td><td data-label="Role">${esc(row.role)}</td><td data-label="W" class="numeric ${signTone(row.relative?.w)}">${points(row.relative?.w)}</td>${earningsEnabled() ? `<td data-label="Earnings" class="table-note">${earnings(row.ticker)}</td>` : ''}<td data-label="Save">${saveButton(row.ticker,location + ':' + row.theme_id)}</td></tr>`;
  }
  const candidateHeaders = () => ['Ticker','Theme','Role',{label:'W · pp',numeric:true},...(earningsEnabled() ? ['Earnings'] : []),'Save'];
  function matchesCandidate(row) {
    const query = $('candidate-search').value.trim().toLowerCase(), filter = $('candidate-theme').value, w = row.relative?.w;
    const text = `${row.ticker} ${name(row.theme_id)} ${name(row.assigned_section)} ${(row.also_qualifies_in || []).map(name).join(' ')}`.toLowerCase();
    const themes = new Set(qualifiedRows().filter(r => r.ticker === row.ticker).map(r => r.theme_id));
    return (!query || text.includes(query)) && (!filter || (ui.candidateMode === 'unique' ? themes.has(filter) : row.theme_id === filter)) && (!$('candidate-role').value || row.role === $('candidate-role').value) && (!$('candidate-w').value || valid(w) && ($('candidate-w').value === 'positive' ? Number(w) > 0 : Number(w) < 0)) && (!$('candidate-earnings').value || (earningsDates(row.ticker).length > 0) === ($('candidate-earnings').value === 'available'));
  }
  function renderCandidates() {
    const enabled = earningsEnabled(), earningsFilter = $('candidate-earnings');
    if (!enabled) { if (document.activeElement === earningsFilter) $('candidate-search').focus({preventScroll:true}); earningsFilter.value = ''; }
    earningsFilter.closest('label').hidden = !enabled;
    const all = qualifiedRows(), unique = uniqueRows(all), mode = ui.candidateMode;
    const rows = (mode === 'unique' ? unique : all).filter(matchesCandidate);
    const sort = $('candidate-sort').value;
    rows.sort((a,b) => (sort === 'w-desc' || sort === 'w-asc' ? compareValues(valid(a.relative?.w) ? Number(a.relative.w) : null, valid(b.relative?.w) ? Number(b.relative.w) : null, sort === 'w-desc') : sort === 'theme' ? name(a.theme_id).localeCompare(name(b.theme_id)) : a.ticker.localeCompare(b.ticker)) || a.ticker.localeCompare(b.ticker) || a.theme_id.localeCompare(b.theme_id));
    document.querySelectorAll('[data-candidate-mode]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.candidateMode === mode)));
    $('primary-count').textContent = unique.length;
    $('primary-context').textContent = `${unique.length} stocks · ${all.length} theme qualifications · ${snapshot?.session || 'No snapshot'}`;
    $('candidate-results').textContent = `${rows.length} shown · ${all.length} theme qualifications · ${unique.length} stocks · ${snapshot?.session || 'No snapshot'}`;
    if (!rows.length) { $('candidates').innerHTML = empty(all.length ? 'No Primary stocks match these filters' : 'No Primary stocks this session', all.length ? 'Try resetting the filters.' : 'No qualifying stocks in this snapshot.', '<button class="button secondary" data-reset="candidates">Reset filters</button>'); return; }
    if (mode === 'unique') $('candidates').innerHTML = `<div class="table-wrap" role="region" tabindex="0" aria-label="Unique Primary stocks">${table(candidateHeaders(),rows.map(r => candidateRow(r,'candidates')), 'Unique Primary stocks. W is from the assigned export relationship, in percentage points.')}</div>`;
    else {
      const groups = new Map();
      for (const row of rows) { if (!groups.has(row.theme_id)) groups.set(row.theme_id,[]); groups.get(row.theme_id).push(row); }
      $('candidates').innerHTML = [...groups].map(([themeId, members]) => `<section class="qualification-group"><div class="group-heading"><h3>${themeLink(themeId)} <span class="muted">· ${members.length}</span></h3>${themeDownload(themeId)}</div><div class="table-wrap" role="region" tabindex="0" aria-label="${esc(name(themeId))} candidates">${table(candidateHeaders(),members.map(r => candidateRow(r,'candidates')),name(themeId) + ' qualifying relationships')}</div></section>`).join('');
    }
  }
  function memberRows(themeId) {
    let rows = (snapshot?.relationships || []).filter(r => r.theme_id === themeId && (!ui.memberSearch || r.ticker.toLowerCase().includes(ui.memberSearch.toLowerCase())) && (!ui.memberRole || r.role === ui.memberRole) && (!ui.memberEligibility || eligibility(r) === ui.memberEligibility));
    rows.sort((a,b) => ui.memberSort === 'ticker' ? a.ticker.localeCompare(b.ticker) : compareValues(valid(a.relative?.w) ? Number(a.relative.w) : null,valid(b.relative?.w) ? Number(b.relative.w) : null, ui.memberSort === 'w-desc') || a.ticker.localeCompare(b.ticker));
    return rows;
  }
  function renderMembers(themeId) {
    const rows = memberRows(themeId), total = (snapshot?.relationships || []).filter(r => r.theme_id === themeId).length;
    $('member-count').textContent = `${rows.length} of ${total} supplied Core + Enabler relationships`;
    $('member-table').innerHTML = rows.length ? table(['Ticker','Role',{label:'W vs Theme Peers',numeric:true},'Eligibility','Qualification',...(earningsEnabled() ? ['Earnings'] : []),'Saved'], rows.map(r => `<tr><td>${tickerLink(r.ticker)}</td><td>${esc(r.role)}</td><td class="numeric ${signTone(r.relative?.w)}">${points(r.relative?.w)}</td><td class="table-note">${esc(eligibility(r))}</td><td><span class="table-note">${r.qualifies ? 'Qualifies' : 'Not qualified'}</span></td>${earningsEnabled() ? `<td class="table-note">${earnings(r.ticker)}</td>` : ''}<td>${saveButton(r.ticker,'member:' + themeId)}</td></tr>`), name(themeId) + ' calculation members; Related members are not present in this snapshot.') : empty(total ? 'No members match this view' : 'No calculation members supplied', total ? 'Try another ticker, role or eligibility filter.' : 'Watch-only concepts and Related members do not enter calculations. No member rows are invented.');
  }
  function renderDetail(themeId) {
    const theme = snapshot?.themes?.find(t => t.theme_id === themeId);
    if (!theme) { $('detail-content').innerHTML = `<a href="#themes" class="back-link">← Back to Themes</a>` + empty('Theme not available', 'This theme is not in the current published snapshot. Return to Themes or refresh your data.'); return; }
    const originName = origin.startsWith('#primary') ? 'Primary' : origin.startsWith('#saved') ? 'Saved' : origin.startsWith('#overview') ? 'Overview' : 'Themes';
    const metric = (label,value,note = '') => `<div class="metric-block"><span class="metric-label">${label}</span><div class="metric-value">${value}</div>${note ? `<small>${note}</small>` : ''}</div>`;
    $('detail-content').innerHTML = `<div class="crumbs"><a href="${esc(origin)}" class="back-link" data-return-theme="${esc(themeId)}">← Back to ${originName}</a>${themeDownload(themeId)}</div><div class="detail-heading"><p class="eyebrow">${esc(theme.family)} · ${theme.status === 'active' ? 'ACTIVE THEME' : 'WATCH-ONLY CONCEPT'}</p><h1 id="detail-title" tabindex="-1">${esc(theme.name || themeId)}</h1>${priority(theme.priority)}</div><div class="detail-summary">${metric('Custom Theme Score', number(theme.score), 'Cross-theme percentile blend')}${metric('Median 1M', `<span class="${signTone(theme.returns?.[0]?.value)}">${percent(theme.returns?.[0]?.value,100,true)}</span>`, '21 completed sessions')}${metric('Median 3M', `<span class="${signTone(theme.returns?.[1]?.value)}">${percent(theme.returns?.[1]?.value,100,true)}</span>`, '63 completed sessions')}${metric(prelaunch() ? 'Pre-launch research trend' : 'Synthetic Theme Trend', state(theme.index?.trend), 'Index vs EMA21 / EMA50')}${metric('Breadth > EMA21', percent(theme.breadth?.[0]?.value), `${theme.breadth?.[0]?.valid ?? 0}/${theme.breadth?.[0]?.configured ?? 0} valid members`)}${metric('Breadth > EMA50', percent(theme.breadth?.[1]?.value), `${theme.breadth?.[1]?.valid ?? 0}/${theme.breadth?.[1]?.configured ?? 0} valid members`)}</div><div class="detail-context"><span>Comparison: <strong>${esc(comparison(theme))}</strong></span><span>Index <strong>${number(theme.index?.level)}</strong></span><span>EMA21 <strong>${number(theme.index?.ema21)}</strong> / EMA50 <strong>${number(theme.index?.ema50)}</strong></span></div><p class="detail-explainer">${comparison(theme) === 'Comparison unavailable' ? 'No compatible prior live session. Research bootstrap and legacy ETF history cannot supply a live transition. ' : ''}Breadth is context only. <a href="#methodology">Metric definitions →</a></p><div class="section-heading"><h2>Member research</h2><span id="member-count" class="muted table-note"></span></div><form id="member-filters" class="filter-bar" role="search" aria-label="Filter theme members"><label class="search-field">Search members<input id="member-search" type="search" placeholder="Ticker…" value="${esc(ui.memberSearch)}"></label><label>Role<select id="member-role"><option value="">All roles</option><option>Core</option><option>Enabler</option></select></label><label>Eligibility<select id="member-eligibility"><option value="">All states</option><option>Eligible</option><option>Ineligible</option><option>Unavailable</option></select></label><label>Sort<select id="member-sort"><option value="ticker">Ticker A–Z</option><option value="w-desc">W high to low</option><option value="w-asc">W low to high</option></select></label></form><div id="member-table" class="table-wrap member-table" role="region" tabindex="0" aria-label="Theme member research"></div>`;
    $('member-role').value = ui.memberRole; $('member-eligibility').value = ui.memberEligibility; $('member-sort').value = ui.memberSort;
    renderMembers(themeId);
  }
  function renderSaved() {
    $('saved-count').textContent = watched.length;
    if (!watched.length) { $('saved').innerHTML = empty('No Saved tickers', 'Browser-local bookmarks.', '<a class="button secondary" href="#primary">Browse Primary →</a>'); return; }
    $('saved').innerHTML = '<p class="saved-scope">Browser-local bookmarks</p><div class="saved-list">' + watched.map(ticker => {
      const rows = (snapshot?.relationships || []).filter(r => r.ticker === ticker), assignment = snapshot?.exports?.assignments?.[ticker];
      const assigned = rows.find(r => r.theme_id === assignment?.assigned_section);
      return `<article class="saved-row ${earningsEnabled() ? '' : 'no-earnings'}">${tickerLink(ticker)}<div class="saved-context"><span>${assignment ? `Current Primary · ${themeLink(assignment.assigned_section)}` : snapshot ? 'Not currently Primary' : 'No snapshot'}</span>${!rows.length ? '<small>No current relationship · bookmark retained</small>' : ''}</div><span class="numeric ${signTone(assigned?.relative?.w)}">${points(assigned?.relative?.w)}</span>${earningsEnabled() ? `<span class="table-note">${earnings(ticker)}</span>` : ''}<button class="button quiet small" data-remove="${esc(ticker)}" data-focus-key="saved-remove:${esc(ticker)}" aria-label="Remove ${esc(ticker)} from Saved">Remove</button></article>`;
    }).join('') + '</div>';
  }

  function syncSaveButtons() {
    document.querySelectorAll('[data-save]').forEach(button => {
      const saved = watched.includes(button.dataset.save);
      button.setAttribute('aria-pressed',String(saved)); button.setAttribute('aria-label',saved ? `Saved ${button.dataset.save}; remove from Saved` : `Save ${button.dataset.save}`);
      button.innerHTML = `<span aria-hidden="true">${saved ? '★' : '☆'}</span><span class="sr-only">${saved ? 'Saved' : 'Save'}</span>`;
    });
    $('saved-count').textContent = watched.length;
  }
  function changeSaved(ticker, remove = false) {
    watched = remove || watched.includes(ticker) ? watched.filter(s => s !== ticker) : [...watched,ticker];
    let persisted = true;
    try { localStorage.setItem(savedKey, JSON.stringify(watched)); } catch { persisted = false; }
    syncSaveButtons();
    if (inspector && route === '#saved') renderSaved();
    if (route === '#saved' && !inspector) {
      const index = [...document.querySelectorAll('[data-remove]')].findIndex(b => b.dataset.remove === ticker);
      renderSaved(); const buttons = document.querySelectorAll('[data-remove]');
      (buttons[Math.min(Math.max(index,0),buttons.length - 1)] || $('saved-title')).focus({preventScroll:true});
    }
    announce(`${ticker} ${watched.includes(ticker) ? 'saved' : 'removed from Saved'}${persisted ? '' : ' for this visit; browser storage is unavailable'}.`);
  }
  function inspectorFromLocation() {
    const params = new URLSearchParams((location.hash || '').split('?')[1] || '');
    const kind = params.has('theme') ? 'theme' : params.has('ticker') ? 'ticker' : null;
    const id = kind && params.get(kind);
    return id ? {kind,id} : null;
  }
  function inspectorView() {
    const key = inspector?.kind + ':' + inspector?.id;
    if (!inspectorViews.has(key)) inspectorViews.set(key,{filter:'All',search:'',sort:'ticker'});
    return inspectorViews.get(key);
  }
  function openInspector(kind,id,trigger) {
    if (!inspector) { inspectorTrigger = trigger; inspectorOrigin = route; inspectorScroll = window.scrollY; }
    const url = (route || '#overview') + '?' + kind + '=' + encodeURIComponent(id);
    const owned = inspector ? Boolean(history.state?.researchInspector) : true;
    if (inspector) history.replaceState({researchInspector:owned},'',url);
    else history.pushState({researchInspector:true},'',url);
    syncInspector();
  }
  function closeInspector() {
    if (history.state?.researchInspector) history.back();
    else { history.replaceState(null,'',route || '#overview'); syncInspector(); }
  }
  function dismissInspector(restore = true) {
    if (!inspector) return;
    inspector = null;
    $('research-inspector').close();
    document.documentElement.classList.remove('inspecting');
    if (restore) {
      window.scrollTo(0,inspectorScroll);
      restoreFocus(inspectorTrigger);
      if (document.activeElement === document.body) document.querySelector('.view:not([hidden]) h1')?.focus({preventScroll:true});
    }
    document.title = (route.startsWith('#themes/') ? name(detailId()) : route === '#primary' ? 'Primary Watchlist' : route.slice(1).replace(/^./,x=>x.toUpperCase())) + ' · ThemeScope';
  }
  function syncInspector() {
    const next = inspectorFromLocation();
    if (!next) { dismissInspector(); return; }
    const unchanged = inspector?.kind === next.kind && inspector?.id === next.id;
    if (!inspector) { inspectorScroll = window.scrollY; if (inspectorOrigin !== route) inspectorTrigger = ''; }
    inspector = next;
    if (inspector.kind === 'theme') { ui.selectedTheme = inspector.id; document.querySelectorAll('[data-theme-row]').forEach(row=>row.classList.toggle('selected-row',row.dataset.themeRow === inspector.id)); }
    renderInspector(unchanged);
    if (!$('research-inspector').open) { closeDisplay(); $('research-inspector').showModal(); document.documentElement.classList.add('inspecting'); }
    if (!unchanged) { $('research-inspector').scrollTop = 0; $('inspector-title').focus({preventScroll:true}); }
  }
  function metric(label,value) { return `<div class="metric-block"><span class="metric-label">${label}</span><div class="metric-value">${value}</div></div>`; }
  function renderInspector(preserve = false) {
    if (!inspector) return;
    const dialog = $('research-inspector'), focused = dialog.contains(document.activeElement) ? focusKey() : null;
    const textSelection = document.activeElement?.id === 'inspector-search' ? document.activeElement.selectionStart : null;
    const scroll = dialog.scrollTop;
    $('inspector-kind').textContent = inspector.kind === 'theme' ? 'Theme research' : 'Ticker research';
    $('inspector-title').textContent = inspector.kind === 'theme' ? name(inspector.id) : inspector.id;
    $('inspector-status').textContent = ['failed','interrupted'].includes(currentStatus.state) ? 'Refresh failed · previous successful snapshot retained' : 'Completed session ' + (snapshot?.session || '—');
    document.title = $('inspector-title').textContent + ' · Research · ThemeScope';
    if (inspector.kind === 'theme') renderThemeInspector(); else renderTickerInspector();
    if (preserve) { dialog.scrollTop = scroll; restoreFocus(focused); if (textSelection != null) $('inspector-search')?.setSelectionRange(textSelection,textSelection); }
  }
  function renderThemeInspector() {
    const t = snapshot?.themes?.find(row=>row.theme_id === inspector.id);
    if (!t) { $('inspector-content').innerHTML = empty('Theme unavailable','No theme supplied in this snapshot.'); return; }
    const v = inspectorView();
    $('inspector-content').innerHTML = `<div class="inspector-subhead"><span>${esc(t.family)} · ${t.status === 'active' ? 'Active' : 'Watch-only'}</span><a class="text-link" href="${themeHref(t.theme_id)}">Open full theme ${chevron}</a></div><div class="inspector-metrics">${metric('Score',number(t.score))}${metric('Priority',priority(t.priority))}${metric('Trend',state(t.index?.trend))}${metric('1M',`<span class="${signTone(t.returns?.[0]?.value)}">${percent(t.returns?.[0]?.value,100,true)}</span>`)}${metric('3M',`<span class="${signTone(t.returns?.[1]?.value)}">${percent(t.returns?.[1]?.value,100,true)}</span>`)}</div><dl class="index-strip"><div><dt>Synthetic index</dt><dd>${number(t.index?.level)}</dd></div><div><dt>EMA21</dt><dd>${number(t.index?.ema21)}</dd></div><div><dt>EMA50</dt><dd>${number(t.index?.ema50)}</dd></div></dl><div class="inspector-breadth">${breadthBar('Above EMA21',t.breadth?.[0]?.value,`${t.breadth?.[0]?.valid ?? 0}/${t.breadth?.[0]?.configured ?? 0} valid`)}${breadthBar('Above EMA50',t.breadth?.[1]?.value,`${t.breadth?.[1]?.valid ?? 0}/${t.breadth?.[1]?.configured ?? 0} valid`)}</div><p class="inspector-comparison">${esc(comparison(t))} · ${prelaunch() ? 'Pre-launch research' : snapshot?.theme_layer?.state === 'initialized' ? 'Launch initialization · no earned return' : snapshot?.theme_layer?.state === 'live' ? 'Official theme history' : 'No official live history'}</p><div class="section-heading"><h3>Member research</h3>${themeDownload(t.theme_id)}</div><form class="inspector-filters" aria-label="Filter inspector members"><div class="segmented" role="group" aria-label="Member view">${['All','Primary','Eligible','Core','Enabler'].map(f=>`<button type="button" data-inspector-filter="${f}" data-focus-key="inspect-filter:${f}" aria-pressed="${v.filter === f}">${f}</button>`).join('')}</div><div class="inspector-search-row"><label>Search members<input id="inspector-search" type="search" placeholder="Ticker…" value="${esc(v.search)}" data-focus-key="inspector-search"></label><label>Sort<select id="inspector-sort" data-focus-key="inspector-sort"><option value="ticker">Ticker A–Z</option><option value="w-desc">W high to low</option><option value="w-asc">W low to high</option></select></label></div></form><p id="inspector-member-count" class="table-meta" role="status"></p><div id="inspector-members" class="inspector-table"></div>`;
    $('inspector-sort').value = v.sort;
    renderInspectorMembers();
  }
  function renderInspectorMembers() {
    if (inspector?.kind !== 'theme' || !$('inspector-members')) return;
    const v = inspectorView(), all = (snapshot?.relationships || []).filter(r=>r.theme_id === inspector.id);
    const rows = all.filter(r=>(!v.search || r.ticker.toLowerCase().includes(v.search.toLowerCase())) && (v.filter === 'All' || v.filter === 'Primary' && r.qualifies || v.filter === 'Eligible' && r.eligibility?.eligible || r.role === v.filter));
    rows.sort((a,b)=>(v.sort === 'ticker' ? a.ticker.localeCompare(b.ticker) : compareValues(valid(a.relative?.w) ? Number(a.relative.w) : null,valid(b.relative?.w) ? Number(b.relative.w) : null,v.sort === 'w-desc')) || a.ticker.localeCompare(b.ticker));
    $('inspector-member-count').textContent = `${rows.length} / ${all.length} supplied members`;
    $('inspector-members').innerHTML = rows.length ? table(['Ticker','Role',{label:'W · pp',numeric:true},'State','Save'],rows.map(r=>`<tr><td>${tickerLink(r.ticker)}</td><td>${esc(r.role)}</td><td class="numeric ${signTone(r.relative?.w)}">${points(r.relative?.w)}</td><td class="member-state">${esc(eligibility(r))}<small>${r.qualifies ? 'Primary' : 'Not qualified'}</small></td><td>${saveButton(r.ticker,'inspector-member')}</td></tr>`),'Supplied theme members; W in percentage points. Related rows are not invented.') : empty('No supplied members match','');
  }
  function renderTickerInspector() {
    const ticker = inspector.id, rows = (snapshot?.relationships || []).filter(r=>r.ticker === ticker).sort((a,b)=>name(a.theme_id).localeCompare(name(b.theme_id)));
    const assignment = snapshot?.exports?.assignments?.[ticker], assigned = rows.find(r=>r.theme_id === assignment?.assigned_section);
    // W and role always belong to a supplied relationship. No cross-theme aggregate.
    const lead = assigned || (rows.length === 1 ? rows[0] : null), e = (lead || rows[0])?.eligibility;
    const primaryState = rows.some(r=>r.qualifies) ? 'Current Primary' : 'Not currently Primary';
    const cell = (label,value,toneClass='')=>`<div><dt>${label}</dt><dd class="${toneClass}">${value}</dd></div>`;
    $('inspector-content').innerHTML = `<div class="inspector-subhead"><span>${primaryState}</span>${saveButton(ticker,'inspector-ticker')}</div><div class="inspector-metrics ticker-metrics ${earningsEnabled() ? 'has-earnings' : ''}">${metric('Role',lead ? esc(lead.role) : rows.length ? 'Per theme' : '—')}${metric('W · pp',`<span class="${signTone(lead?.relative?.w)}">${lead ? points(lead.relative?.w) : rows.length ? 'Per theme' : '—'}</span>`)}${metric('Eligibility',e ? esc(eligibility({eligibility:e})) : 'Unavailable')}${earningsEnabled() ? metric('Earnings',earnings(ticker)) : ''}</div><dl class="assignment"><dt>Assigned theme</dt><dd>${assignment ? themeLink(assignment.assigned_section) : 'No current assignment'}</dd><dt>Other qualifying themes</dt><dd>${rows.filter(r=>r.qualifies && r.theme_id !== assignment?.assigned_section).map(r=>themeLink(r.theme_id)).join('<br>') || '—'}</dd></dl><div class="section-heading"><h3>Theme relationships</h3><span class="muted table-note">${rows.length} supplied</span></div><div class="ticker-relationships">${rows.map(r=>`<section class="ticker-relationship"><div class="relationship-heading">${themeLink(r.theme_id)}<span class="table-note">${r.qualifies ? 'Qualifies' : 'Not qualified'}</span></div><dl class="relationship-metrics">${cell('Role',esc(r.role))}${cell('W',points(r.relative?.w),signTone(r.relative?.w))}${cell('Eligibility',esc(eligibility(r)))}${cell('ER1M',points(r.relative?.er1),signTone(r.relative?.er1))}${cell('ER3M',points(r.relative?.er3),signTone(r.relative?.er3))}${cell('Peer median 1M',percent(r.relative?.peer1?.value,100,true),signTone(r.relative?.peer1?.value))}${cell('Peer median 3M',percent(r.relative?.peer3?.value,100,true),signTone(r.relative?.peer3?.value))}</dl>${r.eligibility?.reasons?.length ? `<p class="table-note">${r.eligibility.reasons.map(reason=>esc(({insufficient_volume_history:'Insufficient volume history',missing_completed_regular_session:'Missing completed session',price_below_floor:'Close below $5',average_volume_not_above_floor:'10-session average volume not above 500,000',turnover_below_floor:'Turnover below $10 million'})[reason] || reason)).join(' · ')}</p>` : ''}</section>`).join('') || '<p class="empty-state">No current relationship supplied. Bookmark retained if Saved.</p>'}</div>${e ? `<details class="liquidity-details"><summary>Liquidity inputs</summary><dl class="relationship-metrics">${cell('Close',money(e.close))}${cell('Average volume · 10 sessions',number(e.average_volume,0))}${cell('Daily turnover',money(e.turnover))}</dl></details>` : ''}`;
  }
  function parseRoute() {
    const raw = (location.hash || '#overview').split('?')[0];
    if (['#market','#daily-plan'].includes(raw)) return '#overview';
    if (raw === '#candidates') return '#primary';
    if (raw === '#watchlist') return '#saved';
    return /^#(overview|themes(?:\/[^/]+)?|primary|saved|methodology)$/.test(raw) ? raw : '#overview';
  }
  function detailId() { try { return decodeURIComponent(route.split('/')[1] || ''); } catch { return ''; } }
  function showRoute(initial = false) {
    const next = parseRoute();
    const previousRoute = route;
    if (next === route) { syncInspector(); return; }
    dismissInspector(false);
    if (route) positions.set(route,{scroll:window.scrollY, table:$('theme-table').scrollTop});
    route = next;
    const part = route.slice(1).split('/')[0], isDetail = route.startsWith('#themes/');
    const viewId = isDetail ? 'theme-detail' : ({overview:'overview-page',themes:'themes-page',primary:'candidate-page',saved:'saved-page',methodology:'methodology-page'})[part];
    document.querySelectorAll('.view').forEach(view => { view.hidden = view.id !== viewId; view.classList.remove('entering'); });
    const view = $(viewId); view?.classList.add('entering');
    document.querySelectorAll('[data-nav]').forEach(link => { if (link.dataset.nav === part) link.setAttribute('aria-current','page'); else link.removeAttribute('aria-current'); });
    if (isDetail) renderDetail(detailId());
    if (part === 'themes' && !isDetail) {
      document.querySelectorAll('[data-theme-row]').forEach(row => row.classList.toggle('selected-row',row.dataset.themeRow === ui.selectedTheme));
    }
    if (part === 'saved') renderSaved();
    const title = isDetail ? name(detailId()) : part.charAt(0).toUpperCase() + part.slice(1);
    document.title = title + ' · ThemeScope';
    requestAnimationFrame(() => {
      if (inspectorFromLocation()) { syncInspector(); return; }
      if (!initial) view?.querySelector('h1')?.focus({preventScroll:true});
      const pos = positions.get(route); window.scrollTo(0,pos?.scroll || 0);
      if (!isDetail && part === 'themes') $('theme-table').scrollTop = pos?.table || 0;
      if (previousRoute.startsWith('#themes/') && route === origin) view?.querySelector(`a[href="${CSS.escape(previousRoute)}"]`)?.focus({preventScroll:true});
    });
  }
  function render(data) {
    if (!data || typeof data !== 'object') return;
    const signature = JSON.stringify(data);
    if (signature === snapshotSignature) return; // Polling must not replace a focused or expanded research control.
    const focused = focusKey(), memberFocused = document.activeElement?.id?.startsWith('member-') ? {id:document.activeElement.id,start:document.activeElement.selectionStart} : null;
    const scroll = window.scrollY, themeScroll = $('theme-table').scrollTop;
    snapshot = data; snapshotSignature = signature;
    for (const url of blobUrls.values()) URL.revokeObjectURL(url); blobUrls.clear();
    renderLayer(); renderOverview();
    setOptions('theme-family',[...new Set((snapshot.themes || []).map(t => t.family).filter(Boolean))].sort().map(f => [f,f]));
    setOptions('candidate-theme',(snapshot.themes || []).filter(t => qualifiedRows().some(r => r.theme_id === t.theme_id)).sort((a,b) => (a.name || a.theme_id).localeCompare(b.name || b.theme_id)).map(t => [t.theme_id,t.name || t.theme_id]));
    renderThemes(); renderCandidates(); renderSaved();
    if (inspector) renderInspector(true);
    if (route.startsWith('#themes/')) { renderDetail(detailId()); document.title = name(detailId()) + ' · ThemeScope'; }
    const url = download();
    $('combined').setAttribute('aria-disabled',String(!url)); $('combined').tabIndex = url ? 0 : -1; if (url) $('combined').href = url;
    $('target').textContent = 'Completed US session ' + (snapshot.session || '—');
    $('theme-table').scrollTop = themeScroll; window.scrollTo(0,scroll); restoreFocus(focused);
    if (memberFocused) { const input = $(memberFocused.id); input?.focus({preventScroll:true}); if (input?.type === 'search' && memberFocused.start != null) input.setSelectionRange(memberFocused.start,memberFocused.start); }
  }
  function showStatus(status) {
    const previous = currentStatus; currentStatus = status;
    const progress = status.progress || status.state || 'Ready';
    if ($('progress').textContent !== progress) $('progress').textContent = progress;
    $('target-detail').textContent = 'Target session ' + (status.target_session || '—');
    $('last-success').textContent = 'Last successful refresh ' + (status.last_successful_refresh || '—');
    const coverage = status.completeness;
    $('completeness').textContent = coverage?.complete ? coverage.terminal_target > 0 ? `Data complete · ${coverage.valid_target}/${coverage.required} inputs · ${coverage.trading_target} trading · ${coverage.terminal_target} terminal` : `Data complete · ${coverage.valid_target}/${coverage.required} symbols` : 'Completeness —';
    $('provider').textContent = 'Provider · ' + (typeof status.provider_health === 'string' ? status.provider_health : status.provider_health?.status || 'Not checked');
    $('read-status').textContent = status.snapshot_read?.startsWith('busy') ? 'Storage is busy. Showing the last committed snapshot.' : '';
    $('refresh').disabled = status.state === 'running';
    $('refresh-label').textContent = publicSnapshot ? 'Read-only snapshot' : preview ? 'Replay fixture' : status.state === 'running' ? 'Refreshing…' : 'Refresh Data';
    const failed = ['failed','interrupted'].includes(status.state);
    if (inspector) $('inspector-status').textContent = failed ? 'Refresh failed · previous successful snapshot retained' : status.state === 'running' ? progress : 'Completed session ' + (snapshot?.session || '—');
    $('error').hidden = !failed && !requestError;
    $('error').textContent = failed ? `${status.state === 'interrupted' ? 'Refresh interrupted' : 'Refresh failed'}${status.error ? ' (' + status.error + ')' : ''}. Previous successful results and exports remain available. Refresh Data to retry.` : requestError;
    if (previous.state === 'running' && status.state === 'success') {
      announce('Refresh complete.');
      $('refresh').classList.remove('refresh-complete');
      void $('refresh').offsetWidth;
      $('refresh').classList.add('refresh-complete');
    }
  }
  let polling = false;
  async function poll() {
    if (preview || polling) return;
    polling = true;
    try {
      const response = await fetch('/api/status'); if (!response.ok) throw Error('status');
      showStatus(await response.json());
      const data = await fetch('/api/dashboard-data'); if (!data.ok) throw Error('snapshot');
      render(await data.json());
    } catch {
      const message = 'Local server unavailable. Start ThemeScope to reconnect.';
      if ($('progress').textContent !== message) $('progress').textContent = message;
    } finally { polling = false; }
  }
  document.addEventListener('submit',event => { if (event.target.matches('form')) event.preventDefault(); });
  document.addEventListener('click',event => {
    const button = event.target.closest('button'), link = event.target.closest('a');
    if ((link?.dataset.inspectTheme || link?.dataset.inspectTicker) && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) {
      event.preventDefault(); openInspector(link.dataset.inspectTheme ? 'theme' : 'ticker',link.dataset.inspectTheme || link.dataset.inspectTicker,link.dataset.focusKey); return;
    }
    if (link?.getAttribute('href') === '#workspace') { event.preventDefault(); $('workspace').focus(); $('workspace').scrollIntoView(); return; }
    if (link?.getAttribute('aria-disabled') === 'true') { event.preventDefault(); return; }
    if (link?.getAttribute('href')?.startsWith('#themes/')) {
      if (!route.startsWith('#themes/')) origin = route || '#themes';
      try { ui.selectedTheme = decodeURIComponent(link.getAttribute('href').split('/')[1]); } catch { ui.selectedTheme = ''; }
    }
    if (link?.getAttribute('href')?.startsWith('#') && link.getAttribute('href') !== '#workspace' && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) {
      event.preventDefault();
      if (location.hash !== link.getAttribute('href')) { history.pushState(null,'',link.getAttribute('href')); showRoute(); }
      return;
    }
    if (!button) return;
    if (button.id === 'inspector-close') { closeInspector(); return; }
    if (button.dataset.inspectorFilter) { inspectorView().filter = button.dataset.inspectorFilter; renderInspector(true); restoreFocus('inspect-filter:' + button.dataset.inspectorFilter); return; }
    if (button.id === 'display-toggle') { const open = $('display-panel').hidden; $('display-panel').hidden = !open; button.setAttribute('aria-expanded',String(open)); if (open) $('display-close').focus(); return; }
    if (button.id === 'display-close') { closeDisplay(); $('display-toggle').focus(); return; }
    if (button.dataset.density) { display.density = button.dataset.density; applyDisplay(true); return; }
    if (button.dataset.textStep) { display.text = Math.max(100,Math.min(200,display.text + Number(button.dataset.textStep))); applyDisplay(true); return; }
    if (button.dataset.save) { changeSaved(button.dataset.save); return; }
    if (button.dataset.remove) { changeSaved(button.dataset.remove,true); return; }
    if (button.dataset.universe) { ui.universe = button.dataset.universe; renderThemes(); return; }
    if (button.dataset.themeSort) {
      const key = button.dataset.themeSort, focused = focusKey();
      ui.themeDescending = ui.themeSort === key ? !ui.themeDescending : ['score','return1','return3','breadth'].includes(key); ui.themeSort = key; renderThemes(); restoreFocus(focused); return;
    }
    if (button.dataset.candidateMode) { ui.candidateMode = button.dataset.candidateMode; renderCandidates(); return; }
    if (button.dataset.reset === 'themes') { $('theme-filters').reset(); renderThemes(); }
    if (button.dataset.reset === 'candidates') { $('candidate-filters').reset(); renderCandidates(); }
  });
  function filterChange(event) {
    const id = event.target.id;
    if (id === 'map-selection') { showMapReadout(event.target.value); return; }
    if (id === 'inspector-search') { inspectorView().search = event.target.value; renderInspectorMembers(); return; }
    if (id === 'inspector-sort') { inspectorView().sort = event.target.value; renderInspectorMembers(); return; }
    if (['theme-search','theme-family','theme-priority','theme-trend'].includes(id)) renderThemes();
    if (id === 'theme-mobile-sort') { const [key,direction] = event.target.value.split(':'); ui.themeSort = key; ui.themeDescending = direction === 'desc'; renderThemes(); $('theme-mobile-sort')?.focus(); }
    if (id.startsWith('candidate-') && id !== 'candidate-filters') renderCandidates();
    if (id.startsWith('member-') && ['member-search','member-role','member-eligibility','member-sort'].includes(id)) {
      ui.memberSearch = $('member-search').value; ui.memberRole = $('member-role').value; ui.memberEligibility = $('member-eligibility').value; ui.memberSort = $('member-sort').value; renderMembers(detailId());
    }
  }
  document.addEventListener('pointerover',event=>{ const point=event.target.closest('[data-map-theme]'); if (point) showMapReadout(point.dataset.mapTheme); });
  document.addEventListener('focusin',event=>{ const point=event.target.closest('[data-map-theme]'); if (point) { showMapReadout(point.dataset.mapTheme); } });
  document.addEventListener('keydown',event=>{
    const point=event.target.closest('[data-map-theme]');
    if (!point || !['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(event.key)) return;
    const points=[...document.querySelectorAll('[data-map-theme]')], index=points.indexOf(point);
    const next=event.key === 'Home' ? 0 : event.key === 'End' ? points.length-1 : (index+(['ArrowRight','ArrowDown'].includes(event.key) ? 1 : -1)+points.length)%points.length;
    event.preventDefault();points[next]?.focus({preventScroll:true});
  });
  document.addEventListener('keydown',event => { if (event.key === 'Escape' && !$('display-panel').hidden) { closeDisplay(); $('display-toggle').focus(); } });
  document.addEventListener('click',event => { if (!$('display-panel').hidden && !event.target.closest('#display-panel, #display-toggle')) closeDisplay(); });
  document.addEventListener('change',event => { if (event.target.id === 'display-motion' || event.target.id === 'display-contrast') { display.motion = $('display-motion').checked; display.contrast = $('display-contrast').checked; applyDisplay(true); } });
  document.addEventListener('input',event => { if (event.target.matches('input')) filterChange(event); });
  document.addEventListener('change',event => { if (event.target.matches('select')) filterChange(event); });
  window.addEventListener('hashchange',() => showRoute());
  $('refresh').addEventListener('click',async () => {
    if (publicSnapshot) return;
    if (preview) { render(window.FIXTURE_SNAPSHOT); showStatus({state:'success',progress:'Synthetic fixture replayed',target_session:snapshot.session,last_successful_refresh:'Inspection fixture',completeness:snapshot.completeness,provider_health:'Fixture'}); return; }
    requestError = '';
    $('refresh').disabled = true;
    try {
      const response = await fetch('/api/refresh',{method:'POST'});
      if (!response.ok && response.status !== 409) requestError = 'Unable to start refresh. Previous results remain available. Refresh Data to retry.';
    } catch { requestError = 'Unable to reach the local server. Previous results remain available. Refresh Data to retry.'; }
    await poll();
  });
  $('theme-map-panel').addEventListener('toggle',()=>{ if ($('theme-map-panel').open) renderThemeMap(); });
  window.addEventListener('resize',()=>{ clearTimeout(mapResizeTimer); mapResizeTimer=setTimeout(()=>{ if ($('theme-map-panel').open) { const key=focusKey(); renderThemeMap(); restoreFocus(key); } },100); });
  $('research-inspector').addEventListener('cancel',event=>{ event.preventDefault(); closeInspector(); });
  applyDisplay();
  history.scrollRestoration = 'manual';
  document.querySelectorAll('[data-nav]').forEach(link => { link.querySelector('.nav-icon').innerHTML = icon(link.dataset.nav); });
  document.querySelector('.brand-mark').innerHTML = icon('orbit');
  document.querySelectorAll('a span[aria-hidden="true"]').forEach(span => { if (span.textContent === '↗') span.innerHTML = icon('up'); });
  renderSaved(); renderOverview(); renderThemes(); renderCandidates(); showRoute(true);
  if (publicSnapshot) { render(window.THEMESCOPE_STATIC_SOURCE.snapshot); showStatus({state:'success',progress:'Read-only snapshot',target_session:snapshot.session,last_successful_refresh:snapshot.refreshed_at,completeness:snapshot.completeness,provider_health:snapshot.provider_health}); }
  else if (preview) { render(window.FIXTURE_SNAPSHOT); showStatus({state:'success',progress:'Synthetic inspection fixture',target_session:snapshot.session,last_successful_refresh:'Inspection fixture',completeness:snapshot.completeness,provider_health:'Fixture'}); }
  else { poll(); setInterval(poll,1500); }
})();
