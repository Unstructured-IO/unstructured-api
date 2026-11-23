import { defineAcceptanceConfig } from "@utic/acceptance-core";

// The framework (env loading + secret fetch + shared tag policy + Keycloak auth + the
// ctx/secrets fixtures + timeouts + trace/report conventions + bddgen) comes from
// @utic/acceptance-core. This repo owns only its own Gherkin under ./features and step
// definitions under ./steps.
//
// `steps` is narrowed to the .ts sources, overriding core's default `steps/**/*.{ts,js}`.
// This suite is also publishable as a test package, and that build compiles steps/*.ts to
// steps/*.js in place (see tsconfig.json) — with the default glob, a build artifact left
// behind by an interrupted pack would register every step twice. Publishing is the only
// thing that produces .js here, so a local run should never look at it.
export default defineAcceptanceConfig({ steps: ["steps/**/*.ts"] });
