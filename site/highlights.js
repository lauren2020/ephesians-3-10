(function(){
  var LS='cpds:highlights';     // legacy flat array (pre-groups) — migrated on first load
  var LSG='cpds:hlgroups';      // groups store: {v,activeId,groups:[{id,name,highlights:[]}]}
  function uid(p){ return (p||'h')+Date.now().toString(36)+Math.random().toString(36).slice(2,6); }

  // ---- groups storage ----
  function groupsRead(){
    try{ var s=JSON.parse(localStorage.getItem(LSG)||'null');
      if(s && s.groups && s.groups.length) return s; }catch(e){}
    return null;
  }
  function groupsSave(s){ try{ localStorage.setItem(LSG, JSON.stringify(s)); }catch(e){} }
  function state(){
    var s=groupsRead();
    if(s) return s;
    var legacy=[]; try{ legacy=JSON.parse(localStorage.getItem(LS)||'[]'); }catch(e){}
    var g={ id:uid('g'), name:'My highlights', highlights:Array.isArray(legacy)?legacy:[] };
    s={ v:1, activeId:g.id, groups:[g] };
    groupsSave(s);
    return s;
  }
  function activeGroup(){
    var s=state();
    var g=null, i;
    for(i=0;i<s.groups.length;i++){ if(s.groups[i].id===s.activeId){ g=s.groups[i]; break; } }
    if(!g){ g=s.groups[0]; s.activeId=g.id; groupsSave(s); }
    return g;
  }
  // The rest of the code reads/writes the ACTIVE group through lsGet/lsSet, unchanged.
  function lsGet(){ return activeGroup().highlights || []; }
  function lsSet(a){
    var s=state(), i;
    for(i=0;i<s.groups.length;i++){ if(s.groups[i].id===s.activeId){ s.groups[i].highlights=a; break; } }
    groupsSave(s);
  }
  function setActiveGroup(id){
    var s=state(); s.activeId=id; groupsSave(s);
    renderPage(); updateCount(); renderList();
  }
  function newGroup(name, highlights){
    var s=state();
    var g={ id:uid('g'), name:(name&&name.trim())||('Group '+(s.groups.length+1)),
            highlights:highlights||[] };
    s.groups.push(g); s.activeId=g.id; groupsSave(s);
    return g;
  }
  function renameGroup(id, name){
    if(!name || !name.trim()) return;
    var s=state(), i;
    for(i=0;i<s.groups.length;i++){ if(s.groups[i].id===id) s.groups[i].name=name.trim(); }
    groupsSave(s); renderList();
  }
  function deleteGroup(id){
    var s=state();
    if(s.groups.length<=1) return false;
    s.groups=s.groups.filter(function(g){ return g.id!==id; });
    if(s.activeId===id) s.activeId=s.groups[0].id;
    groupsSave(s); renderPage(); updateCount(); renderList();
    return true;
  }
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

  // ---- export / import (persist highlights to a file the user owns) ----
  function bookTitle(){
    var a=document.querySelector('.topbar a.bar-link');
    return (a && a.textContent.trim()) || document.title || '';
  }
  function locKey(h){ return h.chap+'|'+h.cidx+'|'+h.start+'|'+h.end; }
  function num(v){ return (v!=null && v!=='' && isFinite(+v)) ? +v : null; }
  function validRec(h){
    if(!h || typeof h.text!=='string' || !h.text) return false;
    return num(h.chap)!=null && num(h.cidx)!=null && num(h.start)!=null && num(h.end)!=null && (+h.end)>(+h.start);
  }
  function slug(s){ return (String(s).replace(/[^a-z0-9]+/gi,'-').replace(/^-+|-+$/g,'').toLowerCase())||'group'; }
  function exportData(gid){
    var s=state(), g=null, i;
    for(i=0;i<s.groups.length;i++){ if(s.groups[i].id===(gid||s.activeId)) g=s.groups[i]; }
    g=g||activeGroup();
    return { app:'cpds', type:'highlights', version:1, book:bookTitle(), group:g.name,
             exportedAt:new Date().toISOString(), highlights:g.highlights||[] };
  }
  function exportHighlights(){
    var g=activeGroup(), hs=g.highlights||[];
    if(!hs.length){ ioMsg('No highlights in “'+g.name+'” to export yet.', true); return; }
    var blob=new Blob([JSON.stringify(exportData(g.id), null, 2)], {type:'application/json'});
    var url=URL.createObjectURL(blob);
    var a=document.createElement('a');
    a.href=url; a.download='highlights-'+slug(g.name)+'-'+new Date().toISOString().slice(0,10)+'.json';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function(){ try{ URL.revokeObjectURL(url); }catch(e){} }, 1000);
    ioMsg(hs.length+' highlight'+(hs.length===1?'':'s')+' from “'+g.name+'” saved to a file.');
  }
  // import into the active group, or into a brand-new group when opts.asNew is set
  function importHighlights(text, opts){
    opts=opts||{};
    var parsed;
    try{ parsed=JSON.parse(text); }catch(e){ ioMsg('Could not read file: it is not valid JSON.', true); return {added:0,updated:0,skipped:0,error:true}; }
    var incoming = Array.isArray(parsed) ? parsed
                 : (parsed && Array.isArray(parsed.highlights) ? parsed.highlights : null);
    if(!incoming){ ioMsg('No highlights found in that file.', true); return {added:0,updated:0,skipped:0,error:true}; }
    if(opts.asNew){
      var nm=(opts.name && opts.name.trim()) || (parsed && parsed.group) || 'Imported';
      newGroup(nm, []);   // becomes the active group
    }
    var existing=lsGet(), byLoc={}, byId={};
    existing.forEach(function(h){ byLoc[locKey(h)]=h; byId[h.id]=h; });
    var added=0, updated=0, skipped=0;
    incoming.forEach(function(h){
      if(!validRec(h)){ skipped++; return; }
      var rec={ chap:num(h.chap), cidx:num(h.cidx), start:num(h.start), end:num(h.end),
                text:String(h.text), note:(h.note?String(h.note).trim():''), ts:(num(h.ts)||Date.now()) };
      var loc=locKey(rec), prev=byLoc[loc];
      if(prev){
        if((prev.note||'')!==rec.note || (prev.text||'')!==rec.text){ prev.note=rec.note; prev.text=rec.text; updated++; }
        return;
      }
      rec.id=(h.id && !byId[h.id]) ? String(h.id) : uid();
      existing.push(rec); byLoc[loc]=rec; byId[rec.id]=rec; added++;
    });
    lsSet(existing); renderPage(); updateCount(); renderList();
    ioMsg('Imported '+added+' new, '+updated+' updated'+(skipped?(', '+skipped+' skipped'):'')+' into “'+activeGroup().name+'”.');
    return {added:added, updated:updated, skipped:skipped, group:activeGroup().name};
  }
  var ioMsgEl=null;
  function ioMsg(t, err){
    if(!ioMsgEl) return;
    ioMsgEl.textContent=t; ioMsgEl.hidden=false;
    ioMsgEl.classList.toggle('is-err', !!err);
    clearTimeout(ioMsg._t); ioMsg._t=setTimeout(function(){ if(ioMsgEl) ioMsgEl.hidden=true; }, 6000);
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
        '<div class="hl-groupbar">'+
          '<select class="hl-group-select" aria-label="Choose highlight group"></select>'+
          '<div class="hl-group-actions">'+
            '<button class="hl-group-new" type="button" title="Create a new group">+ New</button>'+
            '<button class="hl-group-rename" type="button" title="Rename this group">Rename</button>'+
            '<button class="hl-group-del" type="button" title="Delete this group">Delete</button>'+
          '</div>'+
        '</div>'+
        '<div class="hl-list"></div>'+
        '<div class="hl-foot">'+
          '<div class="hl-io">'+
            '<button class="hl-export" type="button">↓ Export group</button>'+
            '<button class="hl-import" type="button">↑ Import</button>'+
          '</div>'+
          '<label class="hl-asnew"><input type="checkbox" class="hl-asnew-check"> Import as a new group</label>'+
          '<p class="hl-io-msg" hidden></p>'+
          '<button class="hl-clear" type="button">Clear this group</button>'+
          '<input type="file" class="hl-file" accept="application/json,.json" hidden>'+
        '</div>'+
      '</aside>';
    document.body.appendChild(panel);
    listEl=panel.querySelector('.hl-list');
    ioMsgEl=panel.querySelector('.hl-io-msg');
    panel.querySelector('.hl-backdrop').addEventListener('click', closePanel);
    panel.querySelector('.hl-x').addEventListener('click', closePanel);
    panel.querySelector('.hl-clear').addEventListener('click', function(){
      if(!lsGet().length) return;
      if(window.confirm('Remove all highlights in “'+activeGroup().name+'”? This cannot be undone.')){
        lsSet([]); renderPage(); updateCount(); renderList();
      }
    });
    // group switching + management
    panel.querySelector('.hl-group-select').addEventListener('change', function(e){
      setActiveGroup(e.target.value);
    });
    panel.querySelector('.hl-group-new').addEventListener('click', function(){
      var nm=window.prompt('Name for the new group:', '');
      if(nm===null) return;
      newGroup(nm, []); renderPage(); updateCount(); renderList();
    });
    panel.querySelector('.hl-group-rename').addEventListener('click', function(){
      var g=activeGroup();
      var nm=window.prompt('Rename group:', g.name);
      if(nm===null) return;
      renameGroup(g.id, nm); renderList();
    });
    panel.querySelector('.hl-group-del').addEventListener('click', function(){
      var s=state();
      if(s.groups.length<=1){ ioMsg('You can’t delete your only group.', true); return; }
      var g=activeGroup();
      if(window.confirm('Delete the group “'+g.name+'” and its '+(g.highlights||[]).length+' highlight(s)? This cannot be undone.'))
        deleteGroup(g.id);
    });
    panel.querySelector('.hl-export').addEventListener('click', exportHighlights);
    var fileInput=panel.querySelector('.hl-file');
    var asNewCheck=panel.querySelector('.hl-asnew-check');
    panel.querySelector('.hl-import').addEventListener('click', function(){ fileInput.click(); });
    fileInput.addEventListener('change', function(){
      var f=fileInput.files && fileInput.files[0]; if(!f) return;
      var asNew=!!(asNewCheck && asNewCheck.checked);
      var reader=new FileReader();
      reader.onload=function(){ importHighlights(String(reader.result), {asNew:asNew}); if(asNewCheck) asNewCheck.checked=false; fileInput.value=''; };
      reader.onerror=function(){ ioMsg('Could not read the file.', true); fileInput.value=''; };
      reader.readAsText(f);
    });
  }
  function renderGroups(){
    if(!panel) return;
    var sel=panel.querySelector('.hl-group-select'); if(!sel) return;
    var s=state();
    sel.innerHTML='';
    s.groups.forEach(function(g){
      var o=document.createElement('option');
      o.value=g.id;
      o.textContent=g.name+' ('+((g.highlights&&g.highlights.length)||0)+')';
      if(g.id===s.activeId) o.selected=true;
      sel.appendChild(o);
    });
    var del=panel.querySelector('.hl-group-del'); if(del) del.disabled=(s.groups.length<=1);
  }
  function openPanel(){ buildPanel(); renderGroups(); renderList(); panel.hidden=false; document.body.classList.add('hl-panel-open'); }
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
    renderGroups();
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
    state();  // migrate legacy highlights into the default group on first load
    buildPanel(); updateCount();
    var ob=document.getElementById('hl-open');
    if(ob) ob.addEventListener('click', openPanel);
    if(!isFlip){ renderPage(); handleHash(); }
  }
  window.cpdsHighlights={ render:renderPage, open:openPanel,
    exportData:exportData, importData:importHighlights,
    state:state, setActiveGroup:setActiveGroup, newGroup:newGroup,
    renameGroup:renameGroup, deleteGroup:deleteGroup };
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', autorun);
  else autorun();
})();
