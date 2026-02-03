import requests
import hashlib
import os

def get_wikimedia_url(filename):
    filename = filename.replace(" ", "_")
    m = hashlib.md5(filename.encode('utf-8')).hexdigest()
    return f"https://upload.wikimedia.org/wikipedia/commons/{m[0]}/{m[:2]}/{filename}"

def download_file():
    # Target: M1083 MTV.png
    # Wikimedia usually keeps original filenames
    filename = "M1083_MTV.png"
    url = get_wikimedia_url(filename)
    print(f"Calculated URL: {url}")
    
    output_path = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models\downloads\M1083_A1P2_Truck.png"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(resp.content)
            print("Download success!")
        else:
            print(f"Failed: {resp.status_code}")
            # Try without underscores if failed?
            # Or try searching
            
            # Backup: Military-Today image
            backup_url = "http://www.military-today.com/trucks/m1083_fmtv.jpg"
            print(f"Trying backup: {backup_url}")
            resp = requests.get(backup_url, headers=headers)
            if resp.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(resp.content)
                print("Download success (backup)!")
            else:
                print(f"Backup failed: {resp.status_code}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    download_file()
