import { ChevronDown, ChevronUp } from "lucide-react";
import { useMemo, useState } from "react";

type CollapsibleBlockProps = {
  title: string;
  label?: string;
  content: string;
  meta?: string;
  limit?: number;
};

export function CollapsibleBlock({ title, label, content, meta, limit = 180 }: CollapsibleBlockProps) {
  const [open, setOpen] = useState(content.length <= limit);
  const shouldCollapse = content.length > limit;
  const visibleContent = useMemo(() => {
    if (!shouldCollapse || open) return content;
    return `${content.slice(0, limit)}...`;
  }, [content, limit, open, shouldCollapse]);

  return (
    <article className="processBlock">
      <header>
        <div>
          {label && <span>{label}</span>}
          <h3>{title}</h3>
        </div>
        {shouldCollapse && (
          <button type="button" onClick={() => setOpen((value) => !value)}>
            {open ? <ChevronUp size={16} aria-hidden="true" /> : <ChevronDown size={16} aria-hidden="true" />}
            {open ? "收起" : "展开全文"}
          </button>
        )}
      </header>
      <p>{visibleContent}</p>
      {meta && <small>{meta}</small>}
    </article>
  );
}
