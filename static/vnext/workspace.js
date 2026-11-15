'use strict';
/* Research presentation and interaction primitives. No financial qualification. */
window.ThemeScopeUI = (() => {
  const help = {
    strength:['Strength','Medium-term strength across reviewed themes on a 0–100 scale. Higher means stronger relative price performance.','strength'],
    rank:['Strength Rank','Rank across all scored Active themes, independent of this table’s filters. Equal scores share ranks.','rank'],
    w:['Peer-relative strength','Weighted 1M/3M excess return versus other Core + Enabler members of the same theme. Positive is stronger, negative weaker. Unit: percentage points.','w'],
    extension:['Market Extension','SPY and QQQ distance from EMA21, scaled by Wilder ATR20. Context for chart review; it does not change market direction or the research list.','extension'],
    breadth:['Members above EMA','Members above EMA21, shown with the valid sample count. Small samples remain context; participation never gates research.','breadth'],
    'market-breadth':['Benchmark breadth','SPY and QQQ constituent breadth supplies Market Matrix context. IWM has no breadth roster.','market'],
    iwm:['Small-cap context','IWM supplies small-cap price and EMA context. It does not affect Market Bias or Extension.','market'],
    priority:['Research Priority','Leading, Improving and Fading themes are researchable for the current market side. Short-side states interpret strength symmetrically.','priority'],
  };
  const displayRows = (all,representatives,theme) => theme ? [...new Map(all.filter(r=>r.theme_id===theme).map(r=>[r.ticker,r])).values()] : representatives;
  function researchRows(snapshot) {
    if(!currentContract(snapshot))return [];
    const supplied=new Map((snapshot?.relationships||[]).map(row=>[row.ticker+':'+row.theme_id,row]));
    return (snapshot?.research_v2?.list?.rows||[]).map((row,index)=>({
      ...supplied.get(row.ticker+':'+row.theme_id),...row,
      relative:supplied.get(row.ticker+':'+row.theme_id)?.relative||{w:row.w},list_order:index
    }));
  }
  function themeState(snapshot,id) {
    if(!currentContract(snapshot))return 'Unavailable';
    const row=snapshot?.research_v2?.themes?.[id];
    if(!row)return 'Unavailable';
    return currentSide(snapshot)?row.current_state||'Unavailable':'Non-directional';
  }
  function currentSide(snapshot) {
    if(!currentContract(snapshot))return null;
    const side=snapshot?.research_v2?.current_side;
    return side==='long'||side==='short'?side:null;
  }
  const currentContract = snapshot => snapshot?.research_v2?.schema==='themescope-research-v2'&&snapshot?.research_v2?.contract_revision===2;
  function comparisonMessage(reason) {
    return ({insufficient_completed_history:'Not enough completed history',current_basis_mismatch:'Current comparison basis unavailable',
      methodology_or_membership_changed:'Methodology or reviewed membership changed',
      insufficient_history:'Not enough completed history',insufficient_return_history:'Not enough completed return history',
      insufficient_comparable_history:'No comparable five-session basis',no_compatible_prior_basis:'No comparable five-session basis',
      methodology_or_universe_changed:'Methodology or theme universe changed',membership_basis_changed:'Reviewed membership changed',
      membership_comparison_unavailable:'Reviewed membership changed',ranked_universe_changed:'Scored theme universe changed',
      score_population_changed:'Scored theme universe changed',unavailable_score:'Structural strength unavailable',
      score_unavailable:'Structural strength unavailable',untracked_concept:'Theme is not tracked'})[reason]||'Five-session comparison unavailable';
  }
  function axis(low,high,count=5) {
    if(!Number.isFinite(low)||!Number.isFinite(high)||high<=low)return {low:-.01,high:.01,ticks:[-.01,0,.01]};
    const raw=(high-low)*100/Math.max(1,count-1), power=10**Math.floor(Math.log10(raw));
    const step=([1,2,2.5,5,10].find(v=>v*power>=raw)||10)*power;
    const start=Math.floor(low*100/step),end=Math.ceil(high*100/step);
    return {low:start*step/100,high:end*step/100,ticks:Array.from({length:end-start+1},(_,i)=>Number(((start+i)*step/100).toPrecision(12)))};
  }
  const reduced = () => document.documentElement.dataset.motion==='reduce'||matchMedia('(prefers-reduced-motion: reduce)').matches;
  const motion=Object.freeze({shift:180,slide:240,sweep:200,reveal:160,confirm:140,lock:180});
  const ease={enter:'cubic-bezier(.22,1,.36,1)',exit:'cubic-bezier(.4,0,1,1)',travel:'cubic-bezier(.2,.8,.2,1)'};
  const running=new WeakMap(),selections=new WeakMap();
  function move(element,kind='shift',direction=1) {
    if(!element)return;
    running.get(element)?.cancel();
    if(reduced())return;
    const distance=kind==='slide'?14:kind==='sweep'?8:kind==='reveal'?4:kind==='shift'?5:0;
    const transform=kind==='slide'||kind==='sweep'?`translateX(${distance*direction}px)`:`translateY(${distance}px)`;
    const animation=element.animate([{opacity:kind==='confirm'?.5:.65,transform},{opacity:1,transform:'translate(0,0)'}],{duration:motion[kind]||motion.shift,easing:kind==='sweep'?ease.travel:ease.enter});
    running.set(element,animation);
  }
  function pulse(ring) {
    if(!ring||reduced())return;
    ring.getAnimations().forEach(a=>a.cancel());
    ring.animate([{opacity:1,transform:'scale(.8)'},{opacity:0,transform:'scale(1.8)'}],{duration:motion.lock,easing:ease.enter});
  }
  function indicator(group,selected) {
    if(!group||!selected)return;
    let mark=group.querySelector(':scope > .selection-indicator');
    if(!mark){mark=document.createElement('span');mark.className='selection-indicator';mark.setAttribute('aria-hidden','true');group.prepend(mark);}
    const g=group.getBoundingClientRect(),r=selected.getBoundingClientRect(),old=mark.getBoundingClientRect(),previous=selections.get(group);
    const x=r.left-g.left,y=r.top-g.top;
    if(previous?.selected===selected&&Math.abs(previous.x-x)<.5&&Math.abs(previous.y-y)<.5&&Math.abs(previous.width-r.width)<.5&&Math.abs(previous.height-r.height)<.5)return;
    mark.getAnimations().forEach(a=>a.cancel());
    group.style.setProperty('--selected-x',x+'px');group.style.setProperty('--selected-y',y+'px');
    group.style.setProperty('--selected-width',r.width+'px');group.style.setProperty('--selected-height',r.height+'px');
    if(previous&&previous.selected!==selected&&!reduced()&&old.width&&r.width){
      mark.animate([{transform:`translate(${old.left-g.left}px,${old.top-g.top}px) scale(${old.width/r.width},${old.height/r.height})`},{transform:`translate(${x}px,${y}px) scale(1)`}],{duration:motion.sweep,easing:ease.travel});
    }
    selections.set(group,{selected,x,y,width:r.width,height:r.height});
  }
  function indicators() {
    document.querySelectorAll('.segmented,.research-tabs,.main-nav').forEach(g=>indicator(g,g.querySelector('[aria-pressed="true"],[aria-selected="true"],[aria-current="page"]')));
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
    document.addEventListener('toggle',e=>{if(e.target instanceof HTMLDetailsElement&&e.target.open){const panel=e.target.querySelector(':scope > div');if(panel&&!e.target.classList.contains('method-item'))move(panel,'reveal');}},true);
    window.addEventListener('resize',()=>close());
    matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change',e=>{if(e.matches)document.getAnimations().forEach(a=>a.cancel());});
    return {closeHelp:close};
  }
  return Object.freeze({help,displayRows,researchRows,themeState,currentSide,currentContract,comparisonMessage,axis,reduced,motion,move,pulse,indicators,install});
})();
