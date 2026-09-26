"""crud_reports.py — Comparative Report data (read-only, no DDL).

Per-PR fulfillment ledger: requested quantities from pr_items vs delivered
quantities from iar_items (all IARs per PR, any status — only actually
received units count as delivered). Shared workspace: user_id is NEVER
applied here; both roles see identical team-wide numbers.
"""


from db import get_db_connection


def get_comparative_rows(search_query="", date_from="", date_to=""):
    """One row per DUAL-APPROVED PR: requested / delivered / outstanding / %.

    Only status='Approved' AND po_status='Approved' PRs compare — anything
    less never entered IAR creation, so it has no received side.
    date_from/date_to (YYYY-MM-DD) form an explicit range on
    pr.date_requested. Invalid input falls back safely (no crash, no rows
    lost — callers validate before invoking).
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
        SELECT pr.pr_id, pr.pr_number, pr.date_requested, pr.status,
               pr.po_status, pr.fund_source,
               u.Firstname, u.Lastname, u.username,
               COALESCE(req.requested_qty, 0) AS requested_qty,
               COALESCE(del.delivered_qty, 0) AS delivered_qty
        FROM purchase_requests pr
        JOIN users u ON pr.user_id = u.id
        LEFT JOIN (
            SELECT pr_id, COALESCE(SUM(quantity), 0) AS requested_qty
            FROM pr_items
            GROUP BY pr_id
        ) req ON req.pr_id = pr.pr_id
        LEFT JOIN (
            SELECT pr_id, COALESCE(SUM(received_quantity), 0) AS delivered_qty
            FROM iar_items
            GROUP BY pr_id
        ) del ON del.pr_id = pr.pr_id
        WHERE pr.status = 'Approved'
          AND COALESCE(pr.po_status, 'Pending') = 'Approved'
        """
        params = []

        if search_query:
            pattern = f"%{search_query}%"
            sql += """ AND (
                pr.pr_number LIKE %s OR
                u.Firstname LIKE %s OR
                u.Lastname LIKE %s OR
                u.username LIKE %s
            )"""
            params.extend([pattern] * 4)

        if date_from and date_to:
            sql += " AND DATE(pr.date_requested) BETWEEN %s AND %s"
            params.extend([date_from, date_to])

        sql += " ORDER BY pr.pr_id DESC;"

        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall() or []
        for r in rows:
            try:
                requested = int(r.get("requested_qty") or 0)
            except (TypeError, ValueError):
                requested = 0
            try:
                delivered = int(r.get("delivered_qty") or 0)
            except (TypeError, ValueError):
                delivered = 0
            outstanding = max(0, requested - delivered)
            pct = round((delivered / requested) * 100, 1) if requested > 0 else 0.0
            r["requested_qty"] = requested
            r["delivered_qty"] = delivered
            r["outstanding_qty"] = outstanding
            r["fulfillment_pct"] = pct
        return rows
    except Exception as err:
        print(f"[get_comparative_rows] DB error: {err}")
        return []
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def get_merged_comparison(pr_ids):
    """Virtual merged PR-vs-IAR compare (presentation only, no DDL).

    pr_ids: iterable of ints (deduped, order preserved). Returns
    (items, totals, numbers, skipped) where items group by product across
    all given PRs: requested qty overall + per-fund breakdown, delivered
    qty across those PRs' IARs, outstanding, fulfillment %. Missing PRs are
    reported in skipped (callers flash them).
    """
    try:
        clean, seen = [], set()
        for pid in pr_ids or []:
            try:
                pid = int(pid)
            except (TypeError, ValueError):
                continue
            if pid not in seen:
                seen.add(pid)
                clean.append(pid)
    except Exception:
        return [], {}, [], []
    if not clean:
        return [], {}, [], []

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        fmt = ",".join(["%s"] * len(clean))

        cursor.execute(
            f"SELECT pr_id, pr_number, fund_source, status, po_status "
            f"FROM purchase_requests "
            f"WHERE pr_id IN ({fmt})",
            tuple(clean),
        )
        headers = {int(r["pr_id"]): r for r in (cursor.fetchall() or [])}
        numbers, skipped = [], []
        for pid in clean:
            h = headers.get(pid)
            if not h:
                skipped.append(f"PR-{pid:03d} (not found)")
                continue
            if str(h.get("status") or "") != "Approved" or str(h.get("po_status") or "Pending") != "Approved":
                skipped.append(str(h.get("pr_number") or f"PR-{pid:03d}"))
                continue
            numbers.append(str(h.get("pr_number") or f"PR-{pid:03d}"))
        valid = [pid for pid in clean if pid in headers]
        if not valid:
            return [], {}, numbers, skipped
        vfmt = ",".join(["%s"] * len(valid))

        # Requested per product per fund (fund lives on the PR header).
        cursor.execute(
            f"""SELECT pi.product_id, pi.item_name, pi.unit, pi.details, pi.size,
                       pr.fund_source AS fund,
                       COALESCE(SUM(pi.quantity), 0) AS requested_qty
                FROM pr_items pi
                JOIN purchase_requests pr ON pr.pr_id = pi.pr_id
                WHERE pi.pr_id IN ({vfmt})
                GROUP BY pi.product_id, pi.item_name, pi.unit, pi.details,
                         pi.size, pr.fund_source
                ORDER BY pi.item_name ASC""",
            tuple(valid),
        )
        requested_rows = cursor.fetchall() or []

        # Delivered per product across those PRs' IARs (any status — only
        # actually received units count).
        cursor.execute(
            f"""SELECT product_id, COALESCE(SUM(received_quantity), 0) AS delivered_qty
                FROM iar_items
                WHERE pr_id IN ({vfmt})
                GROUP BY product_id""",
            tuple(valid),
        )
        delivered = {}
        for r in cursor.fetchall() or []:
            try:
                delivered[int(r["product_id"])] = int(r["delivered_qty"] or 0)
            except (TypeError, ValueError):
                continue

        grouped = {}
        for r in requested_rows:
            try:
                pid = int(r["product_id"])
            except (TypeError, ValueError):
                continue
            try:
                qty = int(r.get("requested_qty") or 0)
            except (TypeError, ValueError):
                qty = 0
            g = grouped.setdefault(pid, {
                "product_id": pid,
                "item_name": r.get("item_name") or "—",
                "unit": r.get("unit") or "",
                "details": r.get("details") or "",
                "size": r.get("size") or "",
                "requested_qty": 0,
                "funds": {},
            })
            g["requested_qty"] += qty
            fund = (r.get("fund") or "—").strip() or "—"
            g["funds"][fund] = g["funds"].get(fund, 0) + qty

        items = []
        total_req = total_del = 0
        for g in grouped.values():
            del_qty = delivered.get(g["product_id"], 0)
            out = max(0, g["requested_qty"] - del_qty)
            pct = round((del_qty / g["requested_qty"]) * 100, 1) if g["requested_qty"] > 0 else 0.0
            g["delivered_qty"] = del_qty
            g["outstanding_qty"] = out
            g["fulfillment_pct"] = pct
            g["fund_list"] = sorted(g["funds"].items())
            items.append(g)
            total_req += g["requested_qty"]
            total_del += del_qty
        items.sort(key=lambda g: str(g["item_name"]).lower())
        totals = {
            "requested_qty": total_req,
            "delivered_qty": total_del,
            "outstanding_qty": max(0, total_req - total_del),
            "fulfillment_pct": round((total_del / total_req) * 100, 1) if total_req > 0 else 0.0,
        }
        return items, totals, numbers, skipped
    except Exception as err:
        print(f"[get_merged_comparison] DB error: {err}")
        return [], {}, [], []
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass
