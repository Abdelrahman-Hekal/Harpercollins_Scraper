from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService 
import undetected_chromedriver as uc
import pandas as pd
import time
import csv
import sys
import numpy as np
import re 

def initialize_bot():

    # Setting up chrome driver for the bot
    chrome_options  = webdriver.ChromeOptions()
    # suppressing output messages from the driver
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--window-size=1920,1080')
    # adding user agents
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    chrome_options.add_argument("--incognito")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # running the driver with no browser window
    chrome_options.add_argument('--headless')
    # disabling images rendering 
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.page_load_strategy = 'normal'
    # installing the chrome driver
    driver_path = ChromeDriverManager().install()
    chrome_service = ChromeService(driver_path)
    # configuring the driver
    driver = webdriver.Chrome(options=chrome_options, service=chrome_service)
    driver.set_page_load_timeout(10000)
    driver.maximize_window()

    return driver

def scrape_harpercollins(path):

    start = time.time()
    print('-'*75)
    print('Scraping harpercollins.com ...')
    print('-'*75)
    # initialize the web driver
    driver = initialize_bot()

    # initializing the dataframe
    data = pd.DataFrame()

    # if no books links provided then get the links
    if path == '':
        name = 'harpercollins_data.xlsx'
        # getting the books under each category
        links = []   
        homepages = ["https://www.harpercollins.com/collections/award-winners", "https://www.harpercollins.com/collections/bestsellers", "https://www.harpercollins.com/collections/books-for-tweens", "https://www.harpercollins.com/collections/large-print-titles", "https://www.harpercollinsfocus.com/"]

        nbooks = 0
        for homepage in homepages:
            npages = 0
            while True:
                npages += 1
                if homepage[-1] != '/':
                    url = homepage + "?page=" + str(npages)
                else:
                    url = homepage

                driver.get(url)
                # scraping books urls
                try:
                    titles = wait(driver, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.ais-hit.ais-product")))
                except:
                    titles = wait(driver, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.image-wrapper")))

                for title in titles:
                    try:                                  
                        link = wait(title, 2).until(EC.presence_of_element_located((By.TAG_NAME, "a"))).get_attribute('href')
                        links.append(link)
                        nbooks += 1 
                        print(f'Scraping the url for book {nbooks}')
                    except Exception as err:
                        pass

                # checking for the next page
                try:
                    wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//a[@aria-label='Next']")))
                except:
                    break
                    
        # saving the links to a csv file
        print('-'*75)
        print('Exporting links to a csv file ....')
        with open('harpercollins_links.csv', 'w', newline='\n', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Link'])
            for row in links:
                writer.writerow([row])

    scraped = []
    if path != '':
        df_links = pd.read_csv(path)
        name = path.split('\\')[-1][:-4]
        name = name + '_data.xlsx'
    else:
        df_links = pd.read_csv('harpercollins_links.csv')

    links = df_links['Link'].values.tolist()

    try:
        data = pd.read_excel(name)
        scraped = data['Title Link'].values.tolist()
    except:
        pass

    # scraping books details
    print('-'*75)
    print('Scraping Books Info...')
    print('-'*75)
    n = len(links)
    for i, link in enumerate(links):
        try:
            if link in scraped: continue
            driver.get(link)           
            details = {}
            print(f'Scraping the info for book {i+1}\{n}')            
            # title and title link
            title_link, title = '', ''              
            try:
                title_link = link
                title = wait(driver, 2).until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).get_attribute('textContent').replace('\n', '').strip().title() 
            except:
                print(f'Warning: failed to scrape the title for book: {link}')               
                
            details['Title'] = title
            details['Title Link'] = title_link                          
            # Author and author link
            author, author_link = '', ''
            try:
                try:
                    p = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.authorsParse")))
                except:
                    p = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.sp__the-author")))

                tags = wait(p, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "a")))
                for tag in tags:
                    author_link += tag.get_attribute('href') + ', '
                    author += tag.get_attribute('textContent') + ', '

                details['Author'] = author[:-2]            
                details['Author Link'] = author_link[:-2]
            except:
                pass

            # price
            price = ''
            try:
                div = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//div[@id='price']")))
                try:
                    price = wait(div, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.special-price-label"))).get_attribute('textContent').split(' ')[-1].replace('$', '')
                except:
                    price = div.get_attribute('textContent').replace('$', '').strip()
            except:
                try:
                    price = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.sp__the-price"))).get_attribute('textContent').replace('\n', ' ').split(' ')[-1].replace('$', '')
                except:
                    pass          
                
            details['Price'] = price            
            
            # format
            form = ''
            try:
                form = wait(driver, 2).until(EC.presence_of_element_located((By.TAG_NAME, "option"))).get_attribute('textContent').strip()
            except:
                pass          
                
            details['Format'] = form           
                               
            # ISBN
            keywords = ["ISBN 10:","ISBN:", "Imprint:", "On Sale:", "Pages:", "List Price:", "Price:", "BISAC", "Age:", "Trimsize:", "Publisher:", "Publication Date:", "Category"]
            ISBN, ISBN10, imprint, date, npages, age, cat = '', '', '', '', '', '', ''
            try:
                try:
                    tag = wait(driver, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.description-content-pane")))[1]
                except:
                    tag = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.sp__the-details")))
                
                text = tag.get_attribute('textContent')

                for word in keywords:
                    text = text.replace(word, '\n'+word)
                elems = text.split('\n')
                for elem in elems:
                    if 'ISBN 10:' in elem:
                        ISBN10 = elem.replace('ISBN 10:', '').strip()
                    elif 'ISBN:' in elem:
                        ISBN = elem.replace('ISBN:', '').strip()
                    elif 'Imprint:' in elem:
                        imprint = elem.replace('Imprint:', '').strip()
                    elif 'On Sale:' in elem:
                        date = elem.replace('On Sale:', '').strip()
                    elif 'Pages:' in elem:
                        npages = elem.replace('Pages:', '').replace('pages', '').strip()  
                    elif 'Age:' in elem:
                        age = elem.replace('Age:', '').strip()                     
                    elif 'BISAC' or "Category" in elem:
                        elem = elem.split(':')[-1].replace('/', ', ').replace('*', '').strip()
                        cat += elem + ', '

                if len(cat) > 0:
                    cat = cat[:-2]
            except:
                pass          
                
            details['ISBN'] = ISBN 
            details['ISBN-10'] = ISBN10 
            details['Age'] = age 
            details['Imprint'] = imprint 
            details['Page Count'] = npages 
            details['Category'] = cat 
            details[' Publication Date'] = date 
                           
            # Amazon Link
            Amazon = ''
            try:
                url = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//a[@data-retailer='Amazon']"))).get_attribute('href')
                driver.get(url)
                Amazon = driver.current_url
                if 'www.amazon' not in Amazon:
                    Amazon = ''
            except:
                pass          
                
            details['Amazon Link'] = Amazon  

            # appending the output to the datafame       
            data = data.append([details.copy()])
            # saving data to csv file each 100 links
            if np.mod(i+1, 100) == 0:
                print('Outputting scraped data ...')
                data.to_excel(name, index=False)
        except Exception as err:
            print(str(err))
            driver.quit()
            driver = initialize_bot()

    # optional output to excel
    data.to_excel(name, index=False)
    elapsed = round((time.time() - start)/60, 2)
    print('-'*75)
    print(f'harpercollins.com scraping process completed successfully! Elapsed time {elapsed} mins')
    print('-'*75)
    driver.quit()

    return data

if __name__ == "__main__":
    
    path = ''
    if len(sys.argv) == 2:
        path = sys.argv[1]
    data = scrape_harpercollins(path)

