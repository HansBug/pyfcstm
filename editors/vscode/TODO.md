# VSCode Extension Roadmap for FCSTM

This document tracks the planned evolution of the VSCode extension under [editors/vscode/](.) from a static language package into a lightweight but practical editing experience for FCSTM.

## Project Positioning and Design Principles

The FCSTM VSCode extension should follow these product and engineering principles:

- The extension must remain language-neutral at runtime.
  - It may rely on JavaScript, because that is native to the VSCode extension host.
  - It must not require Python, Java, or any other external language/runtime at extension runtime.
  - It should avoid non-native runtime dependencies unless they are strictly necessary for the VSCode extension host itself.
- The extension must remain compatible with a very wide range of VSCode versions, including both older and newer releases where feasible.
- The extension must support stable offline use.
  - All core editor features must work without network access.
  - No editor feature should depend on remote services or internet availability.
- The existing ANTLR grammar should be reused as the single source of truth for syntax-driven capabilities.
- The repository should include a long-term maintainable grammar generation entrypoint under [editors/vscode/](.) so that JavaScript lexer/parser artifacts can be regenerated in the future.
  - A local build script or Makefile-style command should be kept in the VSCode extension directory for this purpose.
- Prefer features with strong user impact and moderate implementation cost.
- Avoid introducing a full language server in the near term.

## Technical Constraints

The roadmap below assumes the following constraints:

- No dependency on Python at extension runtime.
- No dependency on the existing CLI at extension runtime.
- No full language server in the near term.
- Reuse the existing ANTLR grammar as the single source of truth whenever feasible.
- Prefer features with strong user impact and moderate implementation cost.

---

## Current State

The extension currently provides:

- File association for `.fcstm`
- TextMate syntax highlighting
- Basic language configuration
  - comments
  - brackets
  - auto-closing pairs
  - surrounding pairs
  - region-based folding markers
- snippets

The extension does **not** yet provide:

- snippets
- diagnostics
- parser-backed features
- outline/document symbols
- completion
- hover help
- folding providers
- formatting
- code actions

---

## Delivery Phases

## Phase P0 - High-Value Foundation Features

These features have the best balance of user impact and engineering cost.

### P0 Feature Checklist

- [x] Add FCSTM snippets
- [x] Generate and integrate ANTLR-based JavaScript parser runtime
- [x] Add syntax diagnostics based on the generated parser
- [x] Add document symbols / outline support
- [x] Add lightweight completion support
- [x] Add hover documentation support
- [x] Implement esbuild all-in-one bundle architecture

### P0 Detailed Plan

#### 1. Add FCSTM snippets

**Goal**

Make FCSTM authoring much faster by covering the most repetitive language constructs with snippet insertion.

**Why this matters**

FCSTM has many recurring structural patterns. Snippets are the fastest way to improve authoring speed without requiring any parser or semantic engine.

**Planned snippet groups**

- Variable definitions
  - `def int ...`
  - `def float ...`
- State declarations
  - simple state
  - composite state
  - pseudo state
  - named state
- Event declarations
  - simple event
  - named event
- Transitions
  - initial transition
  - plain transition
  - event transition
  - guarded transition
  - effect transition
  - guarded + effect transition
- Lifecycle blocks
  - `enter {}`
  - `during {}`
  - `exit {}`
  - `during before {}`
  - `during after {}`
  - `>> during before {}`
  - `>> during after {}`
- Action declarations
  - `abstract`
  - `ref`

**Implementation tasks**

- [x] Add snippet contribution to `package.json`
- [x] Create snippet definition file
- [x] Cover at least 15-20 high-frequency FCSTM templates
- [x] Ensure tab stops follow common FCSTM writing order
- [x] Verify snippet prefixes are short and memorable
- [x] Add snippet usage notes to `README.md`

**Acceptance criteria**

- A new FCSTM user can create a minimal working state machine mostly through snippet expansion.
- Common transition and lifecycle patterns are available without manual boilerplate typing.

---

#### 2. Generate and integrate ANTLR-based JavaScript parser runtime

**Goal**

