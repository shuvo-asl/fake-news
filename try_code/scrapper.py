import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

BASE_URL = "https://www.prothomalo.com"
EDU_URL = f"{BASE_URL}/education"

def scrape_prothomalo_education():
    data = []
    response = requests.get(EDU_URL, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(response.text, "html.parser")
    data_script = soup.find('script', id='static-page')
    if data_script:
        import json
        data = json.loads(data_script.string)
        print(data['qt']['data'])
    return None

    # find article links
    articles = soup.find_all("a", {"class": "title-link"}, href=True)
    for a in articles[:5]:  # limit to first 5 for demo
        url = BASE_URL + a['href']
        article_res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        article_soup = BeautifulSoup(article_res.text, "html.parser")

        title = article_soup.find("h1").text.strip() if article_soup.find("h1") else "No Title"
        body = " ".join([p.text for p in article_soup.find_all("p")])
        images = [img['src'] for img in article_soup.find_all("img") if 'src' in img.attrs]

        data.append({
            "title": title,
            "url": url,
            "text": body,
            "images": images,
            "scraped_at": datetime.now().isoformat()
        })

    return data

if __name__ == "__main__":
    scraped_data = scrape_prothomalo_education()
    print(scraped_data)
    # print(json.dumps(scraped_data, indent=2, ensure_ascii=False))
