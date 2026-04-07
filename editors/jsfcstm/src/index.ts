const packageJson = require('../package.json') as {
    name: string;
    version: string;
    description: string;
};

export interface JsFcstmPackageInfo {
    name: string;
    version: string;
    description: string;
}

/**
 * Return the metadata exposed by the jsfcstm skeleton package.
 *
 * Phase 0/1 intentionally keeps the public API minimal. The immediate goal is
 * to establish a publishable, testable npm package boundary before migrating
 * FCSTM language logic into this package in later phases.
 */
export function getJsFcstmPackageInfo(): JsFcstmPackageInfo {
    return {
        name: packageJson.name,
        version: packageJson.version,
        description: packageJson.description,
    };
}

export const JSFCSTM_PACKAGE_NAME = packageJson.name;
export const JSFCSTM_PACKAGE_VERSION = packageJson.version;