Use the existing FCSTM ANTLR grammar as the source of truth for parser-backed editor features in VSCode.

**Why this matters**

This is the core technical foundation for diagnostics and future lightweight language intelligence, while staying independent from Python and the CLI.

**Scope**

- Generate JavaScript or TypeScript-consumable lexer/parser artifacts from `Grammar.g4`
- Bundle the generated runtime into the extension
- Expose a small parsing adapter inside the extension codebase

**Implementation tasks**

- [x] Decide generated target format
  - [x] JavaScript target implemented from canonical grammar
  - [x] TypeScript adapter implemented
- [x] Define a reproducible generation script under [editors/vscode/](.)
- [x] Add or define a local regeneration command under [editors/vscode/](.)
  - [x] Prefer a Makefile or similarly simple local build entrypoint
  - [x] Ensure the command remains callable for long-term maintenance
- [x] Add ANTLR runtime dependency for Node/VSCode extension host only if it fits the extension dependency policy
- [x] Generate lexer/parser artifacts from the FCSTM grammar
- [x] Store generated lexer/parser artifacts inside the VSCode extension tree
- [x] Add a parser adapter module inside the extension
- [x] Normalize parse entry selection for full FCSTM documents
- [x] Add error listener plumbing
- [x] Verify generated artifacts are packaged correctly into VSIX
- [x] Document how grammar regeneration should be performed after grammar changes
- [x] Ensure generation does not require the extension runtime to depend on Python or CLI execution

**Acceptance criteria**

- [x] The extension can parse a full `.fcstm` document locally in the extension host.
- [x] The parser path is deterministic and tied to the grammar file, not to handwritten duplicate grammar logic.
- [x] Lexer/parser regeneration is documented and callable from within the VSCode extension directory.

**Implementation Notes**

The VSCode extension now uses a pure JavaScript ANTLR parser generated from the canonical `Grammar.g4`.

**Parser Architecture:**
- **Grammar Source**: `pyfcstm/dsl/grammar/Grammar.g4` (single source of truth for both Python and JavaScript)
- **JavaScript Artifacts**: Generated to `editors/vscode/parser/` using ANTLR 4.9.3
- **Parser Adapter**: `src/parser.ts` loads generated artifacts via dynamic import and normalizes ANTLR diagnostics
- **Runtime**: `antlr4@4.9.3` (exact version pinned for artifact compatibility)
- **Error Handling**: Matches Python parser behavior with enhanced error messages

**Grammar Label Compatibility:**
- The original grammar used `function=UFUNC_NAME` which conflicted with JavaScript's reserved `function` keyword
- Updated to `func_name=UFUNC_NAME` for cross-target compatibility
- Python listener updated to use `ctx.func_name` accessor
- Both Python and JavaScript parsers now generate from the same grammar revision

**Regeneration Workflow:**
1. Modify `pyfcstm/dsl/grammar/Grammar.g4`
2. Regenerate Python parser: `make antlr_build` (from project root)
3. Update Python consumers if grammar structure changed
4. Verify Python tests: `make unittest`
5. Regenerate JavaScript parser: `make parser` (from `editors/vscode/`)
6. Rebuild extension: `npm run compile`
7. Verify parser contract: `make verify-p0.2`

**Verification:**
- `make verify-p0.2` runs 32 comprehensive checkpoints covering valid and invalid FCSTM inputs
- Extension runtime remains fully local with no Python, Java, or CLI dependencies
- Full documentation in `README.md`

---

#### 3. Add syntax diagnostics based on the generated parser

**Goal**

Show parser errors directly in VSCode Problems and inline squiggles.

**Why this matters**

This is the single most important productivity feature after snippets. Users need immediate feedback about syntax errors while editing.

**Scope for first version**

Only syntax diagnostics are in scope initially.

Out of scope for the first version:

- advanced semantic validation
- cross-document analysis
- symbol resolution correctness checks
- type validation beyond what syntax provides

**Implementation tasks**

