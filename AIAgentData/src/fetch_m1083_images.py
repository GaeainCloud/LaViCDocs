import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin

URL = "https://en.wikipedia.org/wiki/Family_of_Medium_Tactical_Vehicles"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_images():
    print(f"Fetching {URL}...")
    resp = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(resp.content, 'html.parser')
    
    images = []
    for img in soup.find_all('img'):
        src = img.get('src')
        if not src: continue
        full_url = urljoin(URL, src)
        if 'M1083' in full_url or 'FMTV' in full_url:
            images.append(full_url)
            print(f"Found: {full_url}")

    return images

if __name__ == "__main__":
    fetch_images()
