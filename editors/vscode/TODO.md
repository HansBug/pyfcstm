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
- [ ] Add lightweight completion support
- [ ] Add hover documentation support

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

- [ ] Add `CompletionItemProvider`
- [ ] Provide keyword completions
- [ ] Provide math constant completions
- [ ] Provide built-in function completions
- [ ] Extract document-local symbols from parse tree or lightweight index
- [ ] Offer state names in transition source/target contexts where practical
- [ ] Offer event names in event contexts where practical
- [ ] Offer variable names in expression contexts where practical
- [ ] Add insertion snippets or commit characters where helpful
- [ ] Prevent noisy completion in comments/strings
- [ ] Verify completion remains useful without any network or external service dependency

**Acceptance criteria**

- Users get useful keyword and built-in completions anywhere relevant.
- Document-local names appear often enough to reduce repetitive typing meaningfully.

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

- [ ] Add `HoverProvider`
- [ ] Define concise built-in documentation strings for core FCSTM constructs
- [ ] Match hovers by token or parse-tree context where practical
- [ ] Use markdown formatting for compact examples
- [ ] Avoid overly verbose hovers
- [ ] Ensure hover results remain useful without semantic resolution
- [ ] Verify hover behavior stays compatible with a broad VSCode version range

**Acceptance criteria**

- Hovering core FCSTM constructs provides short, accurate, high-value explanations.
- Hovers reduce the need to consult external documentation for common syntax questions.

---

## Phase P1 - Grammar and Editing Experience Reinforcement

This phase strengthens the existing language package behavior and keeps the declarative/editor-facing layer polished.

### P1 Feature Checklist

- [x] Improve TextMate syntax highlighting coverage
- [ ] Improve language configuration details
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

- [ ] Revisit `wordPattern` for FCSTM-specific token navigation behavior
- [ ] Test double-click selection on representative FCSTM forms
  - [ ] simple identifiers
  - [ ] dotted references like `StateA.UserInit`
  - [ ] absolute event names like `/GlobalEvent`
  - [ ] local event syntax around `::EventName`
  - [ ] pseudo-state token `[*]`
  - [ ] numeric literals including `0x...`
- [ ] Refine `wordPattern` based on real editing behavior rather than generic regex assumptions
- [ ] Review auto-closing pairs for correctness and ergonomics
  - [ ] braces
  - [ ] brackets
  - [ ] parentheses
  - [ ] double quotes
  - [ ] single quotes
  - [ ] block comments
- [ ] Verify surrounding pairs are still appropriate
- [ ] Re-evaluate whether single quotes should remain enabled if they are not meaningfully distinct in the DSL
- [ ] Review bracket matching behavior for `[*]`
- [ ] Keep region markers, but do not rely on them as the primary folding mechanism long term
- [ ] Document any intentional configuration limitations in `README.md`
- [ ] Verify language-configuration changes remain compatible across a broad VSCode version range

**Expected outcome**

- Cursor movement, token selection, and pairing behavior will feel more natural for FCSTM documents.
- Editing common FCSTM constructs will require fewer manual corrections.

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
- [ ] P0.5 Lightweight completion
- [ ] P0.6 Hover documentation
- [x] P1.A Syntax highlighting reinforcement
- [ ] P1.B Language configuration reinforcement

### Deferred

- [ ] Folding range provider
- [ ] Selection range provider
- [ ] Formatter
- [ ] Goto declaration
- [ ] Code actions
- [ ] Semantic tokens