- [x] Add extension runtime entrypoint if not already present
- [x] Register a `DiagnosticCollection` for FCSTM
- [x] Parse active FCSTM documents on save
- [x] Add debounced parse-on-change
- [x] Capture ANTLR syntax errors with range information
- [x] Map parser errors to VSCode diagnostics
- [x] Clear stale diagnostics when documents are fixed or closed
- [x] Handle invalid partial edits gracefully
- [x] Verify diagnostics remain fully local and offline-safe

**Acceptance criteria**

- [x] Invalid FCSTM syntax produces clear diagnostics in the editor and Problems panel.
- [x] Fixing the syntax clears the diagnostics without restarting VSCode.

**Verification**

- `make verify-p0.3` runs 35 comprehensive test cases:
  - 10 valid code tests (no errors expected)
  - 25 error detection tests (various syntax errors)
  - Tests cover: missing semicolons, missing braces, missing brackets, invalid operators, invalid keywords, etc.
- All tests use real FCSTM code and validate actual parser behavior
- Test output uses emoji (✅/❌) and detailed error reporting for easy debugging

**Implementation Notes**

- **Files**: `src/diagnostics.ts`, enhanced `src/parser.ts`
- **Features**: Real-time error detection with 500ms debounce, smart error messages, document version tracking
- **Performance**: Diagnostics mode uses `buildParseTrees = false` for optimal performance

---

#### 4. Add document symbols / outline support

**Goal**

Expose the structural hierarchy of an FCSTM document in the Outline view and breadcrumbs.

**Why this matters**

FCSTM is hierarchical by design. Outline support greatly improves navigation in non-trivial files.

**Planned symbol coverage**

- variables
- states
- pseudo states
- events

Transitions are intentionally lower priority for the first version.

**Implementation tasks**

- [x] Add `DocumentSymbolProvider`
- [x] Build symbols from parse tree where practical
- [x] Represent nested states as nested symbols
- [x] Include variables and events at appropriate levels
- [x] Choose stable symbol kinds
  - variables -> `Variable`
  - states -> `Class`
  - events -> `Event`
- [x] Ensure outline ordering follows source order
- [x] Verify provider behavior on both older and newer supported VSCode releases

**Acceptance criteria**

- [x] Users can navigate nested state hierarchies via Outline.
- [x] The symbol tree reflects the FCSTM document structure closely enough to be useful in real files.

**Verification**

- `make verify-p0.4` runs 35 comprehensive test cases:
  - 4 variable extraction tests
  - 6 state extraction tests (leaf, composite, pseudo, named)
  - 3 event extraction tests
  - 16 mixed extraction tests (variables + states + events)
  - 6 edge case tests (partial parsing, comments, empty states)
- Tests validate symbol names, kinds, details, and nested hierarchies
- Mock VSCode API allows testing in Node.js environment

**Implementation Notes**

- **Files**: `src/symbols.ts`, enhanced `src/parser.ts` with `parseTree()` method
- **Features**: Extracts variables, states (leaf/composite/pseudo), events with display names, nested hierarchies
- **Performance**: Symbol extraction mode uses `buildParseTrees = true` only when needed

---

#### 5. Add lightweight completion support

**Goal**

Provide practical completions without requiring a full language server.

**Why this matters**

Even basic context-aware completion makes FCSTM writing feel much more native inside VSCode.

**Completion scope for first version**

- keywords
- built-in constants
- built-in functions
- document-local names where practical
  - state names
  - event names
  - variable names

**Implementation tasks**

- [x] Add `CompletionItemProvider`
- [x] Provide keyword completions
- [x] Provide math constant completions
- [x] Provide built-in function completions
- [x] Extract document-local symbols from parse tree or lightweight index
- [x] Offer state names in transition source/target contexts where practical
- [x] Offer event names in event contexts where practical
- [x] Offer variable names in expression contexts where practical
- [x] Add insertion snippets or commit characters where helpful
- [x] Prevent noisy completion in comments/strings
- [x] Verify completion remains useful without any network or external service dependency

**Acceptance criteria**

- [x] Users get useful keyword and built-in completions anywhere relevant.
- [x] Document-local names appear often enough to reduce repetitive typing meaningfully.

**Verification**

