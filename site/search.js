(function(){
  var input=document.querySelector('.book-search-input');
  var box=document.querySelector('.book-search-results');
  var INDEX=null, LOADING=false, cur=[], sel=-1, lastTerms=[];
  function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function chapHref(c){ return c===0 ? 'contents.html' : 'chapter-'+c+'.html'; }
  var pending=[];
  function load(cb){
    if(INDEX){ cb(); return; }
    if(window.__CPDS_INDEX__){ INDEX=window.__CPDS_INDEX__; cb(); return; }
    pending.push(cb);
    if(LOADING) return;
    LOADING=true;
    // Load via a <script> tag (not fetch) so it works both deployed and from local
    // files (file://), where fetch() of a local file is blocked by the browser.
    var s=document.createElement('script');
    s.src='search-index.js'; s.async=true;
    s.onload=function(){
      INDEX=window.__CPDS_INDEX__||null; LOADING=false;
      var cbs=pending; pending=[]; cbs.forEach(function(fn){ fn(); });
    };
    s.onerror=function(){
      LOADING=false; pending=[];
      if(box){ box.innerHTML='<div class="bs-empty">Search is unavailable.</div>'; box.hidden=false; }
    };
    document.head.appendChild(s);
  }
  function chapterLabel(c){
    var name=(INDEX && INDEX.chapters && INDEX.chapters[String(c)]) || '';
    return c===0 ? 'Dedication' : ('Chapter '+c+(name?' · '+name:''));
  }
  function snippet(text, terms){
    var lc=text.toLowerCase(), at=-1, i, p;
    for(i=0;i<terms.length;i++){ p=lc.indexOf(terms[i]); if(p>=0 && (at<0||p<at)) at=p; }
    if(at<0) at=0;
    var start=Math.max(0, at-50), end=Math.min(text.length, at+100);
    var s=(start>0?'…':'')+text.slice(start,end)+(end<text.length?'…':'');
    s=esc(s);
    terms.forEach(function(t){
      if(!t) return;
      var re=new RegExp('('+t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+')','ig');
      s=s.replace(re,'<mark>$1</mark>');
    });
    return s;
  }
  function run(q){
    q=q.replace(/\s+/g,' ').trim();
    if(q.length<2){ cur=[]; sel=-1; if(box){ box.hidden=true; box.innerHTML=''; } return; }
    load(function(){
      if(!INDEX) return;
      var terms=q.toLowerCase().split(' ').filter(Boolean); lastTerms=terms;
      var res=[], k, j, it, lc, good;
      for(k=0;k<INDEX.paras.length;k++){
        it=INDEX.paras[k]; lc=it.x.toLowerCase(); good=true;
        for(j=0;j<terms.length;j++){ if(lc.indexOf(terms[j])<0){ good=false; break; } }
        if(good){ res.push(it); if(res.length>=30) break; }
      }
      cur=res; sel=res.length?0:-1; render();
    });
  }
  function render(){
    if(!box) return;
    if(!cur.length){ box.innerHTML='<div class="bs-empty">No matches.</div>'; box.hidden=false; return; }
    var html='', k, it;
    for(k=0;k<cur.length;k++){
      it=cur[k];
      html+='<a class="bs-item'+(k===sel?' sel':'')+'" role="option" href="'+chapHref(it.c)+'#p'+it.i+'" '
        +'data-c="'+it.c+'" data-i="'+it.i+'">'
        +'<span class="bs-where">'+esc(chapterLabel(it.c))+'</span>'
        +'<span class="bs-snip">'+snippet(it.x,lastTerms)+'</span></a>';
    }
    box.innerHTML=html; box.hidden=false;
    [].slice.call(box.querySelectorAll('.bs-item')).forEach(function(a){
      a.addEventListener('click', function(e){ e.preventDefault(); go(+a.getAttribute('data-c'), +a.getAttribute('data-i')); });
    });
  }
  function updateSel(){
    if(!box) return;
    var items=box.querySelectorAll('.bs-item'), k;
    for(k=0;k<items.length;k++){ items[k].classList.toggle('sel', k===sel); if(k===sel) items[k].scrollIntoView({block:'nearest'}); }
  }
  function proseFor(c){
    var all=document.querySelectorAll('.prose[data-chap]'), k;
    for(k=0;k<all.length;k++){ if(+all[k].getAttribute('data-chap')===c) return all[k]; }
    return null;
  }
  function scrollToPara(c,i){
    var pr=proseFor(c); if(!pr) return false;
    var p=pr.querySelector('p[data-cidx="'+i+'"]'); if(!p) return false;
    p.scrollIntoView({behavior:'smooth', block:'center'});
    p.classList.add('para-flash'); setTimeout(function(){ p.classList.remove('para-flash'); }, 1800);
    return true;
  }
  function go(c,i){
    if(box) box.hidden=true;
    if(!scrollToPara(c,i)) location.href=chapHref(c)+'#p'+i;
  }
  if(input && box){
    var t=null;
    input.addEventListener('input', function(){ clearTimeout(t); t=setTimeout(function(){ run(input.value); }, 140); });
    input.addEventListener('focus', function(){ if(input.value.trim().length>=2 && cur.length) box.hidden=false; });
    input.addEventListener('keydown', function(e){
      if(e.key==='ArrowDown'){ e.preventDefault(); if(cur.length){ sel=(sel+1)%cur.length; updateSel(); } }
      else if(e.key==='ArrowUp'){ e.preventDefault(); if(cur.length){ sel=(sel-1+cur.length)%cur.length; updateSel(); } }
      else if(e.key==='Enter'){ if(sel>=0 && cur[sel]){ e.preventDefault(); go(cur[sel].c, cur[sel].i); } }
      else if(e.key==='Escape'){ box.hidden=true; input.blur(); }
    });
    document.addEventListener('click', function(e){
      if(!(e.target.closest && e.target.closest('.bar-center'))) box.hidden=true;
    });
  }
  // on load: jump to #p<cidx> when arriving from a search result
  function hashJump(){
    var m=(location.hash||'').match(/^#p(\d+)$/);
    if(!m) return;
    var pr=document.querySelector('.prose[data-chap]'); if(!pr) return;
    scrollToPara(+pr.getAttribute('data-chap'), +m[1]);
  }
  window.cpdsSearch={ run:run, _setIndex:function(d){ INDEX=d; } };
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', hashJump);
  else hashJump();
})();
