from urllib.parse import parse_qs, urlparse

def parse_last_page(link_header: str) -> int:
    """
    GitHub Link header에서 마지막 페이지 번호 추출. 없으면 1 반환.
    """
    if not link_header:
        return 1

    links = link_header.split(',')
    last_page = 1

    for link in links:
        parts = link.split(";")
        if len(parts) < 2:
            continue

        url_part = parts[0].strip().strip("<>")
        rel_part = parts[1].strip()

        if rel_part == 'rel="last"':
            parsed_url = urlparse(url_part)
            query = parse_qs(parsed_url.query)
            page_vals = query.get("page")
            if page_vals and page_vals[0].isdigit():
                last_page = int(page_vals[0])

    return last_page
