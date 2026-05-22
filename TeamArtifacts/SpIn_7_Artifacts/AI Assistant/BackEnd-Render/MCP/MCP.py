from mcp.server.fastmcp import FastMCP
#-------------------------------------------
import time
#-------------------------------------------
from selenium import webdriver  #Interacts with the browser; clicks buttons, opens pages and reads HTML.
from selenium.webdriver.chrome.options import Options  #Configure chrome driver, not specifically needed but still helpful.
from selenium.webdriver.chrome.service import Service #Acts as a manager. Used to locate the chromedriver nad more or less manage it on the pc.
from selenium.webdriver.common.by import By  #Used to locate elements.
from selenium.webdriver.support.ui import WebDriverWait #Waits for the page to fully load.
from selenium.webdriver.support import expected_conditions as EC #Used intandem with WebDriverWit, basically used to set condition . Wait until something happens (condition) on the webpage before continuing.
from selenium.common.exceptions import NoSuchElementException #Handle errors in try-except clauses
import re #Expressions which be used to navigate the pages of a table
import os

#Naming the MCP
mcp = FastMCP("Claims_Reader_DME")

hm_r = int(os.getenv("nResult", 1))

#Creating the browser driver
def create_driver():
    """
    Options() is a chrome driver configuration object from selenium. We add specific arguments to it. Can be adjusted later on.
    "--headless" specifies to run chrome without a visible window
    "--disable-gpu" specifies to not use gpu, prevents gpu related errors/issues
    "--no-sandbox" specifies chrome to run with few permissions to avoid permission issues, not really needed here but keeping for testing purpose.

     End result:
     Launches chrome with the above settings.

    """
    options = Options()
    options.add_argument("--headless=new")  # Has to be headless when on Render
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # Anti-bot flags
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    chrome_bin = "/opt/render/project/.render/chrome/opt/google/chrome/google-chrome"
    if not os.path.exists(chrome_bin):
        raise FileNotFoundError(f"Chrome binary not found at {chrome_bin}")

    options.binary_location = chrome_bin

    driver = webdriver.Chrome(options=options)

    # Mask webdriver property
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    return driver

#----------------------------------------

# Function to clean up the term provided by the user to the LLM
def term_cleanup(term):

    cleaned_term = term.replace('"','').strip().lower()

    return cleaned_term

#---------------------------------------- OIG Tool Functions ----------------------------------------

