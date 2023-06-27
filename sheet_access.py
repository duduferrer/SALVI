import os
import logging
from time import sleep
from datetime import datetime, timezone, date, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from db_access import db_time_search
import telebot
from db_access import db_chat_id_search

API_TELEGRAM_TOKEN = os.environ['API_TELEGRAM_TOKEN']
bot = telebot.TeleBot(API_TELEGRAM_TOKEN)
SPREADSHEET_ID = os.environ['SPREADSHEET_ID']
last_update = {
    "x" : datetime.strptime('01/01/2000 00:00:00 UTC', '%d/%m/%Y %H:%M:%S %Z').replace(tzinfo=timezone.utc),
    "y" : datetime.strptime('01/01/2000 00:00:00 UTC', '%d/%m/%Y %H:%M:%S %Z').replace(tzinfo=timezone.utc),
    "z" : datetime.strptime('01/01/2000 00:00:00 UTC', '%d/%m/%Y %H:%M:%S %Z').replace(tzinfo=timezone.utc)
}
next_op = {}


def connect_to_spreadsheet():
    scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials_sheets.json', scopes)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    logging.info("Connected to SS")
    return creds

#Receive LPNA Code and search into Schedule Sheet
def search_lpna(lpna):
    creds = connect_to_spreadsheet()
    range_name = 'Cadastro de Efetivo!B2:C'
    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                    range=range_name).execute()
        values = result.get('values', [])

        if not values:
            logging.error("No data found on 'Cadastro de Efetivo'")
            return (None)
        for element in values:
            if lpna in element:
                return(element[0]) 
    except HttpError as err:
        print(err)


def sync_schedule():
    creds = connect_to_spreadsheet()
    
    while True:
        night_shift_routine()
        try:
            service = build('sheets', 'v4', credentials=creds)
        # Call the Sheets API
            sheet = service.spreadsheets()
            schedule = sync_time(sheet)
            if is_updated(sheet, "J6", "x") and is_updated(sheet, "K6", "x"):
                pass
            else:    
                console_x, upcoming_ctr_x, upcoming_ass_x = update_console_x(sheet, schedule)
            
            if is_updated(sheet, "L6", "y") and is_updated(sheet, "M6", "y"):
                pass
            else:
                console_y, upcoming_ctr_y, upcoming_ass_y = update_console_y(sheet, schedule)
            
            if is_updated(sheet, "N6", "z") and is_updated(sheet, "O6", "z"):
                pass
            else:
                console_z, upcoming_ctr_z, upcoming_ass_z = update_console_z(sheet, schedule)
            
            if call_opr(upcoming_ctr_x, console_x, "controle"):
                upcoming_ctr_x.pop(0)
            if call_opr(upcoming_ass_x, console_x, "assistente"):
                upcoming_ass_x.pop(0)
            if call_opr(upcoming_ctr_y, console_y, "controle"):
                upcoming_ctr_y.pop(0)
            if call_opr(upcoming_ass_y, console_y, "assistente"):
                upcoming_ass_y.pop(0)
            if call_opr(upcoming_ctr_z, console_z, "controle"):
                upcoming_ctr_z.pop(0)
            if call_opr(upcoming_ass_z, console_z, "assistente"):
                upcoming_ass_z.pop(0)       
                
        except HttpError as err:
            logging.error("Can't connect to sheets")
            print(err)
        sleep(5)


def night_shift_routine():
 now =  datetime.now(timezone.utc)
 today = date.today()
 night_start = datetime.strptime(f'{today.day}/{today.month}/{today.year} 23:30:00 UTC', '%d/%m/%Y %H:%M:%S %Z').replace(tzinfo=timezone.utc)
 night_end = datetime.strptime(f'{today.day}/{today.month}/2100 00:00:00 UTC', '%d/%m/%Y %H:%M:%S %Z').replace(tzinfo=timezone.utc)#only a place holder
 if now > night_start:
    while now < night_end:
        now =  datetime.now(timezone.utc)
        today = date.today() 
        night_end = datetime.strptime(f'{today.day}/{today.month}/{today.year} 09:30:00 UTC', '%d/%m/%Y %H:%M:%S %Z').replace(tzinfo=timezone.utc)
 return True
         

def call_opr(upcoming_list, console, pos):
    global next_op
    if not upcoming_list:
        return False
    if upcoming_list[0][1] == '':
        return True
    shift_time = upcoming_list[0][0]
    op_name = ''.join(upcoming_list[0][1])
    if op_name in next_op:
        mins_before = next_op[op_name]
    else:
        mins_before = db_time_search(op_name)
        next_op[op_name] = mins_before
    if not mins_before:
        next_op.pop(op_name)
        return True
    mins_before = timedelta(minutes=mins_before)
    call_time = shift_time - mins_before
    call_time = call_time.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if call_time <= now:
       send_call_message(op_name, console, shift_time, pos)
       next_op.pop(op_name)
       return True
    return False

