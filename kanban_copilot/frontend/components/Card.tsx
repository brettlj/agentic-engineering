"use client";

import { Card as CardType } from "../lib/types";

interface Props {
  card: CardType;
  onDelete?: (id: string) => void;
}

export default function Card({ card, onDelete }: Props) {
  return (
    <div className="mb-2 rounded bg-white p-3 shadow">
      <div className="flex justify-between items-start">
        <div className="font-semibold text-sm text-gray-800">{card.title}</div>
        {onDelete && (
          <button
            className="text-red-500 hover:text-red-700 text-xs"
            onClick={() => onDelete(card.id)}
            aria-label="Delete card"
          >
            ✕
          </button>
        )}
      </div>
      {card.details && (
        <p className="mt-1 text-gray-600 text-xs">{card.details}</p>
      )}
    </div>
  );
}
