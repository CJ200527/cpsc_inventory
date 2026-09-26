/* ui_helpers.js — shared page chrome: live clock, toast auto-dismiss, cascade unveil. */
/* ---- interactive feedback toasts (client-side twin of server flashes) ----
   showToast() builds the exact .toast-card markup the server renders, so the
   shared #toast-container CSS applies with zero new styles. The delegated
   interceptor below is GET-only (approvals/POSTs can never be delayed) and
   progressive enhancement (no-JS falls back to native submit): filter/search
   submits and Refresh links show a toast, then navigate after ~850ms so the
   feedback is actually seen. */
function showToast(message, category) {
    var host = document.getElementById('toast-container');
    if (!host) {
        host = document.createElement('div');
        host.id = 'toast-container';
        host.className = 'toast-container';
        document.body.insertBefore(host, document.body.firstChild);
    }
    var cat = category || 'info';
    var symbol = cat === 'success' ? '#i-check'
        : (cat === 'error' || cat === 'danger') ? '#i-x' : '#i-bell';
    var iconCls = cat === 'success' ? 'toast-ico-success'
        : (cat === 'error' || cat === 'danger') ? 'toast-ico-error' : 'toast-ico-info';
    var card = document.createElement('div');
    card.className = 'toast-card toast-' + cat;
    var iconWrap = document.createElement('span');
    iconWrap.className = 'toast-icon';
    var NS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('class', 'act-icon toast-ico ' + iconCls);
    svg.setAttribute('aria-hidden', 'true');
    var use = document.createElementNS(NS, 'use');
    use.setAttribute('href', symbol);
    svg.appendChild(use);
    iconWrap.appendChild(svg);
    var msg = document.createElement('span');
    msg.className = 'toast-message';
    msg.textContent = message; // textContent = XSS-safe, same guarantee as Jinja escaping
    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'toast-close';
    close.textContent = '✕';
    close.addEventListener('click', function () { if (card.parentNode) card.remove(); });
    card.appendChild(iconWrap);
    card.appendChild(msg);
    card.appendChild(close);
    host.appendChild(card);
    setTimeout(function () {
        card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        card.style.opacity = '0';
        card.style.transform = 'translateY(-20px) scale(0.9)';
        setTimeout(function () { if (card.parentNode) card.remove(); }, 400);
    }, 4000);
    return card;
}
var INTERACTIVE_TOAST_DELAY = 850;
document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form || form.tagName !== 'FORM') return;
    if ((form.getAttribute('method') || 'GET').toUpperCase() !== 'GET') return;
    if (form.hasAttribute('data-toast-shown')) return;
    e.preventDefault();
    form.setAttribute('data-toast-shown', '1');
    var submitter = e.submitter;
    var copy = 'Searching records.';
    if (submitter && submitter.classList && submitter.classList.contains('btn-refresh-icon')) {
        copy = 'Refreshing data.';
    } else if (!form.querySelector('input[type="text"][name="search"]')) {
        copy = 'Filters applied. Refreshing results.';
    }
    showToast(copy, 'info');
    try {
        sessionStorage.setItem('cpscRowsAnim', '1');
        sessionStorage.setItem('cpscScrollY', String(window.scrollY || 0));
    } catch (err) {}
    setTimeout(function () { form.submit(); }, INTERACTIVE_TOAST_DELAY);
}, true);
document.addEventListener('click', function (e) {
    var ref = e.target && e.target.closest
        ? e.target.closest('a[title="Refresh"]') : null;
    if (!ref || ref.tagName !== 'A') return;
    e.preventDefault();
    showToast('Refreshing data.', 'info');
    var href = ref.getAttribute('href');
    try {
        sessionStorage.setItem('cpscRowsAnim', '1');
        sessionStorage.setItem('cpscScrollY', String(window.scrollY || 0));
    } catch (err) {}
    setTimeout(function () { window.location.href = href; }, INTERACTIVE_TOAST_DELAY);
}, true);
function updateClock(){
    const now = new Date();
    const clockEl = document.getElementById('live-clock');
    if(!clockEl) return;
    clockEl.innerText = `${now.toLocaleDateString('en-US', {month:'long', day:'numeric', year:'numeric'})} | ${now.toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:true})}`;
}
setInterval(updateClock, 1000); updateClock();

