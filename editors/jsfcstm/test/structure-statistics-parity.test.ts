import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import assert from 'node:assert/strict';

import {createDocument, packageModule} from './support';

const FIXTURES = JSON.parse(readFileSync(
    join(__dirname, 'fixtures', 'structure_statistics_parity.json'),
    'utf8',
)) as Array<{
    name: string;
    dsl: string;
    policy: Record<string, number | null> | null;
    expected: Record<string, unknown>;
}>;

async function buildMachine(source: string) {
    const document = createDocument(source, '/tmp/structure-statistics-parity.fcstm');
    const ast = await packageModule.parseAstDocument(document);
    const machine = packageModule.buildStateMachineModel(ast);
    if (!machine) throw new Error('buildStateMachineModel returned null');
    return machine;
}

describe('structure statistics parity contract', () => {
    for (const fixture of FIXTURES) {
        it(`matches the canonical fixture: ${fixture.name}`, async () => {
            const report = packageModule.inspectModel(
                await buildMachine(fixture.dsl),
                fixture.policy === null
                    ? undefined
                    : {structureStatisticsPolicy: fixture.policy},
            );
            assert.deepEqual(report.structure_statistics, fixture.expected);
        });
    }
});
