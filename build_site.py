#!/usr/bin/env python3
"""Generate a minimalist literary reading website from the book PDF."""
import os, re, subprocess, html, json
import scripture_lib as SX

PDF = "Book After Xulon Version.pdf"
OUT = "site"
TITLE = "Christian Preaching That Devalues Scripture"
SUBTITLE = "A critique of how Bible-school hermeneutics displace the plain Word of God"
AUTHOR = "Theophilus"

# (number, title, first_pdf_page) — end is next chapter's start - 1
CHAPTERS = [
    (1,  "All Bible scholars are wisdom deficient", 9),
    (2,  "God planned every step of creation", 17),
    (3,  "God created Christian conflict", 34),
    (4,  "My introduction to this book", 37),
    (5,  "The importance of Bible school education", 51),
    (6,  "The dispensations reported in Scripture", 63),
    (7,  "God had a Purpose for Creation", 64),
    (8,  "God's purpose was deliberately hidden", 72),
    (9,  "Critical definitions and distinctions", 83),
    (10, "The philosophical basis for this book", 90),
    (11, "The Biblical justification for this book", 102),
    (12, "The rationale of God's plan", 114),
    (13, "The conclusion of this book", 124),
]
LAST_PAGE = 125
HEADER_PHRASE = "Christian preaching that devalues Scripture"

def page_text(a, b):
    r = subprocess.run(["pdftotext", "-layout", "-f", str(a), "-l", str(b),
                        "-enc", "UTF-8", PDF, "-"], capture_output=True, text=True)
    return r.stdout

def _norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", s.lower())).strip()

def clean_to_paragraphs(raw, chap_num, chap_title):
    """Reconstruct paragraphs, stripping running headers, page numbers, and ONLY
    the chapter title where it actually appears (the first few lines)."""
    title_norm = _norm(chap_title)
    paras, cur = [], []
    heading_done = False
    acc = ""
    seen = 0
    for line in raw.split("\n"):
        s = line.rstrip()
        stripped = s.strip()
        if not stripped:
            continue
        # drop running header
        if stripped.lower().rstrip(".") == HEADER_PHRASE.lower():
            continue
        # drop standalone page numbers (arabic) and roman-numeral folios
        if re.fullmatch(r"\d{1,3}", stripped):
            continue
        if re.fullmatch(r"[ivxlcdm]{1,6}", stripped, re.I):
            continue
        # --- chapter heading region (only at the very start of the chapter) ---
        if not heading_done:
            seen += 1
            if re.fullmatch(r"Chapter\s+\d+", stripped, re.I):
                continue
            cand = _norm((acc + " " + stripped).strip())
            if title_norm and (cand == title_norm or _norm(stripped) == title_norm):
                heading_done = True; acc = ""
                continue
            if title_norm and cand and title_norm.startswith(cand):
                acc = (acc + " " + stripped).strip()  # title spans multiple lines
                continue
            # this line is real body text -> heading region is over
            heading_done = True; acc = ""
            if seen > 6:
                heading_done = True
            # fall through and process this line as body
        # --- body ---
        indented = len(s) - len(s.lstrip(" ")) >= 2
        if indented and cur:
            paras.append(" ".join(cur)); cur = []
        cur.append(stripped)
    if cur:
        paras.append(" ".join(cur))
    return [re.sub(r"\s+", " ", p).strip() for p in paras if len(p.strip()) > 1]

def esc(t):
    return html.escape(t, quote=False)

# ---- extract all chapters ----
chapter_data = []
for i, (num, title, start) in enumerate(CHAPTERS):
    end = (CHAPTERS[i+1][2] - 1) if i+1 < len(CHAPTERS) else LAST_PAGE
    raw = page_text(start, end)
    paras = clean_to_paragraphs(raw, num, title)
    chapter_data.append((num, title, paras))
    print(f"Chapter {num}: {len(paras)} paragraphs (pp.{start}-{end})")

# dedication (pages 5-6)
ded_raw = page_text(5, 6)
ded = clean_to_paragraphs(ded_raw, 0, "Dedication of this book")

os.makedirs(OUT, exist_ok=True)

