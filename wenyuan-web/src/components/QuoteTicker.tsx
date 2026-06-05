import { useEffect, useState } from "react";
import { api, type Quote } from "../lib/api";

const fallbackQuotes: Quote[] = [
  { text: "究天人之际，通古今之变。", source: "报任安书" },
  { text: "博学之，审问之，慎思之，明辨之，笃行之。", source: "礼记" },
  { text: "观今宜鉴古，无古不成今。", source: "增广贤文" },
];

export function QuoteTicker() {
  const [quotes, setQuotes] = useState<Quote[]>(fallbackQuotes);

  useEffect(() => {
    api.quotes().then(setQuotes).catch(() => setQuotes(fallbackQuotes));
  }, []);

  const items = [...quotes, ...quotes];

  return (
    <div className="quoteTicker" aria-label="文言名句轮滚">
      <div className="quoteTicker__track">
        {items.map((quote, index) => (
          <span className="quoteTicker__item" key={`${quote.text}-${index}`}>
            {quote.text}
            <b>《{quote.source}》</b>
          </span>
        ))}
      </div>
    </div>
  );
}
