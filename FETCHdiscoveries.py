
import json
import os
from html import unescape
from xml.sax.saxutils import escape

import requests
from bs4 import BeautifulSoup
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


URL = "https://livescience.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def clean_text(value):
    if not value:
        return ""
    return " ".join(unescape(str(value)).split())


def add_article(discoveries, seen_titles, title, description="", link=""):
    title = clean_text(title)
    description = clean_text(description)

    if not title or len(title) < 8:
        return

    key = title.lower()
    if key in seen_titles:
        return

    seen_titles.add(key)
    discoveries.append(
        {
            "title": title,
            "description": description
            or "Click the article link to read the full science report.",
            "link": link,
        }
    )


def extract_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    discoveries = []
    seen_titles = set()

    # Look explicitly for the main news card containers
    containers = soup.find_all(['div', 'article'], class_=lambda x: x and any(c in x for c in ['listingResult', 'content-card']))
    print(f"HTML news blocks matched: {len(containers)}")

    for container in containers:
        
        title_element = container.find(['h3', 'h2'])
        if not title_element:
            continue

        title = title_element.get_text(" ", strip=True)

        # here Skip global navigation elements or short sidebar tags
        if "Recent scientific discoveries" in title or len(title) < 15:
            continue

        
        description_element = container.find(['p', 'span'], class_=lambda x: x and any(c in x for c in ['synopsis', 'description', 'excerpt']))
        description = description_element.get_text(" ", strip=True) if description_element else "Select this entry to read the full scientific breakthrough review."

        # Fetch the destination link
        link_element = title_element.find("a") or container.find("a", href=True)
        link = link_element.get("href", "") if link_element else ""
        if link and link.startswith("/"):
            link = "https://www.livescience.com" + link

        # Add clean article without duplicate entries
        if title not in seen_titles:
            seen_titles.add(title)
            discoveries.append({
                "title": title,
                "description": description,
                "link": link
            })
            print(f"Added Breakthrough: {title[:50]}...")

    print(f"Extraction sequence complete. Total distinct items found: {len(discoveries)}")
    return discoveries


def extract_from_rss():
    rss_url = "https://www.livescience.com/feeds/all"

    try:
        response = requests.get(rss_url, headers=HEADERS, timeout=15)
        print(f"RSS status: {response.status_code}")
        print(f"RSS final URL: {response.url}")
        print(f"RSS content length: {len(response.content)}")

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.content, "html.parser")
        discoveries = []
        seen_titles = set()

        for item in soup.find_all("item"):
            title = item.find("title")
            description = item.find("description")
            link = item.find("link")

            add_article(
                discoveries,
                seen_titles,
                title.get_text(" ", strip=True) if title else "",
                description.get_text(" ", strip=True) if description else "",
                link.get_text(strip=True) if link else "",
            )

        return discoveries

    except requests.RequestException as error:
        print(f"RSS request failed: {error}")
        return []


def fetch_live_science_discoveries():
    print("Connection initiated to Live Science...")

    try:
        response = requests.get(URL, headers=HEADERS, timeout=15, allow_redirects=True)

        print(f"Page status: {response.status_code}")
        print(f"Downloaded HTML characters: {len(response.text)}")
        print(f"Final URL: {response.url}")

        if response.status_code != 200:
            print("The website rejected or blocked the request.")
        else:
            discoveries = extract_from_html(response.text)

            if discoveries:
                print(f"Successfully extracted {len(discoveries)} updates.")
                return discoveries

            print("The page loaded, but no matching articles were found.")

    except requests.RequestException as error:
        print(f"Network request failed: {error}")

    print("Trying the Live Science RSS feed...")
    discoveries = extract_from_rss()

    print(f"Successfully extracted {len(discoveries)} updates.")
    return discoveries


def generate_pdf_report(data, filename="Daily_Discoveries.pdf"):
    if not data:
        print("No data collected. Document generation skipped.")
        return

    print(f"Compiling findings into: {filename}...")

    document = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=15,
    )

    item_title_style = ParagraphStyle(
        "ItemTitle",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#2C3E50"),
        spaceBefore=12,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "ItemBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#4A5568"),
        spaceAfter=8,
    )

    story = [
        Paragraph("Daily Science Discoveries Report", title_style),
        Paragraph(
            "Compiled dynamically from Live Science articles.",
            body_style,
        ),
        Spacer(1, 15),
    ]

    for index, item in enumerate(data, 1):
        title = escape(f"{index}. {item['title']}")
        description = escape(item["description"])

        story.append(Paragraph(title, item_title_style))
        story.append(Paragraph(description, body_style))

        if item.get("link"):
            story.append(Paragraph(escape(item["link"]), body_style))

    document.build(story)
    print("PDF successfully built and closed safely.")


if __name__ == "__main__":
    output_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "Live_Science_Discoveries.pdf",
    )

    science_updates = fetch_live_science_discoveries()
    generate_pdf_report(science_updates, output_file)

