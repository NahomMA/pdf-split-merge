#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from typing import List, Tuple, Optional

from pypdf import PdfReader, PdfWriter


def err(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def require_exists(path: Path) -> None:
    if not path.exists():
        err(f"Input not found: {path}")


def parse_ranges(spec: str, total_pages: int) -> List[Tuple[int, int]]:
    tokens = [t.strip() for t in spec.split(",") if t.strip()]
    if not tokens:
        err("No pages matched ranges: (empty spec)")
    result: List[Tuple[int, int]] = []
    for tok in tokens:
        if tok == "-":
            err("Invalid range token: '-'")
        if "-" in tok:
            if tok.startswith("-"):
                # -B  => 1..B
                try:
                    end = int(tok[1:])
                except ValueError:
                    err(f"Invalid range token: '{tok}'")
                start = 1
            elif tok.endswith("-"):
                # A-  => A..end
                try:
                    start = int(tok[:-1])
                except ValueError:
                    err(f"Invalid range token: '{tok}'")
                end = total_pages
            else:
                a, b = tok.split("-", 1)
                try:
                    start, end = int(a), int(b)
                except ValueError:
                    err(f"Invalid range token: '{tok}'")
        else:
            try:
                start = end = int(tok)
            except ValueError:
                err(f"Invalid range token: '{tok}'")

        if start <= 0 or end <= 0:
            err(f"Range must be positive: '{tok}'")
        if start > end:
            err(f"Range start > end: '{tok}'")
        if start > total_pages or end > total_pages:
            err(f"Range out of bounds for file with {total_pages} pages: {tok}")
        result.append((start, end))

    if not result:
        err(f"No pages matched ranges: {spec}")
    return result


def open_reader(path: Path, password: Optional[str]) -> PdfReader:
    require_exists(path)
    fh = path.open("rb")
    try:
        reader = PdfReader(fh)
        if reader.is_encrypted:
            if not password:
                fh.close()
                err(f"File is encrypted: {path} (pass --password)")
            ok = reader.decrypt(password)
            if not ok:  # decrypt returns 0/1
                fh.close()
                err(f"Failed to decrypt: {path} (check --password)")
        return reader
    except Exception:
        fh.close()
        raise


def merge_cmd(inputs: list[str], output: str, password: str | None, overwrite: bool) -> None:
    from pathlib import Path
    import sys
    out_path = Path(output)
    if out_path.exists() and not overwrite:
        print(f"Refusing to overwrite existing file: {out_path} (use --overwrite)", file=sys.stderr)
        sys.exit(2)

    readers = []
    fhs = []
    try:
        for path in inputs:
            fh = open(path, "rb")
            fhs.append(fh)
            r = PdfReader(fh)
            if r.is_encrypted:
                if not password:
                    print(f"File is encrypted: {path} (pass --password)", file=sys.stderr)
                    sys.exit(2)
                if not r.decrypt(password):
                    print(f"Failed to decrypt: {path} (check --password)", file=sys.stderr)
                    sys.exit(2)
            readers.append(r)

        writer = PdfWriter()
        # preserve metadata from first input
        if readers and readers[0].metadata:
            md = {}
            for k, v in readers[0].metadata.items():
                if k and str(k).startswith("/"):
                    md[str(k)] = "" if v is None else str(v)
            if md:
                writer.add_metadata(md)

        for r in readers:
            for page in r.pages:
                writer.add_page(page)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("wb") as f:
            writer.write(f)
    finally:
        for fh in fhs:
            try: fh.close()
            except: pass


def make_split_name(base: str, start: int, end: int, pattern: Optional[str]) -> str:
    if pattern:
        # Users may supply either page or start/end; both are available.
        return pattern.format(base=base, page=start if start == end else None, start=start, end=end)
    if start == end:
        return f"{base}_p{start}.pdf"
    return f"{base}_p{start}-{end}.pdf"


def split_cmd(input_file: str, ranges_spec: str, outdir: str, password: Optional[str],
            name_pattern: Optional[str], overwrite: bool) -> None:
    in_path = Path(input_file)
    require_exists(in_path)
    out_dir = Path(outdir) if outdir else Path(".")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Open/decrypt
    fh = in_path.open("rb")
    try:
        reader = PdfReader(fh)
        if reader.is_encrypted:
            if not password:
                err(f"File is encrypted: {in_path} (pass --password)")
            ok = reader.decrypt(password)
            if not ok:
                err(f"Failed to decrypt: {in_path} (check --password)")

        total = len(reader.pages)
        ranges = parse_ranges(ranges_spec, total)
        base = in_path.stem

        # Plan filenames
        planned = []
        for (a, b) in ranges:
            name = make_split_name(base, a, b, name_pattern)
            planned.append(out_dir / name)

        # Overwrite guard
        clashes = [p for p in planned if p.exists()]
        if clashes and not overwrite:
            msg = "Refusing to overwrite existing files:\n" + "\n".join(str(p) for p in clashes) + "\n(use --overwrite)"
            err(msg)

        # Write outputs
        for (a, b), target in zip(ranges, planned):
            writer = PdfWriter()
            for i in range(a - 1, b):  # convert to 0-based
                writer.add_page(reader.pages[i])
            with target.open("wb") as out_f:
                writer.write(out_f)

    finally:
        try:
            fh.close()
        except Exception:
            pass


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pdf-merge.py", description="Merge and split PDFs (pypdf).")
    sub = p.add_subparsers(dest="cmd", required=True)

    # merge
    m = sub.add_parser("merge", help="Merge PDFs in the given order")
    m.add_argument("inputs", nargs="+", help="Input PDF files (2+)")
    m.add_argument("-o", "--output", required=True, help="Output PDF file")
    m.add_argument("--password", help="Password for encrypted inputs (applied to all)")
    m.add_argument("--overwrite", action="store_true", help="Allow overwriting existing output")

    # split
    s = sub.add_parser("split", help="Split a PDF by page ranges")
    s.add_argument("input", help="Input PDF file")
    s.add_argument("--ranges", required=True, help='Page ranges, e.g. "1-3,7,9-" (1-based, inclusive)')
    s.add_argument("--outdir", default=".", help="Output directory (default: current dir)")
    s.add_argument("--name-pattern", help="Filename pattern using {base}, {page}, {start}, {end}")
    s.add_argument("--password", help="Password if input is encrypted")
    s.add_argument("--overwrite", action="store_true", help="Allow overwriting existing files")

    return p

def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "merge":
        merge_cmd(inputs=args.inputs, output=args.output, password=args.password, overwrite=args.overwrite)
    elif args.cmd == "split":
        split_cmd(
            input_file=args.input,
            ranges_spec=args.ranges,
            outdir=args.outdir,
            password=args.password,
            name_pattern=args.name_pattern,
            overwrite=args.overwrite,
        )
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()

