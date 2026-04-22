# A Paper LaTeX Environment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an Overleaf-style LaTeX environment inside `/home/jellyz/Experiment/A_paper` so the thesis can compile directly on the host machine or through Docker using the same `main.tex` entrypoint.

**Architecture:** Convert `A_paper` from loose chapter fragments into a standard single-entry LaTeX project. Keep chapter files as included content, add a `ctex`-based main document, standardize compilation around `latexmk + xelatex`, and expose both local and Docker workflows through a small set of documented commands.

**Tech Stack:** LaTeX, `ctex`, `latexmk`, XeLaTeX, Make, Docker

---

### Task 1: Inspect chapter fragments for integration risks

**Files:**
- Reference: `/home/jellyz/Experiment/A_paper/abstract.tex`
- Reference: `/home/jellyz/Experiment/A_paper/1.tex`
- Reference: `/home/jellyz/Experiment/A_paper/2.tex`
- Reference: `/home/jellyz/Experiment/A_paper/3.tex`
- Reference: `/home/jellyz/Experiment/A_paper/4.tex`
- Reference: `/home/jellyz/Experiment/A_paper/5.tex`
- Reference: `/home/jellyz/Experiment/A_paper/6.tex`

**Step 1: Read each fragment and look for standalone-only commands**

Check whether any file contains commands that should not appear inside a `\input` fragment, such as `\documentclass`, `\begin{document}`, `\end{document}`, or package declarations.

**Step 2: Identify minimum compatibility edits**

List only the edits needed to make the fragments safe to include from `main.tex`.

**Step 3: Preserve chapter prose**

Do not rewrite thesis content unless a LaTeX integration problem forces a local fix.

### Task 2: Add the Overleaf-style main document

**Files:**
- Create: `/home/jellyz/Experiment/A_paper/main.tex`
- Create: `/home/jellyz/Experiment/A_paper/refs.bib`

**Step 1: Write the main document skeleton**

Create a `ctex`-based main file that defines:

- document class
- title metadata placeholders
- table of contents if appropriate
- the single `\begin{document}` / `\end{document}` pair
- `\input` statements for `abstract.tex` and `1.tex` through `6.tex`

**Step 2: Add optional bibliography support**

Add a safe placeholder `refs.bib` so bibliography support can be enabled later without restructuring the project.

**Step 3: Keep the template portable**

Avoid host-specific font paths or machine-specific package assumptions.

### Task 3: Add local compilation tooling

**Files:**
- Create: `/home/jellyz/Experiment/A_paper/latexmkrc`
- Create: `/home/jellyz/Experiment/A_paper/Makefile`

**Step 1: Configure `latexmk`**

Set the project to compile with XeLaTeX and make repeat runs predictable.

**Step 2: Add Make targets**

Create targets for:

- `pdf`
- `clean`
- `distclean`

Default `make` should build the PDF from `main.tex`.

**Step 3: Keep target naming simple**

Use command names that are easy to remember and match the README.

### Task 4: Add Docker fallback workflow

**Files:**
- Create: `/home/jellyz/Experiment/A_paper/Dockerfile`
- Create: `/home/jellyz/Experiment/A_paper/.dockerignore`
- Modify: `/home/jellyz/Experiment/A_paper/Makefile`

**Step 1: Define the LaTeX container**

Create a Docker image with the required LaTeX tooling to run the same `latexmk -xelatex main.tex` workflow.

**Step 2: Add Docker Make targets**

Expose:

- `docker-pdf`
- `docker-shell`

**Step 3: Keep output on the host**

Mount the project directory so generated PDF artifacts remain in `A_paper`.

### Task 5: Document usage and assumptions

**Files:**
- Create: `/home/jellyz/Experiment/A_paper/README.md`

**Step 1: Document local prerequisites**

State the expected host tools, especially `latexmk` and XeLaTeX availability.

**Step 2: Document Docker usage**

Explain how to build and compile through the container.

**Step 3: Document Overleaf alignment**

Explain that `main.tex` is the canonical entrypoint and the directory can be uploaded as a normal Overleaf project.

### Task 6: Verify the environment end to end

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/main.tex`
- Modify: `/home/jellyz/Experiment/A_paper/Makefile`
- Modify: `/home/jellyz/Experiment/A_paper/README.md`

**Step 1: Run local tool discovery**

Run:

```bash
latexmk -v
xelatex --version
docker --version
```

Expected: determine which local verification paths are available in the current machine.

**Step 2: Run local compile if available**

Run:

```bash
make -C /home/jellyz/Experiment/A_paper pdf
```

Expected: `main.pdf` is generated, or a concrete missing-tool error is identified.

**Step 3: Run Docker compile if available**

Run:

```bash
make -C /home/jellyz/Experiment/A_paper docker-pdf
```

Expected: `main.pdf` is generated through the container, or a concrete Docker/image issue is identified.

**Step 4: Tighten any integration issues**

Make only the minimal fixes required by actual compile errors.

**Step 5: Inspect the final diff**

Run:

```bash
git -C /home/jellyz/Experiment diff -- /home/jellyz/Experiment/A_paper /home/jellyz/Experiment/docs/plans/2026-04-16-latex-environment-design.md /home/jellyz/Experiment/docs/plans/2026-04-16-latex-environment.md
```

Expected: changes are limited to the LaTeX environment and its planning documents.
