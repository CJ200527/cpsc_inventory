/* pr_logic.js — shared PR create/edit/view modal logic (Admin + Staff). Loaded after ui_helpers.js. */


        /* ===== CREATE PR — Master-Detail (Header + dynamic Line Items) ===== */
        function prNowStr() {
            const n = new Date();
            const p = x => String(x).padStart(2, '0');
            return `${n.getFullYear()}-${p(n.getMonth() + 1)}-${p(n.getDate())} ${p(n.getHours())}:${p(n.getMinutes())}:${p(n.getSeconds())}`;
        }
        function openAddModal() {
            document.getElementById('pr-items-body').innerHTML = '';
            // Locked header: live next PR number + exact current datetime (both readonly).
            const numEl = document.getElementById('pr-number-preview');
            numEl.value = '';
            numEl.placeholder = 'Loading...';
            fetch('/pr/get_next_number').then(r => r.json()).then(d => {
                if (d.pr_number) numEl.value = shortRefNum(d.pr_number);
                else numEl.placeholder = 'Auto-generated upon saving';
                syncFx21Labels('pr-form');
            }).catch(() => { numEl.placeholder = 'Auto-generated upon saving'; });
            const nowStr = prNowStr();
            document.getElementById('pr-date-requested').value = fmtPhDateTime(nowStr);
            document.getElementById('pr-date-requested-value').value = nowStr;
            syncFx21Labels('pr-form');
            addPrItemRow();
            updateGrandTotal();
            document.getElementById('add-modal').classList.remove('hidden');
        }
        function closeAddModal() { document.getElementById('add-modal').classList.add('hidden'); }

        /* Rich catalog store (replaces the native datalist). */
        let catalogProducts = [];

        /* Loads the Master Catalog once per page view for the rich picker. */
        async function loadCatalogProducts() {
            try {
                const res = await fetch('/products/api/list');
                const data = await res.json();
                catalogProducts = data.products || [];
            } catch (e) { /* picker is optional — manual entry always works */ }
        }
        document.addEventListener('DOMContentLoaded', loadCatalogProducts);

        function escHtml(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

        /* Filters the catalog by substring and renders the rich dropdown. */
        function showCatalogDropdown(input){
            const tr = input.closest('tr');
            const list = tr.querySelector('.custom-dropdown-list');
            if(!list) return;
            const q = input.value.trim().toLowerCase();
            // Alphabetical (case-insensitive) regardless of API/collation order.
            const hits = catalogProducts
                .filter(p => !q || (p.product_name || '').toLowerCase().includes(q))
                .sort((a, b) => String(a.product_name || '').localeCompare(String(b.product_name || ''), undefined, { sensitivity: 'base' }))
                .slice(0, 50);
            if(hits.length === 0){
                list.innerHTML = `<div class="custom-dropdown-empty">No match found. This will be saved as a new draft product.</div>`;
            } else {
                list.innerHTML = hits.map(p => {
                    const specs = [p.category, p.size, p.unit, p.details].filter(Boolean).join(' | ');
                    return `<div class="custom-dropdown-item" data-pi="${catalogProducts.indexOf(p)}" onmousedown="selectCatalogItem(this)">`
                        + `<span class="cd-text"><span class="cd-name">${escHtml(p.product_name)}</span>`
                        + `<span class="cd-specs">${escHtml(specs) || '&nbsp;'}</span></span>`
                        + `<span class="cd-price">₱ ${Number(p.price || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span></div>`;
                }).join('');
            }
            list.classList.remove('hidden');
        }
        function hideCatalogDropdown(input){
            const tr = input.closest('tr');
            const list = tr.querySelector('.custom-dropdown-list');
            if(list) setTimeout(() => list.classList.add('hidden'), 150);
        }
        /* Duplicate guard: normalized composite key mirrors the backend
           _resolve_product_id identity (name+category+unit+size+details).
           Blank names return null (required-field validation owns them). */
        function prRowKey(tr){
            const pick = sel => { const el = tr.querySelector(sel); return el ? (el.value || '').trim() : ''; };
            const name = pick('input[name="item_name[]"]').toLowerCase();
            if(!name) return null;
            const cat = (pick('select[name="category[]"]') || 'General').toLowerCase();
            const unit = (pick('input[name="unit[]"]') || 'pcs').toLowerCase();
            const size = (pick('input[name="size[]"]') || 'N/A').toLowerCase();
            const det = pick('input[name="details[]"]').toLowerCase();
            return [name, cat, unit, size, det].join('‖');
        }
        function findDuplicatePrRow(tbodyId, selfTr){
            const key = prRowKey(selfTr);
            if(!key) return null;
            const rows = document.querySelectorAll('#' + tbodyId + ' .pr-item-row');
            for(const tr of rows){
                if(tr === selfTr) continue;
                if(prRowKey(tr) === key) return tr;
            }
            return null;
        }
        /* Duplicate warning modal (replaces native alert()). Custom message
           supported for the submit-time gate; otherwise the default body text
           already rendered in #duplicateItemMessage is shown. */
        const DEFAULT_DUP_MSG = 'This product is already in your request. Please adjust the quantity of the existing item instead.';
        function showDuplicateItemModal(message){
            const msgEl = document.getElementById('duplicateItemMessage');
            const modal = document.getElementById('duplicateItemModal');
            if(msgEl) msgEl.textContent = message || DEFAULT_DUP_MSG;
            if(modal) modal.classList.remove('hidden');
        }
        function closeDuplicateItemModal(){
            const modal = document.getElementById('duplicateItemModal');
            if(modal) modal.classList.add('hidden');
        }
        document.addEventListener('DOMContentLoaded', function(){
            const btn = document.getElementById('duplicateItemConfirm');
            if(btn) btn.addEventListener('click', closeDuplicateItemModal);
        });
        /* Explicit rich pick: overwrite specs from catalog, then smart-lock. */
        function selectCatalogItem(el){
            const p = catalogProducts[parseInt(el.dataset.pi, 10)];
            const tr = el.closest('tr');
            const list = tr.querySelector('.custom-dropdown-list');
            if(list) list.classList.add('hidden');
            if(!p) return;
            // Abort before mutating: the picked product is already listed.
            const pickedKey = [p.product_name || '', p.category || 'General', p.unit || 'pcs', p.size || 'N/A', p.details || '']
                .map(s => String(s).trim().toLowerCase()).join('‖');
            const tb = tr.closest('tbody');
            if(tb){
                for(const other of tb.querySelectorAll('.pr-item-row')){
                    if(other !== tr && prRowKey(other) === pickedKey){ showDuplicateItemModal(); return; }
                }
            }
            const input = tr.querySelector('input[name="item_name[]"]');
            input.value = p.product_name;
            tr.dataset.lastMatch = p.product_name;
            if (p.category && PR_CATEGORIES.includes(p.category)) tr.querySelector('select[name="category[]"]').value = p.category;
            tr.querySelector('input[name="unit[]"]').value = p.unit || '';
            tr.querySelector('input[name="size[]"]').value = p.size || '';
            tr.querySelector('input[name="details[]"]').value = p.details || '';
            tr.querySelector('input[name="price[]"]').value = (p.price === undefined || p.price === null) ? '' : p.price;
            calcPrRowTotal(tr.querySelector('input[name="price[]"]'));
            lockRowSpecs(tr, p);
        }

        /* Strict PR categories (also used by the future Return module). */
        const PR_CATEGORIES = ['Consumables', 'Tools', 'Equipment'];

        /* Exact catalog lookup for a typed item name (null = brand-new product).
           Case-insensitive: "bond paper" matches "Bond Paper" and locks it. */
        function matchCatalog(name) {
            if (!name) return null;
            const key = name.trim().toLowerCase();
            return catalogProducts.find(p => (p.product_name || '').toLowerCase() === key) || null;
        }

        /* Strict lock: ANY existing product picked from the dropdown (draft
           or established) instantly locks Category (HARD-disabled) plus
           Unit/Specification (readonly) — pr_items can never desync from
           products. Fields unlock only when the name is cleared for a
           brand-new typed item. PRICE and QTY ALWAYS STAY EDITABLE.
           Draft/new specs stay editable so typos can be fixed. */
        function lockRowSpecs(tr, match) {
            const catSel = tr.querySelector('select[name="category[]"]');
            const fields = ['unit[]', 'size[]', 'details[]']
                .map(n => tr.querySelector(`input[name="${n}"]`));
            const locked = !!match;
            fields.forEach(el => {
                el.readOnly = locked;
                el.style.backgroundColor = locked ? '#e9ecef' : '';
            });
            // Disabled selects cannot be touched at all (stronger than snap-back).
            // Values are restored to the POST payload by unlockCategoriesFor()
            // right before submit, since disabled fields are never submitted.
            catSel.disabled = locked;
            catSel.style.backgroundColor = locked ? '#e9ecef' : '';
            catSel.title = locked ? 'Category is locked: this is an established catalog product.' : '';
        }

        /* Failsafe: re-enable every Category select inside a form so its value
           is included when FormData is built (disabled fields are skipped). */
        function unlockCategoriesFor(formId) {
            document.querySelectorAll('#' + formId + ' select[name="category[]"]').forEach(sel => {
                sel.disabled = false;
            });
        }

        /* Item-name typing: match → backfill untouched fields + smart-lock;
           no match → clear stale catalog specs + unlock for a new product.
           The rich dropdown filters live on every keystroke. */
        function onPrItemNameInput(input) {
            const tr = input.closest('tr');
            const v = input.value.trim();
            const match = matchCatalog(v);
            const unitEl = tr.querySelector('input[name="unit[]"]');
            const sizeEl = tr.querySelector('input[name="size[]"]');
            const detEl = tr.querySelector('input[name="details[]"]');
            const priceEl = tr.querySelector('input[name="price[]"]');
            const catSel = tr.querySelector('select[name="category[]"]');
            if (!match) {
                // Only wipe specs when leaving a previously matched product;
                // otherwise preserve what the user already typed.
                if (tr.dataset.lastMatch) {
                    unitEl.value = ''; sizeEl.value = ''; detEl.value = ''; priceEl.value = '';
                    catSel.value = 'Consumables';
                    delete tr.dataset.lastMatch;
                    calcPrRowTotal(priceEl);
                }
                delete tr.dataset.dupWarned;
                lockRowSpecs(tr, null);
                hideCatalogDropdown(input);
                return;
            }
            tr.dataset.lastMatch = v;
            const untouched = [unitEl.value, sizeEl.value, detEl.value].every(s => (s || '').trim() === '')
                && (priceEl.value.trim() === '' || parseFloat(priceEl.value) === 0);
            if (untouched) {
                if (match.category && PR_CATEGORIES.includes(match.category)) catSel.value = match.category;
                unitEl.value = match.unit || '';
                sizeEl.value = match.size || '';
                detEl.value = match.details || '';
                priceEl.value = (match.price === undefined || match.price === null) ? '' : match.price;
                formatPriceInput(priceEl);
            }
            lockRowSpecs(tr, match);
            showCatalogDropdown(input);
            // Typed-name path: warn once per matched name if it duplicates a sibling row.
            const tb = tr.closest('tbody');
            if(tb && findDuplicatePrRow(tb.id, tr)){
                if(tr.dataset.dupWarned !== v.toLowerCase()){
                    tr.dataset.dupWarned = v.toLowerCase();
                    showDuplicateItemModal();
                }
            } else if(tr.dataset.dupWarned && tr.dataset.dupWarned !== v.toLowerCase()){
                delete tr.dataset.dupWarned;
            }
        }

        /* Builds one line-item row into the given tbody (optional prefill for Pending-edit). */
        function escAttr(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/"/g, '&quot;'); }
        function buildPrRow(tbodyId, item) {
            const tbody = document.getElementById(tbodyId);
            const tr = document.createElement('tr');
            tr.className = 'pr-item-row';
            const it = item || {};
            const cat = it.category || 'Consumables';
            const catOpts = PR_CATEGORIES.map(c => `<option value="${c}"${c === cat ? ' selected' : ''}>${c}</option>`).join('');
            const priceNum = (it.price === undefined || it.price === null || it.price === '') ? null : Number(String(it.price).replace(/,/g, ''));
            const priceVal = (priceNum === null || isNaN(priceNum)) ? '' : priceNum.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            tr.innerHTML = `
                <td><div class="custom-dropdown-wrap fx21-field"><input type="text" name="item_name[]" class="effect-21" placeholder="Select or type new item" required autocomplete="off" value="${escAttr(it.name || '')}" oninput="onPrItemNameInput(this)" onfocus="showCatalogDropdown(this)" onblur="hideCatalogDropdown(this)"><span class="focus-border"><i></i></span><div class="custom-dropdown-list hidden"></div></div></td>
                <td><div class="fx21-field"><select name="category[]" class="effect-21" required>${catOpts}</select><span class="focus-border"><i></i></span></div></td>
                <td><div class="fx21-field"><input type="text" name="unit[]" class="effect-21" placeholder="pcs" autocomplete="off" list="unit-options" value="${escAttr(it.unit || '')}"><span class="focus-border"><i></i></span></div></td>
                <td><div class="fx21-field"><input type="text" name="size[]" class="effect-21" placeholder="Size" autocomplete="off" value="${escAttr(it.size || '')}"><span class="focus-border"><i></i></span></div></td>
                <td><div class="fx21-field"><input type="text" name="details[]" class="effect-21" placeholder="Specification" autocomplete="off" value="${escAttr(it.details || '')}"><span class="focus-border"><i></i></span></div></td>
                <td><div class="fx21-field"><input type="text" name="price[]" class="effect-21" inputmode="decimal" placeholder="0.00" required value="${priceVal}" oninput="formatPriceInput(this)" onblur="finishPriceInput(this)"><span class="focus-border"><i></i></span></div></td>
                <td><div class="fx21-field"><input type="number" name="quantity[]" class="effect-21" value="${it.quantity || 1}" min="1" step="1" required oninput="calcPrRowTotal(this)"><span class="focus-border"><i></i></span></div></td>
                <td><input type="text" class="pr-row-total" value="0.00" readonly tabindex="-1"></td>
                <td><button type="button" class="btn-remove-row" onclick="removePrRow(this)"><span class="act-icon act-x" aria-hidden="true"></span></button>
            `;
            tbody.appendChild(tr);
            calcPrRowTotal(tr.querySelector('input[name="price[]"]'));
        }
        /* Appends a blank line-item row: rich product picker + strict category select (JIT creation). */
        function addPrItemRow() { buildPrRow('pr-items-body', null); }
        /* Appends a pre-filled row inside the Pending-edit modal. */
        function addPrEditRow(item) { buildPrRow('pr-edit-items-body', item || null); }

        /* Live pesos formatting: thousand separators while typing, exactly
           2 decimals on blur. All readers strip commas before parseFloat. */
        function formatPriceInput(input){
            const raw=(input.value||'').replace(/,/g,'');
            if(raw.trim()===''){ calcPrRowTotal(input); return; }
            const parts=raw.split('.');
            if(parts.length>2){ input.value=raw.slice(0,-1); calcPrRowTotal(input); return; }
            let intPart=(parts[0]||'').replace(/[^0-9]/g,'').replace(/^0+(?=\d)/,'');
            if(intPart==='') intPart='0';
            let out=Number(intPart).toLocaleString('en-US');
            if(raw.indexOf('.')!==-1){ out+='.'+(parts[1]||'').replace(/[^0-9]/g,'').slice(0,2); }
            if(input.value!==out) input.value=out;
            calcPrRowTotal(input);
        }
        function finishPriceInput(input){
            const raw=(input.value||'').replace(/,/g,'').trim();
            if(raw==='') return;
            const n=parseFloat(raw);
            if(isNaN(n)) return;
            input.value=n.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
            calcPrRowTotal(input);
        }
        /* Auto-calculates the row total (Price x Quantity) on every keystroke. */
        function editIdsFor(input) {
            const tb = input.closest('tbody');
            return (tb && tb.id === 'pr-edit-items-body')
                ? { tbody: 'pr-edit-items-body', total: 'pr-edit-grand-total' }
                : { tbody: 'pr-items-body', total: 'pr-grand-total' };
        }
        function calcPrRowTotal(input) {
            const tr = input.closest('tr');
            const price = parseFloat((tr.querySelector('input[name="price[]"]').value || '').replace(/,/g, '')) || 0;
            const qty = parseInt(tr.querySelector('input[name="quantity[]"]').value) || 0;
            tr.querySelector('.pr-row-total').value = (price * qty).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            const ids = editIdsFor(input);
            updateGrandTotalFor(ids.tbody, ids.total);
        }

        /* Sums every row total and updates the footer grand-total readout in real time. */
        function updateGrandTotalFor(tbodyId, totalId) {
            let grand = 0;
            document.querySelectorAll('#' + tbodyId + ' .pr-row-total').forEach(el => {
                grand += parseFloat(el.value.replace(/,/g, '')) || 0;
            });
            const totalEl = document.getElementById(totalId);
            if (!totalEl) return;
            const txt = '₱ ' + grand.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            if (totalEl.tagName === 'INPUT') totalEl.value = txt;
            else totalEl.textContent = txt;
        }
        function updateGrandTotal() { updateGrandTotalFor('pr-items-body', 'pr-grand-total'); }

        function removePrRow(btn) {
            const ids = editIdsFor(btn);
            btn.closest('tr').remove();
            updateGrandTotalFor(ids.tbody, ids.total);
        }

        /* Shared row validation for create + Pending-edit submits. */
        function validatePrRows(tbodyId) {
            const rows = document.querySelectorAll('#' + tbodyId + ' .pr-item-row');
            if (rows.length === 0) { alert('Please add at least one item.'); return false; }
            const seen = {};
            for (const [idx, tr] of [...rows].entries()) {
                const name = tr.querySelector('input[name="item_name[]"]').value.trim();
                const price = parseFloat((tr.querySelector('input[name="price[]"]').value || '').replace(/,/g, ''));
                const qty = parseInt(tr.querySelector('input[name="quantity[]"]').value);
                if (!name) { alert(`Row ${idx + 1}: Item Name is required.`); return false; }
                if (isNaN(price) || price < 0) { alert(`Row ${idx + 1}: Price must be 0 or more.`); return false; }
                if (isNaN(qty) || qty < 1) { alert(`Row ${idx + 1}: Quantity must be at least 1.`); return false; }
                // Final gate: no two rows may resolve to the same product.
                const key = prRowKey(tr);
                if (key) {
                    if (seen[key] !== undefined) { showDuplicateItemModal(`Rows ${seen[key] + 1} and ${idx + 1}: ${DEFAULT_DUP_MSG}`); return false; }
                    seen[key] = idx;
                }
            }
            return true;
        }

        /* Collects Header + Item array and submits via Fetch to the PR creation route. */
        async function submitPrForm(e) {
            e.preventDefault();
            if (!validatePrRows('pr-items-body')) return false;
            unlockCategoriesFor('pr-form');
            // Strip display commas — backend float() takes clean decimals.
            document.querySelectorAll('#pr-items-body input[name="price[]"]').forEach(inp => { inp.value = (inp.value || '').replace(/,/g, ''); });
            const btn = document.getElementById('pr-submit-btn');
            btn.disabled = true;
            const orig = btn.innerHTML;
            btn.innerHTML = '⏳ Submitting...';
            try {
                // /pr/add follows the app flash + redirect pattern; reload to display the result.
                await fetch('/pr/add', { method: 'POST', body: new FormData(document.getElementById('pr-form')) });
                window.location.href = '/pr';
            } catch (err) {
                alert('Submit failed (network error). Your entries are kept — please try again.');
                btn.disabled = false;
                btn.innerHTML = orig;
            }
            return false;
        }

        /* ===== PENDING-EDIT: prefill the edit modal (Approved PRs stay locked) ===== */
        let editingPrId = null;
        async function openEditPrModal(prId) {
            editingPrId = prId;
            const tbody = document.getElementById('pr-edit-items-body');
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:12px;color:#888;">Loading PR...</td></tr>';
            document.getElementById('edit-modal').classList.remove('hidden');
            try {
                const res = await fetch('/pr/details/' + prId);
                const data = await res.json();
                if (data.error) { tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;color:#c62828;">${data.error}</td></tr>`; return; }
                if (data.header.status !== 'Pending') {
                    alert(`PR ${data.header.pr_number} is '${data.header.status}' and locked as an immutable record. Only Pending PRs can be edited.`);
                    closeEditPrModal();
                    return;
                }
                document.getElementById('edit-pr-number').value = shortRefNum(data.header.pr_number) || '';
                document.getElementById('edit-fund-source').value = data.header.fund_source || 'Fund 05';
                document.getElementById('edit-date-requested').value = fmtPhDateTime(data.header.date_requested);
                document.getElementById('edit-date-requested-value').value = data.header.date_requested || '';
                syncFx21Labels('pr-edit-form');
                tbody.innerHTML = '';
                (data.items || []).forEach(it => addPrEditRow({
                    name: it.item_name, category: it.category, unit: it.unit,
                    size: it.size, details: it.details, price: it.price,
                    quantity: it.quantity
                }));
                if (!data.items || !data.items.length) addPrEditRow(null);
                // Same smart-lock check as typing: established specs lock, drafts stay open.
                tbody.querySelectorAll('.pr-item-row').forEach(tr => {
                    const nm = tr.querySelector('input[name="item_name[]"]').value.trim();
                    const m = matchCatalog(nm);
                    if (m) tr.dataset.lastMatch = nm;
                    lockRowSpecs(tr, m);
                });
                updateGrandTotalFor('pr-edit-items-body', 'pr-edit-grand-total');
            } catch (err) {
                tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:#c62828;">Failed to load PR.</td></tr>';
            }
        }
        function closeEditPrModal() {
            document.getElementById('edit-modal').classList.add('hidden');
            editingPrId = null;
        }
        async function submitPrEditForm(e) {
            e.preventDefault();
            if (!editingPrId) return false;
            if (!validatePrRows('pr-edit-items-body')) return false;
            unlockCategoriesFor('pr-edit-form');
            // Strip display commas — backend float() takes clean decimals.
            document.querySelectorAll('#pr-edit-items-body input[name="price[]"]').forEach(inp => { inp.value = (inp.value || '').replace(/,/g, ''); });
            const btn = document.getElementById('pr-edit-submit-btn');
            btn.disabled = true;
            const orig = btn.innerHTML;
            btn.innerHTML = '⏳ Saving...';
            try {
                await fetch('/pr/update/' + editingPrId, { method: 'POST', body: new FormData(document.getElementById('pr-edit-form')) });
                window.location.href = '/pr';
            } catch (err) {
                alert('Save failed (network error). Your entries are kept — please try again.');
                btn.disabled = false;
                btn.innerHTML = orig;
            }
            return false;
        }

        function fmtPeso(n){ return Number(n||0).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2}); }
        /* Display twins of the ph_datetime / short_pr Jinja filters for modal
           chrome (numbers/dates shown short; machine values stay in hidden
           inputs so POST payloads never change shape). */
        function fmtPhDateTime(s){
            if(!s) return '—';
            const m=String(s).trim().match(/^(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?/);
            if(!m) return String(s);
            const months=['January','February','March','April','May','June','July','August','September','October','November','December'];
            const mo=parseInt(m[2],10);
            if(mo<1||mo>12) return String(s);
            let h=parseInt(m[4]||'0',10);
            const ap=h>=12?'PM':'AM'; h=h%12||12;
            return `${months[mo-1]} ${parseInt(m[3],10)}, ${m[1]} | ${h}:${m[5]||'00'} ${ap}`;
        }
        /* effect-21: float the label of every filled header field. */
        function syncFx21Labels(formId){
            document.querySelectorAll('#' + formId + ' .effect-21').forEach(inp => {
                inp.classList.toggle('has-content', (inp.value || '').trim() !== '');
            });
        }
        function shortRefNum(s){
            s=String(s||'');
            if(s.indexOf('-')===-1) return s;
            const parts=s.split('-');
            const tail=(parts.pop()||'').trim();
            const head=(parts[0]||'').trim();
            if(!tail||!head) return s;
            return head+'-'+tail;
        }

        function openViewModal(prId) {
            const content = document.getElementById('view-modal-content');
            content.innerHTML = 'Loading PR items...';
            document.getElementById('view-modal').classList.remove('hidden');

            fetch('/pr/details/' + prId)
                .then(res => res.json())
                .then(data => {
                    if (data.error) { content.innerHTML = data.error; return; }
                    document.getElementById('view-pr-number').innerText = shortRefNum(data.header.pr_number) + " Details";
                    /* Master header (read-only) */
                    let html = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;background:#f8fcff;border:1px solid #e2f0fb;border-radius:8px;padding:12px;margin-bottom:12px;">`;
                    html += `<div><strong>PR Number:</strong> ${shortRefNum(data.header.pr_number)}</div>`;
                    html += `<div><strong>Fund Source:</strong> ${data.header.fund_source || 'Fund 05'}</div>`;
                    html += `<div><strong>Date Requested:</strong> ${fmtPhDateTime(data.header.date_requested)}</div>`;
                    html += `<div><strong>Total Price:</strong> <span class="price-badge">₱ ${fmtPeso(data.header.total_price)}</span></div>`;
                    html += `<div><strong>Requested By:</strong> ${data.header.Firstname} ${data.header.Lastname} (${data.header.username})</div>`;
                    html += `<div><strong>Status:</strong> <span class="badge badge-${(data.header.status || '').toLowerCase()}">${data.header.status}</span></div>`;
                    html += `</div>`;
                    /* Detail: full line-items table */
                    html += `<table class="item-table"><thead><tr><th>Item Name</th><th>Category</th><th>Unit</th><th>Specification</th><th>Size</th><th>Price (₱)</th><th>Qty</th><th>Total (₱)</th></tr></thead><tbody>`;
                    data.items.forEach(i => {
                        html += `<tr><td><strong>${i.item_name}</strong></td><td>${i.category || '-'}</td><td>${i.unit || '-'}</td><td>${i.details || '-'}</td><td>${i.size || '-'}</td><td>₱ ${fmtPeso(i.price)}</td><td>${i.quantity}</td><td>₱ ${fmtPeso(i.total_price)}</td></tr>`;
                    });
                    html += `</tbody></table>`;
                    content.innerHTML = html;
                });
        }
        function closeViewModal() { document.getElementById('view-modal').classList.add('hidden'); }
    