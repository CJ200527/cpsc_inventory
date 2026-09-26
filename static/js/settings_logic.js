/* settings_logic.js — System Settings behaviours.
   1. Hide-until-dirty save bar: stays hidden until a textbox differs from its
      server-rendered defaultValue. Cancel discards edits (form.reset) and
      re-hides the bar. Native submit preserved (flash-safe); no fetch.
   2. Global cascade: typing in Global Default mirrors the value live into the
      three category boxes, so what you see is what the system will enforce
      (category values always win over Global at read time, so the mirror
      makes Global visibly authoritative). Editing a single category box
      afterwards diverges only that category. */
(function () {
    var GLOBAL_ID = 'set-default_reorder_level';
    var CATEGORY_IDS = [
        'set-cat_reorder_consumables',
        'set-cat_reorder_tools',
        'set-cat_reorder_equipment'
    ];
    function init() {
        var form = document.getElementById('settings-form');
        var bar = document.getElementById('settings-save-bar');
        var cancel = document.getElementById('settings-cancel');
        if (!form || !bar) return;
        var fields = Array.prototype.slice.call(form.querySelectorAll('input.effect-21'));
        var globalInput = document.getElementById(GLOBAL_ID);
        var categoryInputs = CATEGORY_IDS.map(function (id) {
            return document.getElementById(id);
        }).filter(function (el) { return !!el; });
        function refresh() {
            var dirty = fields.some(function (el) { return el.value !== el.defaultValue; });
            bar.classList.toggle('show', dirty);
        }
        // Programmatic .value sets below never fire 'input', so no mirror loop.
        if (globalInput && categoryInputs.length) {
            globalInput.addEventListener('input', function () {
                categoryInputs.forEach(function (el) { el.value = globalInput.value; });
                refresh();
            });
        }
        fields.forEach(function (el) {
            el.addEventListener('input', refresh);
            el.addEventListener('change', refresh);
        });
        if (cancel) {
            cancel.addEventListener('click', function (ev) {
                // Let plain clicks without edits still navigate away; when dirty,
                // discard edits in place instead of leaving the page.
                var dirty = fields.some(function (el) { return el.value !== el.defaultValue; });
                if (!dirty) return; // follow href to dashboard
                ev.preventDefault();
                form.reset();
                refresh();
            });
        }
        form.addEventListener('reset', function () {
            setTimeout(refresh, 0);
        });
        refresh();
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
