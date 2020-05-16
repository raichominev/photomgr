import json
import os
import re
import sys
import traceback

import psycopg2
import requests
from sendgrid import Email, Content, Mail, sendgrid

CATEGORY_URL = "https://submit.shutterstock.com/api/content_editor/categories/photo"
NOTES_URL = "https://submit.shutterstock.com/api/content_editor/note_types"

DEFAULT_HEADERS = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0',
                   'Accept-Encoding' : 'gzip, deflate, br',
                   'Accept-Language':'en-US,en;q=0.5',
                   'Accept':'application/json',
                   'Host':'submit.shutterstock.com',
                   'Origin':'https://submit.shutterstock.com',
                   'Proxy-Authorization':'Basic cWVyNG43OHUtdmprdzJ0MzoybnVyeHpnOGRw',
                   'Content-Type':'application/json'}

BASE_FOLDER = "C:\\Users\\user-pc2\\Desktop\\shutterstock"

FOLDER_PENDING = BASE_FOLDER + "\\" + "pending"
FOLDER_UNDER_REVIEW = BASE_FOLDER + "\\" + "underReview"
FOLDER_REVIEWED = BASE_FOLDER + "\\" + "submitted"
FOLDER_REJECTED = BASE_FOLDER + "\\" + "rejected"


cookie_dict = {}
categories = None
reasons = None


