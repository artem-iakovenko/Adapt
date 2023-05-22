import time
import config
import requests
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import json
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from random import randint
import math
from google.oauth2 import service_account
from googleapiclient.discovery import build
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

import get_companies

r_headers = config.HEADERS
company_details = {}


CREDS = service_account.Credentials.from_service_account_file(
    'keys.json', scopes=config.SCOPES
)
SERVICE = build('sheets', 'v4', credentials=CREDS)
sheet = SERVICE.spreadsheets()


def get_credentials():
    options = Options()
    # options.add_argument('--headless')
    # options.add_argument('--disable-gpu')
    caps = DesiredCapabilities.CHROME
    caps['goog:loggingPrefs'] = {'performance': 'ALL'}
    #driver = webdriver.Chrome('chrome/chromedriver', desired_capabilities=caps, chrome_options=options)
    driver = webdriver.Chrome(ChromeDriverManager().install(), desired_capabilities=caps, chrome_options=options)

    driver.get(config.LOGIN_URL)
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="emailSignIn"]')))
    driver.find_element(By.XPATH, '//*[@id="emailSignIn"]').send_keys(config.EMAIL)
    time.sleep(3)
    driver.find_element(By.XPATH, '//*[@id="sl-signin-form"]/div[2]/input').send_keys(config.PASSWORD)
    time.sleep(3)
    driver.find_element(By.XPATH, '//*[@id="sl-signin-form"]/div[3]/div[1]/button').click()
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, '//*[@id="advSearchNavBar"]/a')))
    driver.get('https://leads.adapt.io/advanced-search/contact/saved-searches')
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'open-search-link')))
    driver.find_element(By.CLASS_NAME, 'open-search-link').click()
    time.sleep(20)

    #driver.get('https://leads.adapt.io/advanced-search/contact#search')
    # WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'saved-search')))
    # driver.find_element(By.CLASS_NAME, 'saved-search').click()
    # WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'saved-item')))
    # saved_searches = driver.find_elements(By.CLASS_NAME, 'saved-item')
    # for ind in range(1, len(saved_searches) + 1):
    #     if ind > 1:
    #         driver.find_element(By.CLASS_NAME, 'saved-search').click()
    #         WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'saved-item')))
    #     WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, f'{config.SEARCH_XPATH}[{ind}]')))
    #     driver.find_element(By.XPATH, f'{config.SEARCH_XPATH}[{ind}]').click()
    #     print("Search clicked")
    #     time.sleep(20)
    perfs = driver.get_log('performance')
    headers = None
    searches_post = []
    relevant_cookies = None
    for perf in perfs:
        network_data = json.loads(perf['message'])
        main_method = network_data.get('message').get('method')
        if relevant_cookies is None:
            if main_method == 'Network.requestWillBeSentExtraInfo':
                cookies = network_data.get('message').get('params').get('associatedCookies')
                hdrs = network_data.get('message').get('params').get('headers')
                try:
                    if '/advanced/searchResults.htm?NOW=' in hdrs.get(':path') and len(cookies) > 0:
                        relevant_cookies = hdrs.get('cookie')
                except:
                    pass
        try:
            request_info = network_data.get('message').get('params').get('request')
            request_url = request_info.get('url')
            request_method = request_info.get('method')
            if request_url is None:
                continue
        except AttributeError:
            continue
        if 'https://www.adapt.io/advanced/searchResults' in request_url and request_method == 'POST':
            post_data = request_info.get('postData')
            headers = request_info.get('headers')
            print('Request Found!')
            searches_post.append(post_data)
    time.sleep(5)
    return [headers, searches_post, relevant_cookies]


def get_unixtime():
    return round(time.time() * 1000)


def request_page(params, unix_time, request_direction):
    if request_direction == 'contact':
        url = f'https://www.adapt.io/advanced/searchResults.htm?NOW={unix_time}&userType=PAID&pageType=LB'
    elif request_direction == 'company':
        url = 'https://www.adapt.io/getCompanyInfoById.htm'
    else:
        url = None
    if url is not None:
        response = requests.post(url, headers=r_headers, data=json.dumps(params))
        return {'status_code': response.status_code, 'page_data': response.json()}
    else:
        return {'status_code': 0, 'page_data': None}