# ---------- scripture: detect references, resolve KJV passages, write scripture.js ----------
# Each passage points at its full chapter (sx_chapters) so the modal can expand
# context up and down on demand. Chapters are stored once and shared.
all_paras = [p for _, _, ps in chapter_data for p in ps] + ded
sx_passages = {}        # refKey -> {label, ck (chapterKey), vs, ve}
sx_chapters = {}        # "<booknum>.<chap>" -> {book, n, v:[verse texts...]}
sx_unresolved = set()
for para in all_paras:
    for m, bk, ch, vs, ve in SX.find_refs(para):
        k = SX.key_for(bk, ch, vs, ve)
        if k in sx_passages:
            continue
        ck = f"{bk.value}.{ch}"
        if ck not in sx_chapters:
            verses = SX.chapter_verses(bk, ch)
            if verses:
                sx_chapters[ck] = {"book": SX.DISPLAY[bk], "n": ch, "v": verses}
        if ck not in sx_chapters or vs > len(sx_chapters[ck]["v"]):
            sx_unresolved.add(m.group(0).strip())
            continue
        sx_passages[k] = {"label": SX.label_for(bk, ch, vs, ve), "ck": ck, "vs": vs, "ve": ve}
print(f"Scripture: {len(sx_passages)} passages across {len(sx_chapters)} chapters; "
      f"{len(sx_unresolved)} unresolved {sorted(sx_unresolved)[:6]}")

