/**
 * AdminTable — reusable styled table for admin tabs.
 *
 * Optional row actions:
 *   • onEdit(row)   — clicking the row's "Edit" button calls this; typical
 *                     handler loads the row into the tab's form for editing.
 *   • onDelete(row) — wraps the call in a confirm() and shows a loading state.
 *                     Returns a Promise; the table awaits it before refreshing.
 *
 * If neither handler is provided the actions column is omitted entirely, so
 * existing call sites that don't need CRUD aren't affected.
 */
import { useState } from "react";

export default function AdminTable({
  columns,
  rows,
  emptyText = "No items yet.",
  onEdit,
  onDelete,
  deleteConfirm = (row) => `Delete "${row.entity_id || row.intent_id || row.strategy_id || "this item"}"? This can't be undone.`,
}) {
  const hasActions = Boolean(onEdit || onDelete);

  if (!rows || rows.length === 0) {
    return <div className="admin-empty">{emptyText}</div>;
  }

  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} style={c.width ? { width: c.width } : undefined}>
                {c.label}
              </th>
            ))}
            {hasActions && <th style={{ width: "150px" }}>Actions</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <RowWithActions
              key={row._key || i}
              row={row}
              columns={columns}
              onEdit={onEdit}
              onDelete={onDelete}
              deleteConfirm={deleteConfirm}
              hasActions={hasActions}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RowWithActions({ row, columns, onEdit, onDelete, deleteConfirm, hasActions }) {
  const [busy, setBusy] = useState(false);

  async function handleDelete() {
    if (busy) return;
    const msg = typeof deleteConfirm === "function" ? deleteConfirm(row) : deleteConfirm;
    if (!window.confirm(msg)) return;
    setBusy(true);
    try {
      await onDelete(row);
    } finally {
      setBusy(false);
    }
  }

  return (
    <tr>
      {columns.map((c) => (
        <td key={c.key}>{c.render ? c.render(row) : row[c.key]}</td>
      ))}
      {hasActions && (
        <td className="admin-row-actions">
          {onEdit && (
            <button
              type="button"
              className="admin-row-btn"
              onClick={() => onEdit(row)}
              disabled={busy}
              title="Load this row into the form to edit"
            >
              Edit
            </button>
          )}
          {onDelete && (
            <button
              type="button"
              className="admin-row-btn admin-row-btn-danger"
              onClick={handleDelete}
              disabled={busy}
              title="Permanently delete this row"
            >
              {busy ? "Deleting…" : "Delete"}
            </button>
          )}
        </td>
      )}
    </tr>
  );
}
