export default function StatusDot({ ok }) {
  const cls = ok === true ? "dot ok" : ok === false ? "dot err" : "dot";
  const label = ok === true ? "connected" : ok === false ? "API unreachable" : "checking…";
  return (
    <div className="status">
      <span className={cls} />
      <span>{label}</span>
    </div>
  );
}