SCRIPTURE_JS_TEMPLATE = r"""(function(){
  var P = __PASSAGES__;
  var C = __CHAPTERS__;
  var B = __BOOKMAP__;
  var CHUNK = 5;  // verses added per "load more" click
  var RE = /(?:([1-3])\s?)?([A-Z][A-Za-z]+)\.?\s*(\d{1,3}):\s*(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?(ff?\.?)?/g;
  function keyFor(g1,g2,ch,vs,ve){
    var tok=((g1||'')+g2).toLowerCase(), bn=B[tok];
    if(!bn) return null;
    ve = ve ? +ve : +vs; vs=+vs;
    if(ve<vs) ve=vs;
    return bn+'.'+(+ch)+'.'+vs+'.'+ve;
  }
  var modal=null, ST=null;
  function buildModal(){
    if(modal) return;
    modal=document.createElement('div');
    modal.className='sx-modal'; modal.hidden=true;
    modal.innerHTML='<div class="sx-backdrop"></div>'+
      '<div class="sx-card" role="dialog" aria-modal="true" aria-label="Scripture passage">'+
      '<button class="sx-close" aria-label="Close">×</button>'+
      '<p class="sx-ref"></p>'+
      '<button class="sx-more sx-up" type="button"></button>'+
      '<div class="sx-verses"></div>'+
      '<button class="sx-more sx-down" type="button"></button>'+
      '<p class="sx-foot">King James Version</p></div>';
    document.body.appendChild(modal);
    modal.querySelector('.sx-backdrop').addEventListener('click',closeModal);
    modal.querySelector('.sx-close').addEventListener('click',closeModal);
    modal.querySelector('.sx-up').addEventListener('click',function(){
      if(!ST||ST.lo<=1) return;
      ST.lo=Math.max(1, ST.lo-CHUNK); renderVerses('up');
    });
    modal.querySelector('.sx-down').addEventListener('click',function(){
      if(!ST||ST.hi>=ST.total) return;
      ST.hi=Math.min(ST.total, ST.hi+CHUNK); renderVerses('down');
    });
  }
  function renderVerses(mode){
    var box=modal.querySelector('.sx-verses');
    var prevH=box.scrollHeight, prevTop=box.scrollTop;
    box.innerHTML='';
    for(var v=ST.lo; v<=ST.hi; v++){
      var el=document.createElement('p');
      el.className='sx-v'+(v>=ST.vs && v<=ST.ve ? ' hl' : '');
      el.innerHTML='<sup>'+v+'</sup>'+ST.verses[v-1];
      box.appendChild(el);
    }
    var up=modal.querySelector('.sx-up'), dn=modal.querySelector('.sx-down');
    if(ST.lo<=1){ up.disabled=true; up.textContent='Beginning of '+ST.book+' '+ST.chap; }
    else { up.disabled=false; up.innerHTML='↑ Show earlier verses'; }
    if(ST.hi>=ST.total){ dn.disabled=true; dn.textContent='End of '+ST.book+' '+ST.chap; }
    else { dn.disabled=false; dn.innerHTML='Show later verses ↓'; }
    if(mode==='up') box.scrollTop = prevTop + (box.scrollHeight - prevH);
    else if(mode==='open') box.scrollTop = 0;
  }
  function openModal(key){
    buildModal();
    var p=P[key]; if(!p) return;
    var ch=C[p.ck]; if(!ch) return;
    ST={ verses:ch.v, total:ch.v.length, book:ch.book, chap:ch.n,
         vs:p.vs, ve:p.ve, lo:Math.max(1,p.vs-2), hi:Math.min(ch.v.length, p.ve+2) };
    modal.querySelector('.sx-ref').textContent=p.label;
    renderVerses('open');
    modal.hidden=false;
    document.body.classList.add('sx-open');
  }
  function closeModal(){ if(modal){ modal.hidden=true; document.body.classList.remove('sx-open'); } }
  var SKIP={A:1,SCRIPT:1,STYLE:1,BUTTON:1,SUP:1,H1:1,H2:1};
  function linkifyScripture(root){
    if(!root) return;
    var walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode:function(n){
      if(!n.nodeValue || n.nodeValue.indexOf(':')<0) return NodeFilter.FILTER_REJECT;
      var p=n.parentNode;
      while(p && p!==root){ if(SKIP[p.nodeName]||(p.classList&&p.classList.contains('scripture'))) return NodeFilter.FILTER_REJECT; p=p.parentNode; }
      return NodeFilter.FILTER_ACCEPT;
    }});
    var nodes=[], nn; while(nn=walker.nextNode()) nodes.push(nn);
    nodes.forEach(function(node){
      var text=node.nodeValue, mm, last=0, frag=null; RE.lastIndex=0;
      while(mm=RE.exec(text)){
        var key=keyFor(mm[1],mm[2],mm[3],mm[4],mm[5]);
        if(!key || !P[key]) continue;
        if(!frag) frag=document.createDocumentFragment();
        frag.appendChild(document.createTextNode(text.slice(last,mm.index)));
        var a=document.createElement('a');
        a.className='scripture'; a.href='#'; a.dataset.key=key; a.setAttribute('role','button');
        a.title='View '+P[key].label+' (KJV)';
        a.textContent=mm[0];
        frag.appendChild(a); last=mm.index+mm[0].length;
      }
      if(frag){ frag.appendChild(document.createTextNode(text.slice(last))); node.parentNode.replaceChild(frag,node); }
    });
  }
  // prevent the flip-book from turning the page when a reference is clicked
  document.addEventListener('mousedown',function(e){ if(e.target.closest&&e.target.closest('.scripture')) e.stopPropagation(); },true);
  document.addEventListener('click',function(e){
    var a=e.target.closest&&e.target.closest('.scripture');
    if(a){ e.preventDefault(); e.stopPropagation(); openModal(a.dataset.key); }
  },true);
  document.addEventListener('keydown',function(e){ if(e.key==='Escape') closeModal(); });
  window.linkifyScripture=linkifyScripture;
  function autorun(){
    buildModal();
    if(!document.body.classList.contains('flip-body'))
      linkifyScripture(document.querySelector('main')||document.body);
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',autorun);
  else autorun();
})();
"""
scripture_js = (SCRIPTURE_JS_TEMPLATE
                .replace("__PASSAGES__", json.dumps(sx_passages, ensure_ascii=False, separators=(",", ":")))
                .replace("__CHAPTERS__", json.dumps(sx_chapters, ensure_ascii=False, separators=(",", ":")))
                .replace("__BOOKMAP__", json.dumps(SX.bookmap_js(), separators=(",", ":"))))
open(f"{OUT}/scripture.js", "w").write(scripture_js)

