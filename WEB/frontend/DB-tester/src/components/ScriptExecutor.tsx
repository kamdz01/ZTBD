import React, { useEffect, useState } from 'react';

interface ScriptExecutorProps {
    scriptName: string;
}

const ScriptExecutor: React.FC<ScriptExecutorProps> = ({ scriptName }) => {
    const [outputData, setOutputData] = useState<Record<string, number>>({});
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const executeScript = async () => {
            console.log('Executing script:', scriptName);
            try {
                const response = await fetch('http://127.0.0.1:8000/execute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ script_name: scriptName })
                });

                if (!response.ok) {
                    throw new Error(`HTTP error: ${response.status}`);
                }

                // Używamy ReadableStream do czytania danych na bieżąco
                const reader = response.body?.getReader();
                const decoder = new TextDecoder();
                let done = false;

                while (!done && reader) {
                    const { value, done: doneReading } = await reader.read();
                    done = doneReading;
                    const chunkValue = decoder.decode(value);
                    // Zakładamy, że w otrzymanym fragmencie znajdują się oddzielne obiekty JSON,
                    // np. '{"test-1": 10} {"test-2": 20}'
                    const jsonMatches = chunkValue.match(/{[^}]+}/g);
                    if (jsonMatches) {
                        jsonMatches.forEach(match => {
                            try {
                                const parsed = JSON.parse(match);
                                setOutputData(prev => ({ ...prev, ...parsed }));
                            } catch (error) {
                                console.error("Błąd parsowania JSON:", error);
                            }
                        });
                    }
                }
            } catch (err: unknown) {
                if (err instanceof Error) {
                    setError(err.message);
                } else {
                    setError('Błąd podczas wykonywania skryptu');
                }
            }
        };

        executeScript();
    }, [scriptName]);

    return (
        <div>
            <h2>Wynik skryptu: {scriptName}</h2>
            {error ? (
                <div style={{ color: 'red' }}>Błąd: {error}</div>
            ) : (
                <ul>
                    {Object.entries(outputData).map(([key, value]) => (
                        <li key={key}>{key}: {value}</li>
                    ))}
                </ul>
            )}
        </div>
    );
};

export default ScriptExecutor;