# Function to read the page......
def Read_Block(driver, wait, link):
    page = {}


    wait.until(EC.presence_of_element_located((By.XPATH, ".//main[@id = 'main-content' and @class = 'main']")))

    container = driver.find_element(By.XPATH, ".//main[@id = 'main-content' and @class = 'main']")

    # 1) Heading
    try:
        heading = container.find_element(By.XPATH, ".//article//h1 | .//h1").text.strip()
        page["Heading"] = heading
    except NoSuchElementException:
        print("Heading Not Found")

    # 2) Video Link if any....
    try:
        video = container.find_element(By.XPATH, ".//article//div/div/iframe").get_attribute("src")
        page["Video Link"] = video
    except NoSuchElementException:
        print("Video Link Not Found")

    # 3) Time/Published Date if any....
    try:
        time = container.find_element(By.XPATH, ".//article//time | .//time").text.strip()
        page["Published/Posted Dates"] = time
    except NoSuchElementException:
        print("Published/Posted Dates Not Found")

    # 4) Article (main content) if any....
    try:
        paragraphs = container.find_elements(By.XPATH,
                                             ".//div[contains(@class, 'usa-prose')]//*[self::h2 or self::h3 or self::p or self::li[parent::ol] or self::li[parent::ul]][not(ancestor::div[contains(@class,'usa-accordion')]) and not(preceding-sibling::h3[@id='related-reports']) and not(ancestor::*[preceding-sibling::h3[@id='related-reports']])] | .//article/p")
        if paragraphs:
            content = " ".join([p.text.strip() for p in paragraphs])
            page["Article Body"] = content
        else:
            raise NoSuchElementException
    except NoSuchElementException:
        print("Article Not Found")

    # 5) Transcripts if any......
    try:
        transcripts = container.find_elements(By.XPATH, ".//article/section/div/div/p")
        if transcripts:
            c_transcripts = " ".join([p.text.strip() for p in transcripts])
            page["Podcast/Video Transcripts"] = c_transcripts
        else:
            raise NoSuchElementException
    except NoSuchElementException:
        print("Transcripts Not Found")

    # 6) Bullet Points if any.....
    try:
        points = container.find_elements(By.XPATH, ".//article/ul/li")
        f_points = [p for p in points if not p.find_elements(By.XPATH, ".//a[@href]")]
        if f_points:
            con_pon = " ".join([p.text.strip() for p in f_points])
            page["Bullet Points"] = con_pon
        else:
            raise NoSuchElementException
    except NoSuchElementException:
        print("Bullet Points Not Found")

    # 7) Links to full report if any.....
    try:
        lines = container.find_elements(By.XPATH, ".//article//a[contains(@class, 'text-bold')]")
        links = [a.get_attribute("href") for a in lines]
        if links:
            con_link = ", ".join([p for p in links])
            page["Link to Full Report"] = con_link
        else:
            raise NoSuchElementException
    except NoSuchElementException:
        print("Link to Full Report Not Found")

    # 8) Sub Articles if any .......
    try:
        sub_articles = container.find_elements(By.XPATH,
                                               ".//h2[text()='AGREEMENT PRESS RELEASE' or text()='ENFORCEMENT ACTIONS'] | .//h2[text()='AGREEMENT PRESS RELEASE' or text()='ENFORCEMENT ACTIONS']/following-sibling::h3[not(preceding-sibling::div[contains(@class,'margin-top-4')])] | .//h2[text()='AGREEMENT PRESS RELEASE' or text()='ENFORCEMENT ACTIONS']/following-sibling::time[not(preceding-sibling::div[contains(@class,'margin-top-4')])] | .//h2[text()='AGREEMENT PRESS RELEASE' or text()='ENFORCEMENT ACTIONS']/following-sibling::p[not(preceding-sibling::div[contains(@class,'margin-top-4')])]")
        if sub_articles:
            content = " ".join([el.text.strip() for el in sub_articles if el.text.strip()])
            page["Sub Articles"] = content
        else:
            raise NoSuchElementException
    except NoSuchElementException:
        print("Sub Articles Not Found")

    # 9) Action Details if any......
    try:
        add_details = container.find_elements(By.XPATH, ".//h2[text()='Action Details']/following-sibling::ul[1]/li")

        if not add_details:
            raise NoSuchElementException

        for a in add_details:

            label = a.find_element(By.XPATH, ".//span").text.strip().replace(":", "")
            nested = a.find_elements(By.XPATH, ".//ul//li")
            if nested:
                val = nested[0].text.strip()
            else:
                val = driver.execute_script("return arguments[0].nextSibling.nodeValue;", a.find_element(By.XPATH, ".//span")).strip()
            page[label] = val
    except NoSuchElementException:
        print("Action Details Not Found")

        # 9b) Tags if any....
        try:
            tag_groups = container.find_elements(By.XPATH, ".//dt[contains(@class, 'pep-metadata__term')]")
            if not tag_groups:
                raise NoSuchElementException

            for dt in tag_groups:
                label = dt.text.strip()
                tags = dt.find_elements(By.XPATH, "./following-sibling::div[1]//span[contains(@class, 'usa-tag')]")
                if tags:
                    page[label] = ", ".join([t.text.strip() for t in tags])
        except NoSuchElementException:
            print("Tags Not Found")

    # 10) Investigation_Table if any ......
    try:
        table = container.find_elements(By.XPATH, ".//article/div/div/table/tbody/tr")
        if not table:
            raise NoSuchElementException

        for tr in table:
            label = tr.find_element(By.XPATH, "./th").text.strip()
            val = tr.find_element(By.XPATH, "./td").text.strip()
            page[label] = val
    except NoSuchElementException:
        print("Table Not Found")

    # 11) Investigation specific content
    try:
        paragraphs = container.find_elements(By.XPATH, ".//article/div/div/div/p")
        if paragraphs:
            content = " ".join([p.text.strip() for p in paragraphs])
            page["Investigation Details"] = content
        else:
            raise NoSuchElementException
    except NoSuchElementException:
        print("Investigation Details Not Found")

    return page


