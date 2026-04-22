# A Paper LaTeX Environment Design

**Goal:** Turn `/home/jellyz/Experiment/A_paper` into an Overleaf-style LaTeX project that can compile directly on the host machine and through Docker with the same main entrypoint.

## Current State

`/home/jellyz/Experiment/A_paper` currently contains only chapter fragments:

- `abstract.tex`
- `1.tex`
- `2.tex`
- `3.tex`
- `4.tex`
- `5.tex`
- `6.tex`

There is no `main.tex`, no document class declaration, no build tooling, and no environment documentation. That means the paper cannot currently compile as a standalone project locally or in an Overleaf-like workflow.

## Requirements

- Use an Overleaf-style project layout centered on a single `main.tex`.
- Default to a Chinese-paper-friendly compilation mode aligned with common Overleaf behavior.
- Support direct local compilation.
- Support Docker-based compilation as a fallback environment.
- Keep existing chapter content changes minimal.
- Avoid touching unrelated repository files because the worktree already contains other in-progress changes outside `A_paper`.

## Chosen Approach

Use a single-entry Overleaf-style structure with local-first compilation and Docker fallback.

### Why this approach

- It matches how Overleaf expects LaTeX projects to be organized: one main file plus included chapter files.
- It keeps daily editing fast on the host machine.
- It gives a reproducible fallback when the local TeX installation differs from the expected environment.
- It minimizes maintenance cost by keeping one canonical compile target instead of separate local and container project layouts.

## Project Structure

The paper directory will be extended with:

- `main.tex` as the canonical entrypoint
- `latexmkrc` for repeatable multi-pass builds
- `Makefile` for local and Docker commands
- `Dockerfile` for containerized compilation
- `.dockerignore` to keep build context clean
- `README.md` to document usage
- optional `refs.bib` placeholder for future bibliography support

The existing chapter files will remain as content fragments and be included from `main.tex` via `\input`.

## Compilation Strategy

The default compiler pipeline will be `latexmk + xelatex`.

### Rationale

- `xelatex` is the safer default for Chinese-language thesis content.
- `latexmk` mirrors the practical Overleaf workflow by coordinating repeated compilation runs and auxiliary files.
- Using the same `main.tex` entrypoint locally and in Docker reduces drift.

The LaTeX template will prefer a `ctex`-based document setup so Chinese typesetting works without hard-coding machine-specific font paths.

## Compatibility Goals

The local project should behave like a normal Overleaf upload:

- Overleaf can compile `main.tex` directly.
- Local users can run `make` or `latexmk -xelatex main.tex`.
- Docker users can run `make docker-pdf` without relying on host TeX packages.

This is not a byte-for-byte reproduction of Overleaf's internal platform, but it is designed to align with the project structure and build behavior a user expects from Overleaf.

## Command Surface

Planned commands:

- `make` or `make pdf` for local compilation
- `make clean` for auxiliary cleanup
- `make docker-pdf` for containerized compilation
- `make docker-shell` for debugging inside the LaTeX container

## Risk Areas

- Some chapter fragments may contain commands that only belong in a main preamble or a standalone document.
- Bibliography or figure dependencies may appear later and require extending the initial template.
- Exact package parity with Overleaf may vary depending on the local TeX Live installation or Docker base image.

## Validation Plan

Validation will focus on:

- confirming `main.tex` compiles locally if required tools are present
- confirming Docker-based compilation can generate the PDF
- confirming chapter files integrate cleanly as included fragments
- confirming the documented commands match the actual build behavior
