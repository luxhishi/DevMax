from pathlib import Path
import textwrap


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "DevMax_Reviewer_Guide.md"
TARGET = ROOT / "docs" / "DevMax_Reviewer_Guide.pdf"

PAGE_WIDTH = 612
PAGE_HEIGHT = 792
LEFT_MARGIN = 54
RIGHT_MARGIN = 54
TOP_MARGIN = 54
BOTTOM_MARGIN = 54
BODY_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN


def normalize_text(text: str) -> str:
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def wrap_text(text: str, font_size: int, indent: int = 0) -> list[str]:
    average_char_width = max(font_size * 0.52, 1)
    max_chars = max(int((BODY_WIDTH - indent) / average_char_width), 20)
    return textwrap.wrap(text, width=max_chars) or [""]


def parse_markdown(markdown_text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    for raw_line in markdown_text.splitlines():
        line = normalize_text(raw_line.rstrip())
        stripped = line.strip()

        if not stripped:
            blocks.append(("blank", ""))
        elif stripped.startswith("# "):
            blocks.append(("h1", stripped[2:].strip()))
        elif stripped.startswith("## "):
            blocks.append(("h2", stripped[3:].strip()))
        elif stripped.startswith("### "):
            blocks.append(("h3", stripped[4:].strip()))
        elif stripped.startswith("- "):
            blocks.append(("bullet", stripped[2:].strip()))
        elif stripped[:2].isdigit() and ". " in stripped:
            blocks.append(("number", stripped))
        else:
            blocks.append(("para", stripped))
    return blocks


def layout_lines(blocks: list[tuple[str, str]]) -> list[dict]:
    lines: list[dict] = []
    previous_kind = ""
    for kind, text in blocks:
        if kind == "blank":
            if lines and lines[-1]["text"] != "":
                lines.append({"text": "", "font": "F1", "size": 8, "leading": 10, "indent": 0})
            previous_kind = kind
            continue

        if kind == "h1":
            if lines and lines[-1]["text"] != "":
                lines.append({"text": "", "font": "F1", "size": 8, "leading": 10, "indent": 0})
            for piece in wrap_text(text, 22):
                lines.append({"text": piece, "font": "F2", "size": 22, "leading": 28, "indent": 0})
            lines.append({"text": "", "font": "F1", "size": 8, "leading": 12, "indent": 0})
        elif kind == "h2":
            if previous_kind not in {"blank", ""}:
                lines.append({"text": "", "font": "F1", "size": 8, "leading": 10, "indent": 0})
            for piece in wrap_text(text, 16):
                lines.append({"text": piece, "font": "F2", "size": 16, "leading": 21, "indent": 0})
            lines.append({"text": "", "font": "F1", "size": 8, "leading": 8, "indent": 0})
        elif kind == "h3":
            for piece in wrap_text(text, 13):
                lines.append({"text": piece, "font": "F2", "size": 13, "leading": 17, "indent": 0})
        elif kind == "bullet":
            wrapped = wrap_text(text, 11, indent=18)
            for index, piece in enumerate(wrapped):
                prefix = "- " if index == 0 else "  "
                lines.append({"text": prefix + piece, "font": "F1", "size": 11, "leading": 15, "indent": 12})
        elif kind == "number":
            wrapped = wrap_text(text, 11, indent=18)
            for piece in wrapped:
                lines.append({"text": piece, "font": "F1", "size": 11, "leading": 15, "indent": 12})
        else:
            for piece in wrap_text(text, 11):
                lines.append({"text": piece, "font": "F1", "size": 11, "leading": 15, "indent": 0})

        previous_kind = kind

    while lines and lines[-1]["text"] == "":
        lines.pop()
    return lines


def paginate(lines: list[dict]) -> list[list[dict]]:
    pages: list[list[dict]] = []
    current_page: list[dict] = []
    y = PAGE_HEIGHT - TOP_MARGIN

    for line in lines:
        leading = line["leading"]
        if line["text"] == "":
            y -= leading
            if current_page and y < BOTTOM_MARGIN:
                pages.append(current_page)
                current_page = []
                y = PAGE_HEIGHT - TOP_MARGIN
            continue

        if y - leading < BOTTOM_MARGIN:
            pages.append(current_page)
            current_page = []
            y = PAGE_HEIGHT - TOP_MARGIN

        current_page.append(
            {
                "x": LEFT_MARGIN + line["indent"],
                "y": y,
                "font": line["font"],
                "size": line["size"],
                "text": line["text"],
            }
        )
        y -= leading

    if current_page:
        pages.append(current_page)
    return pages


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_page_stream(page_lines: list[dict], page_number: int, page_total: int) -> str:
    commands = ["BT"]
    for line in page_lines:
        commands.append(f"/{line['font']} {line['size']} Tf")
        commands.append(f"1 0 0 1 {line['x']} {line['y']} Tm")
        commands.append(f"({pdf_escape(line['text'])}) Tj")

    footer_text = f"Page {page_number} of {page_total}"
    commands.append("/F1 10 Tf")
    commands.append(f"1 0 0 1 {PAGE_WIDTH - RIGHT_MARGIN - 70} 28 Tm")
    commands.append(f"({footer_text}) Tj")
    commands.append("ET")
    return "\n".join(commands)


def write_pdf(pages: list[list[dict]], target: Path) -> None:
    objects: list[bytes] = []

    def add_object(body: str | bytes) -> int:
        payload = body.encode("latin-1") if isinstance(body, str) else body
        objects.append(payload)
        return len(objects)

    font_regular = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    font_bold = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    page_object_ids: list[int] = []
    content_object_ids: list[int] = []

    pages_object_id = 0
    catalog_object_id = 0

    for page_index, page_lines in enumerate(pages, start=1):
        stream = build_page_stream(page_lines, page_index, len(pages))
        content_id = add_object(
            f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream"
        )
        content_object_ids.append(content_id)
        page_object_ids.append(0)

    kids_placeholder = " ".join(f"{obj_id} 0 R" for obj_id in page_object_ids)
    pages_object_id = add_object(
        f"<< /Type /Pages /Kids [ {kids_placeholder} ] /Count {len(page_object_ids)} /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] >>"
    )

    for index, content_id in enumerate(content_object_ids):
        page_body = (
            f"<< /Type /Page /Parent {pages_object_id} 0 R "
            f"/Resources << /Font << /F1 {font_regular} 0 R /F2 {font_bold} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        )
        page_object_ids[index] = add_object(page_body)

    objects[pages_object_id - 1] = (
        f"<< /Type /Pages /Kids [ {' '.join(f'{obj_id} 0 R' for obj_id in page_object_ids)} ] "
        f"/Count {len(page_object_ids)} /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] >>"
    ).encode("latin-1")

    catalog_object_id = add_object(f"<< /Type /Catalog /Pages {pages_object_id} 0 R >>")

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("latin-1"))
        output.extend(obj)
        output.extend(b"\nendobj\n")

    xref_position = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))

    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_object_id} 0 R >>\n"
            f"startxref\n{xref_position}\n%%EOF"
        ).encode("latin-1")
    )
    target.write_bytes(output)


def main() -> None:
    markdown = SOURCE.read_text(encoding="utf-8")
    blocks = parse_markdown(markdown)
    lines = layout_lines(blocks)
    pages = paginate(lines)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    write_pdf(pages, TARGET)
    print(f"Generated {TARGET}")


if __name__ == "__main__":
    main()