# ---------- highlights: user text-highlighting + saved list panel ----------
# No server-side data needed; this is a static client script. Anchored by
# chapter + paragraph index (data-chap / data-cidx) + character offsets within
# the paragraph's text, so highlights survive reloads and are view-independent
# (the same anchor maps onto the flip view's paragraphs for future support).
HIGHLIGHTS_JS = r"""(function(){
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
  function exportData(){
    return { app:'cpds', type:'highlights', version:1, book:bookTitle(),
             exportedAt:new Date().toISOString(), highlights:lsGet() };
  }
  function exportHighlights(){
    var hs=lsGet();
    if(!hs.length){ ioMsg('No highlights to export yet.', true); return; }
    var blob=new Blob([JSON.stringify(exportData(), null, 2)], {type:'application/json'});
    var url=URL.createObjectURL(blob);
    var a=document.createElement('a');
    a.href=url; a.download='highlights-'+new Date().toISOString().slice(0,10)+'.json';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function(){ try{ URL.revokeObjectURL(url); }catch(e){} }, 1000);
    ioMsg(hs.length+' highlight'+(hs.length===1?'':'s')+' saved to a file.');
  }
  function importHighlights(text){
    var parsed;
    try{ parsed=JSON.parse(text); }catch(e){ ioMsg('Could not read file: it is not valid JSON.', true); return {added:0,updated:0,skipped:0,error:true}; }
    var incoming = Array.isArray(parsed) ? parsed
                 : (parsed && Array.isArray(parsed.highlights) ? parsed.highlights : null);
    if(!incoming){ ioMsg('No highlights found in that file.', true); return {added:0,updated:0,skipped:0,error:true}; }
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
    ioMsg('Imported '+added+' new, '+updated+' updated'+(skipped?(', '+skipped+' skipped'):'')+'.');
    return {added:added, updated:updated, skipped:skipped};
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
        '<div class="hl-list"></div>'+
        '<div class="hl-foot">'+
          '<div class="hl-io">'+
            '<button class="hl-export" type="button">↓ Export</button>'+
            '<button class="hl-import" type="button">↑ Import</button>'+
          '</div>'+
          '<p class="hl-io-msg" hidden></p>'+
          '<button class="hl-clear" type="button">Clear all highlights</button>'+
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
      if(window.confirm('Remove all of your saved highlights? This cannot be undone.')){
        lsSet([]); renderPage(); updateCount(); renderList();
      }
    });
    panel.querySelector('.hl-export').addEventListener('click', exportHighlights);
    var fileInput=panel.querySelector('.hl-file');
    panel.querySelector('.hl-import').addEventListener('click', function(){ fileInput.click(); });
    fileInput.addEventListener('change', function(){
      var f=fileInput.files && fileInput.files[0]; if(!f) return;
      var reader=new FileReader();
      reader.onload=function(){ importHighlights(String(reader.result)); fileInput.value=''; };
      reader.onerror=function(){ ioMsg('Could not read the file.', true); fileInput.value=''; };
      reader.readAsText(f);
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
  window.cpdsHighlights={ render:renderPage, open:openPanel,
    exportData:exportData, importData:importHighlights };
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', autorun);
  else autorun();
})();
"""
open(f"{OUT}/highlights.js", "w").write(HIGHLIGHTS_JS)

# ---------- shared head ----------
def head(page_title, depth_home="index.html"):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(page_title)}</title>
<meta name="description" content="{esc(SUBTITLE)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;1,400&family=Spectral:wght@500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="style.css">
<script src="scripture.js" defer></script>
<script src="highlights.js" defer></script>
</head>"""

THEME_SCRIPT = """<script>
(function(){
  var k='cpds-theme';
  var saved=localStorage.getItem(k);
  if(saved){document.documentElement.setAttribute('data-theme',saved);}
  window.toggleTheme=function(){
    var cur=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';
    document.documentElement.setAttribute('data-theme',cur);
    localStorage.setItem(k,cur);
  };
})();
</script>"""

def topbar(show_contents=True, view="scroll"):
    c = '<a class="bar-link" href="contents.html">Contents</a>' if show_contents else ''
    if view == "flip":
        viewlink = '<a class="bar-link" href="index.html">Scroll&nbsp;view</a>'
    else:
        viewlink = '<a class="bar-link" href="book.html">Flip&nbsp;view</a>'
    hl = ('<button class="bar-link hl-open-btn" id="hl-open" type="button" '
          'aria-label="View your highlights">Highlights'
          '<span class="hl-count" id="hl-count" hidden>0</span></button>')
    return f"""<div class="topbar">
  <a class="bar-link" href="index.html">{esc(TITLE)}</a>
  <div class="bar-right">{c}{viewlink}{hl}<button class="bar-link theme-btn" onclick="toggleTheme()" aria-label="Toggle light or dark mode">◑</button></div>
