interface MetadataFieldProps {
  label: string;
  value: string;
}

export function MetadataField({ label, value }: MetadataFieldProps) {
  return (
    <div className="min-w-0">
      <span className="text-xs text-[var(--text-secondary)]">{label}</span>
      <p className="text-sm font-medium text-[var(--text-primary)] break-words">{value}</p>
    </div>
  );
}
