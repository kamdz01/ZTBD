import React from 'react';
import DatabaseBox from './DatabaseBox';
// import ScenarioChart from './ScenarioChart';
// import ScenarioChart from './SC';
import ScenarioChart from './ScenarioChart/ScenarioChart';


interface ScenarioProps {
    scenario: string;
    databases: {
        [database: string]: {
            [size: string]: number[];
        };
    };
    reloadMain: () => void;
}

const Scenario: React.FC<ScenarioProps> = ({ scenario, databases, reloadMain}) => {
    return (
        <div className="scenario">
            <h2 className="scenario-title">Scenariusz: {scenario}</h2>
            <div className='scenario-content'>
                <div className="databases">
                    {Object.keys(databases).map(database => (
                        <React.Fragment key={database}>
                            <DatabaseBox scenario={scenario} database={database} sizes={databases[database]} reloadMain={reloadMain}/>
                            {/* <ScenarioChart key={scenario} scenario={scenario} databases={databases} /> */}
                        </React.Fragment>
                    ))}
                </div>
                <ScenarioChart databases={databases} />
            </div>
        </div>
    );
};

export default Scenario;