</div>"""

# ---------- index / cover ----------
toc_items = "\n".join(
    f'    <li><a href="chapter-{n}.html"><span class="toc-num">{n}</span>'
    f'<span class="toc-title">{esc(t)}</span></a></li>'
    for n, t, _ in chapter_data
)
index = f"""{head(TITLE)}
<body class="cover-page">
{THEME_SCRIPT}
{topbar(show_contents=False)}
<main class="cover">
  <div class="cover-inner">
    <p class="kicker">An essay in {len(chapter_data)} chapters</p>
    <h1 class="cover-title">{esc(TITLE)}</h1>
    <p class="cover-sub">{esc(SUBTITLE)}</p>
    <p class="cover-author">{esc(AUTHOR)}</p>
    <p class="cover-blurb">A sustained argument that Bible-school hermeneutics teach preachers to
      &ldquo;lean unto their own understanding&rdquo; rather than report what God plainly inspired &mdash;
      and a case for exposition grounded in the conviction that <em>why</em> God spoke matters more than
      competing opinions about <em>what</em> He meant.</p>
    <a class="begin" href="chapter-1.html">Begin reading &rarr;</a>
    <p class="alt-read"><a href="book.html">or turn the pages as a flip-book &rarr;</a></p>
  </div>
</main>
<section class="contents-block">
  <h2 class="contents-h">Contents</h2>
  <ol class="toc">
{toc_items}
  </ol>
  <p class="ded-link"><a href="contents.html">Full table of contents &amp; dedication &rarr;</a></p>
</section>
<footer class="site-foot">{esc(TITLE)} &middot; {esc(AUTHOR)}</footer>
</body></html>"""
open(f"{OUT}/index.html", "w").write(index)

# ---------- contents page (with dedication) ----------
ded_html = "\n".join(f'    <p data-cidx="{i}">{esc(p)}</p>' for i, p in enumerate(ded))
contents = f"""{head('Contents — ' + TITLE)}
<body>
{THEME_SCRIPT}
{topbar(show_contents=False)}
<main class="reader">
  <h1 class="page-h">Contents</h1>
  <ol class="toc toc-full">
{toc_items}
  </ol>
  <hr class="rule">
  <h2 class="page-h" id="dedication">Dedication</h2>
  <div class="prose" data-chap="0" data-chap-title="Dedication">
{ded_html}
  </div>
  <nav class="chap-nav"><a href="chapter-1.html">Begin reading: Chapter 1 &rarr;</a></nav>
</main>
<footer class="site-foot">{esc(TITLE)} &middot; {esc(AUTHOR)}</footer>
</body></html>"""
open(f"{OUT}/contents.html", "w").write(contents)

# ---------- chapter pages ----------
for idx, (num, title, paras) in enumerate(chapter_data):
    body = "\n".join(f'    <p data-cidx="{i}">{esc(p)}</p>' for i, p in enumerate(paras))
    prev_link = (f'<a class="nav-prev" href="chapter-{num-1}.html">&larr; Chapter {num-1}</a>'
                 if idx > 0 else '<a class="nav-prev" href="contents.html">&larr; Contents</a>')
    nxt = chapter_data[idx+1] if idx+1 < len(chapter_data) else None
    next_link = (f'<a class="nav-next" href="chapter-{nxt[0]}.html">Chapter {nxt[0]} &rarr;</a>'
                 if nxt else '<a class="nav-next" href="index.html">Back to cover &rarr;</a>')
    page = f"""{head(f'Chapter {num}: {title} — ' + TITLE)}
<body>
{THEME_SCRIPT}
{topbar()}
<div class="progress"><div class="progress-bar" id="pb"></div></div>
<main class="reader">
  <header class="chap-head">
    <p class="chap-num">Chapter {num}</p>
    <h1 class="chap-title">{esc(title)}</h1>
  </header>
  <article class="prose" data-chap="{num}" data-chap-title="{esc(title)}">
{body}
  </article>
  <nav class="chap-nav">
    {prev_link}
    <a class="nav-top" href="#" onclick="window.scrollTo({{top:0,behavior:'smooth'}});return false;">Top</a>
    {next_link}
  </nav>
</main>
<footer class="site-foot">{esc(TITLE)} &middot; {esc(AUTHOR)}</footer>
<script>
var pb=document.getElementById('pb');
window.addEventListener('scroll',function(){{
  var h=document.documentElement;
  var p=(h.scrollTop)/(h.scrollHeight-h.clientHeight);
  pb.style.width=(p*100)+'%';
}});
</script>
</body></html>"""
    open(f"{OUT}/chapter-{num}.html", "w").write(page)

# ---------- flip-book view ----------
book_json = json.dumps(
    [{"n": n, "title": t, "paras": paras} for n, t, paras in chapter_data],
    ensure_ascii=False)

flip = f"""{head('Flip-book — ' + TITLE)}
<script src="page-flip.min.js"></script>
<body class="flip-body">
{THEME_SCRIPT}
{topbar(show_contents=False, view="flip")}
<script type="application/json" id="bookdata">{book_json}</script>

