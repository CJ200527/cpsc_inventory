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
            numEl.value=''; numEl.classList.remove('has-content'); numEl.placeholder='Loading...';
            fetch('/returns/get_next_number').then(r=>r.json()).then(dt=>{
                if(dt.return_number){ numEl.value=dt.return_number; numEl.classList.add('has-content'); }
                else numEl.placeholder='Auto-generated';
            }).catch(()=>{ numEl.value=`RET-${todayLocal()}-${Math.floor(1000+Math.random()*9000)}`; numEl.classList.add('has-content'); });
        }
        async function openReturnModal(){
            try { await returnCatalogReady; } catch (e) {} document.getElementById('return-items-body').innerHTML=''; addReturnRow(); document.getElementById('return-modal').classList.remove('hidden');
            const numEl=document.getElementById('return-number-auto'); if(numEl && !numEl.value) fetchReturnNumber(numEl);
            const d=document.querySelector('#return-modal input[name="date_returned"]'); if(d){ if(!d.value) d.valueAsDate=new Date(); d.max=todayLocal(); d.classList.toggle('has-content',!!d.value); }
            const sInput=document.getElementById('withdraw-smart-search'); if(sInput){ sInput.value=''; sInput.classList.remove('has-content'); }
            const sHidden=document.getElementById('withdraw-id-hidden'); if(sHidden) sHidden.value='';
            const sList=document.getElementById('withdraw-dropdown-list'); if(sList){ sList.innerHTML=''; sList.classList.add('hidden'); }
            returnSourceItems=[]; }
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
            if(input){ input.value=el.dataset.ris||''; input.classList.toggle('has-content',(input.value||'').trim()!==''); }
            if(hidden) hidden.value=el.dataset.wid||'';
            if(el.dataset.wid) onWithdrawalSelect(el.dataset.wid);
        }
        function onWithdrawalSelect(val){
            const tbody=document.getElementById('return-items-body');
            tbody.innerHTML='';
            if(!val){ returnSourceItems=[]; addReturnRow(); return; }
            fetch('/withdraw/details/'+val).then(r=>r.json()).then(data=>{
                if(data.error){ returnSourceItems=[]; addReturnRow(); return; }
                // Department follows the chosen withdrawn record.
                const deptInput=document.querySelector('#return-modal input[name="department"]');
                if(deptInput && data.header && data.header.department){ deptInput.value=data.header.department; deptInput.classList.add('has-content'); }
                // Item picker offers only this withdrawal's Tools/Equipment lines.
                returnSourceItems=(data.items||[]).filter(it=>it.category==='Tools'||it.category==='Equipment').map(it=>({id:it.product_id,name:it.item_name,unit:it.unit||'pcs',category:it.category||'',specs:[it.withdraw_details||it.details,it.size].filter(Boolean).join(' '),maxQty:parseInt(it.quantity||0)}));
                returnSourceItems.forEach(it=>{ addReturnRowWithProduct(it.id, it.name, it.unit, it.maxQty, it.specs, it.category); });
                if(tbody.children.length===0) addReturnRow();
            });
        }
        let returnSourceItems=[]; // chosen withdrawal's Tools/Equipment lines; empty until a Withdraw Number is picked
        function returnToolsEq(p){ return p && (p.category==='Tools'||p.category==='Equipment'); }
        function returnSourceList(){
            return returnSourceItems;
        }
        function returnItemSpecs(it){ return it.specs||[it.details,it.size].filter(Boolean).join(' '); }
        function filterReturnItemHits(q){
            q=(q||'').trim().toLowerCase();
            const out=[];
            returnSourceList().forEach((it,idx)=>{
                const hay=`${it.name||''} ${returnItemSpecs(it)} ${it.category||''}`.toLowerCase();
                if(!q || hay.includes(q)) out.push({it, idx});
            });
            return out.slice(0,50);
        }
        function renderReturnItemDropdown(input, hits){
            const tr=input.closest('tr');
            const list=tr ? tr.querySelector('.custom-dropdown-list') : null;
            if(!list) return;
            if(hits.length===0){ list.innerHTML=`<div class="custom-dropdown-empty">No matching products.</div>`; }
            else {
                list.innerHTML=hits.map(h=>{
                    const p=h.it;
                    const specLine=[returnItemSpecs(p), p.category].filter(Boolean).join(' | ');
                    return `<div class="custom-dropdown-item" data-idx="${h.idx}" onmousedown="selectReturnItem(this)">`
                        +`<span class="cd-text"><span class="cd-name">${escHtml(p.name)}</span>`
                        +`<span class="cd-specs">${escHtml(specLine) || '&nbsp;'}</span></span>`
                        +`<span class="cd-price">${escHtml(p.unit||'pcs')}</span></div>`;
                }).join('');
            }
            list.classList.remove('hidden');
        }
        function onReturnSearchInput(input){ renderReturnItemDropdown(input, filterReturnItemHits(input.value)); }
        function showReturnDropdown(input){ renderReturnItemDropdown(input, filterReturnItemHits('')); }
        function hideReturnDropdown(input){
            const tr=input.closest('tr');
            const list=tr ? tr.querySelector('.custom-dropdown-list') : null;
            if(list) setTimeout(()=>list.classList.add('hidden'),150);
        }
        function selectReturnItem(el){
            const tr=el.closest('tr'); if(!tr) return;
            const list=tr.querySelector('.custom-dropdown-list'); if(list) list.classList.add('hidden');
            const src=returnSourceList()[parseInt(el.dataset.idx||'-1',10)];
            if(!src) return;
            const input=tr.querySelector('.return-item-search'); if(input) input.value=src.name||'';
            const hidden=tr.querySelector('input[name="product_id[]"]'); if(hidden) hidden.value=src.id||'';
            const spec=tr.querySelector('.r-spec'); if(spec) spec.innerText=returnItemSpecs(src)||'—';
            const unit=tr.querySelector('.r-unit'); if(unit) unit.innerText=src.unit||'pcs';
            const cat=tr.querySelector('.r-cat'); if(cat) cat.innerText=src.category||'—';
            const issued=tr.querySelector('.r-issued'); if(issued) issued.innerText=src.maxQty;
            const qty=tr.querySelector('input[name="returned_quantity[]"]'); if(qty){ qty.max=src.maxQty; qty.value=''; }
        }
        function addReturnRow(){
            const tbody=document.getElementById('return-items-body');
            const tr=document.createElement('tr');
            tr.innerHTML=`
                <td><div class="custom-dropdown-wrap fx21-field"><input type="text" class="effect-21 return-item-search" placeholder="Select Product" autocomplete="off" required oninput="onReturnSearchInput(this)" onfocus="showReturnDropdown(this)" onblur="hideReturnDropdown(this)" style="width:100%;padding:6px;font-size:12px;border:1px solid #ccc;border-radius:4px;padding-right:26px;"><span class="focus-border"><i></i></span><span class="dd-caret">▾</span><input type="hidden" name="product_id[]"><div class="custom-dropdown-list hidden"></div></div></td>
                <td><span class="readonly-cell r-spec">—</span></td>
                <td><span class="r-unit">—</span></td>
                <td><span class="r-cat">—</span></td>
                <td><div class="fx21-field"><select name="condition_status[]" class="effect-21" required style="width:100%;padding:6px;font-size:12px;border:1px solid #ccc;border-radius:4px;background:#ffffff;"><option value="Serviceable">Serviceable</option><option value="Unserviceable">Unserviceable</option></select><span class="focus-border"><i></i></span></div></td>
                <td><span class="stock-info r-issued">—</span></td>
                <td><div class="fx21-field" style="display:inline-block;"><input type="number" name="returned_quantity[]" class="effect-21" min="1" placeholder="0" style="width:90px; padding:6px; border:1.5px solid #d0dbe5; border-radius:6px;" required><span class="focus-border"><i></i></span></div></td>
                <td><button type="button" class="btn-action btn-delete" title="Remove row" onclick="this.closest('tr').remove()"><svg class="act-icon" aria-hidden="true"><use href="#i-x"/></svg></button></td>
            `;
            tbody.appendChild(tr);
        }
        function addReturnRowWithProduct(pid, name, unit, issuedQty, specs, category){
            const tbody=document.getElementById('return-items-body');
            const tr=document.createElement('tr');
            tr.innerHTML=`
                <td><span style="font-weight:600;">${name}</span><input type="hidden" name="product_id[]" value="${pid}"></td>
                <td><span class="readonly-cell">${specs || '—'}</span></td>
                <td>${unit}</td>
                <td>${category || '—'}</td>
                <td><div class="fx21-field"><select name="condition_status[]" class="effect-21" required style="width:100%;padding:6px;font-size:12px;border:1px solid #ccc;border-radius:4px;background:#ffffff;"><option value="Serviceable">Serviceable</option><option value="Unserviceable">Unserviceable</option></select><span class="focus-border"><i></i></span></div></td>
                <td><span class="stock-info">${issuedQty}</span></td>
                <td><div class="fx21-field" style="display:inline-block;"><input type="number" name="returned_quantity[]" class="effect-21" min="1" max="${issuedQty}" placeholder="max ${issuedQty}" style="width:90px; padding:6px; border:1.5px solid #d0dbe5; border-radius:6px;" required><span class="focus-border"><i></i></span></div></td>
                <td><button type="button" class="btn-action btn-delete" title="Remove row" onclick="this.closest('tr').remove()"><svg class="act-icon" aria-hidden="true"><use href="#i-x"/></svg></button></td>
            `;
            tbody.appendChild(tr);
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
    