def ss_login():
    global categories
    global reasons

    # cookies = os.environ['SS_AUTO_LOGIN_COOKIES']
    # cookies acquired on 14.04.2020
    cookies = 'locale=en-US; did=izwknfMux8KIk8VZXA__Lglwhq9MfRcqrgR2Bg2Opds%3D; ajs_user_id=%22239148037%22; ajs_group_id=null; visitor_id=59301717277; ajs_anonymous_id=%2206d2efca-d8aa-4349-a5ea-cd4c7d405ff6%22; __ssid=b91608fa8ae758b2479c8a0446eb43f; cto_lwid=d4cdedf9-5fbf-4c3d-a45b-17926ef11d3c; language=en; session=s%3A5dqASNOq_EugkGHMs0gK4VNPkm9QWPmu.zFRBK8QHxHuvzFuvSFGDXedtv5EK2IiDYqiBljKJQ%2Fo; _ga=GA1.2.2025806565.1570193260; _ym_uid=1570193260262376265; _ym_d=1586216457; __qca=P0-32455493-1570193261124; cto_bundle=6of2U19YQ0czb2owR0dhNWtleGRzNDBLZE9WNDY2YnhjcEpjandZVHNTQVBoJTJGbHI1NDViMWs4cmNEVlJDazczNnF5TTBKcUpjNnpveW5zaWc0OTFtZmYlMkZPWU9qa0ZvbDFFRWU2eVYzS0p2QXJjT21jYzZjaVdyVFdsaGZPeG9WZVZCNVZMWVltajFnVHpVZ3VHeUpOM3BCajJtNzF3JTJCaSUyQjZvb0laT2ZacWV3TEhYUSUzRA; ELOQUA=GUID=29DBE6CD48E345CBA843A3B372D1CDEE; _ceir=1; IR_PI=030d3091-e9e1-11e9-9f43-42010a246604%7C1587946729720; accts_customer=; accts_customer_sso1=; splitVar=AB_Test-adroll; _cs_c=1; _cs_id=a49ec4fa-7aa4-a86f-da64-2386df0dc63c.1576221764.38.1580233576.1580233241.1576175022.1610385764368; splitVar=AB_Test-criteo; _biz_uid=5069e667b50f459ebd0bf686275426b4; _biz_nA=3; _biz_pendingA=%5B%5D; _biz_flagsA=%7B%22Version%22%3A1%2C%22XDomain%22%3A%221%22%7D; ei_client_id=5e0cbbc40b3de10010253878; __insp_wid=7949100; __insp_slim=1577892765372; __insp_nv=true; __insp_targlpu=aHR0cHM6Ly9jdXN0b20uc2h1dHRlcnN0b2NrLmNvbS8%3D; __insp_targlpt=U2h1dHRlcnN0b2NrIEN1c3RvbQ%3D%3D; __insp_norec_sess=true; _pxvid=f74749c3-6a6d-11ea-8333-0242ac120009; _gcl_au=1.1.1508469977.1585824443; _fbp=fb.1.1586615325580.1295321476; _actts=1582551713.1587799312.1587860333; _actvc=44; _actcc=1.1.57.57; _actmu=208821ed-1609-45b0-a10b-8cfd4b3e8d40; visit_id=64820572179; accts_contributor=Raicho%20Minev; accts_contributor_sso1=238906963-undefined'

    # cookies = 'local    e=en-US; did=izwknfMux8KIk8VZXA__Lglwhq9MfRcqrgR2Bg2Opds%3D; ajs_user_id=%22239148037%22; ajs_group_id=null; visitor_id=44020985583; ajs_anonymous_id=%2206d2efca-d8aa-4349-a5ea-cd4c7d405ff6%22; __ssid=b91608fa8ae758b2479c8a0446eb43f; cto_lwid=d4cdedf9-5fbf-4c3d-a45b-17926ef11d3c; language=en; session=s%3AagMfBd7iSlvWaobLeV1J4LhAbkOtLDmz.RTiEumfZzTGbmxeZhhVav%2FN%2Fqxc4zrEdzedWcOUYEnQ; _ga=GA1.2.2025806565.1570193260; _ym_uid=1570193260262376265; _ym_d=1586216457; __qca=P0-32455493-1570193261124; cto_bundle=pLLbI19YQ0czb2owR0dhNWtleGRzNDBLZE9ibyUyQiUyQm9wMnlQJTJGSlVtdndJbVJGR2hFRWdCM3VhWiUyQlMzOHdtQUUzWXZxT1ZWNzkyRlBkZWkyTlg3cnkxTENRbk9KT0NxWUhTUEJKJTJGN1NMS2ZxSVdiMHBwaUpCMXkyRldEJTJCZE1vZHVzMTdiJTJCcm1PTkhIR0FxdTF4Z29Cb2FJNTdvajlENW9oYlZYdEFBSGVyWmR6bVN1MCUzRA; ELOQUA=GUID=29DBE6CD48E345CBA843A3B372D1CDEE; _ceir=1; IR_PI=030d3091-e9e1-11e9-9f43-42010a246604%7C1586950965493; accts_customer=; accts_customer_sso1=; splitVar=AB_Test-adroll; _cs_c=1; _cs_id=a49ec4fa-7aa4-a86f-da64-2386df0dc63c.1576221764.38.1580233576.1580233241.1576175022.1610385764368; splitVar=AB_Test-criteo; _biz_uid=5069e667b50f459ebd0bf686275426b4; _biz_nA=3; _biz_pendingA=%5B%5D; _biz_flagsA=%7B%22Version%22%3A1%2C%22XDomain%22%3A%221%22%7D; ei_client_id=5e0cbbc40b3de10010253878; __insp_wid=7949100; __insp_slim=1577892765372; __insp_nv=true; __insp_targlpu=aHR0cHM6Ly9jdXN0b20uc2h1dHRlcnN0b2NrLmNvbS8%3D; __insp_targlpt=U2h1dHRlcnN0b2NrIEN1c3RvbQ%3D%3D; __insp_norec_sess=true; bce=emailcore-shutters.23813205-; _pxvid=f74749c3-6a6d-11ea-8333-0242ac120009; _gid=GA1.2.647632038.1584683114; urefid={%22time%22:1585383092%2C%22referrer%22:%22https://submit.shutterstock.com/dashboard?language=en%22%2C%22entry_url%22:%22https://www.shutterstock.com/g/Raicho+Minev%22%2C%22contributor_id%22:%22238906963%22}; _gcl_au=1.1.1508469977.1585824443; CookieAwin=Other; CookieAwinExpiration=1589020633425; _fbp=fb.1.1586615325580.1295321476; _px3=be05fc683190f83b3763a655e1063ee4fbac3fb6c88ba1dd38b66754360ecae6:0ZRRxZp5nTc8BqruYWq1tLoixvucJOyRXk8BMSUVTM81ucia3/SX7RiquftLRhohAM2jT3pmRjh8RvspqSLy+Q==:1000:4MKsPBw0NYakDrTxFjaBmo9vsn1WTtEIQrdF/ffJpy45mt5czZKuV76/1QaqGqiEGaFm/58khAM+Q2i7OafkgFKCSClNB5M58R6NmDUqLdAVBjGq5oQNAYFqidaKXvQBH7Av4q6qi6kxwJRhKxmtqJU/IkI+AooR23jwXD7r5J4=; IR_gbd=shutterstock.com; IR_1305=1586864565493%7C83765%7C1586864565493%7C%7C; _4c_=jVJNj9sgEP0rK84hARsTiFRVaqVKPbdSjysMOEZJjMVHvOkq%2F71D4mxWyaU%2BWMzMe2%2BYx7yjqbcD2tBGcMEZp5Vs5ALt7CmizTvSY%2Fkfyy%2BHPdqgPqUxblarmNuDS8vY55RsiMnr3VL7w8qo2LdeBfN1r4ZtVlv7BeQXyA4ggsZg4Bxj2kWXLCS0H1JwbU4%2BlEJuow5uTM4Pv09jAeTB2M4NtvBytOFXUinHwszQ9GALTfsMKqcHtPamCFC5pHRZQSL9LaEgcByDN1mn13RtMtn2JZodFIw9Om1fJ2dSX9BNze%2FZ3rptnyANRpXsGApkWTUQTG4wfnokztkPYs3LRdrgJxgF4h8u2M6%2FvayLhC9j%2FbkwIoRQsSFcYDfTp2l6drz4djXzsTRX4C0fisWB48UMOO29VvtCv7xTtLq4%2F%2FQ0avDD6eBz%2FGmgRripbKcVNkIpzGomsWqswtowvTaMNF3H0XmB3q6LJRtKKCUMFisl2CLwj5QPEMGZecOQ5FQJqgWWmgrMKGdYCFbh1tS1amtSyba83UVTMl4xwUldi%2FN1mIsGFU89xXPPq%2F%2F404DYDncN9j%2F3njW%2BVd8%2Fcz9TiZSU8%2BaZenS3iW3Tdox0Eou6M5gRK7CwTOG1aCureVcZ1qAPScE5o2RNyCwJqzwrjvvb3e%2FgtZCcrBm9gdnc%2F3z%2BBw%3D%3D; _ym_isad=1; accts_contributor=Raicho%20Minev; accts_contributor_sso1=238906963-undefined; _actts=1582551713.1586856508.1586863557; visit_id=62689881411; _pxff_tm=1; AMP_TOKEN=%24NOT_FOUND; _uetsid=_uetc86cf04a-19f3-3a16-8fc8-f6c3d68e5bd3; _ym_visorc_23564932=b; _actvc=31; _actcc=1.1.43.43; _gat_UA-32034-2=1; _actmu=208821ed-1609-45b0-a10b-8cfd4b3e8d40; _actms=4a441f86-96eb-45ae-bbe2-5dffcaa16c22'
    #cookies = 'locale=en-US; did=izwknfMux8KIk8VZXA__Lglwhq9MfRcqrgR2Bg2Opds%3D; ajs_user_id=%22239148037%22; ajs_group_id=null; visitor_id=44020985583; ajs_anonymous_id=%2206d2efca-d8aa-4349-a5ea-cd4c7d405ff6%22; __ssid=b91608fa8ae758b2479c8a0446eb43f; cto_lwid=d4cdedf9-5fbf-4c3d-a45b-17926ef11d3c; language=en; session=s%3AXBvZb6f-v3m7lZUcmzpHHPzhJi9UQn-1.7nwhu2UJ7%2BRjg5rfurI59%2FX%2Bd3U6g2TJ%2BkscyVh%2FM%2FE; _ga=GA1.2.2025806565.1570193260; _ym_uid=1570193260262376265; _ym_d=1570193260; __qca=P0-32455493-1570193261124; cto_bundle=T7JXX19YQ0czb2owR0dhNWtleGRzNDBLZE9TTmZUbiUyRlYlMkZubWZOMk1KRHlaU3Z4bXQ4bVlXTSUyQkpQOXAlMkZ6c2NkNCUyRmNaQWNURnJXUjFUMmt3YlRCdDRuWkJtWDBVUEwxM3NnRUdxUlNlV25LcCUyRk1nVUglMkJ4UmpxYjJ6Z3lmTlpHYnI1TWhWcUltWThqNjVBbDVscWd6R3k0NnJFJTJCVmJYa2Z5ZTZHclEydERJemZWV0c4JTNE; ELOQUA=GUID=29DBE6CD48E345CBA843A3B372D1CDEE; _ceir=1; IR_PI=030d3091-e9e1-11e9-9f43-42010a246604%7C1585910843710; accts_customer=; accts_customer_sso1=; splitVar=AB_Test-adroll; _cs_c=1; _cs_id=a49ec4fa-7aa4-a86f-da64-2386df0dc63c.1576221764.38.1580233576.1580233241.1576175022.1610385764368; splitVar=AB_Test-criteo; _biz_uid=5069e667b50f459ebd0bf686275426b4; _biz_nA=3; _biz_pendingA=%5B%5D; _biz_flagsA=%7B%22Version%22%3A1%2C%22XDomain%22%3A%221%22%7D; ei_client_id=5e0cbbc40b3de10010253878; __insp_wid=7949100; __insp_slim=1577892765372; __insp_nv=true; __insp_targlpu=aHR0cHM6Ly9jdXN0b20uc2h1dHRlcnN0b2NrLmNvbS8%3D; __insp_targlpt=U2h1dHRlcnN0b2NrIEN1c3RvbQ%3D%3D; __insp_norec_sess=true; bce=emailcore-shutters.23808045-; accts_contributor=Raicho%20Minev; accts_contributor_sso1=238906963-undefined; _pxvid=f74749c3-6a6d-11ea-8333-0242ac120009; _gid=GA1.2.647632038.1584683114; urefid={%22time%22:1585383092%2C%22referrer%22:%22https://submit.shutterstock.com/dashboard?language=en%22%2C%22entry_url%22:%22https://www.shutterstock.com/g/Raicho+Minev%22%2C%22contributor_id%22:%22238906963%22}; _gcl_au=1.1.1508469977.1585824443; _actts=1582551713.1585594427.1585824445; _actvc=22; _actcc=1.1.27.27; _actmu=208821ed-1609-45b0-a10b-8cfd4b3e8d40; IR_gbd=shutterstock.com; IR_1305=1585824443710%7Cc-17705%7C1585824443710%7C%7C; _4c_=jVNNb9swDP0rhQ491Y78IVkOEOw2YIeeVmDHQpboWEsiGZKcNCvy30fls812aHyIRD4%2BkXzkO9kNYMm8YIJTzgRt2qZ6IivYBzJ%2FJ97o9Lclc1L0HetEyTPZ9X1WS9ZlHW9Z1jIlqNSiKDQjT%2BQtcbUVLWpR0bauD09E2wuHBw3BLO0NVwhKG8FFhTgzxjMQs2Gs4ZwKWpafsII37Ii9UI7kv341ngHvZPJrxA0xjmE%2Bm4Wp25iYh2GKEXyITq1y5TYzD1sDO9Df1tIuJ7mEBdjHi%2FE1RBmnsPDwG1QE%2FRicjwuLrhAf436ExTi46DAVsMekvMZzCHEVTAQ0KGejN90UnU%2BOqQvKY7nG2ReMRsBkNfTGQoqbAvifxwdT5IQ5biCFKTchy%2F4OrZxOBEWbF0VeoiH%2BSVdB8Th6pycVX%2BPpkR10D0Gv0KGxMAWvO6PjkNA1FTfrAGY5oBSkaROfHn2C5BX%2F9CWxd8Zqt7unOVuvNFwka%2BfdDgvD%2B3fjoXdvD02NZpeK%2FHWMCHhFD3h%2FhF0Us5uK5rLb5t1y9izNOh%2FiZp26eGrtvZJnD07wnTP1I4lTNnhaOyXXKRzSMAZUFbX4Ryhpnd1v3BR%2B4BoQynUJvZKZFlJmdVW3mWQgM6Vr1eiasr7nGPTizXIJ%2Fhni4FLYi5faJHqZsk7L8HEPdOoQ3lbRjVfz4TzTghesLCmnlKKuEedY8Jqm3%2BFUzHHEy%2BYr8FP%2Fsw8FZmBvHOwrHNvr2kFZlrKpIOt0gb1oRZ2JkuoM6rZqGOOF1i25UlLecMqatMtHyrSp5yLWl5W%2FgXHpE1hcwPX5%2FcPhLw%3D%3D; visit_id=62060923486'
    for c in cookies.split(';'):
        name,val = c.split('=',1)
        cookie_dict[name.strip()] = val.strip()

    ##############################
    # GET AUXILIARY  DATA LIST
    response = requests.get(CATEGORY_URL, cookies=cookie_dict, headers=DEFAULT_HEADERS)
    print('Login response:' + str(response))
    print(str(response.content))
    category_json = response.json()
    categories = dict((ct['cat_id'],ct) for ct in category_json['data'])

    # print(json.dumps(categories))

    response = requests.get(NOTES_URL, cookies=cookie_dict, headers=DEFAULT_HEADERS)
    reasons_json = response.json()
    reasons = dict((ct['id'],ct['name']) for ct in reasons_json['data'])

    # print(json.dumps(reasons))