- `make verify-p0.5` runs 30 comprehensive test cases:
  - 5 keyword completion tests
  - 2 built-in constant tests
  - 3 built-in function tests
  - 5 document-local symbol tests
  - 5 comment/string filtering tests
  - 5 context-specific tests
  - 5 edge case tests
- Tests validate completion items, kinds, and filtering behavior
- Mock VSCode API allows testing in Node.js environment

**Implementation Notes**

- **Files**: `src/completion.ts`, enhanced `src/extension.ts`
- **Features**: Keywords, constants (pi, E, tau, true/false), functions (sin, cos, sqrt, etc.), document symbols (variables, states, events)
- **Filtering**: Completions disabled in comments and strings
- **Performance**: Uses parse tree extraction for document-local symbols

---

#### 6. Add hover documentation support

**Goal**

Explain FCSTM constructs in place without requiring the user to leave the editor.

**Why this matters**

FCSTM includes several constructs whose meaning is easy to forget during writing, especially event scoping and lifecycle aspect syntax.

**Planned hover topics**

- `::`
- `:`
- `/`
- `[*]`
- `pseudo state`
- `effect`
- `abstract`
- `ref`
- `during before`
- `during after`
- `>> during before`
- `>> during after`

**Implementation tasks**

- [x] Add `HoverProvider`
- [x] Define concise built-in documentation strings for core FCSTM constructs
- [x] Match hovers by token or parse-tree context where practical
- [x] Use markdown formatting for compact examples
- [x] Avoid overly verbose hovers
- [x] Ensure hover results remain useful without semantic resolution
- [x] Verify hover behavior stays compatible with a broad VSCode version range

**Acceptance criteria**

- [x] Hovering core FCSTM constructs provides short, accurate, high-value explanations.
- [x] Hovers reduce the need to consult external documentation for common syntax questions.

**Verification**

- `make verify-p0.6` runs 35 comprehensive test cases:
  - 3 event scoping operator tests (::, :, /)
  - 2 pseudo-state marker tests ([*])
  - 5 keyword tests (pseudo, effect, abstract, ref, named)
  - 4 lifecycle aspect tests (during before/after, >> during before/after)
  - 5 lifecycle action tests (enter, during, exit, before, after)
  - 4 control flow/declaration tests (if, def, state, event)
  - 5 edge case tests (no hover on identifiers, whitespace)
  - 7 context-specific tests (operators in transitions, keywords in context)
- Tests validate hover titles, descriptions, and examples
- Mock VSCode API with proper document.getText() implementation

**Implementation Notes**

- **Files**: `src/hover.ts`, enhanced `src/extension.ts`
- **Features**: Hover docs for operators (::, :, /), keywords, lifecycle aspects, with markdown examples
- **Coverage**: 26 FCSTM constructs documented with title, description, and example code
- **Context-Aware**: Distinguishes between :: and :, handles multi-character operators correctly

---

#### 7. Implement esbuild all-in-one bundle architecture

**Goal**

Replace multi-file TypeScript compilation with esbuild bundling to create a single, self-contained extension file that includes all dependencies.

**Why this matters**

The original architecture had dependency loading issues in VSCode environments. A single bundled file eliminates runtime dependency resolution problems, improves extension loading performance, and simplifies deployment.

**Scope**

- Replace TypeScript compiler (`tsc`) with esbuild for extension bundling
- Bundle all ANTLR-generated parser files into the extension
- Bundle antlr4 runtime library
- Bundle all extension sources
- Maintain separate TypeScript compilation for verification scripts
- Preserve all existing functionality and test compatibility

**Implementation tasks**

- [x] Add esbuild as dev dependency
- [x] Create esbuild configuration (`esbuild.config.js`)
- [x] Configure esbuild to bundle all sources and dependencies
- [x] Migrate parser loading from dynamic import to static require
- [x] Fix ANTLR line number conversion (1-based to 0-based)
- [x] Update Makefile with separate build targets
  - [x] `make build` - Production bundle with esbuild
  - [x] `make build-dev` - Development bundle with sourcemaps
  - [x] `make build-tsc` - TypeScript compilation for verification
