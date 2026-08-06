# unstructured-api

Helm chart for the self-hosted [Unstructured API](https://github.com/Unstructured-IO/unstructured-api),
a REST API that partitions documents with the
[`unstructured`](https://github.com/Unstructured-IO/unstructured) library.

It deploys a stateless Deployment behind a Service. The image bundles ML models, Tesseract OCR,
and LibreOffice, so it is CPU/memory heavy — size `resources` accordingly for `hi_res` workloads.

## Quick start

```bash
helm install unstructured-api ./charts/unstructured-api
kubectl port-forward svc/unstructured-api 8000:80
curl --fail http://localhost:8000/healthcheck
```

Requirements: Kubernetes >= 1.23, Helm >= 3.8, and a node that can fit
`resources.requests` (default `500m` / `3Gi`).

## Configuration

Common values. See [`values.yaml`](./values.yaml) for the rest.

### Image

| Key | Default | Description |
|---|---|---|
| `image.repository` | `quay.io/unstructured-io/unstructured-api` | Image repository. |
| `image.tag` | `""` | Image tag; defaults to the chart `appVersion`. |
| `image.pullPolicy` | `IfNotPresent` | Pull policy. |
| `imagePullSecrets` | `[]` | Secrets for a private registry. |

### Workload

| Key | Default | Description |
|---|---|---|
| `replicaCount` | `1` | Replicas (ignored when autoscaling is on). |
| `resources.requests` | `500m` / `3Gi` | CPU / memory requests. |
| `resources.limits` | `4` / `8Gi` | CPU / memory limits. |
| `terminationGracePeriodSeconds` | `120` | Time to finish in-flight requests on shutdown. |
| `progressDeadlineSeconds` | `900` | Rollout deadline (the image is slow to pull). |
| `podSecurityContext` / `securityContext` | non-root uid/gid `1000`, drop `ALL` | Security contexts. |
| `nodeSelector` / `tolerations` / `affinity` | `{}` | Scheduling. |
| `podAntiAffinity` | `soft` | Spread replicas across nodes: `soft`, `hard`, `""`. |

### Application (env vars)

| Key | Default | Env var | Description |
|---|---|---|---|
| `config.port` | `8000` | `PORT` | Listen port. |
| `config.host` | `0.0.0.0` | `HOST` | Bind interface. |
| `config.workers` | `1` | `WORKERS` | Uvicorn workers per pod. |
| `config.memoryFreeMinimumMb` | `2048` | `UNSTRUCTURED_MEMORY_FREE_MINIMUM_MB` | Return 503 below this free memory; `0` disables. |
| `config.allowedOrigins` | `""` | `ALLOWED_ORIGINS` | Comma-separated CORS origins. |
| `config.maxLifetimeSeconds` | `""` | `MAX_LIFETIME_SECONDS` | Graceful self-restart after N seconds. |
| `config.env` | `prod` | `ENV` | Silences the noisy uvicorn error logger. |
| `config.parallelMode.*` | off | `UNSTRUCTURED_PARALLEL_MODE_*` | Experimental parallel PDF mode. |
| `extraEnv` / `extraEnvFrom` | `[]` | | Extra environment variables. |

### Service, Ingress, autoscaling

| Key | Default | Description |
|---|---|---|
| `service.enabled` | `true` | Create a Service (required by Ingress and the helm test). |
| `service.type` / `service.port` | `ClusterIP` / `80` | Service type and port. |
| `ingress.enabled` | `false` | Create an Ingress. |
| `autoscaling.enabled` | `false` | Create a HorizontalPodAutoscaler. |
| `autoscaling.minReplicas` / `maxReplicas` | `1` / `5` | HPA bounds. |
| `autoscaling.targetCPUUtilizationPercentage` | `80` | CPU target (% of the CPU request). |
| `podDisruptionBudget.enabled` | `false` | Create a PodDisruptionBudget. |

## API-key auth

Set `UNSTRUCTURED_API_KEY` so clients must send the `unstructured-api-key` header. The chart
creates the Secret, or point it at an existing one:

```yaml
apiKey:
  enabled: true
  value: "super-secret-key"
# or
apiKey:
  enabled: true
  existingSecret: my-unstructured-secret
  existingSecretKey: UNSTRUCTURED_API_KEY
```

## Probes

All probes hit `GET /healthcheck`. This only confirms the HTTP server is up — it does not check
that models are loaded (they load on the first request) or that memory is free (the 503 guard is
in the partition endpoint). So readiness won't drain an overloaded pod; deeper checks would need
an app-side endpoint. The `startupProbe` covers process start only, not model loading.

## Scaling

Each worker loads its own copy of the models, so scale out (`replicaCount` / `autoscaling`) rather
than raising `config.workers`. HPA CPU utilisation is relative to the CPU request, so tune
`targetCPUUtilizationPercentage` and `resources.requests.cpu` together.

Scale-out isn't instant: the image is ~10GB, so a replica on a node without it cached can't serve
until the pull finishes (minutes). Pre-pull or cache the image, or keep a warm node pool.
`progressDeadlineSeconds: 900` keeps rollouts from failing mid-pull.

`podAntiAffinity: hard` gives one pod per node, but needs at least `maxReplicas` schedulable nodes
or the extras stay `Pending`.

## Test

```bash
helm test my-release
```

Runs a Pod that curls `/healthcheck` through the Service.