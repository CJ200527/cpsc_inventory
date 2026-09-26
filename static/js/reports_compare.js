/* reports_compare.js — merged PR-vs-IAR compare selection (admin + staff).
   --------------------------------------------------------------------------
   Same merge pattern as pr_logic.js: checkboxes on the comparative ledger +
   a counter button that unlocks at 2+ selections. The button carries its
   destination in data-href-base, so one file serves both report pages with
   zero per-page code. Native GET navigation (bookmarkable ?ids= URLs);
   crafted ids are guarded server-side with skipped-with-flash.
   -------------------------------------------------------------------------- */

(function () {
    function setBtn(btn, label, base, ids) {
        if (!btn) return;
        btn.textContent = label + ' (' + ids.length + ')';
        if (ids.length >= 2) {
            btn.href = base + '?ids=' + ids.join(',');
            btn.classList.remove('is-disabled');
        } else {
            btn.href = '#';
            btn.classList.add('is-disabled');
        }
    }
    function refreshCompareBtn() {
        var ids = Array.prototype.map.call(
            document.querySelectorAll('.merge-check:checked'),
            function (c) { return c.value; });
        var cmp = document.getElementById('compare-btn');
        if (cmp) setBtn(cmp, 'Compare Selected', cmp.getAttribute('data-href-base') || '#', ids);
        var prt = document.getElementById('compare-print-btn');
        if (prt) setBtn(prt, '\ud83d\udda8 Print Compared', prt.getAttribute('data-href-base') || '#', ids);
    }
    document.addEventListener('change', function (e) {
        if (e.target && e.target.id === 'merge-check-all') {
            document.querySelectorAll('.merge-check').forEach(function (c) { c.checked = e.target.checked; });
            refreshCompareBtn();
        } else if (e.target && e.target.classList && e.target.classList.contains('merge-check')) {
            var all = document.querySelectorAll('.merge-check');
            var checked = document.querySelectorAll('.merge-check:checked');
            var head = document.getElementById('merge-check-all');
            if (head) head.checked = all.length > 0 && checked.length === all.length;
            refreshCompareBtn();
        }
    });
    document.addEventListener('DOMContentLoaded', refreshCompareBtn);
    refreshCompareBtn();
})();
