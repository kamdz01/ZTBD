import React from 'react';
import SizeBox from './SizeBox';

interface DatabaseBoxProps {
    scenario: string;
    database: string;
    sizes: {
        [size: string]: number[];
    };
    reloadMain: () => void;
}

const DatabaseBox: React.FC<DatabaseBoxProps> = ({scenario, database, sizes, reloadMain }) => {
    return (
        <div className="database-box">
            <h3 className="database-title">{database}</h3>
            {Object.keys(sizes).map(size => (
                <SizeBox scenario={scenario} database={database} key={size} size={size} times={sizes[size]} reloadMain = {reloadMain}/>
            ))}
        </div>
    );
};

export default DatabaseBox;