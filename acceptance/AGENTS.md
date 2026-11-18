# Acceptance Tests — Instructions

The shared conventions ship with `@utic/acceptance-core`, at the version this suite locks. From
this directory:

```bash
npm ci                                          # installs exactly the locked framework version
npx acceptance-help conventions                 # shared rules + Gherkin guidelines; read before changing any scenario or step
npx acceptance-help update-for-product-change   # after a product change that may affect what this suite asserts
npx acceptance-help                             # every framework command and guide
```

This file holds only what is specific to this repo.

## This repo

- Surface: the partition API's request/response behaviour — `POST /general/v0/general` on
  `TEST_API_URL`, authenticated with `TEST_API_KEY` in the `unstructured-api-key` header. The
  scenarios call it directly; there is no UI here.
- Where it runs: staging by default (`TEST_ENV=staging npm test`). Its key comes from
  `acceptance-tests/staging` in Secrets Manager, which the standing SND `AcceptanceSecretsReadOnly`
  role can read. Not SND: API keys do not work on SND instances, so every scenario carries
  `@skip-snd`. transform-staging and transform-prod do not serve this API and are skipped too.
- This suite runs no scenario in this repo's CI. The `Acceptance contract` job only checks that
  every step binds and every scenario is collected. Real runs happen in `infra/acceptance`, which
  installs the published `@utic/unstructured-api-acceptance` package.
- Test files come from `s3://u10d-acceptance-test-data` under `unstructured-api/`, pinned by
  SHA-256.