- [x] Update package.json scripts
  - [x] `compile` uses esbuild
  - [x] `compile:tsc` for verification scripts
- [x] Update .vscodeignore to only include bundled file
- [x] Remove parser/package.json module type declaration
- [x] Verify all 167 tests pass with bundled architecture
- [x] Update documentation (README.md, build guides)

**Acceptance criteria**

- [x] Single `dist/extension.js` file contains all dependencies
- [x] ANTLR-generated parser files (GrammarLexer, GrammarParser, GrammarVisitor) bundled
- [x] antlr4 runtime library bundled
- [x] All extension sources bundled
- [x] No runtime dependency loading issues
- [x] All 167 verification tests pass (P0.2-P0.6)
- [x] Build time significantly faster than TypeScript compiler
- [x] VSIX package size reasonable and functional

**Implementation Notes**

**Architecture:**
- **Build Tool**: esbuild (replaces tsc for extension bundling)
- **Bundle Output**: `dist/extension.js` (246KB, single file)
- **Bundle Contents**:
  - ANTLR-generated parser: ~104KB (GrammarLexer, GrammarParser, GrammarVisitor)
  - antlr4 runtime library: ~80KB
  - Extension sources: ~20KB (extension.ts, parser.ts, diagnostics.ts, symbols.ts, completion.ts, hover.ts)
- **Build Time**: ~77ms (26x faster than tsc ~2s)
- **VSIX Size**: 83KB (compressed)

**Technical Details:**

1. **esbuild Configuration** (`esbuild.config.js`):
   - Entry point: `src/extension.ts`
   - Bundle: true (includes all dependencies)
   - External: `vscode` (VSCode API must remain external)
   - Format: CommonJS (required by VSCode)
   - Platform: Node.js
   - Target: Node 16 (VSCode 1.60+ compatibility)
   - Minification: Production mode only
   - Source maps: Development mode only
   - Tree shaking: Enabled
   - Metafile: Enabled for bundle analysis

2. **Parser Loading Migration**:
   ```typescript
   // Before: Dynamic import (not bundled by esbuild)
   const nativeImport = new Function('specifier', 'return import(specifier);');
   const [lexerModule, parserModule] = await Promise.all([...]);

   // After: Static require (bundled by esbuild)
   const GrammarLexer = require('../parser/GrammarLexer').default;
   const GrammarParser = require('../parser/GrammarParser').default;
   ```

3. **Build Targets**:
   - `make build`: Production bundle (minified, no sourcemaps)
   - `make build-dev`: Development bundle (sourcemaps, no minification)
   - `make build-tsc`: TypeScript compilation for verification scripts (out/ directory)
   - Verification scripts use `out/` directory (separate from bundle)
   - Extension uses `dist/extension.js` (bundled)

4. **Module System**:
   - Removed `"type": "module"` from `parser/package.json`
   - Unified CommonJS throughout (no ESM/CommonJS conflicts)
   - esbuild handles all module resolution

5. **Line Number Fix**:
   - ANTLR reports 1-based line numbers
   - VSCode expects 0-based line numbers
   - Added conversion in error listener: `line: line - 1`

**Benefits:**

- **Reliability**: No runtime dependency loading issues
- **Performance**:
  - Build: 77ms vs 2s (26x faster)
  - Loading: Single file loads faster than multiple modules
- **Simplicity**:
  - Single file deployment
  - No manual dependency management in .vscodeignore
  - Cleaner package structure
- **Maintainability**:
  - Bundle analysis shows exact size contributions
  - Easy to identify large dependencies
  - Clear separation between extension bundle and verification scripts

**Verification:**

All 167 tests pass:
- ✅ P0.2: Parser integration (32 tests)
- ✅ P0.3: Syntax diagnostics (35 tests)
- ✅ P0.4: Document symbols (35 tests)
- ✅ P0.5: Code completion (30 tests)
- ✅ P0.6: Hover documentation (35 tests)

**Bundle Analysis:**

