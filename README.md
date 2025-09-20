### Requirements

-**Python**: 3.11+

-**Deps**: `pypdf` (installed automatically if you use `uv`; otherwise `pip install pypdf`)

- Optional: **uv** (`uv` reads `pyproject.toml` / `uv.lock`)

### Quick start

Using uv (recommended):

```bash

uvrunpythonpdf-merge.py--help

uvrunpythonpdf-merge.pymergea.pdfb.pdf-omerged.pdf

uvrunpythonpdf-merge.pysplitinput.pdf--ranges"1-3,7,9-"--outdirout/

```

Plain Python:

```bash

# Optionally: python -m venv .venv && source .venv/bin/activate

pipinstallpypdf

python3pdf-merge.py--help

python3pdf-merge.pymergea.pdfb.pdf-omerged.pdf

python3pdf-merge.pysplitinput.pdf--ranges"1-3,7,9-"--outdirout/

```

### Usage

-**Merge**

```bash

python3pdf-merge.pymergein1.pdfin2.pdfin3.pdf\

  -o out/merged.pdf \

--passwordSECRET\

  --overwrite

```

-**Split**

```bash

python3pdf-merge.pysplitinput.pdf\

  --ranges "1-3,7,9-" \

--outdirout/\

  --name-pattern "{base}_part_{start}-{end}.pdf" \

--passwordSECRET\

  --overwrite

```

### Range syntax (1-based, inclusive)

-**N**: page N (e.g., `7`)

-**A-B**: pages A through B (e.g., `4-9`)

-**-B**: pages 1 through B (e.g., `-3`)

-**A-**: pages A through last page (e.g., `10-`)

Examples: `"1-3,7,9-"`

### Notes

- Encrypted inputs must share the same password; pass it via `--password`.
- Merge preserves metadata (when present) from the first input.
- Default split filenames:
- Single page: `{base}_p{N}.pdf`
- Range: `{base}_p{A}-{B}.pdf`

-`--name-pattern` placeholders: `{base}`, `{page}`, `{start}`, `{end}`.
