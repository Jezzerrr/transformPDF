def parse_page_ranges(page_range_text, max_pages):
    page_range_text = page_range_text.strip()

    if not page_range_text:
        raise ValueError("Please enter at least one page number or page range.")

    pages = []

    parts = page_range_text.split(",")

    for part in parts:
        part = part.strip()

        if not part:
            continue

        if "-" in part:
            start_text, end_text = part.split("-", 1)

            start = int(start_text.strip())
            end = int(end_text.strip())

            if start > end:
                raise ValueError(f"Invalid page range: {part}")

            pages.extend(range(start, end + 1))

        else:
            pages.append(int(part))

    pages = list(dict.fromkeys(pages))

    for page in pages:
        if page < 1 or page > max_pages:
            raise ValueError(
                f"Page {page} is outside the PDF range. "
                f"This PDF has {max_pages} pages."
            )

    return pages


def parse_page_groups(text, max_pages):
    """
    Several page selections, separated by ';' (or new lines). Every group
    becomes its own PDF. The word 'end' means the last page.
    Example: "1-3; 4-end" -> [[1, 2, 3], [4, 5, ..., max_pages]]
    """
    text = text.lower().replace("end", str(max_pages)).replace("\n", ";")
    groups = [part for part in text.split(";") if part.strip()]
    if not groups:
        raise ValueError("Please enter at least one page number or page range.")
    return [parse_page_ranges(group, max_pages) for group in groups]


def format_page_ranges(pages):
    """[1, 2, 3, 5, 7, 8] -> "1-3,5,7-8" """
    parts = []
    start = previous = None
    for page in pages:
        if start is None:
            start = previous = page
        elif page == previous + 1:
            previous = page
        else:
            parts.append(f"{start}" if start == previous else f"{start}-{previous}")
            start = previous = page
    if start is not None:
        parts.append(f"{start}" if start == previous else f"{start}-{previous}")
    return ",".join(parts)