# Function to get first few results and their content....
def Link_Fetch_Block(url_result):
    driver = create_driver()
    wait = WebDriverWait(driver, 200)
    driver.get(url_result)

    wait.until(EC.presence_of_element_located((By.XPATH, "//div[@id = 'results']")))
    items = driver.find_elements(By.XPATH, "//div[contains(@class,'search-result-item')]//div[@role='link']")
    result = []

    for index in range(min(hm_r, len(items))):
        try:


            """
            Based on the iteration of the loop, select respective result webelement
            eg; at 3rd loop check the 3 result.....
            """
            i = items[index]

            title = i.find_element(By.XPATH, ".//h2[@class='result-title-label']").text.strip()

            # Scroll the page to the webelement from items
            driver.execute_script("arguments[0].scrollIntoView(true);", i)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", i)

            wait.until(lambda d: d.current_url != url_result)

            link = driver.current_url

            page_content = Read_Block(driver, wait, link)
            time.sleep(0.3)

            result.append({"Title": title, "Link": link, "WebPage": page_content})

            driver.back()
            wait.until(EC.presence_of_element_located((By.XPATH, "//div[@id = 'results']")))

        except Exception as e:
            driver.get(url_result)
            wait.until(EC.presence_of_element_located((By.XPATH, "//div[@id = 'results']")))

    driver.quit()

    return result

#----------------------------------------
@mcp.tool()
def OIG_search (item: str) -> list:
    url_search = "https://search.usa.gov/search?utf8=%E2%9C%93&query=&affiliate=hhs_oig&commit=Search"
    driver = create_driver()
    wait = WebDriverWait(driver, 200)
    driver.get(url_search)

    wait.until(EC.presence_of_element_located((By.XPATH, ".//div[@class = 'grid-container']//form[contains(@class,'usa-search--small')]//input[@id = 'search-field']")))

    container = driver.find_element(By.XPATH, ".//form[contains(@class,'usa-search--small') and @role = 'search']")

    term = term_cleanup(item)

    # Finding and storing the location where terms are to be added....
    terminput = container.find_element(By.XPATH, ".//input[@id = 'search-field' and @type = 'search']")

    # Clearning input just in-case.
    terminput.clear()

    # Sending the inputs
    terminput.send_keys(term)

    # Find and storing the location of the button that allows the search process.
    search = driver.find_element(By.XPATH, "//button[contains(@class,'usa-button') and @type = 'submit' ]")
    driver.execute_script("arguments[0].click();", search)

    # Waits for changes in link.
    wait.until(lambda new: new.current_url != url_search)

    # Stores the new link.
    url_result = driver.current_url

    driver.quit()
    # Kills the chrome instance to save memory

    time.sleep(0.3)
    output = Link_Fetch_Block(url_result)

    return output



#----------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------

#---------------------------------------- MCP CODE SPACE BREAK --------------------------------------

#----------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------

#---------------------------------------- SOS Tool Functions ----------------------------------------


# SOS MO has many tabs and as such there will be quite a few functions to get info from each tab....

# Owners Tab
def SOS_Owners_Block(driver, wait):
    cc = []

    wait.until(lambda d: "Just a moment" not in d.title)
    try:
        clicktab = driver.find_element(By.XPATH, "//div[@id='ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBEDetail_tsBEDetail']//span[@class='rtsTxt' and text()='Owners']")
        driver.execute_script("arguments[0].click();", clicktab)

        wait.until(EC.presence_of_element_located((By.XPATH,"//div[@id='ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBEDetail_pvBEOwner']//table[contains(@class,'rgMasterTable')]")))

        rows = driver.find_elements(By.XPATH,"//div[@id='ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBEDetail_BEOwnerGrid']//tbody/tr")

        for row in rows:
            cols = row.find_elements(By.XPATH, "./td")
            if len(cols) < 5:
                continue
            cc.append({
                "Name": cols[1].text.strip(),
                "Type": cols[2].text.strip(),
                "Address": cols[3].text.strip().replace("\n", ", ").replace(",,", ","),
                "Since": cols[4].text.strip(),
                "To": cols[5].text.strip() if len(cols) > 5 else None
            })

    except Exception:
        return None
    return cc

# Business Address Tab
def SOS_Business_Block(driver, wait):
    cc = []

    wait.until(lambda d: "Just a moment" not in d.title)
    try:
        clicktab = driver.find_element(By.XPATH, "//div[@id='ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBEDetail_tsBEDetail']//span[@class='rtsTxt' and text()='Business Address']")
        driver.execute_script("arguments[0].click();", clicktab)

        wait.until(EC.presence_of_element_located((By.XPATH,"//div[@id='ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBEDetail_pvBEAddress']//table[contains(@class,'rgMasterTable')]")))

        rows = driver.find_elements(By.XPATH,"//div[@id='ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBEDetail_BEAddressGrid']//table[contains(@class,'rgMasterTable')]//tbody/tr")

        for row in rows:
            cols = row.find_elements(By.XPATH, "./td")
            if len(cols) < 4:
                continue
            cc.append({
                "Type": cols[1].text.strip(),
                "Address": cols[2].text.strip().replace("\n", ", ").replace(",,", ","),
                "Since": cols[3].text.strip(),
                "To": cols[4].text.strip() if len(cols) > 4 else None
            })

    except Exception:
        return None

    return cc

