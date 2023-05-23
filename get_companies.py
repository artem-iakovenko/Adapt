import requests
import config
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import time


CREDS = service_account.Credentials.from_service_account_file(
    'keys.json', scopes=config.SCOPES
)
SERVICE = build('sheets', 'v4', credentials=CREDS)
sheet = SERVICE.spreadsheets()

r_headers = config.HEADERS

backup = {}


def get_companies(range):
    sheet_data = sheet.values().get(spreadsheetId=config.SPREADSHEET_ID, majorDimension="COLUMNS",range=f'Grabber!{range}').execute()
    return sheet_data.get('values')


def request_company(params):
    url = 'https://www.adapt.io/getCompanyInfoById.htm'
    try:
        response = requests.post(url, headers=r_headers, data=json.dumps(params), timeout=20)
    except:
        return None
    print(response.status_code)
    if response.status_code == 200:
        try:
            return response.json()
        except:
            return None
    else:
        return None


def parse_response(company_data):
    industry = company_data.get('industry')
    employee_size = company_data.get('employeeCount')
    revenue = company_data.get('revenue')
    founded_date = company_data.get('founded')
    company_li = company_data.get('linkedInId')
    company_street = company_data.get('street')
    company_city = company_data.get('city')
    company_state = company_data.get('state')
    company_country = company_data.get('country')
    company_zip = company_data.get('zip')
    website = company_data.get('website')
    try:
        company_sectors = ', '.join(company_data.get('sectors'))
    except:
        company_sectors = None
    return [
        company_li,
        website,
        industry,
        company_sectors,
        employee_size,
        revenue,
        founded_date,
        company_country,
        company_state,
        company_city,
        company_street,
        company_zip
    ]


def update_spreadsheets(data, index):
    update_sheets = sheet.values().update(spreadsheetId=config.SPREADSHEET_ID, range=f'Grabber!L{index}',
                                          valueInputOption='USER_ENTERED', body={'values': data}).execute()


def company_handler():
    with open('cookie.txt', 'r') as file:
        cookie = file.read().rstrip()
    r_headers['Cookie'] = cookie
    sheet_data = get_companies('J2:L')
    start_index = 2
    company_ids = sheet_data[0]
    try:
        companies_done = len(sheet_data[2])
        start_index += companies_done
    except IndexError:
        companies_done = 0
    if companies_done > 0:
        company_ids = company_ids[companies_done:]
    gsheet_data = []
    iteration = 0
    curr_ind = start_index
    for company_id in company_ids:
        print(f'{company_id}, {iteration+1} of {len(company_ids)}')
        if iteration > 0 and iteration % 100 == 0:
            time.sleep(30)
            print("Short Break...")
        if company_id in backup.keys():
            company_array = backup[company_id]
        else:
            post_data = {"companyId": company_id}
            company_response = request_company(post_data)
            if company_response is None:
                company_array = []
            else:
                company_array = parse_response(company_response)
                backup[company_id] = company_array
        gsheet_data.append(company_array)
        '''
        if len(gsheet_data) == 10:
            update_spreadsheets(gsheet_data, curr_ind)
            curr_ind += 10
            gsheet_data = []
        #the last iteration - write to excel the last portion of company data
        if len(gsheet_data) < 10:
            update_spreadsheets(gsheet_data, curr_ind)
            curr_ind += len(gsheet_data)
            gsheet_data = []
        '''
        update_spreadsheets(gsheet_data, curr_ind)
        curr_ind += len(gsheet_data)
        gsheet_data = []

        iteration += 1
        time.sleep(2)
        print("=====================================================")


#company_handler()

