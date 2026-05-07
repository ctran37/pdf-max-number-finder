import argparse
import io
import sys
import urllib.error
import urllib.request
import pdfplumber

from utils import (
    Hit,
    better_raw,
    better_scaled,
    detect_scale,
    get_prose_text,
    chunk_text,
    process_table,
    process_chunk,
)


def find_max_in_pdf(path: str) -> dict:
    best_raw = best_scaled = None
    global_scale = None

    try:
        pdf = pdfplumber.open(resolve_source(path))
    except FileNotFoundError:
        sys.exit(f"Error: file not found: {path}")
    except Exception as e:
        sys.exit(f"Error: could not open PDF ({type(e).__name__}): {e}")

    with pdf:
        for page_num, page in enumerate(pdf.pages):
            try:
                raw_hit, scaled_hit, page_scale = process_page(page, page_num + 1, global_scale)
            except Exception as e:
                print(f"Warning: skipping page {page_num + 1} ({type(e).__name__}): {e}", file=sys.stderr)
                continue
            best_raw = better_raw(best_raw, raw_hit)
            best_scaled = better_scaled(best_scaled, scaled_hit)
            if page_scale and global_scale is None:
                global_scale = page_scale

    return {
        "max_numerical_raw": best_raw.raw if best_raw else None,
        "max_numerical_adjusted": best_scaled.scaled if best_scaled else None,
        "global_scale": global_scale,
        "raw_hit": best_raw,
        "scaled_hit": best_scaled,
    }


def resolve_source(source: str) -> str | io.BytesIO:
    if source.startswith("http://") or source.startswith("https://"):
        try:
            with urllib.request.urlopen(source) as response:
                return io.BytesIO(response.read())
        except urllib.error.HTTPError as e:
            sys.exit(f"Error: failed to fetch URL ({e.code} {e.reason}): {source}")
        except urllib.error.URLError as e:
            sys.exit(f"Error: could not reach URL ({e.reason}): {source}")
    return source


def process_page(page, page_num: int, global_scale: int | None) -> tuple[Hit | None, Hit | None, int | None]:
    found_tables = page.find_tables()
    table_bboxes = [t.bbox for t in found_tables]
    extracted_tables = [t.extract() for t in found_tables]
    prose_text = get_prose_text(page, table_bboxes)

    page_scale = detect_scale(prose_text)
    effective_scale = page_scale or global_scale

    best_raw = best_scaled = None

    for t_idx, table in enumerate(extracted_tables):
        raw_hit, scaled_hit = process_table(table, page_num, t_idx, effective_scale)
        best_raw = better_raw(best_raw, raw_hit)
        best_scaled = better_scaled(best_scaled, scaled_hit)

    for chunk, chunk_start in chunk_text(prose_text):
        raw_hit, scaled_hit = process_chunk(chunk, chunk_start, prose_text, page_num, effective_scale)
        best_raw = better_raw(best_raw, raw_hit)
        best_scaled = better_scaled(best_scaled, scaled_hit)

    return best_raw, best_scaled, page_scale


def print_results(best_raw: Hit | None, best_scaled: Hit | None) -> None:
    print(f"\n{'='*60}")
    print("FINAL RESULTS")
    print(f"{'='*60}")

    if not best_raw and not best_scaled:
        print("No numerical values found in document.")
        print(f"\n{'='*60}\n")
        return

    if best_raw:
        print(f"max_numerical_raw     : {best_raw.raw:,.2f}")
        print(f"  Number in document  : '{best_raw.num_str}'")
        print(f"  Found at            : page {best_raw.page}, {best_raw.location}")
        print(f"  Context             : '...{best_raw.context}...'")
    print()

    if best_scaled:
        print(f"max_numerical_adjusted: {best_scaled.scaled:,.2f}")
        print(f"  Number in document  : '{best_scaled.num_str}' x {best_scaled.scale_source}")
        print(f"  Found at            : page {best_scaled.page}, {best_scaled.location}")
        print(f"  Context             : '...{best_scaled.context}...'")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find the largest numerical value in a PDF.")
    parser.add_argument("pdf", help="Path or URL to the PDF file")
    args = parser.parse_args()

    result = find_max_in_pdf(args.pdf)
    print_results(result["raw_hit"], result["scaled_hit"])