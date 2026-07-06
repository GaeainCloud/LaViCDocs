import os
from pathlib import Path

from config import DOWNLOADS_DIR, apply_proxy_env
from logger import get_logger
from utils.image_utils import fetch_and_select_best, scrape_images_from_page

apply_proxy_env()
log = get_logger(__name__)
DOWNLOAD_DIR = str(DOWNLOADS_DIR)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Candidate sources - mix of Pages to scrape and Direct Image URLs
# Mapping of model names to specific search URLs or direct image candidates
targets = {
    "M1083_A1P2_Truck": [
        "https://en.wikipedia.org/wiki/Family_of_Medium_Tactical_Vehicles",
        "https://commons.wikimedia.org/wiki/Category:Family_of_Medium_Tactical_Vehicles",
        "https://upload.wikimedia.org/wikipedia/commons/2/23/3%29_Oshkosh-produced_M1083_A1P2_5-ton_MTV_cargo_in_A-%3Dkit_configuration.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/d/d3/M1083_A1P2_FMTV_at_Fort_McCoy.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/6/6d/M1083_FMTV_truck.jpg",
        "https://www.army-technology.com/projects/fmtv/",
    ],
    "Polaris_MRZR_Alpha": [
        "https://military.polaris.com/en-us/mrzr-alpha/",
        "https://upload.wikimedia.org/wikipedia/commons/4/4b/759th_Military_Police_Battalion_conducts_Polaris_Razor_drivers_training_%289089416%29.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/7/7a/759th_Military_Police_Battalion_conducts_Polaris_Razor_drivers_training_%289089401%29.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/5/52/Polaris_rzr-xp_1000.JPG",
        "https://www.polaris.com/en-us/military/mrzr-alpha/",
    ],
    "Dongfeng-15_Missile_Launcher": [
        "https://missilethreat.csis.org/missile/df-15/",
        "https://upload.wikimedia.org/wikipedia/commons/8/87/Dongfeng-15B.JPG",
        "https://upload.wikimedia.org/wikipedia/commons/5/54/The_military_parade_in_honor_of_the_70-th_anniversary_of_the_end_of_the_Second_world_war_04.jpg",
        "https://en.wikipedia.org/wiki/Dongfeng_(missile)",
        "https://www.militarytoday.com/missiles/df_15.htm",
    ],
    "Norinco_Lynx_CS_VP4": [
        "https://en.topwar.ru/135136-mnogocelevoy-vezdehod-norinco-cs-vp4-kitay.html",
        "https://www.army-guide.com/eng/product5723.html",
        "https://www.joint-forces.com/features/21779-chinese-armour-at-zhuhai-air-show-2018",
        "https://armyrecognition.com/defense_news_april_2022_global_security_army_industry/venezuelan_army_deploys_norinco_atv_lynx_amphibious_vehicles_in_operation_bolivarian_shield_2022.html",
    ],
    "Oshkosh_JLTV": [
        "https://oshkoshdefense.com/vehicles/light-tactical-vehicles/jltv/",
        "https://upload.wikimedia.org/wikipedia/commons/5/5f/M1278_JLTV_Heavy_Guns_Carrier_%28JLTV-HGC%29.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/e/e0/Humvee_vs_JLTV_comparison.jpg",
        "https://en.wikipedia.org/wiki/Joint_Light_Tactical_Vehicle",
        "https://www.army-technology.com/projects/joint-light-tactical-vehicle-jltv/",
    ],
    "Dongfeng_Mengshi_CSK181": [
        "https://en.wikipedia.org/wiki/Dongfeng_Mengshi",
        "https://upload.wikimedia.org/wikipedia/commons/1/1a/Dongfeng_Mengshi_02.jpg",
        "https://en.dongfeng-club.com/sub-model/dongfeng-mengshi-csk-181-32",
        "https://www.reddit.com/r/TankPorn/comments/1jsc080/csk181_gen_iii_dongfeng_mengshi_aka_chinese_squad/",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Dongfeng_Mengshi_02.jpg/1200px-Dongfeng_Mengshi_02.jpg",
    ],
}


def collect_candidates(urls):
    candidates = []
    for url in urls:
        lower = url.lower()
        if lower.endswith((".jpg", ".jpeg", ".png", ".webp")):
            candidates.append(url)
        else:
            candidates.extend(scrape_images_from_page(url))
    return list(dict.fromkeys(candidates))


for name, urls in targets.items():
    log.info(f"\nProcessing {name}...")
    all_candidates = collect_candidates(urls)
    log.info(f"Found {len(all_candidates)} unique candidates.")

    best = fetch_and_select_best(all_candidates, max_candidates=5, query=name)

    if best:
        save_path = Path(DOWNLOAD_DIR) / f"{name}.{best.format}"
        save_path.write_bytes(best.data)
        log.info(f"SUCCESS: Saved best image to {save_path}")
        with open(Path(DOWNLOAD_DIR) / "best_urls.txt", "a", encoding="utf-8") as uf:
            uf.write(f"{name}: {best.url}\n")
    else:
        log.warning(f"FAILURE: No suitable image found for {name}")