Top contributors to bundle size:
- `parser/GrammarParser.js`: 84.9KB (34.6%)
- `antlr4/atn/ParserATNSimulator.js`: 17.0KB (6.9%)
- `parser/GrammarLexer.js`: 16.2KB (6.6%)
- `antlr4/atn/ATNDeserializer.js`: 9.8KB (4.0%)
- `antlr4/atn/LexerATNSimulator.js`: 6.9KB (2.8%)
- `src/hover.ts`: 6.2KB (2.5%)
- `src/parser.ts`: 4.1KB (1.7%)
- `parser/GrammarVisitor.js`: 3.4KB (1.4%)

**Migration Impact:**

- **For Users**: No changes, extension works the same
- **For Developers**:
  - Use `make build` instead of `npm run compile`
  - Verification scripts still use `make build-tsc`
  - All existing workflows preserved
- **For CI/CD**: No changes, `make package` still works

---

## Phase P1 - Grammar and Editing Experience Reinforcement

This phase strengthens the existing language package behavior and keeps the declarative/editor-facing layer polished.

### P1 Feature Checklist

- [x] Improve TextMate syntax highlighting coverage
- [x] Improve language configuration details
- [ ] Add dedicated folding range provider
- [ ] Add selection range provider

### P1 Detailed Plan for Syntax Highlighting and Language Configuration Reinforcement

This section is included in extra detail because it is already selected for implementation together with all P0 items.

#### A. Syntax Highlighting Reinforcement

**Goal**

Make highlighting more accurate, more complete, and more aligned with the FCSTM grammar and documentation.

**Current issues to address**

- The TextMate grammar should stay explicitly aligned with the ANTLR grammar and the shipped VSCode grammar copy.
- Some token categories are still broad and can be made more precise.
- Naming scopes can be improved for states, events, and declarations.
- Highlighting quality should be verified against the grammar and example documents.

**Detailed implementation checklist**

- [x] Audit TextMate grammar against the ANTLR grammar and documentation
- [x] Verify hexadecimal, decimal, float, and scientific notation coverage
- [x] Verify multi-character operator ordering remains correct
  - [x] `**` before `*`
  - [x] `<<` before `<`
  - [x] `<=`, `>=`, `==`, `!=` before single-character comparisons
  - [x] `&&`, `||` before `!`
  - [x] `::` before `:`
  - [x] `->` before `-`
  - [x] `>>` before `>`
- [x] Improve scopes for declaration keywords
  - [x] `state`
  - [x] `pseudo`
  - [x] `event`
  - [x] `def`
  - [ ] `named`
- [x] Improve scopes for lifecycle and modifier keywords
  - [x] `enter`
  - [x] `during`
  - [x] `exit`
  - [x] `before`
  - [x] `after`
  - [x] `abstract`
  - [x] `ref`
  - [x] `effect`
  - [x] `if`
- [x] Add or refine scopes for type keywords
  - [x] `int`
  - [x] `float`
- [x] Add or refine scopes for state names in declarations where feasible
- [x] Add or refine scopes for event names in declarations where feasible
- [x] Add or refine scopes for built-in constants
  - [x] `true`, `false`
  - [x] `True`, `False`
  - [x] `pi`, `E`, `tau`
- [x] Add or refine scopes for built-in functions
- [x] Verify string handling with escape sequences
- [x] Verify comments remain correct for `//`, `/* */`, and `#`
- [x] Run or update grammar validation workflow for representative FCSTM files
- [x] Refresh README examples if highlighting capabilities change materially
- [x] Ensure highlighting changes do not depend on network access or non-extension runtimes

**Expected outcome**

- FCSTM source code highlights more accurately and more consistently across themes.
- Common declarations and language constructs become easier to visually scan.

---

#### B. Language Configuration Reinforcement

**Goal**

Improve editing behavior for selection, pairing, and structure-aware text operations.

**Current issues to address**

- `wordPattern` is generic and may not align well with FCSTM symbol forms.
- Folding markers are limited to region comments.
- Pairing behavior should be reviewed against actual FCSTM writing patterns.

**Detailed implementation checklist**

