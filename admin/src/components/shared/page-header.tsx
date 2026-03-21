interface PageHeaderProps {
  title: string;
  children?: React.ReactNode;
}

export function PageHeader({ title, children }: PageHeaderProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 animate-fadeInUp-1">
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">{title}</h1>
      {children}
    </div>
  );
}
