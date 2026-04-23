const fs = require('fs');
const path = require('path');

const packageDir = path.resolve(__dirname, '..');
const sourceDir = path.join(packageDir, 'src', 'dsl', 'grammar');
const targetDir = path.join(packageDir, 'dist', 'dsl', 'grammar');

function ensureSourceExists() {
    if (!fs.existsSync(sourceDir)) {
        throw new Error(`Generated grammar source directory not found: ${sourceDir}`);
    }
}

function copyTree(sourcePath, targetPath) {
    const stat = fs.statSync(sourcePath);
    if (stat.isDirectory()) {
        fs.mkdirSync(targetPath, {recursive: true});
        for (const child of fs.readdirSync(sourcePath)) {
            copyTree(path.join(sourcePath, child), path.join(targetPath, child));
        }
        return;
    }

    fs.mkdirSync(path.dirname(targetPath), {recursive: true});
    fs.copyFileSync(sourcePath, targetPath);
}

function main() {
    ensureSourceExists();
    fs.rmSync(targetDir, {recursive: true, force: true});
    copyTree(sourceDir, targetDir);
}

main();
