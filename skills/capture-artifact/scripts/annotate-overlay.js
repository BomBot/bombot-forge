// Red-box overlay for change-summary screenshots.
// Inject with: bsk evaluate "$(cat annotate-overlay.js)"   (or cdp.py evalf annotate-overlay.js)
// Then per shot: scroll to the spot, call __A({...}), take the screenshot.
//
//   __A({
//     title: 'Short title',            // red heading in the caption panel
//     sub:   'What it was before',     // optional grey line under the title
//     kicker:'PAGE NAME',              // small grey label above the title
//     pos:   'br' | 'tr' | 'bl' | 'tl',// where the caption panel sits (default 'br')
//     top:   16, w: 470,               // panel offset (only for pos t*) / width in px
//     boxes: [selectorOrElement, ...], // numbered red boxes; item N below = box N
//     lines: ['was X -> now Y', ...]   // one line per box
//   })
//
// Helpers: __find(cssSel, text) returns the first element whose text contains `text`.
window.__sleep = ms => new Promise(r => setTimeout(r, ms));
window.__q = s => (typeof s === 'string' ? document.querySelector(s) : s);
window.__find = (sel, txt) => [...document.querySelectorAll(sel)].find(e => e.textContent.indexOf(txt) >= 0);
window.__A = function (o) {
  document.querySelectorAll('.__ann').forEach(e => e.remove());
  (o.boxes || []).forEach((b, i) => {
    const el = __q(b); if (!el) { return; }
    const r = el.getBoundingClientRect();
    const d = document.createElement('div'); d.className = '__ann';
    Object.assign(d.style, { position: 'fixed', left: (r.left - 5) + 'px', top: (r.top - 5) + 'px', width: (r.width + 10) + 'px', height: (r.height + 10) + 'px',
      border: '3px solid #e11d1d', borderRadius: '8px', zIndex: 99998, pointerEvents: 'none', boxSizing: 'border-box' });
    const n = document.createElement('div'); n.textContent = String(i + 1);
    Object.assign(n.style, { position: 'absolute', left: '-15px', top: '-15px', width: '28px', height: '28px', borderRadius: '50%', background: '#e11d1d', color: '#fff',
      font: '700 15px/28px sans-serif', textAlign: 'center', boxShadow: '0 1px 4px rgba(0,0,0,.3)' });
    d.appendChild(n); document.body.appendChild(d);
  });
  const p = document.createElement('div'); p.className = '__ann';
  const pos = o.pos || 'br';
  Object.assign(p.style, { position: 'fixed', width: (o.w || 470) + 'px', background: '#fff', border: '3px solid #e11d1d', borderRadius: '12px', padding: '14px 16px',
    boxShadow: '0 10px 30px rgba(16,24,40,.25)', font: '14px/1.5 -apple-system,Segoe UI,sans-serif', color: '#1d2939', zIndex: 99999 });
  if (pos.indexOf('b') >= 0) { p.style.bottom = '16px'; } else { p.style.top = (o.top || 16) + 'px'; }
  if (pos.indexOf('r') >= 0) { p.style.right = '16px'; } else { p.style.left = '16px'; }
  p.innerHTML = '<div style="font-size:12px;color:#98a2b3;font-weight:700;letter-spacing:.4px">' + (o.kicker || 'CHANGE SUMMARY') + '</div>'
    + '<div style="font-weight:700;font-size:17px;color:#b42318;margin:2px 0 6px">' + o.title + '</div>'
    + (o.sub ? '<div style="color:#475467;margin-bottom:6px">' + o.sub + '</div>' : '')
    + '<ol style="margin:0;padding-left:22px">' + (o.lines || []).map(l => '<li style="margin:5px 0">' + l + '</li>').join('') + '</ol>';
  document.body.appendChild(p);
  return 'ok';
};
'loaded';
