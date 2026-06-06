(function(){
  var LS='cpds:highlights';
  function lsGet(){ try{ return JSON.parse(localStorage.getItem(LS)||'[]'); }catch(e){ return []; } }
  function lsSet(a){ try{ localStorage.setItem(LS, JSON.stringify(a)); }catch(e){} }
  function uid(){ return 'h'+Date.now().toString(36)+Math.random().toString(36).slice(2,6); }
  var isFlip = document.body && document.body.classList.contains('flip-body');

  // ---- prose / paragraph helpers ----
  function proseEls(){ return [].slice.call(document.querySelectorAll('.prose[data-chap]')); }
  function textNodes(root){
    var w=document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null), n, out=[];
    while(n=w.nextNode()){ out.push(n); }
    return out;
  }
  function fullText(p){ var t=textNodes(p), s=''; for(var i=0;i<t.length;i++) s+=t[i].nodeValue; return s; }
  function paraLen(p){ var t=textNodes(p), s=0; for(var i=0;i<t.length;i++) s+=t[i].nodeValue.length; return s; }
  // char offset of (container,off) within paragraph p, using a range (matches text concatenation)
  function offsetIn(p, container, off){
    if(!(p===container || p.contains(container))) return null;
    try{
      var r=document.createRange();
      r.selectNodeContents(p);
      r.setEnd(container, off);
      return r.toString().length;
    }catch(e){ return null; }
  }

  // ---- applying highlights to the DOM ----
  function applyOne(p, start, end, id){
    var nodes=textNodes(p), pos=0, segs=[];
    for(var i=0;i<nodes.length;i++){
      var node=nodes[i], len=node.nodeValue.length, nStart=pos, nEnd=pos+len; pos=nEnd;
      if(len===0 || nEnd<=start || nStart>=end) continue;
      segs.push({node:node, a:Math.max(start,nStart)-nStart, b:Math.min(end,nEnd)-nStart});
    }
    for(var j=0;j<segs.length;j++){
      var s=segs[j];
      try{
        var rg=document.createRange();
        rg.setStart(s.node, s.a); rg.setEnd(s.node, s.b);
        var mk=document.createElement('mark');
        mk.className='hl'; mk.setAttribute('data-hid', id);
        rg.surroundContents(mk);
      }catch(e){}
    }
  }
  function unwrapAll(root){
    var marks=[].slice.call(root.querySelectorAll('mark.hl'));
    marks.forEach(function(m){
      var parent=m.parentNode; if(!parent) return;
      while(m.firstChild) parent.insertBefore(m.firstChild, m);
      parent.removeChild(m);
      parent.normalize();
    });
  }
  function renderPage(){
    if(isFlip) return;
    var all=lsGet();
    proseEls().forEach(function(prose){
      unwrapAll(prose);
      var chap=+prose.getAttribute('data-chap');
      var byCidx={};
      all.forEach(function(h){ if(h.chap===chap){ (byCidx[h.cidx]=byCidx[h.cidx]||[]).push(h); } });
      Object.keys(byCidx).forEach(function(ci){
        var p=prose.querySelector('p[data-cidx="'+ci+'"]'); if(!p) return;
        byCidx[ci].sort(function(a,b){ return a.start-b.start; }).forEach(function(h){
          applyOne(p, h.start, h.end, h.id);
          var segs=p.querySelectorAll('mark.hl[data-hid="'+h.id+'"]');
          if(segs.length){
            if(!segs[0].id) segs[0].id='hl-'+h.id;
            var noted=!!(h.note && h.note.trim());
            for(var k=0;k<segs.length;k++){
              if(noted){ segs[k].classList.add('hl-noted'); segs[k].title=h.note; }
              else { segs[k].title='Highlighted — click to add a note or remove'; }
            }
            if(noted) segs[0].classList.add('hl-noted-first');
          }
        });
      });
    });
  }

  // ---- floating "Highlight" button on selection ----
  var fab=null;
  function makeFab(){
    if(fab) return fab;
    fab=document.createElement('button');
    fab.className='hl-fab'; fab.type='button'; fab.textContent='Highlight';
    fab.addEventListener('mousedown', function(e){ e.preventDefault(); });
    fab.addEventListener('click', function(e){ e.preventDefault(); e.stopPropagation(); commitSelection(); });
    document.body.appendChild(fab);
    return fab;
  }
  function hideFab(){ if(fab) fab.classList.remove('show'); }
  function validSelection(){
    var s=window.getSelection();
    if(!s || s.isCollapsed || s.rangeCount===0) return null;
    var r=s.getRangeAt(0);
    if(!r.toString().trim()) return null;
    var sn=r.startContainer, en=r.endContainer;
    var se=(sn.nodeType===1?sn:sn.parentNode), ee=(en.nodeType===1?en:en.parentNode);
    var prose=se.closest && se.closest('.prose[data-chap]');
    if(!prose || !prose.contains(ee)) return null;
    return {r:r, prose:prose};
  }
  function maybeShowFab(){
    if(isFlip) return;
    var v=validSelection();
    if(!v){ hideFab(); return; }
    var rect=v.r.getBoundingClientRect();
    if(!rect || (!rect.width && !rect.height)){ hideFab(); return; }
    makeFab();
    fab.classList.add('show');
    var top=window.scrollY + rect.top - fab.offsetHeight - 8;
    if(top < window.scrollY + 4) top=window.scrollY + rect.bottom + 8;
    var left=window.scrollX + rect.left + rect.width/2 - fab.offsetWidth/2;
    left=Math.max(8, Math.min(left, window.scrollX + document.documentElement.clientWidth - fab.offsetWidth - 8));
    fab.style.top=top+'px'; fab.style.left=left+'px';
  }
  function commitSelection(){
    var v=validSelection(); if(!v) return;
    var r=v.r, prose=v.prose, chap=+prose.getAttribute('data-chap');
    var title=prose.getAttribute('data-chap-title') || ('Chapter '+chap);
    var paras=[].slice.call(prose.querySelectorAll('p[data-cidx]'));
    var arr=lsGet(), added=0;
    paras.forEach(function(p){
      if(r.intersectsNode && !r.intersectsNode(p)) return;
      var len=paraLen(p), start, end;
      start=(p===r.startContainer||p.contains(r.startContainer)) ? offsetIn(p, r.startContainer, r.startOffset) : 0;
      end=(p===r.endContainer||p.contains(r.endContainer)) ? offsetIn(p, r.endContainer, r.endOffset) : len;
      if(start==null) start=0; if(end==null) end=len;
      if(start<0) start=0; if(end>len) end=len;
      if(end-start < 1) return;
      var text=fullText(p).slice(start, end);
      if(!text.trim()) return;
      arr.push({ id:uid(), chap:chap, title:title, cidx:+p.getAttribute('data-cidx'),
                 start:start, end:end, text:text, ts:Date.now() });
      added++;
    });
    if(added){ lsSet(arr); renderPage(); updateCount(); renderList(); }
    var sel=window.getSelection(); if(sel) sel.removeAllRanges();
    hideFab();
  }
  function removeHl(id){
    lsSet(lsGet().filter(function(h){ return h.id!==id; }));
    renderPage(); updateCount(); renderList();
  }
  function setNote(id, text){
    var arr=lsGet(), changed=false;
    arr.forEach(function(h){ if(h.id===id){ h.note=(text||'').trim(); changed=true; } });
    if(changed){ lsSet(arr); renderPage(); renderList(); }
  }

  // ---- click a highlight -> small remove popup ----
  var pop=null;
  function hidePop(){ if(pop){ pop.remove(); pop=null; } }
  function showPop(mark){
    hidePop();
    var id=mark.getAttribute('data-hid');
    var rec=null, arr=lsGet();
    for(var i=0;i<arr.length;i++){ if(arr[i].id===id){ rec=arr[i]; break; } }
    pop=document.createElement('div'); pop.className='hl-pop';
    pop.innerHTML=
      '<textarea class="hl-note-input" rows="3" placeholder="Add a note to this highlight…"></textarea>'+
      '<div class="hl-pop-actions">'+
        '<button type="button" class="hl-note-save">Save note</button>'+
        '<button type="button" class="hl-pop-remove">Remove</button>'+
      '</div>';
    document.body.appendChild(pop);
    var ta=pop.querySelector('.hl-note-input');
    if(rec && rec.note) ta.value=rec.note;
    pop.querySelector('.hl-note-save').addEventListener('click', function(e){ e.stopPropagation(); setNote(id, ta.value); hidePop(); });
    pop.querySelector('.hl-pop-remove').addEventListener('click', function(e){ e.stopPropagation(); removeHl(id); hidePop(); });
    pop.addEventListener('mousedown', function(e){ e.stopPropagation(); });
    var rect=mark.getBoundingClientRect();
    var top=window.scrollY + rect.bottom + 6;
    var left=window.scrollX + rect.left;
    left=Math.max(8, Math.min(left, window.scrollX + document.documentElement.clientWidth - pop.offsetWidth - 8));
    pop.style.top=top+'px'; pop.style.left=left+'px';
    ta.focus();
  }

  // ---- slide-out panel ----
  var panel=null, listEl=null;
  function buildPanel(){
    if(panel) return;
    panel=document.createElement('div'); panel.className='hl-panel'; panel.hidden=true;
    panel.innerHTML=
      '<div class="hl-backdrop"></div>'+
      '<aside class="hl-aside" role="dialog" aria-modal="true" aria-label="Your highlights">'+
        '<div class="hl-head"><span class="hl-head-t">Your highlights</span>'+
        '<button class="hl-x" type="button" aria-label="Close">×</button></div>'+
        '<div class="hl-list"></div>'+
        '<div class="hl-foot"><button class="hl-clear" type="button">Clear all highlights</button></div>'+
      '</aside>';
    document.body.appendChild(panel);
    listEl=panel.querySelector('.hl-list');
    panel.querySelector('.hl-backdrop').addEventListener('click', closePanel);
    panel.querySelector('.hl-x').addEventListener('click', closePanel);
    panel.querySelector('.hl-clear').addEventListener('click', function(){
      if(!lsGet().length) return;
      if(window.confirm('Remove all of your saved highlights? This cannot be undone.')){
        lsSet([]); renderPage(); updateCount(); renderList();
      }
    });
  }
  function openPanel(){ buildPanel(); renderList(); panel.hidden=false; document.body.classList.add('hl-panel-open'); }
  function closePanel(){ if(panel){ panel.hidden=true; document.body.classList.remove('hl-panel-open'); } }
  function chapHref(chap){ return chap===0 ? 'contents.html' : 'chapter-'+chap+'.html'; }
  function onThisPage(chap){
    return proseEls().some(function(pr){ return +pr.getAttribute('data-chap')===chap; });
  }
  function jumpTo(h){
    if(onThisPage(h.chap)){
      closePanel();
      var el=document.getElementById('hl-'+h.id);
      if(el){ el.scrollIntoView({behavior:'smooth', block:'center'}); flash(el); }
    } else {
      location.href=chapHref(h.chap)+'#hl-'+h.id;
    }
  }
  function flash(el){ el.classList.add('hl-flash'); setTimeout(function(){ el.classList.remove('hl-flash'); }, 1600); }
  function renderList(){
    if(!listEl) return;
    var all=lsGet().slice().sort(function(a,b){
      return (a.chap-b.chap) || (a.cidx-b.cidx) || (a.start-b.start);
    });
    if(!all.length){
      listEl.innerHTML='<p class="hl-empty">No highlights yet. Select any text while reading, then click <strong>Highlight</strong>.</p>';
      return;
    }
    var groups={}, order=[];
    all.forEach(function(h){ if(!groups[h.chap]){ groups[h.chap]=[]; order.push(h.chap); } groups[h.chap].push(h); });
    var html='';
    order.forEach(function(chap){
      var label=groups[chap][0].title || (chap===0?'Dedication':'Chapter '+chap);
      var pre=(chap===0)?'':'Chapter '+chap+' · ';
      html+='<div class="hl-group"><h3 class="hl-group-h">'+pre+escAttr(label)+'</h3>';
      groups[chap].forEach(function(h){
        var snip=h.text.length>180 ? h.text.slice(0,180).replace(/\s+\S*$/,'')+'…' : h.text;
        var hasNote=!!(h.note && h.note.trim());
        html+='<div class="hl-item" data-id="'+h.id+'">'+
              '<div class="hl-item-row">'+
                '<button class="hl-go" type="button" data-id="'+h.id+'">“'+escAttr(snip)+'”</button>'+
                '<button class="hl-del" type="button" data-id="'+h.id+'" aria-label="Remove highlight">×</button>'+
              '</div>'+
              (hasNote ? '<div class="hl-note-disp" data-id="'+h.id+'">'+escAttr(h.note)+'</div>' : '')+
              '<div class="hl-note-edit-wrap" data-id="'+h.id+'" hidden>'+
                '<textarea class="hl-note-ta" rows="2" placeholder="Add a note…">'+escAttr(h.note||'')+'</textarea>'+
                '<div class="hl-note-edit-actions">'+
                  '<button class="hl-note-savep" type="button" data-id="'+h.id+'">Save</button>'+
                  '<button class="hl-note-cancel" type="button">Cancel</button>'+
                '</div>'+
              '</div>'+
              '<button class="hl-note-toggle" type="button" data-id="'+h.id+'">'+(hasNote?'Edit note':'+ Add note')+'</button>'+
              '</div>';
      });
      html+='</div>';
    });
    listEl.innerHTML=html;
    var map={}; all.forEach(function(h){ map[h.id]=h; });
    function openEditor(id){
      var wrap=listEl.querySelector('.hl-note-edit-wrap[data-id="'+id+'"]'); if(!wrap) return;
      wrap.hidden=false;
      var tog=listEl.querySelector('.hl-note-toggle[data-id="'+id+'"]'); if(tog) tog.hidden=true;
      var disp=listEl.querySelector('.hl-note-disp[data-id="'+id+'"]'); if(disp) disp.hidden=true;
      var ta=wrap.querySelector('.hl-note-ta'); if(ta){ ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length); }
    }
    [].slice.call(listEl.querySelectorAll('.hl-go')).forEach(function(btn){
      btn.addEventListener('click', function(){ jumpTo(map[btn.getAttribute('data-id')]); });
    });
    [].slice.call(listEl.querySelectorAll('.hl-del')).forEach(function(btn){
      btn.addEventListener('click', function(){ removeHl(btn.getAttribute('data-id')); });
    });
    [].slice.call(listEl.querySelectorAll('.hl-note-toggle')).forEach(function(btn){
      btn.addEventListener('click', function(){ openEditor(btn.getAttribute('data-id')); });
    });
    [].slice.call(listEl.querySelectorAll('.hl-note-disp')).forEach(function(d){
      d.addEventListener('click', function(){ openEditor(d.getAttribute('data-id')); });
    });
    [].slice.call(listEl.querySelectorAll('.hl-note-savep')).forEach(function(btn){
      btn.addEventListener('click', function(){
        var wrap=btn.closest('.hl-note-edit-wrap');
        var ta=wrap.querySelector('.hl-note-ta');
        setNote(btn.getAttribute('data-id'), ta.value);
      });
    });
    [].slice.call(listEl.querySelectorAll('.hl-note-cancel')).forEach(function(btn){
      btn.addEventListener('click', function(){ renderList(); });
    });
  }
  function escAttr(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

  // ---- count badge ----
  function updateCount(){
    var c=document.getElementById('hl-count'); if(!c) return;
    var n=lsGet().length;
    c.textContent=n;
    if(n>0){ c.hidden=false; } else { c.hidden=true; }
  }

  // ---- jump from hash on load (cross-page navigation) ----
  function handleHash(){
    if(!location.hash || location.hash.indexOf('#hl-')!==0) return;
    var el=document.getElementById(location.hash.slice(1));
    if(el){ el.scrollIntoView({behavior:'smooth', block:'center'}); flash(el); }
  }

  // ---- global events ----
  document.addEventListener('mouseup', function(){ setTimeout(maybeShowFab, 0); });
  var scTimer=null;
  document.addEventListener('selectionchange', function(){
    clearTimeout(scTimer);
    scTimer=setTimeout(function(){
      var v=validSelection();
      if(!v){ hideFab(); } else { maybeShowFab(); }
    }, 200);
  });
  window.addEventListener('scroll', function(){ hideFab(); hidePop(); }, true);
  document.addEventListener('click', function(e){
    if(e.target.closest && e.target.closest('.scripture')) return;   // scripture link wins
    if(e.target.closest && e.target.closest('.hl-fab')) return;
    if(e.target.closest && e.target.closest('.hl-pop')) return;
    var m=e.target.closest && e.target.closest('mark.hl');
    if(m){ e.preventDefault(); e.stopPropagation(); showPop(m); return; }
    hidePop();
  });
  document.addEventListener('keydown', function(e){ if(e.key==='Escape'){ hidePop(); hideFab(); closePanel(); } });

  function autorun(){
    buildPanel(); updateCount();
    var ob=document.getElementById('hl-open');
    if(ob) ob.addEventListener('click', openPanel);
    if(!isFlip){ renderPage(); handleHash(); }
  }
  window.cpdsHighlights={ render:renderPage, open:openPanel };
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', autorun);
  else autorun();
})();
