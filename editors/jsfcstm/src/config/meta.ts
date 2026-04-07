const packageJson = require('../../package.json') as {
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
 * Return the metadata exposed by the jsfcstm package.
 *
 * The package boundary is intentionally stable so the VSCode extension and
 * future consumers can import metadata without reaching into package.json
 * directly.
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
