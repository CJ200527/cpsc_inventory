/* staff_return_logic.js — return modal logic. Loaded after ui_helpers.js. */

        
        let availableProducts = [];
        let returnCatalogReady = loadReturnCatalog();
        async function loadReturnCatalog(){
            try {
                const res = await fetch('/products/api/list');
                const data = await res.json();
                availableProducts = (data.products || []).map(p => ({
                    id: p.product_id, name: p.product_name,
                    category: p.category || '', unit: p.unit || 'pcs',
                    details: p.details || '', size: p.size || '',
                    price: Number(p.price || 0),
                    stock: (p.stock === undefined || p.stock === null)
                        ? 0 : parseInt(p.stock),
                    reorder: (p.reorder === undefined || p.reorder === null)
                        ? 10 : parseInt(p.reorder)
                }));
                availableProducts.sort((a,b)=>String(a.name||'').localeCompare(String(b.name||''),undefined,{sensitivity:'base'}));
            } catch (e) { availableProducts = []; }
        }

        function todayLocal(){ const n=new Date(); const p=x=>String(x).padStart(2,'0'); return `${n.getFullYear()}-${p(n.getMonth()+1)}-${p(n.getDate())}`; }
        /* Return Slip Number: daily server sequence (offline fallback keeps the
           RET-YYYY-MM-DD shape with a random suffix; DB enforces uniqueness). */
        function fetchReturnNumber(numEl){
            if(!numEl) return;
            numEl.value=''; numEl.placeholder='Loading...';
            fetch('/returns/get_next_number').then(r=>r.json()).then(dt=>{
                if(dt.return_number) numEl.value=dt.return_number;
                else numEl.placeholder='Auto-generated';
            }).catch(()=>{ numEl.value=`RET-${todayLocal()}-${Math.floor(1000+Math.random()*9000)}`; });
        }
        async function openReturnModal(){
            try { await returnCatalogReady; } catch (e) {} document.getElementById('return-items-body').innerHTML=''; addReturnRow(); document.getElementById('return-modal').classList.remove('hidden');
            const numEl=document.getElementById('return-number-auto'); if(numEl && !numEl.value) fetchReturnNumber(numEl);
            const d=document.querySelector('#return-modal input[name="date_returned"]'); if(d){ if(!d.value) d.valueAsDate=new Date(); d.max=todayLocal(); }
            const sInput=document.getElementById('withdraw-smart-search'); if(sInput) sInput.value='';
            const sHidden=document.getElementById('withdraw-id-hidden'); if(sHidden) sHidden.value='';
            const sList=document.getElementById('withdraw-dropdown-list'); if(sList){ sList.innerHTML=''; sList.classList.add('hidden'); } }
        function closeReturnModal(){ document.getElementById('return-modal').classList.add('hidden'); }
        /* Withdraw Number smart search (delivery-picker pattern): click shows
           the list, typing filters it; only an explicit pick links a record. */
        function escHtml(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
        function withdrawDropdownData(){
            const sel=document.getElementById('withdraw-select');
            if(!sel) return [];
            return [...sel.options].filter(o=>o.value).map(o=>({
                id:o.value, ris:o.dataset.ris||o.text, dept:o.dataset.dept||''
            }));
        }
        function renderWithdrawDropdown(input, hits){
            const list=document.getElementById('withdraw-dropdown-list');
            if(!list) return;
            if(hits.length===0){
                list.innerHTML=`<div class="custom-dropdown-empty">No matching withdrawals.</div>`;
            } else {
                list.innerHTML=hits.map(w=>`<div class="custom-dropdown-item" data-wid="${w.id}" data-ris="${escHtml(w.ris)}" onmousedown="selectWDItem(this)">`
                    +`<span class="cd-text"><span class="cd-name">${escHtml(w.ris)}</span>`
                    +`<span class="cd-specs">${escHtml(w.dept) || '&nbsp;'}</span></span></div>`).join('');
            }
            list.classList.remove('hidden');
        }
        function filterWithdrawDropdown(input){
            const hidden=document.getElementById('withdraw-id-hidden');
            if(hidden) hidden.value='';
            const q=input.value.trim().toLowerCase();
            renderWithdrawDropdown(input, withdrawDropdownData().filter(w=>!q||(w.ris+' '+w.dept).toLowerCase().includes(q)).slice(0,50));
        }
        function showWithdrawDropdown(input){
            renderWithdrawDropdown(input, withdrawDropdownData().slice(0,50));
        }
        function hideWithdrawDropdown(input){
            const list=document.getElementById('withdraw-dropdown-list');
            if(list) setTimeout(()=>list.classList.add('hidden'),150);
        }
        function selectWDItem(el){
            const list=document.getElementById('withdraw-dropdown-list');
            if(list) list.classList.add('hidden');
            const input=document.getElementById('withdraw-smart-search');
            const hidden=document.getElementById('withdraw-id-hidden');
            if(input) input.value=el.dataset.ris||'';
            if(hidden) hidden.value=el.dataset.wid||'';
            if(el.dataset.wid) onWithdrawalSelect(el.dataset.wid);
        }
        function onWithdrawalSelect(val){
            const tbody=document.getElementById('return-items-body');
            tbody.innerHTML='';
            if(!val){ addReturnRow(); return; }
            fetch('/withdraw/details/'+val).then(r=>r.json()).then(data=>{
                if(data.error){ addReturnRow(); return; }
                // Department follows the chosen withdrawn record.
                const deptInput=document.querySelector('#return-modal input[name="department"]');
                if(deptInput && data.header && data.header.department) deptInput.value=data.header.department;
                data.items.forEach(it=>{ addReturnRowWithProduct(it.product_id, it.item_name, it.unit, it.quantity, it.withdraw_details || it.details); });
                if(tbody.children.length===0) addReturnRow();
            });
        }
        function addReturnRow(){
            const tbody=document.getElementById('return-items-body');
            const rowId=tbody.rows.length;
            const tr=document.createElement('tr');
            let opts='<option value="" disabled selected>Select Product</option>';
            availableProducts.forEach(p=>{ opts+=`<option value="${p.id}">${p.name} — ${p.unit}</option>`; });
            tr.innerHTML=`
                <td><select onchange="onReturnProductSelect(this, ${rowId})" required>${opts}</select><input type="hidden" name="product_id[]" id="r-prod-${rowId}"></td>
                <td><span id="r-spec-${rowId}" class="readonly-cell">—</span></td>
                <td><span id="r-issued-${rowId}" class="stock-info">—</span></td>
                <td><input type="number" name="returned_quantity[]" id="r-qty-${rowId}" min="1" placeholder="0" style="width:90px; padding:6px; border:1.5px solid #d0dbe5; border-radius:6px;" required></td>
                <td><span id="r-unit-${rowId}">—</span></td>
                <td><select name="condition_status[]" required><option value="Serviceable">Serviceable</option><option value="Unserviceable">Unserviceable</option></select></td>
                <td><button type="button" class="btn-action btn-delete" title="Remove row" onclick="this.closest('tr').remove()"><span class="act-icon act-x" aria-hidden="true"></span></button></td>
            `;
            tbody.appendChild(tr);
        }
        function addReturnRowWithProduct(pid, name, unit, issuedQty, specs){
            const tbody=document.getElementById('return-items-body');
            const tr=document.createElement('tr');
            tr.innerHTML=`
                <td><span style="font-weight:600;">${name}</span><input type="hidden" name="product_id[]" value="${pid}"></td>
                <td><span class="readonly-cell">${specs || '—'}</span></td>
                <td><span class="stock-info">${issuedQty}</span></td>
                <td><input type="number" name="returned_quantity[]" min="1" max="${issuedQty}" placeholder="max ${issuedQty}" style="width:90px; padding:6px; border:1.5px solid #d0dbe5; border-radius:6px;" required></td>
                <td>${unit}</td>
                <td><select name="condition_status[]" required><option value="Serviceable">Serviceable</option><option value="Unserviceable">Unserviceable</option></select></td>
                <td><button type="button" class="btn-action btn-delete" title="Remove row" onclick="this.closest('tr').remove()"><span class="act-icon act-x" aria-hidden="true"></span></button></td>
            `;
            tbody.appendChild(tr);
        }
        function onReturnProductSelect(sel,rowId){
            const p=availableProducts.find(x=>String(x.id)===String(sel.value));
            if(!p) return;
            document.getElementById(`r-prod-${rowId}`).value=p.id;
            document.getElementById(`r-spec-${rowId}`).innerText=[p.details, p.size].filter(Boolean).join(' ') || '—';
            document.getElementById(`r-unit-${rowId}`).innerText=p.unit;
            document.getElementById(`r-issued-${rowId}`).innerText=p.stock;
            const qty=document.getElementById(`r-qty-${rowId}`);
            if(qty){ qty.max=p.stock; qty.value=''; }
        }
        function validateReturnForm(){
            const widHidden=document.getElementById('withdraw-id-hidden');
            if(!widHidden || !widHidden.value){ alert('Select a Withdraw Number from the list.'); return false; }
            const rows=document.querySelectorAll('#return-items-body tr');
            if(rows.length===0){ alert('Add at least one item.'); return false; }
            let ok=true, msg='';
            rows.forEach(tr=>{
                const qtyInput=tr.querySelector('input[name="returned_quantity[]"]');
                const qty=parseInt(qtyInput.value||0);
                const max=parseInt(qtyInput.max);
                if(max && qty>max){ ok=false; msg=`Returned ${qty} exceeds issued ${max}.`; }
                if(qty<=0){ ok=false; msg='Quantity must be >0.'; }
            });
            if(!ok){ alert(msg); return false; }
            return true;
        }
        function openViewModal(id){
            const c=document.getElementById('view-modal-content');
            c.innerHTML='Loading...';
            document.getElementById('view-modal').classList.remove('hidden');
            fetch('/returns/details/'+id).then(r=>r.json()).then(data=>{
                if(data.error){ c.innerHTML=data.error; return; }
                document.getElementById('view-return-number').innerText=data.header.return_number + ' Details';
                let html=`<div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; background:#f8fcff; border:1px solid #e2f0fb; border-radius:8px; padding:12px; margin-bottom:12px; font-size:12px;">`;
                html+=`<div><strong>Return #:</strong> ${data.header.return_number}</div><div><strong>Ref RIS:</strong> ${data.header.ris_number || '— Direct'}</div>`;
                html+=`<div><strong>Department:</strong> ${data.header.department}</div><div><strong>Returned By:</strong> ${data.header.Firstname} ${data.header.Lastname}</div>`;
                html+=`<div><strong>Reason:</strong> ${data.header.reason}</div><div><strong>Date:</strong> ${data.header.date_returned}</div>`;
                html+=`<div><strong>Status:</strong> <span class="badge badge-${(data.header.status||'').toLowerCase()}">${data.header.status}</span></div>`;
                html+=`</div>`;
                html+=`<table class="item-table"><thead><tr><th>Item</th><th>Qty</th><th>Condition</th><th>Unit Price</th><th>Total</th></tr></thead><tbody>`;
                data.items.forEach(i=>{
                    const col=i.condition_status==='Serviceable'?'#2e7d32':'#c62828';
                    html+=`<tr><td>${i.item_name}</td><td>${i.returned_quantity}</td><td style="color:${col}; font-weight:700;">${i.condition_status}</td><td>₱ ${Number(i.unit_price).toLocaleString('en-US',{minimumFractionDigits:2})}</td><td>₱ ${Number(i.total_price).toLocaleString('en-US',{minimumFractionDigits:2})}</td></tr>`;
                });
                html+=`</tbody></table>`;
                c.innerHTML=html;
            });
        }
        function closeViewModal(){ document.getElementById('view-modal').classList.add('hidden'); }
    