<div id="loader" class="loader">Setting the type&hellip;</div>

<div id="stage" class="stage" hidden>
  <button id="prev" class="flip-arrow flip-prev" aria-label="Previous page">&lsaquo;</button>
  <div id="book" class="flipbook"></div>
  <button id="next" class="flip-arrow flip-next" aria-label="Next page">&rsaquo;</button>
</div>
<div id="resume" class="resume-bar" hidden></div>
<div id="flip-foot" class="flip-foot" hidden>
  <button id="bookmark-btn" class="bk-mark-btn" title="Bookmark this page">&#x2691;&nbsp;<span>Bookmark</span></button>
  <span id="pagelabel"></span>
  <span class="flip-hint">click a page edge, drag a corner, or use &larr; &rarr;</span>
</div>

<script>
const BOOK = JSON.parse(document.getElementById('bookdata').textContent);
const TITLE = {json.dumps(TITLE)};
const AUTHOR = {json.dumps(AUTHOR)};

function calcSize(){{
  const vw = innerWidth, vh = innerHeight;
  const portrait = vw < 860;
  // base page height on the space actually left between the top bar and footer
  const bar = document.querySelector('.topbar');
  const barH = bar ? bar.offsetHeight : 56;
  const footH = 46;
  const avail = vh - barH - footH - 24;     // 24 = stage padding/breathing room
  let h = Math.min(avail, 820);
  h = Math.max(h, 320);
  let w = Math.round(h / 1.5);
  const maxW = portrait ? (vw - 36) : (vw - 130) / 2;
  if (w > maxW) {{ w = Math.floor(maxW); h = Math.round(w * 1.5); }}
  return {{ w, h, portrait }};
}}

let pageFlip = null;

function buildPageEl(inner, cls){{
  const d = document.createElement('div');
  d.className = 'page ' + (cls || '');
  d.innerHTML = '<div class="page-content">' + inner + '</div>';
  return d;
}}

function paginate(size){{
  // offscreen measurer matching the real page content box
  const m = document.createElement('div');
  m.className = 'page-content measurer';
  m.style.width = size.w + 'px';
  document.body.appendChild(m);
  const padY = 0; // padding already in CSS .page-content
  const limit = size.h; // content box height target
  // measurer has same padding; compare scrollHeight to page height
  m.style.height = 'auto';

  const pages = [];     // array of html strings (content only)
  let curHTML = '';
  const fits = () => m.scrollHeight <= size.h;

  function flush(){{ if (curHTML.trim()) {{ pages.push(curHTML); curHTML = ''; m.innerHTML=''; }} }}
  function tryBlock(htmlStr){{
    const prev = curHTML;
    m.innerHTML = curHTML + htmlStr;
    if (fits()) {{ curHTML += htmlStr; return true; }}
    // does not fit
    if (!prev.trim()){{ // empty page but block too big -> must split (paragraph)
      return splitParagraph(htmlStr);
    }}
    m.innerHTML = prev; // revert
    flush();
    // retry on fresh page
    m.innerHTML = htmlStr;
    if (fits()) {{ curHTML = htmlStr; return true; }}
    return splitParagraph(htmlStr);
  }}
  function splitParagraph(htmlStr){{
    // htmlStr is a <p ...>....</p>; split text by words
    const mo = htmlStr.match(/^(<p[^>]*>)([\\s\\S]*)(<\\/p>)$/);
    if (!mo){{ curHTML += htmlStr; return true; }}
    const open = mo[1], close = mo[3];
    const words = mo[2].split(' ');
    let lo = '';
    for (let i=0;i<words.length;i++){{
      const test = (lo ? lo+' ' : '') + words[i];
      m.innerHTML = curHTML + open + test + close;
      if (fits()){{ lo = test; }}
      else {{
        if (!lo){{ // single word too big, force it
          curHTML += open + words[i] + close; flush();
          return splitParagraph(open + words.slice(i+1).join(' ') + close);
        }}
        curHTML += open + lo + close; flush();
        return splitParagraph(open + words.slice(i).join(' ') + close);
      }}
    }}
    curHTML += open + lo + close;
    return true;
  }}

  // cover page
  const tocLis = BOOK.map(c => '<li><span>'+c.n+'</span>'+c.title+'</li>').join('');
  pages.push('<div class="cover-face"><p class="bk-kicker">An essay in '+BOOK.length+' chapters</p>'
    + '<h1 class="bk-title">'+TITLE+'</h1><p class="bk-author">'+AUTHOR+'</p>'
    + '<ol class="bk-toc">'+tocLis+'</ol></div>');

  // chapters
  let PID = 0;
  for (const ch of BOOK){{
    flush(); // each chapter starts on a fresh leaf
    const headHTML = '<div class="bk-chaphead"><p class="bk-chapnum">Chapter '+ch.n
      + '</p><h2 class="bk-chaptitle">'+ch.title+'</h2></div>';
    m.innerHTML = headHTML; curHTML = headHTML;
    let CIDX = 0;
    for (const p of ch.paras){{
      tryBlock('<p data-pid="'+(PID++)+'" data-chap="'+ch.n+'" data-cidx="'+(CIDX++)+'">'+p+'</p>');
    }}
  }}
  flush();
  m.remove();
  return pages;
}}

