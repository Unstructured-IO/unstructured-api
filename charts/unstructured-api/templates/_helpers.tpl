{{/*
Expand the name of the chart.
*/}}
{{- define "unstructured-api.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
*/}}
{{- define "unstructured-api.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "unstructured-api.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "unstructured-api.labels" -}}
helm.sh/chart: {{ include "unstructured-api.chart" . }}
{{ include "unstructured-api.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "unstructured-api.selectorLabels" -}}
app.kubernetes.io/name: {{ include "unstructured-api.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use.
*/}}
{{- define "unstructured-api.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "unstructured-api.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Name of the Secret holding the API key.
*/}}
{{- define "unstructured-api.apiKeySecretName" -}}
{{- if .Values.apiKey.existingSecret }}
{{- .Values.apiKey.existingSecret }}
{{- else }}
{{- printf "%s-api-key" (include "unstructured-api.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Affinity: explicit .Values.affinity wins, otherwise render the podAntiAffinity preset.
*/}}
{{- define "unstructured-api.affinity" -}}
{{- if .Values.affinity -}}
{{- toYaml .Values.affinity -}}
{{- else if eq .Values.podAntiAffinity "hard" -}}
podAntiAffinity:
  requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchLabels:
          {{- include "unstructured-api.selectorLabels" . | nindent 10 }}
      topologyKey: kubernetes.io/hostname
{{- else if eq .Values.podAntiAffinity "soft" -}}
podAntiAffinity:
  preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchLabels:
            {{- include "unstructured-api.selectorLabels" . | nindent 12 }}
        topologyKey: kubernetes.io/hostname
{{- end -}}
{{- end -}}

{{/*
Validate configuration.
*/}}
{{- define "unstructured-api.validateValues" -}}
{{- if and .Values.apiKey.enabled (not .Values.apiKey.existingSecret) (not .Values.apiKey.value) -}}
{{- fail "apiKey.enabled is true but neither apiKey.value nor apiKey.existingSecret is set." -}}
{{- end -}}
{{- if and .Values.config.parallelMode.enabled (not .Values.config.parallelMode.url) -}}
{{- fail "config.parallelMode.enabled is true but config.parallelMode.url is empty." -}}
{{- end -}}
{{- if and .Values.ingress.enabled (not .Values.service.enabled) -}}
{{- fail "ingress.enabled requires service.enabled=true." -}}
{{- end -}}
{{- if not (has .Values.podAntiAffinity (list "" "soft" "hard")) -}}
{{- fail "podAntiAffinity must be one of: \"\", soft, hard." -}}
{{- end -}}
{{- end -}}