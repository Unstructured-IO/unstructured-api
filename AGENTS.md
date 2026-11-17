# unstructured-api

## Before committing

- **If your change alters anything a user can see or do** — the partition API's request/response
  behavior: endpoints, parameters, response fields, status codes and error messages — the
  acceptance suite may assert on it. Before finishing, run
  `cd acceptance && npm ci && npx acceptance-help update-for-product-change` and follow it.
  `npm ci` needs `AZURE_ARTIFACTS_TOKEN` exported; how to mint it is at the top of
  `acceptance/.npmrc`.