function render(){{
  const size = calcSize();
  const pages = paginate(size);

  const bookEl = document.getElementById('book');
  bookEl.innerHTML = '';
  // page numbers (skip cover = leaf 0)
  pages.forEach((htmlStr, i) => {{
    const isCover = (i === 0);
    const foot = isCover ? '' : '<div class="page-num">'+i+'</div>';
    const run = isCover ? '' : '<div class="run-head">'+TITLE+'</div>';
    const el = buildPageEl(run + htmlStr + foot, isCover ? 'page-cover' : '');
    el.dataset.density = isCover ? 'hard' : 'soft';
    bookEl.appendChild(el);
  }});

  if (pageFlip) {{ try {{ pageFlip.destroy(); }} catch(e){{}} }}
  pageFlip = new St.PageFlip(bookEl, {{
    width: size.w, height: size.h,
    size: 'fixed',
    minWidth: 280, maxWidth: 1000, minHeight: 380, maxHeight: 1200,
    usePortrait: size.portrait,
    showCover: true,
    maxShadowOpacity: 0.5,
    flippingTime: 700,
    drawShadow: true,
    mobileScrollSupport: false,
    swipeDistance: 20,
  }});
  pageFlip.loadFromHTML(document.querySelectorAll('#book .page'));

  // hyperlink scripture references on the freshly paginated pages
  if (window.linkifyScripture) window.linkifyScripture(document.getElementById('book'));

  const total = pages.length;
  const label = document.getElementById('pagelabel');
  function upd(){{
    const idx = pageFlip.getCurrentPageIndex();
    label.textContent = idx === 0 ? 'Cover' : ('Page ' + idx + ' / ' + (total-1));
  }}

  // ---------- bookmark + resume (anchored to text, resize-safe) ----------
  const LS_LAST = 'cpds:last', LS_MARK = 'cpds:mark';
  const lsGet = k => {{ try {{ return JSON.parse(localStorage.getItem(k) || 'null'); }} catch(e) {{ return null; }} }};
  const lsSet = (k,v) => {{ try {{ localStorage.setItem(k, JSON.stringify(v)); }} catch(e) {{}} }};
  const lsDel = k => {{ try {{ localStorage.removeItem(k); }} catch(e) {{}} }};

  const leaves = [...document.querySelectorAll('#book .page')];
  const pidLeaf = new Map();   // paragraph id -> first leaf it appears on
  const leafPid = [];          // first paragraph id on each leaf
  leaves.forEach((el,i) => {{
    const ids = [...el.querySelectorAll('[data-pid]')].map(n => +n.dataset.pid);
    leafPid[i] = ids.length ? ids[0] : null;
    ids.forEach(pid => {{ if (!pidLeaf.has(pid)) pidLeaf.set(pid, i); }});
  }});
  const sortedPids = [...pidLeaf.keys()].sort((a,b) => a-b);
  function leafForPid(pid){{
    if (pid == null) return 1;
    if (pidLeaf.has(pid)) return pidLeaf.get(pid);
    let best = 1;
    for (const p of sortedPids) {{ if (p <= pid) best = pidLeaf.get(p); else break; }}
    return best;
  }}
  function currentAnchor(){{
    const idx = pageFlip.getCurrentPageIndex();
    let i = idx, pid = null;
    while (i < leaves.length && pid == null) {{ pid = leafPid[i]; i++; }}
    return {{ pid: pid, page: idx }};
  }}

  const markBtn = document.getElementById('bookmark-btn');
  function refreshMarkBtn(){{
    const mark = lsGet(LS_MARK);
    const idx = pageFlip.getCurrentPageIndex();
    const on = mark && leafForPid(mark.pid) === idx;
    markBtn.classList.toggle('is-marked', !!on);
    markBtn.querySelector('span').textContent = on ? 'Bookmarked' : 'Bookmark';
  }}
  markBtn.onclick = () => {{
    const mark = lsGet(LS_MARK);
    const idx = pageFlip.getCurrentPageIndex();
    if (mark && leafForPid(mark.pid) === idx) lsDel(LS_MARK);
    else lsSet(LS_MARK, currentAnchor());
    refreshMarkBtn();
  }};

  pageFlip.on('flip', () => {{ upd(); lsSet(LS_LAST, currentAnchor()); refreshMarkBtn(); }});
  upd();
  refreshMarkBtn();

  const rb = document.getElementById('resume');
  const hideResume = () => {{ rb.hidden = true; }};
  function jump(pid){{ pageFlip.turnToPage(leafForPid(pid)); upd(); refreshMarkBtn(); hideResume(); }}

  if (!window.__cpdsBooted) {{
    // first load: offer to resume bookmark and/or last position
    window.__cpdsBooted = true;
    const mark = lsGet(LS_MARK), last = lsGet(LS_LAST);
    const offers = [];
    if (mark && mark.pid != null) offers.push({{ label: '\\u2691 Bookmark · p.' + leafForPid(mark.pid), pid: mark.pid }});
    if (last && last.page > 0 && (!mark || leafForPid(last.pid) !== leafForPid(mark.pid)))
      offers.push({{ label: 'Continue · p.' + leafForPid(last.pid), pid: last.pid }});
    if (offers.length) {{
      rb.innerHTML = '';
      const msg = document.createElement('span');
      msg.className = 'resume-msg'; msg.textContent = 'Pick up where you left off:';
      rb.appendChild(msg);
      offers.forEach(o => {{
        const btn = document.createElement('button');
        btn.className = 'resume-go'; btn.textContent = o.label;
        btn.onclick = () => jump(o.pid);
        rb.appendChild(btn);
      }});
      const x = document.createElement('button');
      x.className = 'resume-x'; x.innerHTML = '&times;'; x.title = 'Dismiss';
      x.onclick = hideResume; rb.appendChild(x);
      rb.hidden = false;
      setTimeout(() => {{ hideResume(); }}, 15000);
    }}
  }} else {{
    // re-render after a resize: silently restore the reader's place
    const last = lsGet(LS_LAST);
    if (last && last.pid != null) {{ pageFlip.turnToPage(leafForPid(last.pid)); upd(); refreshMarkBtn(); }}
  }}

  document.getElementById('loader').hidden = true;
  document.getElementById('stage').hidden = false;
  document.getElementById('flip-foot').hidden = false;
}}