- [x] Revisit `wordPattern` for FCSTM-specific token navigation behavior
- [x] Test double-click selection on representative FCSTM forms
  - [x] simple identifiers
  - [x] dotted references like `StateA.UserInit`
  - [x] absolute event names like `/GlobalEvent`
  - [x] local event syntax around `::EventName`
  - [x] pseudo-state token `[*]`
  - [x] numeric literals including `0x...`
- [x] Refine `wordPattern` based on real editing behavior rather than generic regex assumptions
- [x] Review auto-closing pairs for correctness and ergonomics
  - [x] braces
  - [x] brackets
  - [x] parentheses
  - [x] double quotes
  - [x] single quotes
  - [x] block comments
- [x] Verify surrounding pairs are still appropriate
- [x] Re-evaluate whether single quotes should remain enabled if they are not meaningfully distinct in the DSL
- [x] Review bracket matching behavior for `[*]`
- [x] Keep region markers, but do not rely on them as the primary folding mechanism long term
- [x] Document any intentional configuration limitations in `README.md`
- [x] Verify language-configuration changes remain compatible across a broad VSCode version range

**Verification**

- `make verify-p1.b` validates the language configuration declaratively:
  - FCSTM-specific `wordPattern` coverage for identifiers, dotted references, absolute and local events, pseudo-state tokens, and numeric literals
  - bracket, auto-closing, and surrounding pair definitions
  - `package.json` wiring for `language-configuration.json`
- Manual VSCode checks should still confirm double-click selection, selection wrapping, and comment toggling behavior in a real editor session

---

#### C. Integration Notes for P0 + Syntax/Configuration Work

Because all P0 items and the syntax/config reinforcement are currently in scope together, implementation should be staged to reduce churn.

**Recommended order**

1. Stabilize TextMate grammar and language configuration
2. Add snippets
3. Add extension runtime scaffold
4. Integrate generated ANTLR parser
5. Add diagnostics
6. Add outline/document symbols
7. Add completion
8. Add hover
9. Reconcile README and packaging metadata

**Why this order**

- The declarative layer should be cleaned up before runtime-backed features depend on assumptions about tokens and editing behavior.
- Diagnostics and symbols should be built on a stable parse adapter.
- Completion and hover benefit from the indexing work done for symbols.

---

## Phase P2 - Nice-to-Have Editor Intelligence

### P2 Feature Checklist

- [ ] Add conservative formatter support
- [ ] Add limited goto declaration support
- [ ] Add lightweight code actions for obvious syntax fixes
- [ ] Add semantic token enhancement if needed

### Notes

These should only be tackled after P0 and P1 are stable.

---

## Non-Goals for Now

The following items are intentionally out of scope for the near term:

- Full language server implementation
- Python-backed validation or Python runtime dependency
- CLI-backed validation or generation features inside the extension
- Deep semantic validation equivalent to the Python model layer
- Cross-file rename/reference analysis
- Heavy formatting that rewrites document layout aggressively
- Any network-dependent feature for core editor capabilities

---

## Documentation and Maintenance Checklist

- [ ] Keep this roadmap updated as work progresses
- [ ] Check off completed features immediately after merge
- [ ] Document regeneration steps for any ANTLR-generated assets
- [ ] Keep README capability claims aligned with actual extension behavior
- [ ] Add example FCSTM files for manual QA of editor features
- [ ] Keep local generation commands under [editors/vscode/](.) usable for long-term maintenance
- [ ] Recheck supported VSCode version compatibility when new APIs are introduced
- [ ] Preserve offline usability for all core editor features

---

## Implementation Status Summary

### Selected for Immediate Work

The current selected scope is:

- [x] P0.1 Snippets
- [x] P0.2 ANTLR-based JavaScript parser runtime
- [x] P0.3 Syntax diagnostics
- [x] P0.4 Document symbols / outline
- [x] P0.5 Lightweight completion
- [x] P0.6 Hover documentation
- [x] P1.A Syntax highlighting reinforcement
- [ ] P1.B Language configuration reinforcement

### Deferred

- [ ] Folding range provider
- [ ] Selection range provider
- [ ] Formatter
- [ ] Goto declaration
- [ ] Code actions
- [ ] Semantic tokens