/* ---- staggered unveil (1-by-1 entrance) ----
   Runtime delays replace the old fixed tiers: header first, then each
   direct content block in order (0.1s + i x 0.12s). transform/opacity only
   (compositor), will-change released on landing, reduced-motion respected.
   No click lock anywhere — input stays live throughout the motion. */
function staggerUnveil() {
    if (window.__staggerDone) return;
    window.__staggerDone = true;
    try {
        if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    } catch (e) {}
    /* Uniform stagger spacing on every page — one calm settle everywhere,
       no per-page gates, no drift. */
    var STEP = 0.22, i = 0;
    function skip(el) {
        if (!el || !el.tagName) return true;
        var tag = el.tagName.toLowerCase();
        if (tag === 'script' || tag === 'template' || tag === 'style' || tag === 'link' || tag === 'datalist') return true;
        try {
            if (window.getComputedStyle(el).display === 'none') return true;
        } catch (e) {}
        return false;
    }
    function arm(el) {
        el.classList.add('cascade-unveil');
        el.style.animationDelay = (0.1 + (i++) * STEP).toFixed(2) + 's';
        el.style.willChange = 'opacity, transform';
        el.addEventListener('animationend', function h() {
            el.style.willChange = 'auto';
            el.removeEventListener('animationend', h);
        });
    }
    var header = document.querySelector('.top-header');
    if (header && !skip(header)) arm(header);
    document.querySelectorAll('.dashboard-container > *').forEach(function (el) {
        if (!skip(el)) arm(el);
    });
}

/* ---- view-transition arrival gating ----
   The cross-page morph runs on sidebar tab clicks (logout excluded — an
   exit gets a plain swap) AND on filter/search/refresh arrivals
   (same-origin GETs all glide identically): either click plants a one-shot
   flag, and the pagereveal handler skips the transition for every other
   arrival (reload, forms, POST-redirects). Sidebar snapshots are frozen by
   CSS so the nav stays pixel-still. */
document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('.sidebar .nav-btn:not(.logout-btn)') : null;
    if (!a) return;
    try { sessionStorage.setItem('cpscTabAnim', '1'); } catch (err) {}
});
window.addEventListener('pagereveal', function (e) {
    var want = false;
    try { want = sessionStorage.getItem('cpscTabAnim') === '1'; } catch (err) {}
    if (!want) {
        try { want = sessionStorage.getItem('cpscRowsAnim') === '1'; } catch (err) {}
    }
    if (want) {
        try { sessionStorage.removeItem('cpscTabAnim'); } catch (err2) {}
    } else if (e.viewTransition) {
        try { e.viewTransition.skipTransition(); } catch (err3) {}
    }
});
window.addEventListener('pageshow', function () {
    try { sessionStorage.removeItem('cpscTabAnim'); } catch (e) {}
});

/* Show a toast planted by the previous page (retired pilot — kept as a
   no-op-safe helper; nothing plants it anymore). */
function showPendingToast() {
    try { sessionStorage.removeItem('cpscPendingToast'); } catch (e) {}
}
try { showPendingToast(); } catch (e) {}

/* Run the stagger synchronously at parse end (before first paint in the
   common case) so content never paints un-animated and flashes. The
   DOMContentLoaded calls below stay as a safety net (guarded, no-ops). */
