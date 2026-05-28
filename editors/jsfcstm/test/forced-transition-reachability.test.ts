import assert from 'node:assert/strict';
import * as fs from 'node:fs';
import * as path from 'node:path';

import {createDocument, packageModule} from './support';

const FIXTURE_DIR = path.join(__dirname, 'fixtures', 'forced-transition-issue99');

function loadFixture(name: string) {
    const filePath = path.join(FIXTURE_DIR, name);
    const text = fs.readFileSync(filePath, 'utf8');
    return createDocument(text, filePath);
}

async function collectCodes(name: string): Promise<string[]> {
    const document = loadFixture(name);
    const diagnostics = await packageModule.collectDocumentDiagnostics(document);
    return diagnostics.map(item => `${item.code}|${item.message}`);
}

describe('forced transition reachability (issue #99)', () => {
    afterEach(() => {
        packageModule.getWorkspaceGraph().clearOverlays();
    });

    it('minimal repro: state reachable only via "!* -> X : Event" must not be flagged unreachable', async () => {
        const codes = await collectCodes('minimal.fcstm');

        // The forced-transition target must not be reported unreachable.
        assert.ok(
            !codes.some(line => line.includes('fcstm.unreachableState') && line.includes('Root.ErrorState')),
            `Root.ErrorState should be reachable via "!* -> ErrorState : Err". Got:\n${codes.join('\n')}`
        );

        // Sanity: a genuinely unused event must still surface.
        assert.ok(
            codes.some(line => line.includes('fcstm.unusedEvent') && line.includes('Root.UnusedOne')),
            `Root.UnusedOne should still be reported as unused. Got:\n${codes.join('\n')}`
        );

        // Sanity: the event used only by the forced transition must NOT be flagged unused.
        assert.ok(
            !codes.some(line => line.includes('fcstm.unusedEvent') && line.includes('Root.Err')),
            `Root.Err is used by a forced transition and must not be flagged unused. Got:\n${codes.join('\n')}`
        );
    });

    it('118.fcstm: ErrorOperational must be reachable via "!* -> ErrorOperational : ..." forced transitions', async () => {
        const codes = await collectCodes('118.fcstm');
        assert.ok(
            !codes.some(line => line.includes('fcstm.unreachableState')),
            `118.fcstm should produce no unreachableState diagnostics. Got:\n${codes.join('\n')}`
        );
        assert.ok(
            !codes.some(line => line.includes('fcstm.deadTransition')),
            `118.fcstm should produce no deadTransition diagnostics. Got:\n${codes.join('\n')}`
        );
    });

    it('160.fcstm: MissionControllerOff reachable via forced transitions', async () => {
        const codes = await collectCodes('160.fcstm');
        assert.ok(
            !codes.some(line => line.includes('fcstm.unreachableState')),
            `160.fcstm should produce no unreachableState diagnostics. Got:\n${codes.join('\n')}`
        );
        assert.ok(
            !codes.some(line => line.includes('fcstm.deadTransition')),
            `160.fcstm should produce no deadTransition diagnostics. Got:\n${codes.join('\n')}`
        );
    });

    it('169.fcstm: ReturnToHome/FaultHandling reachable; no dead transition between them', async () => {
        const codes = await collectCodes('169.fcstm');
        assert.ok(
            !codes.some(line => line.includes('fcstm.unreachableState')),
            `169.fcstm should produce no unreachableState diagnostics. Got:\n${codes.join('\n')}`
        );
        assert.ok(
            !codes.some(line => line.includes('fcstm.deadTransition')),
            `169.fcstm should produce no deadTransition diagnostics. Got:\n${codes.join('\n')}`
        );
    });
});
