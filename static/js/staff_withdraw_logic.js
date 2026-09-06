/* staff_withdraw_logic.js — withdraw modal logic. Loaded after ui_helpers.js. */

        
        let availableProducts = [];
        let withdrawCatalogReady = loadWithdrawCatalog();
        async function loadWithdrawCatalog(){
            try {
                const res = await fetch('/products/api/list');
                const data = await res.json();
                availableProducts = (data.products || []).map(p => ({
                    id: p.product_id, name: p.product_name,
                    category: p.category || '', unit: p.unit || 'pcs',
                    price: Number(p.price || 0),
                    stock: (p.stock === undefined || p.stock === null)
                        ? 0 : parseInt(p.stock),
                    reorder: (p.reorder === undefined || p.reorder === null)
                        ? 10 : parseInt(p.reorder)
                }));
            } catch (e) { availableProducts = []; }
        }

        function fmtPeso(n){ return '₱ ' + Number(n||0).toLocaleString('en-US',{minimumFractionDigits:2, maximumFractionDigits:2}); }
        async function openWithdrawModal(){
            try { await withdrawCatalogReady; } catch (e) {} document.getElementById('withdraw-items-body').innerHTML=''; addWithdrawRow(); document.getElementById('withdraw-modal').classList.remove('hidden'); const d=document.querySelector('#withdraw-modal input[name="date_requested"]'); if(d && !d.value) d.valueAsDate=new Date(); }
        function closeWithdrawModal(){ document.getElementById('withdraw-modal').classList.add('hidden'); }
        function addWithdrawRow(){
            const tbody=document.getElementById('withdraw-items-body');
            const rowId=tbody.rows.length;
            const tr=document.createElement('tr');
            let opts='<option value="" disabled selected>Select Product</option>';
            availableProducts.forEach((p,idx)=>{ opts+=`<option value="${idx}">${p.name} — ${p.unit} — Stock:${p.stock}</option>`; });
            tr.innerHTML=`
                <td><select onchange="onWithdrawProductSelect(this, ${rowId})" required>${opts}</select><input type="hidden" name="product_id[]" id="w-prod-${rowId}"></td>
                <td><span id="w-stock-${rowId}" class="stock-info">—</span></td>
                <td><span id="w-unit-${rowId}">—</span></td>
                <td><span id="w-price-${rowId}">—</span></td>
                <td><input type="number" name="quantity[]" id="w-qty-${rowId}" min="1" placeholder="0" style="width:90px; padding:6px; border:1.5px solid #d0dbe5; border-radius:6px;" oninput="calcWithdrawSubtotal(${rowId})" required><div id="w-stock-msg-${rowId}" class="stock-info"></div></td>
                <td><span id="w-subtotal-${rowId}">₱ 0.00</span></td>
                <td><button type="button" class="btn-action" style="background:#ffebee; color:#c62828;" onclick="this.closest('tr').remove(); recalcWithdrawGrand()">✖</button></td>
            `;
            tbody.appendChild(tr);
        }
        function onWithdrawProductSelect(sel,rowId){
            const p=availableProducts[sel.value];
            if(!p) return;
            document.getElementById(`w-prod-${rowId}`).value=p.id;
            document.getElementById(`w-unit-${rowId}`).innerText=p.unit;
            document.getElementById(`w-price-${rowId}`).innerText=fmtPeso(p.price);
            const stockEl=document.getElementById(`w-stock-${rowId}`);
            stockEl.innerText=p.stock;
            stockEl.className = p.stock==0 ? 'stock-out' : (p.stock<=p.reorder ? 'stock-low' : 'stock-ok');
            const qty=document.getElementById(`w-qty-${rowId}`);
            qty.max=p.stock; qty.placeholder=`max ${p.stock}`; qty.value='';
            document.getElementById(`w-subtotal-${rowId}`).innerText='₱ 0.00';
            document.getElementById(`w-stock-msg-${rowId}`).innerText=`Available: ${p.stock}`;
            recalcWithdrawGrand();
        }
        function calcWithdrawSubtotal(rowId){
            const qty=parseInt(document.getElementById(`w-qty-${rowId}`).value)||0;
            const prodId=document.getElementById(`w-prod-${rowId}`).value;
            const prod=availableProducts.find(pp=>String(pp.id)===String(prodId));
            if(!prod) return;
            const msgEl=document.getElementById(`w-stock-msg-${rowId}`);
            const qtyInput=document.getElementById(`w-qty-${rowId}`);
            if(qty > prod.stock){ qtyInput.setCustomValidity(`Exceeds stock ${prod.stock}`); qtyInput.reportValidity(); msgEl.innerText=`❌ Exceeds stock! Max ${prod.stock}`; msgEl.className='stock-out'; }
            else { qtyInput.setCustomValidity(''); msgEl.innerText=`Available: ${prod.stock}`; msgEl.className = prod.stock==0?'stock-out':(prod.stock<=prod.reorder?'stock-low':'stock-ok'); }
            document.getElementById(`w-subtotal-${rowId}`).innerText=fmtPeso(qty * prod.price);
            recalcWithdrawGrand();
        }
        function recalcWithdrawGrand(){
            let grand=0;
            document.querySelectorAll('[id^="w-subtotal-"]').forEach(el=>{
                let v=el.innerText.replace(/[^0-9.-]/g,'').replace(/,/g,'');
                grand+=parseFloat(v)||0;
            });
            document.getElementById('withdraw-grand-total').innerText=fmtPeso(grand);
        }
        function validateWithdrawForm(){
            const rows=document.querySelectorAll('#withdraw-items-body tr');
            if(rows.length===0){ alert('Add at least one item.'); return false; }
            let ok=true, msg='';
            rows.forEach(tr=>{
                const sel=tr.querySelector('select');
                const qtyInput=tr.querySelector('input[name="quantity[]"]');
                if(!sel || sel.selectedIndex<=0){ ok=false; msg='Select product for each row.'; }
                const qty=parseInt(qtyInput.value||0);
                const prod=availableProducts[sel.value];
                if(prod && qty > prod.stock){ ok=false; msg=`Requested ${qty} exceeds stock ${prod.stock} for ${prod.name}`; }
                if(qty<=0){ ok=false; msg='Quantity must be >0.'; }
            });
            if(!ok){ alert(msg); return false; }
            return true;
        }
        function openViewModal(id){
            const c=document.getElementById('view-modal-content');
            c.innerHTML='Loading...';
            document.getElementById('view-modal').classList.remove('hidden');
            fetch('/withdraw/details/'+id).then(r=>r.json()).then(data=>{
                if(data.error){ c.innerHTML=data.error; return; }
                document.getElementById('view-ris-number').innerText=data.header.ris_number + ' Details';
                let html=`<div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; background:#f8fcff; border:1px solid #e2f0fb; border-radius:8px; padding:12px; margin-bottom:12px; font-size:12px;">`;
                html+=`<div><strong>RIS #:</strong> ${data.header.ris_number}</div><div><strong>Department:</strong> ${data.header.department}</div>`;
                html+=`<div><strong>Requested By:</strong> ${data.header.Firstname} ${data.header.Lastname}</div><div><strong>Purpose:</strong> ${data.header.purpose}</div>`;
                html+=`<div><strong>Date:</strong> ${data.header.date_requested}</div><div><strong>Status:</strong> <span class="badge badge-${(data.header.status||'').toLowerCase()}">${data.header.status}</span></div>`;
                html+=`</div>`;
                html+=`<table class="item-table"><thead><tr><th>Item</th><th>Unit</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr></thead><tbody>`;
                data.items.forEach(i=>{ html+=`<tr><td>${i.item_name}</td><td>${i.unit}</td><td>${i.quantity}</td><td>${fmtPeso(i.unit_price)}</td><td>${fmtPeso(i.total_price)}</td></tr>`; });
                html+=`</tbody></table>`;
                const total=data.items.reduce((a,b)=>a+parseFloat(b.total_price||0),0);
                html+=`<p style="text-align:right; font-weight:700;">Grand Total: ${fmtPeso(total)}</p>`;
                if(data.header.status==='Pending') html+=`<div style="margin-top:10px; padding:8px; background:#fff3cd; border:1px solid #ffe082; border-radius:6px; font-size:11px; color:#856404;">⏳ Pending — awaiting Admin approval.</div>`;
                c.innerHTML=html;
            });
        }
        function closeViewModal(){ document.getElementById('view-modal').classList.add('hidden'); }
    