document.getElementById('next').onclick = () => pageFlip && pageFlip.flipNext();
document.getElementById('prev').onclick = () => pageFlip && pageFlip.flipPrev();
document.addEventListener('keydown', e => {{
  if (!pageFlip) return;
  if (e.key === 'ArrowRight') pageFlip.flipNext();
  if (e.key === 'ArrowLeft') pageFlip.flipPrev();
}});

function safeRender(){{
  try {{ render(); }}
  catch (e) {{
    console.error(e);
    const l = document.getElementById('loader');
    if (l) {{ l.hidden = false; l.textContent = 'Sorry — the flip-book could not be laid out. Please reload the page.'; }}
  }}
}}

let rt;
window.addEventListener('resize', () => {{
  clearTimeout(rt);
  rt = setTimeout(() => {{
    document.getElementById('stage').hidden = true;
    document.getElementById('flip-foot').hidden = true;
    document.getElementById('loader').hidden = false;
    document.getElementById('loader').textContent = 'Setting the type\\u2026';
    requestAnimationFrame(safeRender);
  }}, 250);
}});

// Build once fonts are ready so pagination matches rendered metrics, but never
// wait more than 1.8s — otherwise a slow/blocked font request would hang the loader.
const fontsReady = (document.fonts && document.fonts.ready) ? document.fonts.ready : Promise.resolve();
Promise.race([fontsReady, new Promise(r => setTimeout(r, 1800))])
  .then(() => requestAnimationFrame(safeRender));
</script>
</body></html>"""
open(f"{OUT}/book.html", "w").write(flip)

print("Done. Files in", OUT)
