        /* delivery_logic.js — shared delivery receive/complete/view logic (Admin + Staff). Loaded after ui_helpers.js. */
        /* Stale-guard cleanup: a freshly loaded page has no submission in flight
           from it. Keys left behind by a refresh/cancel during "Processing"
           would otherwise ghost-block every later Confirm click forever. */
        try {
            Object.keys(sessionStorage).forEach(k=>{ if(k.indexOf('approving_')===0) sessionStorage.removeItem(k); });
        } catch (e) {}

        function fmtPeso(n){ return '₱ ' + Number(n||0).toLocaleString('en-US',{minimumFractionDigits:2, maximumFractionDigits:2}); }
        /* Live totals: any unit-price or quantity edit recalculates its row
           total and the modal footer grand total. Blank price falls back to
           the PR-estimated price stored in data-est-price (server mirrors it). */
        function recalcDeliveryTbody(tbodyId, totalId){
            const tbody=document.getElementById(tbodyId);
            const tot=document.getElementById(totalId);
            if(!tbody) return;
            let grand=0;
            tbody.querySelectorAll('tr').forEach(tr=>{
                const p=tr.querySelector('input.delivery-unit-price');
                const q=tr.querySelector('input[name="received_quantity[]"]');
                if(!p||!q) return;
                const raw=(p.value||'').trim();
                let price=raw==='' ? parseFloat(p.dataset.estPrice||0) : parseFloat(raw);
                if(isNaN(price)||price<0) price=0;
                let qty=parseInt(q.value||0);
                if(isNaN(qty)||qty<0) qty=0;
                const lineTotal=price*qty;
                grand+=lineTotal;
                const cell=tr.querySelector('.delivery-row-total');
                if(cell) cell.innerText=fmtPeso(lineTotal);
            });
            if(tot) tot.innerText=fmtPeso(grand);
        }
        function todayLocal(){ const n=new Date(); const p=x=>String(x).padStart(2,'0'); return `${n.getFullYear()}-${p(n.getMonth()+1)}-${p(n.getDate())}`; }
        /* Delivery Date guard: past/present only — future dates blocked (backend double-checks). */
        function validateDeliveryDate(input){
            if(!input) return true;
            if(!input.max) input.max=todayLocal();
            if(input.value && input.value > todayLocal()){ alert('Delivery Date cannot be in the future.'); input.focus(); return false; }
            return true;
        }

        function openReceiveModal(){
            document.getElementById('receive-modal').classList.remove('hidden');
            const d=document.querySelector('#receive-modal input[name="delivery_date"]'); if(d && !d.value) d.valueAsDate=new Date(); if(d && !d.max) d.max=todayLocal();
            // Auto-generated delivery number (readonly) + reset PR total.
            const numEl=document.getElementById('delivery-number-auto');
            if(numEl){ numEl.value=''; numEl.placeholder='Loading...'; }
            fetch('/delivery/get_next_number').then(r=>r.json()).then(dt=>{
                if(numEl){ if(dt.delivery_number) numEl.value=dt.delivery_number; else numEl.placeholder='Auto-generated'; }
            }).catch(()=>{ if(numEl) numEl.placeholder='Auto-generated'; });
            const tot=document.getElementById('delivery-total-price'); if(tot) tot.innerText='₱ 0.00';
            // Auto-generated IAR number (readonly), same pattern as delivery number.
            const iarEl=document.querySelector('#receive-form input[name="iar_number"]');
            if(iarEl){ iarEl.value=''; iarEl.placeholder='Loading...'; }
            fetch('/delivery/get_next_iar').then(r=>r.json()).then(dt=>{
                if(iarEl){ if(dt.iar_number) iarEl.value=dt.iar_number; else iarEl.placeholder='Auto-generated'; }
            }).catch(()=>{ if(iarEl) iarEl.placeholder='Auto-generated'; });
            const sInput=document.getElementById('pr-smart-search'); if(sInput) sInput.value='';
            const sHidden=document.getElementById('pr-id-hidden'); if(sHidden) sHidden.value='';
            const sList=document.getElementById('pr-dropdown-list'); if(sList){ sList.innerHTML=''; sList.classList.add('hidden'); }
            document.getElementById('receive-no-results').classList.add('hidden');
            const tbody=document.getElementById('delivery-items-tbody'); if(tbody) tbody.innerHTML='';
            // Section 2 stays visible: show the placeholder until a PR loads rows.
            const ph=document.getElementById('delivery-items-empty'); if(ph) ph.style.display='';
        }
        function closeReceiveModal(){ document.getElementById('receive-modal').classList.add('hidden'); }
        /* Smart PR dropdown: typable field filtering the hidden server-rendered options. */
        function prDropdownData(){
            const sel=document.getElementById('pr-select');
            if(!sel) return [];
            return [...sel.options].filter(o=>o.value).map(o=>({
                id:o.value, pr:o.dataset.pr||o.text, req:o.dataset.req||'',
                status:o.dataset.status||'', total:parseFloat(o.dataset.total||0)
            }));
        }
        function escHtml(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
        function renderPRDropdown(input, hits){
            const list=document.getElementById('pr-dropdown-list');
            if(!list) return;
            const noRes=document.getElementById('receive-no-results');
            if(hits.length===0){
                list.innerHTML=`<div class="custom-dropdown-empty">No matching PRs.</div>`;
                if(noRes) noRes.classList.remove('hidden');
            } else {
                if(noRes) noRes.classList.add('hidden');
                list.innerHTML=hits.map(p=>`<div class="custom-dropdown-item" data-pid="${p.id}" data-pr="${escHtml(p.pr)}" onmousedown="selectPRItem(this)">`
                    +`<span class="cd-text"><span class="cd-name">${escHtml(p.pr)}</span>`
                    +`<span class="cd-specs">${escHtml(p.req)}${p.status ? ' | ' + escHtml(p.status) : ''}</span></span>`
                    +`<span class="cd-price">₱ ${Number(p.total||0).toLocaleString('en-US',{minimumFractionDigits:2, maximumFractionDigits:2})}</span></div>`).join('');
            }
            list.classList.remove('hidden');
        }
        function filterPRDropdown(input){
            const q=input.value.trim().toLowerCase();
            renderPRDropdown(input, prDropdownData().filter(p=>!q||(p.pr+' '+p.req+' '+p.status).toLowerCase().includes(q)).slice(0,50));
        }
        function showPRDropdown(input){
            renderPRDropdown(input, prDropdownData().slice(0,50));
        }
        function hidePRDropdown(input){
            const list=document.getElementById('pr-dropdown-list');
            if(list) setTimeout(()=>list.classList.add('hidden'),150);
        }
        function selectPRItem(el){
            const list=document.getElementById('pr-dropdown-list');
            if(list) list.classList.add('hidden');
            const input=document.getElementById('pr-smart-search');
            const hidden=document.getElementById('pr-id-hidden');
            if(input) input.value=el.dataset.pr||'';
            if(hidden) hidden.value=el.dataset.pid||'';
            const noRes=document.getElementById('receive-no-results');
            if(noRes) noRes.classList.add('hidden');
            if(el.dataset.pid) loadPRForDelivery(el.dataset.pid);
        }
        function loadPRForDelivery(prId){
            if(!prId) return;
            const tbody=document.getElementById('delivery-items-tbody');
            const ph=document.getElementById('delivery-items-empty');
            tbody.innerHTML='<tr><td colspan="7" style="text-align:center;padding:12px;color:#888;">Loading PR items…</td></tr>';
            if(ph) ph.style.display='none';
            fetch('/pr/details/'+prId).then(r=>r.json()).then(data=>{
                if(data.error){ tbody.innerHTML='<tr><td colspan="7" style="text-align:center;color:#c62828;">'+escHtml(data.error)+'</td></tr>'; if(ph) ph.style.display=''; return; }
                tbody.innerHTML='';
                data.items.forEach(item=>{
                    const orderedQty = parseInt(item.quantity||0);
                    const unitPrice = Number(item.price||0);
                    const tr=document.createElement('tr');
                    tr.innerHTML=`
                        <td class="readonly-cell"><strong>${escHtml(item.item_name)}</strong><br><small>${escHtml(item.details||'')} ${item.size? '('+escHtml(item.size)+')':''}</small><input type="hidden" name="product_id[]" value="${item.product_id}"></td>
                        <td class="readonly-cell">${escHtml(item.category||'-')}</td>
                        <td class="readonly-cell">${escHtml(item.unit||'pcs')}</td>
                        <td><input type="number" name="unit_price[]" class="form-control delivery-unit-price" min="0" step="0.01" value="${unitPrice.toFixed(2)}" data-est-price="${unitPrice.toFixed(2)}" title="Actual invoice unit price — pre-filled with PR estimate, override as needed" oninput="recalcDeliveryTbody('delivery-items-tbody','delivery-total-price')"></td>
                        <td class="readonly-cell" style="font-weight:700;">${orderedQty}</td>
                        <td><input type="number" name="received_quantity[]" min="0" max="${orderedQty}" placeholder="0" style="width:90px;padding:6px;border:1.5px solid #53c5f1;border-radius:6px;background:#ffffff;" oninput="if(parseInt(this.value||0)>${orderedQty}){this.setCustomValidity('Exceeds ordered '+${orderedQty}); this.reportValidity();}else{this.setCustomValidity('');}recalcDeliveryTbody('delivery-items-tbody','delivery-total-price');"></td>
                        <td class="readonly-cell delivery-row-total" style="font-weight:700;">₱ 0.00</td>
                    `;
                    tbody.appendChild(tr);
                });
                // Sync footer to live-computed totals (starts at ₱ 0.00 until quantities are entered).
                recalcDeliveryTbody('delivery-items-tbody','delivery-total-price');
                if(!tbody.children.length && ph) ph.style.display='';
            }).catch(()=>{ tbody.innerHTML='<tr><td colspan="7" style="text-align:center;color:#c62828;">Failed to load PR items.</td></tr>'; });
        }
        function validateReceiveForm(){
            // A PR must be picked from the smart dropdown first.
            const prHidden=document.getElementById('pr-id-hidden');
            if(!prHidden || !prHidden.value){ alert('Please select an Approved PR.'); return false; }
            // Blank or 0 = zero arriving units for that row (partial shipment); both are valid.
            if(!validateDeliveryDate(document.querySelector('#receive-form input[name="delivery_date"]'))) return false;
            const inputs=document.querySelectorAll('#delivery-items-tbody input[name="received_quantity[]"]');
            let hasPositive=false, err='';
            inputs.forEach(inp=>{
                if(inp.value.trim()==='') inp.value='0';
                const n=parseInt(inp.value||0), mx=parseInt(inp.getAttribute('max')||0);
                if(isNaN(n)||n<0) err='Received quantity must be a whole number 0 or more.';
                else if(n>mx) err=`Received ${n} exceeds ordered ${mx}.`;
                if(n>0) hasPositive=true;
            });
            // Actual invoice prices: blank falls back to the PR estimate server-side.
            document.querySelectorAll('#delivery-items-tbody input.delivery-unit-price').forEach(inp=>{
                const raw=(inp.value||'').trim();
                if(raw!=='' && (isNaN(parseFloat(raw))||parseFloat(raw)<0)) err='Unit price must be 0 or more (or blank to keep the PR estimate).';
            });
            if(err){ alert(err); return false; }
            if(!hasPositive){ alert('Enter a quantity greater than 0 for at least one item.'); return false; }
            return true;
        }

        let currentCompleteDeliveryId=null;
        function openCompleteModal(deliveryId){
            currentCompleteDeliveryId=deliveryId;
            document.getElementById('complete-modal').classList.remove('hidden');
            const form=document.getElementById('complete-form'); form.action='/delivery/complete/'+deliveryId;
            const dateInput=form.querySelector('input[name="delivery_date"]'); if(dateInput) dateInput.valueAsDate=new Date(); if(dateInput && !dateInput.max) dateInput.max=todayLocal();
            // Auto-generated completion number (readonly) via the shared delivery sequence.
            const numEl=document.getElementById('complete-delivery-number-auto');
            if(numEl){ numEl.value=''; numEl.placeholder='Loading...'; }
            fetch('/delivery/get_next_number').then(r=>r.json()).then(dt=>{
                if(numEl){ if(dt.delivery_number) numEl.value=dt.delivery_number; else numEl.placeholder='Auto-generated'; }
            }).catch(()=>{ if(numEl) numEl.placeholder='Auto-generated'; });
            // Auto-generated IAR number (readonly), same endpoint as the Creation modal.
            const iarEl=document.getElementById('complete-iar-number-auto');
            if(iarEl){ iarEl.value=''; iarEl.placeholder='Loading...'; }
            fetch('/delivery/get_next_iar').then(r=>r.json()).then(dt=>{
                if(iarEl){ if(dt.iar_number) iarEl.value=dt.iar_number; else iarEl.placeholder='Auto-generated'; }
            }).catch(()=>{ if(iarEl) iarEl.placeholder='Auto-generated'; });
            document.getElementById('complete-items-tbody').innerHTML='<tr><td colspan="5" style="text-align:center;padding:12px;color:#888;">Loading remaining…</td></tr>';
            document.getElementById('complete-pr-meta').innerHTML='Loading…';
            const ctot0=document.getElementById('complete-total-price'); if(ctot0) ctot0.innerText='₱ 0.00';
            fetch('/delivery/details/'+deliveryId).then(r=>r.json()).then(d=>{
                if(d.error){ document.getElementById('complete-pr-meta').innerHTML=escHtml(d.error); return; }
                const prId=d.header.pr_id;
                const poRefInput=document.getElementById('complete-po-ref'); if(poRefInput) poRefInput.value=d.header.po_reference_number||'';
                const supInput=document.getElementById('complete-supplier'); if(supInput && !supInput.value) supInput.value=d.header.supplier_name||'';
                fetch('/delivery/remaining/'+prId).then(r=>r.json()).then(rem=>{
                    const header=rem.header;
                    const remaining=rem.remaining||[];
                    let meta=`<strong>PR:</strong> ${header? escHtml(header.pr_number):'?'} — <strong>Remaining total:</strong> ${remaining.reduce((a,b)=>a+(b.remaining_quantity||0),0)} units — <em style="color:#c62828;">You see REMAINING, not initial ordered.</em>`;
                    if(remaining.length===0) meta+=' — <span style="color:#c62828;">No remaining</span>';
                    document.getElementById('complete-pr-meta').innerHTML=meta;
                    const tbody=document.getElementById('complete-items-tbody');
                    tbody.innerHTML='';
                    if(remaining.length===0){ tbody.innerHTML='<tr><td colspan="5" style="text-align:center;color:#c62828;">Nothing remaining.</td></tr>'; return; }
                    remaining.forEach(rw=>{
                        if(rw.remaining_quantity<=0) return;
                        const estPrice=Number(rw.price||0);
                        const tr=document.createElement('tr');
                        tr.innerHTML=`<td class="readonly-cell"><strong>${escHtml(rw.item_name)}</strong><input type="hidden" name="product_id[]" value="${rw.product_id}"></td><td class="readonly-cell" style="font-weight:700;">${rw.remaining_quantity} <small style="color:#888;">/ ordered ${rw.ordered_quantity} (recv ${rw.total_received})</small></td><td><input type="number" name="unit_price[]" class="form-control delivery-unit-price" min="0" step="0.01" value="${estPrice.toFixed(2)}" data-est-price="${estPrice.toFixed(2)}" title="Actual batch unit price — pre-filled with PR estimate, override if this batch differs" oninput="recalcDeliveryTbody('complete-items-tbody','complete-total-price')"></td><td><input type="number" name="received_quantity[]" min="0" max="${rw.remaining_quantity}" placeholder="0" style="width:90px;padding:6px;border:1.5px solid #ef6c00;border-radius:6px;background:#ffffff;" oninput="if(parseInt(this.value||0)>${rw.remaining_quantity}){this.setCustomValidity('Exceeds remaining '+${rw.remaining_quantity}); this.reportValidity();}else{this.setCustomValidity('');}recalcDeliveryTbody('complete-items-tbody','complete-total-price');"></td><td class="readonly-cell delivery-row-total" style="font-weight:700;">₱ 0.00</td>`;
                        tbody.appendChild(tr);
                    });
                    // Sync footer to live-computed totals.
                    recalcDeliveryTbody('complete-items-tbody','complete-total-price');
                    if(tbody.children.length===0) tbody.innerHTML='<tr><td colspan="5" style="text-align:center;color:#888;">All fully delivered.</td></tr>';
                });
            });
        }
        function closeCompleteModal(){ document.getElementById('complete-modal').classList.add('hidden'); currentCompleteDeliveryId=null; }
        function validateCompleteForm(){
            // Blank or 0 = zero arriving units for that row (partial shipment); both are valid.
            if(!validateDeliveryDate(document.querySelector('#complete-form input[name="delivery_date"]'))) return false;
            const inputs=document.querySelectorAll('#complete-items-tbody input[name="received_quantity[]"]');
            let hasPositive=false, err='';
            inputs.forEach(inp=>{
                if(inp.value.trim()==='') inp.value='0';
                const n=parseInt(inp.value||0), mx=parseInt(inp.getAttribute('max')||0);
                if(isNaN(n)||n<0) err='Received quantity must be a whole number 0 or more.';
                else if(n>mx) err=`Received ${n} exceeds remaining ${mx}.`;
                if(n>0) hasPositive=true;
            });
            // Actual batch prices: blank falls back to the PR estimate server-side.
            document.querySelectorAll('#complete-items-tbody input.delivery-unit-price').forEach(inp=>{
                const raw=(inp.value||'').trim();
                if(raw!=='' && (isNaN(parseFloat(raw))||parseFloat(raw)<0)) err='Unit price must be 0 or more (or blank to keep the PR estimate).';
            });
            if(err){ alert(err); return false; }
            if(!hasPositive){ alert('Enter a quantity greater than 0 for at least one item.'); return false; }
            return true;
        }

        function openViewModal(deliveryId){
            const content=document.getElementById('view-modal-content');
            // Staff pages have no approve area — guard keeps shared logic safe there.
            const approveArea=document.getElementById('view-modal-approve-area');
            content.innerHTML='Loading...';
            if(approveArea){ approveArea.classList.add('hidden'); approveArea.innerHTML=''; }
            document.getElementById('view-modal').classList.remove('hidden');
            fetch('/delivery/details/'+deliveryId).then(r=>r.json()).then(data=>{
                if(data.error){ content.innerHTML='<span style="color:#c62828;">'+data.error+'</span>'; return; }
                document.getElementById('view-delivery-title').innerText=`${data.header.delivery_number} — ${data.header.iar_number||''}`;
                let html=`<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;background:#f8fcff;border:1px solid #e2f0fb;border-radius:8px;padding:12px;margin-bottom:12px;">`;
                html+=`<div><strong>PR:</strong> ${data.header.pr_number}</div><div><strong>PO Ref #:</strong> ${data.header.po_reference_number||'-'}</div><div><strong>Supplier:</strong> ${data.header.supplier_name||'N/A'}</div>`;
                html+=`<div><strong>IAR #:</strong> ${data.header.iar_number||'-'}</div><div><strong>Date:</strong> ${data.header.delivery_date}</div>`;
                html+=`<div><strong>Inspected By:</strong> ${data.header.inspected_by||'-'}</div><div><strong>Supply Officer:</strong> ${data.header.supply_officer||'-'}</div>`;
                html+=`<div><strong>Status:</strong> <span class="badge badge-${(data.header.status||'').toLowerCase()}">${data.header.status}</span></div><div><strong>Partial:</strong> ${data.header.is_partial? 'Yes (auto)':'No'}</div>`;
                if(data.header.remarks) html+=`<div style="grid-column:span 2;"><strong>Remarks:</strong> ${data.header.remarks}</div>`;
                html+=`</div>`;
                html+=`<table class="item-table"><thead><tr><th>Item</th><th>Ordered</th><th>Received</th><th>Price</th><th>Total</th></tr></thead><tbody>`;
                data.items.forEach(i=>{
                    const clr = i.received_quantity >= i.ordered_quantity ? '#2e7d32' : '#c62828';
                    html+=`<tr><td><strong>${i.item_name}</strong></td><td>${i.ordered_quantity}</td><td style="font-weight:700;color:${clr}">${i.received_quantity} / ${i.ordered_quantity}</td><td>₱ ${Number(i.price).toLocaleString('en-US',{minimumFractionDigits:2, maximumFractionDigits:2})}</td><td>₱ ${Number(i.total_price).toLocaleString('en-US',{minimumFractionDigits:2, maximumFractionDigits:2})}</td></tr>`;
                });
                html+=`</tbody></table>`;
                // Footer total: every record (partial or complete) sums its
                // actually-delivered lines (received qty x delivery price).
                const grandTotal=(data.items||[]).reduce((a,i)=>a+(Number(i.received_quantity||0)*Number(i.price||0)),0);
                html+=`<div class="footer-total-display" style="text-align:right;margin-top:10px;">Grand Total: <span>${fmtPeso(grandTotal)}</span></div>`;
                if(data.header.status==='Pending'){
                    html+=`<div style="margin-top:10px;padding:8px 10px;background:#fff3cd;border:1px solid #ffe082;border-radius:6px;font-size:11px;color:#856404;">⏳ Pending — stock not credited. Approve via professional confirmation to ingest.</div>`;
                    if(approveArea){
                    approveArea.innerHTML=`<button type="button" class="btn-modal-save" style="background:#2e7d32;" onclick="closeViewModal(); openApproveConfirmModal(${data.header.delivery_id}, '${data.header.delivery_number}', '${data.header.pr_number}', ${data.header.is_partial})">✔️ Approve & Credit Stock</button>`;
                    approveArea.classList.remove('hidden');
                    fetch('/delivery/remaining/'+data.header.pr_id).then(r=>r.json()).then(rem=>{
                        const remainingTotal = (rem.remaining||[]).reduce((a,b)=>a+(b.remaining_quantity||0),0);
                        if(remainingTotal > 0){
                            approveArea.innerHTML+=`<button type="button" class="btn-modal-cancel" style="background:#fff8e1;border:1px solid #ffe082;margin-left:8px;" onclick="closeViewModal(); openCompleteModal(${data.header.delivery_id});">➕ Add Remaining (${remainingTotal} left)</button>`;
                        }
                    });
                    }
                }
                content.innerHTML=html;
            });
        }
        function closeViewModal(){ document.getElementById('view-modal').classList.add('hidden'); }

        let pendingApproveDeliveryId = null;
        function openApproveConfirmModal(deliveryId, deliveryNumber, prNumber, isPartial){
            pendingApproveDeliveryId = deliveryId;
            // Fresh intent: restore the Confirm button in case a previous
            // attempt left it disabled (cancelled/refreshed mid-processing).
            const cbtn = document.querySelector('#approve-confirm-modal .btn-modal-save');
            if(cbtn){ cbtn.disabled = false; cbtn.style.opacity = ''; cbtn.style.pointerEvents = ''; if(!/Approve/.test(cbtn.innerHTML)) cbtn.innerHTML = '✔️ Yes, Approve & Credit Stock'; }
            document.getElementById('approve-delivery-number').innerText = deliveryNumber;
            document.getElementById('approve-pr-number').innerText = prNumber;
            const statusEl = document.getElementById('approve-partial-text');
            const isPartialFlag = parseInt(isPartial) === 1;
            statusEl.innerText = isPartialFlag ? 'Partial delivery — remaining qty can be completed afterwards' : 'Complete delivery — all ordered quantities received';
            statusEl.style.background = isPartialFlag ? '#e2e3ff' : '#d4edda';
            statusEl.style.color = isPartialFlag ? '#383d8a' : '#155724';
            statusEl.style.borderColor = isPartialFlag ? '#c5cae9' : '#c3e6cb';
            document.getElementById('approve-confirm-modal').classList.remove('hidden');
        }
        function closeApproveConfirmModal(){
            document.getElementById('approve-confirm-modal').classList.add('hidden');
            pendingApproveDeliveryId = null;
        }
        function confirmApproveDelivery(){
            if(!pendingApproveDeliveryId) return;
            const key = 'approving_' + pendingApproveDeliveryId;
            // Genuine in-flight submit: stay quiet WITHOUT touching the button,
            // so a blocked retry never fakes a "Processing..." state.
            if(sessionStorage.getItem(key)) return; // already submitting
            // Frontend double-click guard: disable button, show processing, block second submit via sessionStorage
            const btn = document.querySelector('#approve-confirm-modal .btn-modal-save');
            if(btn) { btn.disabled = true; btn.innerHTML = '⏳ Processing...'; btn.style.opacity = '0.6'; btn.style.pointerEvents = 'none'; }
            const form = document.getElementById('approve-hidden-form');
            form.action = '/delivery/approve/' + pendingApproveDeliveryId;
            sessionStorage.setItem(key, '1');
            // Also prevent refresh double-submit: clear after 5s
            setTimeout(() => sessionStorage.removeItem(key), 5000);
            form.submit();
        }
    