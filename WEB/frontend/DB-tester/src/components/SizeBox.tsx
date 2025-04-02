import React, { useState } from "react";

interface SizeBoxProps {
  scenario: string;
  database: string;
  size: string;
  times: number[];
  rows?: number[];
  reloadMain: () => void;
}

const SizeBox: React.FC<SizeBoxProps> = ({
  scenario,
  database,
  size,
  times,
  rows = [],
  reloadMain,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [loadingTest, setLoadingTest] = useState(false);

  const toggleExpand = () => {
    setExpanded((prev: boolean) => !prev);
  };

  const entriesToShow = expanded ? times.length : Math.min(times.length, 3);
  const indicesToShow = Array.from({ length: entriesToShow }, (_, i) => i);

  const runTest = async () => {
    setLoadingTest(true);
    let url = `http://127.0.0.1:8000/run/${database}/${scenario}`;
    if (size !== "default") {
      url = url + `/${size}`;
    }
    try {
      const response = await fetch(url);
      if (!response.ok) {
        console.error("Błąd podczas wywołania testu");
        return;
      }
      const data = await response.json();
      if (data.result !== undefined) {
        // Przekazujemy wynik do komponentu wyższego rzędu, żeby odświeżyć dane i przerysować wykresy
        reloadMain();
      } else {
        console.error("Nieprawidłowy format odpowiedzi", data);
      }
    } catch (error) {
      console.error("Błąd:", error);
    } finally {
      setLoadingTest(false);
    }
  };

  return (
    <div className="size-box" onClick={toggleExpand}>
      <h4 className="size-title">
        Rozmiar: {size}
        <span className="size-show-more">
          {times.length > 3 && (expanded ? " △" : " ▽")}
        </span>
      </h4>
      <p className="size-description">
        <strong>Wyniki:</strong>
        {indicesToShow.map((index) => (
          <span key={index}>
            <br />
            <span className="time-value">Czas: {times[index]}</span>
            {rows[index] !== undefined && (
              <p className="row-count"> (Wierszy: {rows[index]})</p>
            )}
          </span>
        ))}
      </p>
      <button
        onClick={(e) => {
          e.stopPropagation();
          runTest();
        }}
      >
        {loadingTest ? "Testowanie..." : "Uruchom test"}
      </button>
    </div>
  );
};

export default SizeBox;
