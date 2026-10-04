// Replay generated statecharts in XState and write, per event, the active leaf
// path and the ordered entry/exit log.  Usage: node run_xstate.mjs cases.json out.json
import { createMachine, createActor } from 'xstate';
import { readFileSync, writeFileSync } from 'node:fs';

function build(node, log) {
  const cfg = {
    id: node.id,
    entry: () => log.push('enter ' + node.id),
    exit: () => log.push('exit ' + node.id),
  };
  if (node.children.length) {
    cfg.initial = node.initial;
    cfg.states = {};
    for (const c of node.children) cfg.states[c.name] = build(c, log);
    for (const h of node.history) {
      cfg.states[h.key] = { id: node.id + '.' + h.key, type: 'history', history: h.kind, target: h.target };
    }
  }
  if (node.on && Object.keys(node.on).length) cfg.on = node.on;
  return cfg;
}

function leafPath(rootName, value) {
  const path = [rootName];
  let v = value;
  while (typeof v === 'object') {
    const k = Object.keys(v)[0];
    path.push(k);
    v = v[k];
  }
  path.push(v);
  return path.join('.');
}

const cases = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const results = [];
for (const c of cases) {
  const log = [];
  const actor = createActor(createMachine(build(c.spec, log)));
  actor.start();
  const steps = [{ leaf: leafPath(c.spec.name, actor.getSnapshot().value), log: log.splice(0) }];
  for (const ev of c.events) {
    actor.send({ type: ev });
    steps.push({ leaf: leafPath(c.spec.name, actor.getSnapshot().value), log: log.splice(0) });
  }
  results.push(steps);
}
writeFileSync(process.argv[3], JSON.stringify(results));
