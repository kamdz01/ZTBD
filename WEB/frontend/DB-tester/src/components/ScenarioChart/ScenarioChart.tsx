import React from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    Title,
    Tooltip,
    Legend,
    Filler,
} from 'chart.js';
import type { ChartDataset } from 'chart.js';
import LineScenarioChart from './LineScenarioChart';
import BarScenarioChart from './BarScenarioChart';

// Rejestracja komponentów Chart.js
ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

interface ScenarioChartProps {
    databases: {
        [database: string]: {
            [size: string]: number[];
        };
    };
}

interface ChartData<T extends 'line' | 'bar'> {
    labels: string[];
    datasets: ChartDataset<T, (number | null)[]>[];
}

const ScenarioChart: React.FC<ScenarioChartProps> = ({ databases }) => {
    // Pobranie unii wszystkich kluczy "size" ze wszystkich baz danych
    const allSizesSet = new Set<string>();
    Object.values(databases).forEach(db => {
        Object.keys(db).forEach(size => allSizesSet.add(size));
    });
    const allSizes = Array.from(allSizesSet);

    // Sortowanie rozmiarów – numerycznie, jeśli to możliwe, inaczej leksykograficznie
    allSizes.sort((a, b) => {
        const numA = parseFloat(a);
        const numB = parseFloat(b);
        if (!isNaN(numA) && !isNaN(numB)) {
            return numA - numB;
        }
        return a.localeCompare(b);
    });

    // Predefiniowane kolory do wykresu
    const colors = [
        'rgba(255, 99, 132, 1)',
        'rgba(54, 162, 235, 1)',
        'rgba(255, 206, 86, 1)',
        'rgba(75, 192, 192, 1)',
        'rgba(153, 102, 255, 1)',
        'rgba(255, 159, 64, 1)',
    ];

    // Wspólna logika przetwarzania danych
    const commonDatasets = Object.keys(databases).map((database, index) => {
        const dataPoints = allSizes.map(size => {
            const numbers = databases[database][size];
            if (numbers && numbers.length > 0) {
                const avg = numbers.reduce((sum, n) => sum + n, 0) / numbers.length;
                return avg;
            }
            return null; // Zostawiamy null, by stworzyć "dziurę" na wykresie
        });
        return {
            label: database,
            data: dataPoints,
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length],
        };
    });

    // Dane dla wykresu liniowego – dodajemy właściwości specyficzne dla linii
    const datasetsLine: ChartDataset<'line', (number | null)[]>[] = commonDatasets.map(dataset => ({
        ...dataset,
        tension: 0.4,
        fill: false,
    }));

    // Dane dla wykresu słupkowego – bez właściwości charakterystycznych dla linii
    const datasetsBar: ChartDataset<'bar', (number | null)[]>[] = commonDatasets.map(dataset => ({
        label: dataset.label,
        data: dataset.data,
        backgroundColor: dataset.backgroundColor,
        borderColor: dataset.borderColor,
    }));

    if (allSizes.length === 1) {
        const chartData: ChartData<'bar'> = {
            labels: allSizes,
            datasets: datasetsBar,
        };
        return (
            <div className="scenario-chart">
                <BarScenarioChart data={chartData} />
            </div>
        );
    } else {
        const chartData: ChartData<'line'> = {
            labels: allSizes,
            datasets: datasetsLine,
        };
        return (
            <div className="scenario-chart">
                <LineScenarioChart data={chartData} />
            </div>
        );
    }
};

export default ScenarioChart;