def parse_data(contacts, search_id):
    page_contacts = []
    c = 1
    for contact in contacts:
        first_name = contact.get('firstName')
        last_name = contact.get('lastName')
        full_name = f'{first_name} {last_name}'
        company_id = contact.get('companyId')
        company_domain = contact.get('companyDomain')
        contact_li = contact.get('linkedInId')
        level = contact.get('level')
        title = contact.get('title')
        street = contact.get('street')
        city = contact.get('city')
        state = contact.get('state')
        country = contact.get('country')
        zip = contact.get('zip')
        contact_id = contact.get('id')
        company_name = contact.get('companyName')
        contact_city = contact.get('contactCity')
        contact_state = contact.get('contactState')
        contact_country = contact.get('contactCountry')
        contact_array = [
            full_name,
            contact_li,
            level,
            title,
            company_domain,
            company_name,
            contact_country,
            contact_state,
            contact_city,
            company_id
        ]
        contact_result = contact_array  + [search_id]
        page_contacts.append(contact_result)
        print(f'{c}/{len(contacts)}. {full_name}, {title} at {company_name}')
        c += 1
        # c += 1
        # if company_id in company_details.keys():
        #     company_array = company_details[company_id]
        # else:
        #     # SEND REQUEST
        #     post_data = {"companyId": company_id}
        #     company_data = request_page(post_data, None,'company').get('page_data')
        #     industry = company_data.get('industry')
        #     employee_size = company_data.get('employeeCount')
        #     revenue = company_data.get('revenue')
        #     founded_date = company_data.get('founded')
        #     company_li = company_data.get('linkedInId')
        #     company_street = company_data.get('street')
        #     company_city = company_data.get('city')
        #     company_state = company_data.get('state')
        #     company_country = company_data.get('country')
        #     company_zip = company_data.get('zip')
        #     website = company_data.get('website')
        #     try:
        #         company_sectors = ', '.join(company_data.get('sectors'))
        #     except:
        #         company_sectors = None
        #     company_array = [
        #         company_li,
        #         website,
        #         industry,
        #         company_sectors,
        #         employee_size,
        #         revenue,
        #         founded_date,
        #         company_country,
        #         company_state,
        #         company_city,
        #         company_street,
        #         company_zip
        #     ]
        #     company_details[company_id] = company_array
        #     time.sleep(5)
        # # print(contact_array)
        # # print(company_array)
        # contact_result = contact_array + company_array + [search_id]
        # page_contacts.append(contact_result)
    return page_contacts


def update_spreadsheets(data):
    sheet_data = sheet.values().get(spreadsheetId=config.SPREADSHEET_ID, range='Grabber!A1:A').execute()
    total_rows = len(sheet_data.get('values'))
    update_sheets = sheet.values().update(spreadsheetId=config.SPREADSHEET_ID, range=f'Grabber!A{total_rows+1}',
                                          valueInputOption='USER_ENTERED', body={'values': data}).execute()


def main():
    credentials = get_credentials()
    search_queries = credentials[1]
    cookie = credentials[2]
    with open('cookie.txt', 'w') as f:
        f.write(str(cookie))
    print('cookie saved')
    if cookie is None:
        print('Cookies are Undefined')
        return 0
    print(f'Prepared COOKIE: {cookie}')
    r_headers['Cookie'] = cookie
    s = 1
    for search_query in search_queries:
        unix_time = get_unixtime()
        post_data = json.loads(search_query)
        post_data['limit'] = 100
        print(f'Prepared Search Data: {post_data}')
        page_response = request_page(post_data, unix_time,'contact')
        print('Search Details: ')
        print(f'\tStatus Code: {page_response["status_code"]}')
        time.sleep(5)
        if page_response["status_code"] == 200:
            print(f'\tSearch Number: {s}/{len(search_queries)}')
            print('\tConnection: Success')
            page_json = page_response["page_data"]
            cursor_mark = None
            #cursor_mark = 'AoMIRpxPqkE4NTliMTAzN2MzODNiMmM3ZWNmYjE4ZWE1'
            total_contacts = int(page_json.get('hits'))
            total_pages = math.ceil(total_contacts / 100)
            search_id = randint(100000, 999999)
            print(f'\tSearch ID: {search_id}')
            print(f'\tContacts Available: {total_contacts}')
            print(f'\tTotal Pages: {total_pages}')
            print(" ")
            start_page = 0
            for page in range(start_page, total_pages):
                print('------------------------------')
                print(f'Current Page: {page + 1}/{total_pages}')
                if page != 0:
                    post_data['cursorMark'] = cursor_mark
                    post_data['currentPage'] = page
                page_response = request_page(post_data, unix_time,'contact')
                cursor_mark = page_response['page_data'].get('cursorMark')
                if page < start_page:
                    print(f'Skipping Page {page + 1}')
                    time.sleep(5)
                    continue
                contacts = page_response['page_data'].get('contacts')
                parsed_page = parse_data(contacts, search_id)
                update_spreadsheets(parsed_page)
                print(parsed_page)
                print(f'Next Cursor: {cursor_mark}')
                print('Status: Success')
                time.sleep(10)
        else:
            print('Connection: Fail')
            continue
    time.sleep(30)
    print('Launching Companies Grabber')
    get_companies.company_handler()


if __name__ == '__main__':
    status_code = main()
    print(status_code)

