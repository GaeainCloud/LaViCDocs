import requests
import re
import sys

def get_wiki_image_url(page_url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(page_url, headers=headers)
        if response.status_code != 200:
            print(f"Error fetching {page_url}: Status {response.status_code}")
            return None
        
        # Look for the original file link. 
        # Pattern: <a href="https://upload.wikimedia.org/wikipedia/commons/..." class="internal" ...>Original file</a>
        # Or just find the first upload.wikimedia.org link that ends with .jpg/.JPG and is not a thumbnail
        
        content = response.text
        # Common pattern for the full resolution image in the 'Original file' link
        match = re.search(r'href="(https://upload\.wikimedia\.org/wikipedia/commons/[^"]+)" class="internal"', content)
        if match:
            return match.group(1)
        
        # Fallback: look for the main image display
        match = re.search(r'class="fullImageLink" id="file"><a href="(https://upload\.wikimedia\.org/wikipedia/commons/[^"]+)"', content)
        if match:
            return match.group(1)
            
        print(f"Could not find image URL in {page_url}")
        return None
    except Exception as e:
        print(f"Exception fetching {page_url}: {e}")
        return None

if __name__ == "__main__":
    urls = [
        "https://commons.wikimedia.org/wiki/File:US_Navy_051202-N-9362D-004_An_F-14D_Tomcat_prepares_to_launch_off_of_the_flight_deck_of_the_Nimitz-class_aircraft_carrier_USS_Theodore_Roosevelt_(CVN_71).jpg",
        "https://commons.wikimedia.org/wiki/File:Rafale_M_of_Flottile_12F_in_flight_2014.JPG",
        "https://commons.wikimedia.org/wiki/File:A_PLAN_Shenyang_J-15_carrier-based_fighter_aircraft_takes_off_from_Chinese_aircraft_carrier_PLANS_Liaoning_(CV-16)_20221218.jpg"
    ]
    
    for url in urls:
        img_url = get_wiki_image_url(url)
        print(f"Page: {url}")
        print(f"Image: {img_url}")
        print("-" * 20)