# Filing Tab
def SOS_Filings_Block(driver, wait):
    cc = []

    wait.until(lambda d: "Just a moment" not in d.title)
    try:
        clicktab = driver.find_element(By.XPATH, "//div[@id='ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBEDetail_tsBEDetail']//span[@class='rtsTxt' and text()='Filings']")
        driver.execute_script("arguments[0].click();", clicktab)

        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@id='ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBEDetail_pgFilings_pnlFilingsGrid']//table[contains(@class,'rgMasterTable')]")))

        while True:
            rows = driver.find_elements(By.XPATH, "//div[@id='ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBEDetail_pgFilings_pnlFilingsGrid']//tbody/tr")

            for row in rows:
                cols = row.find_elements(By.XPATH, "./td")
                if len(cols) < 6:
                    continue
                cc.append({
                    "Type": cols[3].text.strip(),
                    "Create Filing": cols[4].text.strip(),
                    "Date Filed": cols[5].text.strip(),
                    "Effective Date": cols[6].text.strip() if len(cols) > 6 else None
                })

            try:
                page_info = driver.find_element(By.XPATH,"//div[@id='ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBEDetail_pgFilings_pnlFilingsGrid']//div[contains(@class,'rgInfoPart')]").text



                match = re.search(r'Page\s+(\d+)\s+of\s+(\d+)', page_info)
                if match:
                    current = int(match.group(1))
                    total = int(match.group(2))
                    if current >= total:
                        break

                next_btn = driver.find_element(By.XPATH, "//div[@id='ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBEDetail_pgFilings_pnlFilingsGrid']//input[contains(@class,'rgPageNext')]")
                driver.execute_script("arguments[0].click();", next_btn)

                wait.until(lambda d: d.find_element(By.XPATH, "//div[@id='ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBEDetail_pgFilings_pnlFilingsGrid']//div[contains(@class,'rgInfoPart')]").text != page_info)

            except Exception:
                break

    except Exception:
        return None

    return cc

# Principal Office Address Tab
def SOS_POA_Block(driver, wait):
    cc = []

    wait.until(lambda d: "Just a moment" not in d.title)

    try:
        clicktab = driver.find_element(By.XPATH, "//div[@id='ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBEDetail_tsBEDetail']//span[@class='rtsTxt' and text()='Principal Office Address']")
        driver.execute_script("arguments[0].click();", clicktab)

        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@id='ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBEDetail_pvBEAddress']//table[contains(@class,'rgMasterTable')]")))

        rows = driver.find_elements(By.XPATH, "//div[@id='ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBEDetail_BEAddressGrid']//tbody/tr")

        for row in rows:
            cols = row.find_elements(By.XPATH, "./td")
            if len(cols) < 4:
                continue
            cc.append({
                "Type": cols[1].text.strip(),
                "Address": cols[2].text.strip().replace("\n", ", ").replace(",,", ","),
                "Since": cols[3].text.strip(),
                "To": cols[4].text.strip() if len(cols) > 4 else None
            })

    except Exception:
        return None

    return cc

# General Information Tab
def SOS_General_Info_Block(driver, wait):
    cc = {}

    wait.until(lambda d: "Just a moment" not in d.title)

    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@id='ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBEDetail_psBEDetail']//div[@class='container']")))

        rows = driver.find_elements(By.XPATH, "//div[contains(@class,'swOuterPanelWhiteBox')]//div[contains(@class,'row') and not(contains(@class,'my-1')) and not(contains(@class,'no-gutters'))]")

        for row in rows:
            cols = row.find_elements(By.XPATH, "./div")
            for i in range(0, len(cols), 2):
                try:
                    label = cols[i].find_element(By.XPATH, "./span[contains(@class,'swFieldLabel')]").text.strip()
                except NoSuchElementException:
                    continue
                try:
                    val = cols[i+1].find_element(By.XPATH, ".//span[@class='swLabelDetailsBlack'] | .//div[@class='swLabelDetailsBlack']").text.strip().replace('\n', ', ')
                except (NoSuchElementException, IndexError):
                    val = None
                cc[label] = val

    except Exception:
        return None

    return cc

