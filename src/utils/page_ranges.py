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
