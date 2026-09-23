/* filter-panel.js — anchored filter card behavior (all lists).
   --------------------------------------------------------------------------
   Groupmate-proven recipe in our theme: each `.filter-wrap` holds a funnel
   `.filter-btn` and an absolutely-anchored `.filter-panel` toggled by the
   `.open` class. The panel carries its own GET form (same endpoint, same
   param names as the page filters), so Apply is a native submit and Reset
   is a plain link. Buttons speak the decision-modal language
   (btn-modal-save btn-confirm-go / btn-modal-cancel); no coordinates,
   no fixed layers, no scroll/resize handlers.
   -------------------------------------------------------------------------- */

(function () {
    function closeAll(except) {
        document.querySelectorAll('.filter-panel.open').forEach(function (p) {
            if (p === except) return;
            p.classList.remove('open');
            var wrap = p.closest('.filter-wrap');
            var btn = wrap ? wrap.querySelector('.filter-btn') : null;
            if (btn) { btn.classList.remove('open'); btn.setAttribute('aria-expanded', 'false'); }
        });
    }
    function bind() {
        document.querySelectorAll('.filter-wrap').forEach(function (wrap) {
            if (wrap.hasAttribute('data-panel-bound')) return;
            wrap.setAttribute('data-panel-bound', '1');
            var btn = wrap.querySelector('.filter-btn');
            var pop = wrap.querySelector('.filter-panel');
            if (btn && pop) {
                btn.addEventListener('click', function (e) {
                    e.stopPropagation();
                    var open = pop.classList.toggle('open');
                    btn.classList.toggle('open', open);
                    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
                });
            }
            var cancel = wrap.querySelector('[data-filter-cancel]');
            if (cancel) {
                cancel.addEventListener('click', function () { closeAll(null); });
            }
        });
    }
    function closeNotifs(except) {
        document.querySelectorAll('.notif-panel.open').forEach(function (p) {
            if (p === except) return;
            p.classList.remove('open');
            var wrap = p.closest('.notif-wrap');
            var btn = wrap ? wrap.querySelector('.notif-bell') : null;
            if (btn) { btn.classList.remove('open'); btn.setAttribute('aria-expanded', 'false'); }
        });
    }
    document.addEventListener('click', function (e) {
        var pop = e.target.closest ? e.target.closest('.filter-panel') : null;
        if (pop) return;
        closeAll(null);
        var npop = e.target.closest ? e.target.closest('.notif-panel') : null;
        if (npop) return;
        closeNotifs(null);
    });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') { closeAll(null); closeNotifs(null); }
    });
    document.addEventListener('DOMContentLoaded', bind);
    bind();
    // Notification bell toggles (same open/outside/Escape contract).
    // Bound here (not inline) with stopPropagation, so the document
    // closer below can never double-toggle the just-opened panel.
    function toggleNotif(btn) {
        var wrap = btn.closest('.notif-wrap');
        if (!wrap) return;
        var pop = wrap.querySelector('.notif-panel');
        if (!pop) return;
        var willOpen = !pop.classList.contains('open');
        closeAll(null);
        closeNotifs(wrap);
        pop.classList.toggle('open', willOpen);
        btn.classList.toggle('open', willOpen);
        btn.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
    }
    function bindNotifs() {
        document.querySelectorAll('.notif-wrap').forEach(function (wrap) {
            if (wrap.hasAttribute('data-notif-bound')) return;
            wrap.setAttribute('data-notif-bound', '1');
            var btn = wrap.querySelector('.notif-bell');
            if (btn) {
                btn.addEventListener('click', function (e) {
                    e.stopPropagation();
                    toggleNotif(btn);
                });
            }
        });
    }
    document.addEventListener('DOMContentLoaded', bindNotifs);
    bindNotifs();
    window.toggleNotif = toggleNotif;
})();
