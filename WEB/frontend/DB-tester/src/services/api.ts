export interface DatabasesResponse {
    databases: string[];
}

export interface Scenario {
    description: string;
    sizes?: number[]; // opcjonalne rozmiary
}

export interface TestScenariosResponse {
    testScenarios: {
        [key: string]: Scenario;
    };
}

export interface ResultResponse {
    database: string;
    scenario: string;
    size: string;
    times: number[];
}

export interface StructuredResults {
    [scenario: string]: {
        [database: string]: {
            [size: string]: number[];
        };
    };
}

// Wyekstrahowana funkcja pobierająca wynik dla konkretnego połączenia
export const fetchResult = async (
    database: string,
    scenarioKey: string,
    size: string
): Promise<ResultResponse | null> => {
    const url = `http://127.0.0.1:8000/results/${database}/${scenarioKey}/${size}`;
    try {
        const response = await fetch(url);
        if (!response.ok) {
            console.error(`Błąd pobierania wyników z: ${url}`);
            return null;
        }
        const data: ResultResponse = await response.json();
        return data;
    } catch (err) {
        console.error(`Błąd przy fetchowaniu ${url}:`, err);
        return null;
    }
};

export const getStructuredResults = async (): Promise<StructuredResults> => {
    // Pobieramy dane o bazach i scenariuszach równolegle
    const [dbRes, scenariosRes] = await Promise.all([
        fetch('http://127.0.0.1:8000/databases'),
        fetch('http://127.0.0.1:8000/test-scenarios')
    ]);

    if (!dbRes.ok) {
        throw new Error('Błąd podczas pobierania baz danych');
    }
    if (!scenariosRes.ok) {
        throw new Error('Błąd podczas pobierania scenariuszy testowych');
    }

    const [databasesData, scenariosData] = await Promise.all([
        dbRes.json(),
        scenariosRes.json()
    ]) as [DatabasesResponse, TestScenariosResponse];

    // Pobierz wszystkie wyniki równolegle, używając wyekstrahowanej funkcji fetchResult
    const allFetches: Promise<ResultResponse | null>[] = [];
    Object.entries(scenariosData.testScenarios).forEach(([scenarioKey, scenarioValue]) => {
        const sizes = scenarioValue.sizes ? scenarioValue.sizes.map(String) : ['default'];
        databasesData.databases.forEach(database => {
            sizes.forEach(size => {
                allFetches.push(fetchResult(database, scenarioKey, size));
            });
        });
    });

    const results = await Promise.all(allFetches);
    const grouped: StructuredResults = {};

    results.forEach((data) => {
        if (data) {
            if (!grouped[data.scenario]) {
                grouped[data.scenario] = {};
            }
            if (!grouped[data.scenario][data.database]) {
                grouped[data.scenario][data.database] = {};
            }
            grouped[data.scenario][data.database][data.size] = data.times;
        }
    });

    return grouped;
};