# Function to read the page (calls the above functions)......
def Read_Block_SOS(driver, wait):
    content = []
    general_info = SOS_General_Info_Block(driver, wait)
    time.sleep(0.5)
    poa_info = SOS_POA_Block(driver, wait)
    time.sleep(0.5)
    fil_info = SOS_Filings_Block(driver, wait)
    time.sleep(0.5)
    bus_info = SOS_Business_Block(driver, wait)
    time.sleep(0.5)
    own_info = SOS_Owners_Block(driver, wait)
    content.append({"General Information": general_info, "Filings": fil_info, "Principal Office Address": poa_info,"Business Address": bus_info, "Owners": own_info})

    return content

# Function to get first few links.....
def Link_Fetch_Block_SOS(driver, wait, url_search, term):

    driver.get(url_search)
    wait.until(EC.presence_of_element_located((By.XPATH, ".//div[@id = 'main-content']/div[@id = 'page-content']//div[@class = 'container']//div[@class = 'row']")))
    container = driver.find_element(By.XPATH, ".//div[@id = 'main-content']/div[@id = 'page-content']//div[@class = 'container']//div[@class = 'row']")

    terminput = container.find_element(By.XPATH, ".//div[@class = 'row']//input[@type = 'text' and @id = 'ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBESearch_bsPanel_tbBusinessName']")
    terminput.clear()
    terminput.send_keys(term)

    search = container.find_element(By.XPATH, ".//div/a[@id = 'ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBESearch_bsPanel_stdbtnSearch_LinkStandardButton' and @title = 'Search']")
    driver.execute_script("arguments[0].click();", search)

    wait.until(EC.presence_of_element_located((By.XPATH, ".//div//table[contains(@class,'table')]/tbody/tr/td/a[@style = 'font-weight:bold;']")))
    link_con = driver.find_elements(By.XPATH, ".//div//table[contains(@class,'table')]/tbody/tr/td/a[@style = 'font-weight:bold;']")
    targets = [link.get_attribute("href") for link in link_con]
    driver.quit()

    try:
        pages = []
        for index in range(min(hm_r, len(link_con))):
            href= targets[index]

            driver = create_driver()
            wait = WebDriverWait(driver, 3)

            driver.get(url_search)
            wait.until(EC.presence_of_element_located((By.XPATH, ".//div[@id = 'main-content']/div[@id = 'page-content']//div[@class = 'container']//div[@class = 'row']")))
            container = driver.find_element(By.XPATH, ".//div[@id = 'main-content']/div[@id = 'page-content']//div[@class = 'container']//div[@class = 'row']")

            terminput = container.find_element(By.XPATH, ".//div[@class = 'row']//input[@type = 'text' and @id = 'ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBESearch_bsPanel_tbBusinessName']")
            terminput.clear()
            terminput.send_keys(term)

            search = container.find_element(By.XPATH, ".//div/a[@id = 'ctl00_ctl00_ContentPlaceHolderMain_ContentPlaceHolderMainSingle_ppBESearch_bsPanel_stdbtnSearch_LinkStandardButton' and @title = 'Search']")
            driver.execute_script("arguments[0].click();", search)

            wait.until(EC.presence_of_element_located((By.XPATH, ".//div//table[contains(@class,'table')]/tbody/tr/td/a[@style = 'font-weight:bold;']")))
            point = driver.find_elements(By.XPATH, ".//div//table[contains(@class,'table')]/tbody/tr/td/a[@style = 'font-weight:bold;']")

            link = point[index]
            driver.execute_script("arguments[0].scrollIntoView(true);", link)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", link)
            wait.until(lambda d: d.current_url == href)

            page = Read_Block_SOS(driver, wait)
            pages.append({"Link": href, "Page": page})

            driver.quit()
            time.sleep(2)

        return pages

    except Exception:
        return None
#---------------------------------------- SOS MCP TooL ----------------------------------------

@mcp.tool()
def SOS_search (item: str) -> list:
    url_search = "https://bsd.sos.mo.gov/BusinessEntity/BESearch.aspx?SearchType=0"
    driver = create_driver()
    wait = WebDriverWait(driver, 3)
    term = term_cleanup(item)

    output = Link_Fetch_Block_SOS(driver, wait, url_search, term)

    return output


#----------------------------------------
if __name__ == "__main__":

    mcp.run()






















