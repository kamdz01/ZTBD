import React, { useEffect, useState } from 'react';
import { getStructuredResults, StructuredResults } from '../services/api';
import Scenario from './Scenario';
import './TestResults.css';

const TestResults: React.FC = () => {
    const [structuredResults, setStructuredResults] = useState<StructuredResults | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [reload, setReload] = useState<boolean>(false);

    const reloadMain = () => {
        setReload(prev => !prev);
    }

    useEffect(() => {
        const fetchData = async () => {
            try {
                const results = await getStructuredResults();
                setStructuredResults(results);
            } catch (err: unknown) {
                if (err instanceof Error) {
                    setError(err.message);
                }
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [reload]);

    if (loading) return <div>Ładowanie...</div>;
    if (error) return <div>Błąd: {error}</div>;
    if (!structuredResults) return <div>Brak wyników.</div>;

    return (
        <div className="container">
            {Object.keys(structuredResults).map(scenario => (
                <Scenario key={scenario} scenario={scenario} databases={structuredResults[scenario]} reloadMain = {reloadMain} />
            ))}
        </div>
    );
};

export default TestResults;