def connect_database():
    return psycopg2.connect(os.environ["DATABASE_URL"])

titleMatch = r'T#.*#T'
catMatch = r'C#[0-9]{1,2}'
reworkMatch = r'[-]?R[!][0-9]{1,2}'


def get_stripped_file_name(filename, do_not_strip_exclamation = False):
    m = re.search(titleMatch, filename)
    if m:
        filename = filename [:m.start()] + filename[m.end():]

    while True:
        m = re.search(catMatch, filename)
        if not m: break
        filename = filename [:m.start()] + filename[m.end():]

    filename = filename.replace("..",".")
    if not do_not_strip_exclamation:
        filename = filename.replace("!","")
    return filename

def is_rework(filename):
    m = re.search(reworkMatch, filename)
    if m:
        return True

    return False

def get_rework_original_file_name(filename):
    while True:
        m = re.search(reworkMatch, filename)
        if not m:
            break

        filename = filename [:m.start()] + filename[m.end():]

    # 25.04.2020 - patch for Lightroom edited and reworked files
    while True:
        m = re.search(r'-Edit', filename)
        if not m:
            break

        filename = filename [:m.start()] + filename[m.end():]

    return get_stripped_file_name(filename)

def extract_data_from_file_name(filename):

    m = re.search(titleMatch, filename)
    title = filename[m.start()+2:m.end()-2] if m else None

    catList = re.findall(catMatch, filename)
    cat1 = str(int(catList[0][2:])) if len(catList) > 0 else None
    cat2 = str(int(catList[1][2:])) if len(catList) > 1 else None

    return {'title': title, 'cat1': cat1, 'cat2': cat2, 'location':None}


def send_notification_email(subject, message):

    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
    from_email = Email(os.environ.get('SENDGRID_USERNAME'))
    to_email = os.environ.get('SERVICE_EMAIL')
    content = Content("text/plain", message)
    mail = Mail(from_email=from_email, subject=subject, to_emails=to_email, plain_text_content=content)
    response = sg.client.mail.send.post(request_body=mail.get())

    print(response.status_code)
    print(response.body)
    print(response.headers)


def handleException(exception_data, module_name):
    try:
        send_notification_email('Error in ' + module_name, exception_data)
    except:
        print('Error sending exception mail.')
        print(''.join(traceback.format_exception(*sys.exc_info())))
