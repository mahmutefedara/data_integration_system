from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag


class LinkExtractor:
    def extract(self, base_url: str, html: str):
        soup = BeautifulSoup(html or "", "html.parser")

        # text
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text("\n", strip=True)

        links = []
        for a in soup.select("a[href]"):
            href = a.get("href")
            if not href:
                continue
            abs_url = urljoin(base_url, href)
            abs_url, _ = urldefrag(abs_url)
            links.append(abs_url)


        seen = set()
        out = []
        for u in links:
            if u not in seen:
                seen.add(u)
                out.append(u)

        return text, out
