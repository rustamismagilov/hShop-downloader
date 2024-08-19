import requests
from bs4 import BeautifulSoup
import re
from tqdm import tqdm
import os
import urllib.parse
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

baseurl = "https://hshop.erista.me"

# Set up Selenium
options = Options()
options.headless = True
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def get_main_categories():
    driver.get(baseurl)
    time.sleep(1)  # Wait for the page to fully load
    soup = BeautifulSoup(driver.page_source, "html.parser")
    categories = soup.find_all("a", href=re.compile(r'^/c/'))
    return categories

def get_headers():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/57.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:46.0) Gecko/20100101 Firefox/46.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9",
    ]
    return {
        'User-Agent': random.choice(user_agents),
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': baseurl
    }

def get_games():
    categories = get_main_categories()
    print("Select main categories (comma separated, '*' for all):")
    for i, category in enumerate(categories, start=1):
        print(f"{i}. {category.text.strip()}")
    selections = input("Enter your selections: ")

    if selections.strip() == '*':
        selected_categories = categories
    else:
        selected_categories = []
        for selection in selections.split(','):
            selection = selection.strip()
            if not selection.isdigit() or int(selection) not in range(1, len(categories) + 1):
                print(f"Invalid selection '{selection}', please try again. Example: 1,2,3")
                return
            selected_categories.append(categories[int(selection) - 1])

    for selected_category in selected_categories:
        category_url = baseurl + selected_category['href']
        download_games_in_category(category_url)

def download_games_in_category(category_url):
    driver.get(category_url)
    time.sleep(1)  # Wait for the page to fully load
    soupRegion = BeautifulSoup(driver.page_source, "html.parser")
    region = soupRegion.find("div", class_="list pre-top")
    regex = re.findall(r'href="([^"]+)', str(region))
    nom = region.find_all("h3", class_="green bold")
    region = ([i.text for i in nom])

    # Retrieve the list of subcategories for the selected main category
    sub_categories = {}
    for i, j in zip(regex, region):
        if "/s/" in i:
            sub_categories[j] = i

    # Display a menu to select subcategories
    print(f"Select subcategories for {category_url.replace(baseurl + '/c/', '')} (comma separated, '*' for all):")
    sub_category_list = list(sub_categories.items())
    for i, (name, url) in enumerate(sub_category_list, start=1):
        print(f"{i}. {name}")
    selections = input("Enter your selections: ")

    if selections.strip() == '*':
        selected_sub_categories = sub_category_list
    else:
        selected_sub_categories = []
        for selection in selections.split(','):
            selection = selection.strip()
            if not selection.isdigit() or int(selection) not in range(1, len(sub_category_list) + 1):
                print(f"Invalid selection '{selection}', please try again. Example: 1,2,3")
                return
            selected_sub_category_name, selected_sub_category = sub_category_list[int(selection) - 1]
            selected_sub_categories.append((selected_sub_category_name, selected_sub_category))

    for selected_sub_category_name, selected_sub_category in selected_sub_categories:
        download_path = f"./downloads/{category_url.replace(baseurl + '/c/', '')}/{selected_sub_category_name}"
        os.makedirs(download_path, exist_ok=True)

        offset = 0
        while True:
            url = baseurl + selected_sub_category + f"?count=100&offset={offset}"
            driver.get(url)
            time.sleep(1)  # Wait for the page to fully load
            soupOffset = BeautifulSoup(driver.page_source, "html.parser")
            content = soupOffset.find("div", class_="list pre-top")
            game_list = re.findall(r'href="([^"]+)', str(content))

            if not game_list:
                break

            download(game_list, download_path)

            if len(game_list) < 100:
                break

            offset += 100

            time.sleep(random.uniform(1, 3))

def download(urls, download_path):
    for url in urls:
        download_game(baseurl + url, download_path)

def download_game(url, download_path):
    try:
        headers = get_headers()
        driver.get(url)
        time.sleep(10)  # Wait for the page to fully load
        game_page = BeautifulSoup(driver.page_source, "html.parser")
        
        # Check for Direct Download button
        download_link = game_page.find("a", class_="btn btn-c3", string="Direct Download")
        if download_link:
            download_url = download_link['href']
        else:
            # Check for download link pattern
            download_url = game_page.find("a", href=re.compile(r'https://download\d+\.erista\.me/content/\d+\?token=\w+'))
            if download_url:
                download_url = download_url['href']

        if download_url:
            response = requests.get(download_url, headers=headers, stream=True)
            
            # Extract the ID from the game URL
            game_id = url.split('/')[-1]
            content_disposition = response.headers.get('content-disposition', '')
            filename = re.findall('filename="(.+)"', content_disposition)
            if filename:
                filename = urllib.parse.unquote(filename[0])
                filename = re.sub(r'[<>:\"/\\\|\?\*]', '', filename)
                filename = filename.replace('%20', ' ')
                filename = html_decode(filename)
                
                filename_parts = filename.rsplit('.', 1)
                filename = f"{filename_parts[0]}_[hID-{game_id}].{filename_parts[1]}"
                
                extension = filename.split('.')[-1]
                tempfilename = filename.replace(f'.{extension}', f'.{extension}.part')
                
                full_temp_path = os.path.join(download_path, tempfilename)
                full_final_path = os.path.join(download_path, filename)
                
                total_length = int(response.headers.get('content-length', 0))
                
                if os.path.exists(full_final_path) and os.path.getsize(full_final_path) == total_length:
                    print(f"{filename} already downloaded and matches the expected size.")
                    return
                
                with open(full_temp_path, 'wb') as f, tqdm(
                    total=total_length,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=f"{filename} ({total_length/1024/1024:.2f} MB)"
                ) as bar:
                    for data in response.iter_content(chunk_size=4096):
                        f.write(data)
                        bar.update(len(data))

                os.rename(full_temp_path, full_final_path)
                print(f"Downloaded: {filename}")
            else:
                print("Filename could not be determined.")
        else:
            print("No valid download link found.")
    except requests.exceptions.RequestException as e:
        print("An error occurred while downloading the game:", e)
    except Exception as e:
        print("An unexpected error occurred:", e)

def html_decode(filename):
    # Insert your HTML decoding logic here
    filename = filename.replace('%3A', ':')
    filename = filename.replace('%2F', '/')
    filename = filename.replace('%2C', ',')
    filename = filename.replace('%5F', '_')
    filename = filename.replace('%28', '(')
    filename = filename.replace('%29', ')')
    filename = filename.replace("'", '')
    return filename

if __name__ == "__main__":
    get_games()
    driver.quit()
