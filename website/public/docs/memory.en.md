# Memory

ResearchClaw keeps a persistent research memory for the active runtime.

## What It Tracks

- recent conversation messages
- session count
- discussed papers
- research notes
- a compact summary of older conversation context
- plus a separate structured research state for projects, workflows, claims, experiments, and artifacts

## Storage

The current implementation stores memory state under the working dir:

```text
~/.researchclaw/
└── memory/
    ├── memory_state.json
    └── *.md                # optional notes / memory markdown files
```

This is different from older docs that described one JSON file per session.

The structured Research OS state is stored separately:

```text
~/.researchclaw/
└── research/
    └── state.json
```

## Related Runtime Features

- `/history` shows memory stats
- `/papers` lists recently discussed papers
- `/refs` summarizes the BibTeX library
- `memory_search()` searches the memory layer
- workspace APIs can list and read memory markdown files
- the Research APIs manage structured notes such as paper notes, experiment notes, writing notes, and decision logs

## Notes

- memory is local to the current runtime workspace
- compaction is covered separately in [Compact](./compact.md)
- chat/session memory and structured research state are related, but not the same storage layer
