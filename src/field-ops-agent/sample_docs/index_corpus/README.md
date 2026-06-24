# Supplier docs corpus — upload set for Foundry IQ

This folder holds the **ready-to-upload documents** that back the field-ops agent's
`supplier_docs` knowledge tool. They are plain Markdown (git-safe, diffable, and
citation-friendly) generated from the supplier agreement JSON in the parent folder.

| Item | Value |
| --- | --- |
| Files | 12 (6 topics × 2 suppliers) |
| Suppliers | Cascade Fiber Services, LLC · Pacific OptoLink Networks, Inc. |
| Topics | MSA, certificate of insurance, rate card, SLA, safety attestation, dispatch quick reference |
| Format | Markdown with YAML front matter (supplier, vendor_id, agreement_id, document_type, dates) |

Each filename **is** the citation the agent prints (e.g. `cascade-fiber-rate-card.md`),
so keep names human-readable. The agent's instructions tell the model to *"cite
filenames in your answer"* — the front-matter `supplier` and `document_type` fields
also surface in retrieval, so don't strip them.

## Regenerate

```pwsh
python ../generate_index_corpus.py
```

Edit `../supplier_agreement.json` or `../pacific_optolink_agreement.json` and re-run;
the corpus is fully derived from those two files.

## Upload to the data source behind `supplier-docs-index`

The three Foundry IQ objects (see `../../SETUP-INTEGRATIONS.md` §2) chain like this:

```
index_corpus/*.md ──► supplier-docs-index ──► supplier-docs-ks ──► supplier-docs-kb
   (these files)        (Azure AI Search)      (knowledge source)   (knowledge base)
                                                                          │
                                                          Toolbox tool name: supplier_docs
```

### Option A — Portal upload (fastest for the demo)

1. In the Azure AI Search index `supplier-docs-index`, open **Import data** and point it
   at the blob container you back the index with.
2. Upload every `*.md` file in this folder to that container.
3. Run the indexer so the documents land in `supplier-docs-index`.

### Option B — Blob upload by CLI

```pwsh
az storage blob upload-batch `
  --account-name <storage-account> `
  --destination <container> `
  --source . `
  --pattern "*.md"
```

Then run the indexer that feeds `supplier-docs-index`.

### After upload

1. Create the knowledge source `supplier-docs-ks` over `supplier-docs-index`. In
   **sourceDataFields**, include the **file-name field** so citations resolve.
2. Create the knowledge base `supplier-docs-kb` referencing `supplier-docs-ks`.
3. Expose it through the Toolbox MCP endpoint with the tool name **exactly** `supplier_docs`.
   The default quickstart name is `knowledge_base_retrieve` — renaming is required or the
   agent silently falls back to its offline mock.

## What's in each file

- **MSA** — parties, term, governing law, key clauses.
- **Certificate of insurance** — carrier, policy numbers, limits, expiry, EMR.
- **Rate card** — labor/material codes with USD rates (the after-hours and P1 numbers
  the demo asks about).
- **SLA** — response/ack targets and credits.
- **Safety attestation** — EMR, training, attestation date.
- **Dispatch quick reference** — site, preferred connector, trunk, locker (the
  punchline facts: Cascade `LC/UPC Duplex`, Pacific `LC/APC Duplex`).
