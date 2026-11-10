'use strict';
/* Research presentation and interaction primitives. No financial qualification. */
window.ThemeScopeUI = (() => {
  const help = {
    strength:['Strength','Relative strength across Active themes on a 0–100 scale. Higher is stronger; this is not expected return or Research Priority.','strength'],
    rank:['Strength Rank','Rank across all scored Active themes, independent of this table’s filters. Equal scores share ranks.','rank'],
    w:['Peer-relative strength','Weighted 1M/3M excess return versus other Core + Enabler members of the same theme. Positive is stronger, negative weaker. Unit: percentage points.','w'],
    extension:['Market Extension','SPY and QQQ distance from EMA21, scaled by Wilder ATR20. Changes research attention, never Market Bias or qualification.','extension'],
    breadth:['Members above EMA','The share of valid members above EMA21 and EMA50. Theme breadth requires at least five valid members and 80% coverage.','breadth'],
    'market-breadth':['Benchmark breadth','SPY and QQQ constituent breadth supplies Market Matrix context. IWM has no breadth roster.','market'],
    iwm:['Small-cap context','IWM supplies small-cap price and EMA context. It does not affect Market Bias or Extension.','market'],
    countertrend:['Countertrend research','Observations of relative strength or weakness within directional themes. W predicts neither reversal, rebound, pullback nor trade success. Chart evaluation is separate.','countertrend'],
    priority:['Research Priority','Current Directional theme relevance under Market Bias. Strength Rank is separate: a strong theme may be Watch during Short Bias.','priority'],
  };
  const bucketLabel = (side,key) => side==='short' ? key==='resilient'?'Peer outperformers':'Weak-theme laggards' : key==='resilient'?'Strong leaders':'Underperforming theme peers';
  const bucketHelp = (side,key) => side==='short' ? key==='resilient'?'Relative strength within structurally weak themes.':'Relative weakness within structurally weak themes. Review separately for mean reversion.' : key==='resilient'?'Relative strength within strong themes. Market extension may make chasing less attractive.':'Relative weakness within otherwise strong themes.';
  const focusLabel = value => ({'Countertrend Highlighted':'Countertrend review','Directional + Countertrend Watch':'Countertrend watch','Pullback-Risk Highlighted':'Pullback-risk review','Directional + Pullback-Risk Watch':'Pullback-risk watch',Directional:'Directional research',Observe:'Observe'})[value] || 'Market context unavailable';
  const displayRows = (all,representatives,theme) => theme ? [...new Map(all.filter(r=>r.theme_id===theme).map(r=>[r.ticker,r])).values()] : representatives;
  function axis(low,high,count=5) {
    if(!Number.isFinite(low)||!Number.isFinite(high)||high<=low)return {low:-.01,high:.01,ticks:[-.01,0,.01]};
    const raw=(high-low)*100/Math.max(1,count-1), power=10**Math.floor(Math.log10(raw));
    const step=([1,2,2.5,5,10].find(v=>v*power>=raw)||10)*power;
    const start=Math.floor(low*100/step),end=Math.ceil(high*100/step);
    return {low:start*step/100,high:end*step/100,ticks:Array.from({length:end-start+1},(_,i)=>Number(((start+i)*step/100).toPrecision(12)))};
  }
  const reduced = () => document.documentElement.dataset.motion==='reduce'||matchMedia('(prefers-reduced-motion: reduce)').matches;
  function fade(element) { if(element&&!reduced())element.animate([{opacity:.65},{opacity:1}],{duration:160,easing:'ease-out'}); }
  function indicator(group,selected) {
    if(!group||!selected)return;
    let mark=group.querySelector(':scope > .selection-indicator');
    if(!mark){mark=document.createElement('span');mark.className='selection-indicator';mark.setAttribute('aria-hidden','true');group.prepend(mark);}
    const g=group.getBoundingClientRect(),r=selected.getBoundingClientRect();
    group.style.setProperty('--selected-x',(r.left-g.left)+'px');group.style.setProperty('--selected-y',(r.top-g.top)+'px');
    group.style.setProperty('--selected-width',r.width+'px');group.style.setProperty('--selected-height',r.height+'px');
    requestAnimationFrame(()=>group.classList.add('selection-ready'));
  }
  function indicators() {
    document.querySelectorAll('.segmented,.research-tabs').forEach(g=>indicator(g,g.querySelector('[aria-pressed="true"],[aria-selected="true"]')));
  }
  function install() {
    const pop=document.getElementById('metric-tooltip');let trigger=null,pinned=false,timer,suppressFocus=false;
    function close(restore=false) {
      clearTimeout(timer);if(!trigger)return;
      const old=trigger;old.setAttribute('aria-expanded','false');old.removeAttribute('aria-describedby');
      pop.hidden=true;trigger=null;pinned=false;if(restore){suppressFocus=true;old.focus({preventScroll:true});setTimeout(()=>suppressFocus=false,0);}
    }
    function show(button,pin=false) {
      const info=help[button.dataset.help];if(!info)return;
      close();trigger=button;pinned=pin;
      (button.closest('dialog')||document.body).append(pop);
      pop.querySelector('strong').textContent=info[0];pop.querySelector('p').textContent=info[1];
      const link=pop.querySelector('a');link.href='#methodology?metric='+info[2];link.hidden=!pin;
      pop.hidden=false;pop.setAttribute('role',pin?'dialog':'group');pop.setAttribute('aria-labelledby','metric-tooltip-title');pop.setAttribute('aria-describedby','metric-tooltip-copy');pop.tabIndex=-1;button.setAttribute('aria-expanded',String(pin));button.setAttribute('aria-describedby','metric-tooltip-copy');
      const r=button.getBoundingClientRect(),p=pop.getBoundingClientRect();
      pop.style.left=Math.max(12,Math.min(r.left,innerWidth-p.width-12))+'px';
      pop.style.top=(r.bottom+p.height+8<innerHeight?r.bottom+6:Math.max(12,r.top-p.height-6))+'px';
      if(pin)pop.focus({preventScroll:true});
    }
    document.addEventListener('pointerover',e=>{const b=e.target.closest('[data-help]');if(b&&!pinned){clearTimeout(timer);timer=setTimeout(()=>show(b),250);}});
    document.addEventListener('pointerout',e=>{if(e.target.closest('[data-help]')&&!pinned)close();});
    document.addEventListener('focusin',e=>{const b=e.target.closest('[data-help]');if(b&&!pinned&&!suppressFocus){clearTimeout(timer);timer=setTimeout(()=>show(b),250);}});
    document.addEventListener('focusout',e=>{if(e.target.closest('[data-help]')&&!pinned)close();});
    document.addEventListener('click',e=>{
      const b=e.target.closest('[data-help]');
      if(b){if(trigger===b&&pinned)close();else show(b,true);return;}
      if(!e.target.closest('#metric-tooltip'))close();
      document.querySelectorAll('.export-menu[open],.secondary-filters[open]').forEach(d=>{if(!d.contains(e.target))d.open=false;});
    });
    document.addEventListener('keydown',e=>{
      if(e.key==='Escape'&&trigger){e.preventDefault();e.stopImmediatePropagation();close(true);return;}
      const opened=document.querySelector('.export-menu[open],.secondary-filters[open]');
      if(e.key==='Escape'&&opened){e.preventDefault();e.stopImmediatePropagation();opened.open=false;opened.querySelector('summary').focus();return;}
      const tab=e.target.closest('[role="tab"]');
      if(tab&&['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){
        const tabs=[...tab.closest('[role="tablist"]').querySelectorAll('[role="tab"]')],i=tabs.indexOf(tab);
        const next=e.key==='Home'?0:e.key==='End'?tabs.length-1:(i+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
        e.preventDefault();tabs[next].click();tabs[next].focus();
      }
    },true);
    new ResizeObserver(()=>{indicators();document.querySelectorAll('.table-wrap').forEach(e=>{e.dataset.scroll=String(e.scrollWidth>e.clientWidth+1);});}).observe(document.querySelector('.app-shell'));
    window.addEventListener('resize',()=>close());
    matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change',e=>{if(e.matches)document.getAnimations().forEach(a=>a.cancel());});
    return {closeHelp:close};
  }
  return Object.freeze({help,bucketLabel,bucketHelp,focusLabel,displayRows,axis,reduced,fade,indicators,install});
})();
