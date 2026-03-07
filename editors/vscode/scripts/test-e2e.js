#!/usr/bin/env node
/**
 * End-to-End Test for FCSTM VSCode Extension
 *
 * This script verifies that the extension package includes all necessary
 * dependencies and can load successfully.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

console.log('=== FCSTM Extension E2E Test ===\n');

// Test 1: Check if package exists
console.log('Test 1: Checking if package exists...');
const packagePath = path.join(__dirname, '..', 'build', 'fcstm-language-support-0.1.0.vsix');
if (!fs.existsSync(packagePath)) {
    console.error('✗ Package not found at:', packagePath);
    console.error('  Run "make package" first');
    process.exit(1);
}
console.log('✓ Package found:', packagePath);

// Test 2: Verify antlr4 is in package
console.log('\nTest 2: Verifying antlr4 is included in package...');
try {
    const output = execSync(`unzip -l "${packagePath}" | grep "node_modules/antlr4"`, { encoding: 'utf8' });
    const fileCount = output.trim().split('\n').length;
    console.log(`✓ antlr4 included (${fileCount} files)`);
} catch (error) {
    console.error('✗ antlr4 not found in package');
    console.error('  Check .vscodeignore configuration');
    process.exit(1);
}

// Test 3: Verify parser files are in package
console.log('\nTest 3: Verifying parser files are included...');
try {
    const output = execSync(`unzip -l "${packagePath}" | grep "parser/Grammar"`, { encoding: 'utf8' });
    const fileCount = output.trim().split('\n').length;
    console.log(`✓ Parser files included (${fileCount} files)`);
} catch (error) {
    console.error('✗ Parser files not found in package');
    console.error('  Run "make parser" first');
    process.exit(1);
}

// Test 4: Verify compiled output is in package
console.log('\nTest 4: Verifying compiled output is included...');
try {
    const output = execSync(`unzip -l "${packagePath}" | grep "out/.*\\.js"`, { encoding: 'utf8' });
    const fileCount = output.trim().split('\n').length;
    console.log(`✓ Compiled output included (${fileCount} files)`);
} catch (error) {
    console.error('✗ Compiled output not found in package');
    console.error('  Run "make build" first');
    process.exit(1);
}

// Test 5: Test parser functionality
console.log('\nTest 5: Testing parser functionality...');
(async () => {
    try {
        const parser = require('../out/parser.js');
        const p = parser.getParser();

        // Wait for async loading
        await new Promise(resolve => setTimeout(resolve, 1000));

        if (!p.isAvailable()) {
            console.error('✗ Parser not available');
            process.exit(1);
        }

        // Test valid code
        const validResult = await p.parse('state Root;');
        if (!validResult.success) {
            console.error('✗ Failed to parse valid code');
            console.error('  Errors:', validResult.errors);
            process.exit(1);
        }

        // Test invalid code
        const invalidResult = await p.parse('state Root');
        if (invalidResult.success || invalidResult.errors.length === 0) {
            console.error('✗ Failed to detect invalid code');
            process.exit(1);
        }

        console.log('✓ Parser functionality verified');

        // Test 6: Package size check
        console.log('\nTest 6: Checking package size...');
        const stats = fs.statSync(packagePath);
        const sizeKB = (stats.size / 1024).toFixed(2);
        console.log(`✓ Package size: ${sizeKB} KB`);

        if (stats.size > 1024 * 1024) { // > 1MB
            console.warn('⚠ Warning: Package size exceeds 1MB');
            console.warn('  Consider using a bundler (webpack/esbuild) to reduce size');
        }

        console.log('\n=== All Tests Passed ===');
        console.log('\nExtension is ready for installation:');
        console.log(`  code --install-extension ${packagePath} --force`);

    } catch (error) {
        console.error('✗ Test failed:', error.message);
        console.error('Stack:', error.stack);
        process.exit(1);
    }
})();