def send_call_message(op_name, console, shift_time, pos):
    shift_time = shift_time - timedelta(hours=3)
    shift_time = shift_time.strftime("%H:%M")
    chat_id = db_chat_id_search(op_name)
    bot.send_message(chat_id,
            f'''
            {op_name} dá tempo de fazer um bolinho antes de render {pos} na {console} às {shift_time}
            '''
            )        
        
def is_updated(sheet, position, console):
    range_name = 'BOT!'+ position
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
        range=range_name).execute()
    update = result.get('values', [])
    update = ''.join(update[0])
    update = update + " UTC"
    update = datetime.strptime(update, '%d/%m/%Y %H:%M:%S %Z').replace(tzinfo=timezone.utc)
    if not update:
        logging.error(f"Can t find last update on {range_name}")
        return (True)
    global last_update 
    if update > last_update.get(console):
        return False
    return True

def sync_time(sheet):
    range_name = 'Horário!B9:B22'
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
        range=range_name).execute()
    time = result.get('values', [])
    if not time:
        logging.error(f"No data found on {range_name}")
        return (None) 
    return time 
    
    
def sync_op(sheet, range):
    range_name = range
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
        range=range_name).execute()
    operators = result.get('values', [])
    if not operators:
        logging.error(f"No data found on {range_name}")
        return (None) 
    return(operators)
    
    
def sync_console(sheet, range):
    range_name = range
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
        range=range_name).execute()
    console = result.get('values', [])
    if not console:
        logging.error(f"No data found on {range_name}")
        return (None) 
    return(''.join(console[0]))

def generate_op_schedule_list(schedule, operator_list):
    if operator_list == None:
        return
    now = datetime.now(timezone.utc)
    today = now.date()
    time_list =[]
    slot = []
    for time in schedule:
        time = "".join(time)
        time = str(today) + " " +time
        time = datetime.strptime(time, '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)
        time_list.append(time)
    i = 0
    for ctr in operator_list:
        if i - 1 >= 0:
            if ctr == operator_list[i-1]:
                ctr = ""
        slot.append([time_list[i], ctr])
        i += 1
    return (slot)

def verify_hour(opr_hour_list):
    if opr_hour_list == None:
        return
    now = datetime.now(timezone.utc)
    upcoming_call = []
    for opr_hour in opr_hour_list:
        if opr_hour[0] > now and opr_hour[1]!='':
            upcoming_call.append(opr_hour)     
    return upcoming_call
        
def update_console_x(sheet, schedule):
    console_x = sync_console(sheet, 'Horário!E6')
    ctr_x = sync_op(sheet, 'Horário!E9:E22')
    ass_x = sync_op(sheet, 'Horário!F9:F22')
    ctr_x_sch_list = generate_op_schedule_list(schedule, ctr_x)
    ass_x_sch_list = generate_op_schedule_list(schedule, ass_x)
    upcoming_call_ctr_x = verify_hour(ctr_x_sch_list)
    upcoming_call_ass_x = verify_hour(ass_x_sch_list)
    global last_update
    last_update.update({'x' : datetime.now(timezone.utc)})
    return(console_x, upcoming_call_ctr_x, upcoming_call_ass_x)
            
def update_console_y(sheet, schedule):
    console_y = sync_console(sheet, 'Horário!I6')
    ctr_y = sync_op(sheet, 'Horário!I9:I22')
    ass_y = sync_op(sheet, 'Horário!J9:J22')
    ctr_y_sch_list= generate_op_schedule_list(schedule, ctr_y)
    ass_y_sch_list= generate_op_schedule_list(schedule, ass_y)
    upcoming_call_ctr_y = verify_hour(ctr_y_sch_list)
    upcoming_call_ass_y = verify_hour(ass_y_sch_list)    
    global last_update
    last_update.update({'y' : datetime.now(timezone.utc)})
    return(console_y, upcoming_call_ctr_y, upcoming_call_ass_y)

def update_console_z(sheet, schedule):
    console_z = sync_console(sheet, 'Horário!M6')
    ctr_z = sync_op(sheet, 'Horário!M9:M22')
    ass_z = sync_op(sheet, 'Horário!N9:N22')
    ctr_z_sch_list= generate_op_schedule_list(schedule, ctr_z)
    ass_z_sch_list= generate_op_schedule_list(schedule, ass_z)
    upcoming_call_ctr_z = verify_hour(ctr_z_sch_list)
    upcoming_call_ass_z = verify_hour(ass_z_sch_list)        
    global last_update
    last_update.update({'z' : datetime.now(timezone.utc)})
    return(console_z, upcoming_call_ctr_z, upcoming_call_ass_z)  
        