try {
    // Filter/search/refresh arrivals morph exactly like sidebar clicks
    // (pagereveal allows the transition while this flag is present), then
    // run the same full stagger: every same-origin GET feels identical.
    // Scroll position restores and the search box refocuses; the flag is
    // consumed so plain arrivals and reloads render exactly as before.
    var rowsArrival = false;
    try { rowsArrival = sessionStorage.getItem('cpscRowsAnim') === '1'; } catch (e) {}
    if (rowsArrival) {
        try { sessionStorage.removeItem('cpscRowsAnim'); } catch (e) {}
    }
    staggerUnveil();
    if (rowsArrival) {
        (function () {
            var y = 0;
            try { y = parseInt(sessionStorage.getItem('cpscScrollY') || '0', 10) || 0; } catch (e) {}
            try { sessionStorage.removeItem('cpscScrollY'); } catch (e) {}
            function settle() {
                if (y > 0) { try { window.scrollTo({ top: y, behavior: 'smooth' }); } catch (e) { try { window.scrollTo(0, y); } catch (e2) {} } }
                var box = document.querySelector('.search-input-box input[type="text"]');
                if (box && box.focus) { try { box.focus({ preventScroll: true }); } catch (e) { try { box.focus(); } catch (e2) {} } }
            }
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', settle);
            } else {
                settle();
            }
        })();
    }
} catch (e) {}

        document.addEventListener('DOMContentLoaded', function() {
            const toasts = document.querySelectorAll('.toast-card');
            toasts.forEach(toast => {
                setTimeout(() => {
                    toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
                    toast.style.opacity = '0';
                    toast.style.transform = 'translateY(-20px) scale(0.9)';
                    setTimeout(() => { if (toast.parentNode) toast.remove(); }, 400);
                }, 4000);
            });
        });
    
        document.addEventListener('DOMContentLoaded', function() {
            const isFromLogin = document.referrer.includes('/login');
            const skeleton = document.getElementById('skeleton-overlay');
            // Only show skeleton when coming from /login, otherwise bypass and do cascade
            if (!isFromLogin) {
                document.getElementById('skeleton-overlay')?.remove();
                const main = document.getElementById('main-dashboard-content');
                if (main) { main.style.opacity = '1'; main.classList.add('loaded'); }
                // Also handle dashboards that use .main-wrapper without #main-dashboard-content
                const fallbackMain = document.querySelector('.main-wrapper') || document.body;
                if (fallbackMain && !main) {
                    fallbackMain.style.opacity = '1';
                }
            }
            // Progressive 1-by-1 unveil - top to bottom, sidebar stays static.
            // (No click lock: motion is compositor-only, input stays live.)
            // Only run cascade if internal navigation (not from login) OR if no skeleton present
            if (!isFromLogin || !skeleton) {
                staggerUnveil();
            }
        });
    
        /* ---- front-shell skeleton loader (from base.html) ---- */
        const SKELETON_ENABLED = true;
        document.addEventListener('DOMContentLoaded', function() {
            const skeleton = document.getElementById('skeleton-overlay');
            const main = document.getElementById('main-dashboard-content');
            const isFromLogin = document.referrer.includes('/login');
            if (!isFromLogin) {
                document.getElementById('skeleton-overlay')?.remove();
                if (main) { main.style.opacity = '1'; main.classList.add('loaded'); }
            // Progressive 1-by-1 unveil - top to bottom, sidebar stays static.
                // (No click lock: motion is compositor-only, input stays live.)
                staggerUnveil();
                return;
            }
            if (!SKELETON_ENABLED || !skeleton || !main) {
                if (skeleton) skeleton.style.display = 'none';
                if (main) { main.style.opacity = '1'; main.classList.add('loaded'); }
                return;
            }
            // Overlay starts server-rendered (class="show" only on ?welcome=1
            // landings) so there is never a first-paint pop-in. Clean the
            // one-time flag so refresh never replays the shimmer.
            try {
                if (window.location.search.indexOf('welcome=1') !== -1 &&
                        window.history.replaceState) {
                    window.history.replaceState(
                        null, '',
                        window.location.pathname + window.location.hash);
                }
            } catch (e) {}
            setTimeout(() => {
                skeleton.style.transition = 'opacity 0.4s ease';
                skeleton.style.opacity = '0';
                main.classList.add('loaded');
                main.style.opacity = '1';
                setTimeout(() => { skeleton.style.display = 'none'; }, 400);
            }, 1200);
        });
