import React from "react";
import DatabaseBox from "./DatabaseBox";
import ScenarioChart from "./ScenarioChart/ScenarioChart";

interface ScenarioProps {
  scenario: string;
  databases: {
    [database: string]: {
      [size: string]: {
        times: number[];
        rows: number[];
      };
    };
  };
  reloadMain: () => void;
}

const Scenario: React.FC<ScenarioProps> = ({
  scenario,
  databases,
  reloadMain,
}) => {
  const timesForChart = Object.entries(databases).reduce((acc, [db, sizes]) => {
    acc[db] = Object.entries(sizes).reduce((sizeAcc, [size, data]) => {
      sizeAcc[size] = data.times;
      return sizeAcc;
    }, {} as Record<string, number[]>);
    return acc;
  }, {} as Record<string, Record<string, number[]>>);

  return (
    <div className="scenario">
      <h2 className="scenario-title">Scenariusz: {scenario}</h2>
      <div className="scenario-content">
        <div className="databases">
          {Object.keys(databases).map((database) => (
            <React.Fragment key={database}>
              <DatabaseBox
                scenario={scenario}
                database={database}
                sizes={databases[database]}
                reloadMain={reloadMain}
              />
            </React.Fragment>
          ))}
        </div>
        <ScenarioChart databases={timesForChart} />
      </div>
    </div>
  );
};

export default Scenario;
