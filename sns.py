import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time
import threading
import thread
import sys
import Tkinter as tk
import json
from random import randint
import cfscrape

start_time = time.time()
atc_flag = False
botcheck_flag = False
botcheck_gate = False
proxy_flag = False
login_flag = False
restock_flag = False
autocheckout = False
countdown_retry_delay = 0

# TODO: change most of this stuff in config file later
url = 'http://sneakersnstuff.com'
sizes = ['10']
accounts = [
    {
        'username':'',
        'password':''
    }
]

proxies = [
    {
        "http": "",
        "https": ""
    }
]

tokens = []
ThreadCount = 1
threads = []

#2captcha
API_KEY = ''  # Your 2captcha API KEY
site_key = '6LflVAkTAAAAABzDDFKRJdb6RphdNfRPitO3xz2c'  # site-key, read the 2captcha docs on how to get this
s = requests.Session()
#anticaptcha
API_KEY_ANTI = ''
a = requests.Session()
# domain to solve captchas from
urlc = 'http://sneakersnstuff.com'

def addToCart(id, autocheckout, size):
    global url
    if botcheck_flag:
        chromedriver = webdriver.Chrome()
        chromedriver.get(urlc)

        global botcheck_gate
        while not botcheck_gate:
            continue

    headers = {
        "User-Agent":
            "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    c = cfscrape.create_scraper()
    #c = requests.Session()
    c.headers.update(headers)

    if botcheck_flag == True:
        browser_cookies = chromedriver.get_cookies()
        #c.cookies.update( {cookie['name']:cookie['value'] for cookie in browser_cookies} )
        for cookie in browser_cookies:
             c.cookies.set(cookie['name'], cookie['value'])#, path='/', domain=cookie['domain'])

    #set proxy
    if proxy_flag:
        if (len(proxies) > 0):
            c.proxies.update(proxies.pop())
    #login process\
    if login_flag:
        homepage = c.get("http://sneakersnstuff.com")
        homepage_content = BeautifulSoup(homepage.content, "html.parser")
        login_csrf = c.cookies['AntiCsrfToken']

        LOGIN_HEADERS = {
            'origin': "https://www.sneakersnstuff.com",
            "referer": "https://www.sneakersnstuff.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
            "x-anticsrftoken": login_csrf,
            "x-requested-with": "XMLHttpRequest"
        }

        account = accounts.pop()
        login_payload = {
            'ReturnURL': "",
            'username': account["username"],
            'password': account["password"],
            '_AntiCsrfToken': login_csrf
        }

        try:
            printToConsole("Logging in as %s" % (account["username"]), id)
            login_response = c.post('https://www.sneakersnstuff.com/en/authentication/login?skip_layout=1', data=login_payload, headers=LOGIN_HEADERS)
            login_response.raise_for_status()
            sys.stdout.flush()
        except requests.exceptions.HTTPError as err:
            sys.stdout.flush()
            if login_response.json():
                printToConsole("%s" % str(login_response.json()["Status"]), id)
            if err:
                print(err)
                sys.stdout.flush()
        else:
            printToConsole("Status: %s - Succesfully logged in as %s" % (str(login_response.json()["Status"]), account["username"]), id)

    printToConsole("Ready to ATC!", id)

    progress = 0
    if not restock_flag:
        global atc_flag
        while not atc_flag:
            # if progress%10000000 == 0:
            #     printToConsole("Standing By", id)
            # progress += 1
            continue

    #get product page info for product id
    #TODO: if size doesn't exist
    ID = -1
    first_load = 0
    while (ID == -1) or (ID is None):
        # currently must have url inputted or error :S
        url = url_entry.get()
        try:
            if (first_load == 0):
                printToConsole("Loading Product Page", id)
                first_load = 1
            response = c.get(url, timeout=10)
        except requests.exceptions.Timeout:
            printToConsole("Product Page Timed Out, retrying..", id)
            continue
        except requests.exceptions.HTTPError as err:
            printToConsole(err, id)
        soup = BeautifulSoup(response.content, "html.parser")
        #pull post parameters CSRF, partial, productID
        if 'AntiCsrfToken' in c.cookies:
            CSRF_TOKEN = c.cookies['AntiCsrfToken']
        PARTIAL = 'cart-summary'
        size_spans = soup.find_all("span", class_="size-type")
        for span in size_spans:
            size_text = span.string.replace('\r','').replace('\n','').replace('\t','').replace('US','').strip()
            if size_text == size:
                size_div = span.find_parent("div", class_="size-button")
                ID = size_div.attrs.get("data-productid")
        if ID is None:
            printToConsole("ProductID not available, product is not live, or size is not available. Retrying...", id)
            if countdown_retry_delay > 0:
                time.sleep(countdown_retry_delay)
        if (ID == -1):
            printToConsole("Size does not exist or page is not returning as expected. Retrying...", id)
            if countdown_retry_delay > 0:
                time.sleep(countdown_retry_delay)

    # get add to cart request ready
    HEADERS = {
        'origin': "https://www.sneakersnstuff.com",
        "referer": url,
        "user-agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        "x-anticsrftoken": CSRF_TOKEN,
        "x-requested-with": "XMLHttpRequest"
    }

    if restock_flag:
        while not atc_flag:
            continue
            # if progress%100000000 == 0:
            #     printToConsole("Standing By", id)
            # progress += 1

    # format atc payload (move this inside try to pop a new captcha response each time)
    PARTIAL = 'cart-summary'
    post_payload = {}
    if (len(tokens) > 0):
        post_payload = {
            'g-recaptcha-response': tokens.pop(),
            '_AntiCsrfToken': CSRF_TOKEN,
            'partial': PARTIAL,
            'id': ID
        }
        label.config(text="captchas: " + str(len(tokens)))
    else:
        post_payload = {
            '_AntiCsrfToken': CSRF_TOKEN,
            'partial': PARTIAL,
            'id': ID
        }

    # send atc post request, retry i times if httperror
    # TODO: handle errors better, add scheduling, and figure out better retry protocol
    for i in range(1,60):
        try:
            printToConsole("ATC Request sent, attempt #%d" % (i), id)
            atc_response = c.post('https://www.sneakersnstuff.com/en/cart/add', data=post_payload, headers=HEADERS, timeout=30)
            atc_response.raise_for_status()
        except requests.exceptions.Timeout:
            printToConsole("ATC Request Timed Out, retrying..", id)
            if (len(tokens) > 0):
                post_payload = {
                'g-recaptcha-response': tokens.pop(),
                '_AntiCsrfToken': CSRF_TOKEN,
                'partial': PARTIAL,
                'id': ID
                }
                label.config(text="captchas: " + str(len(tokens)))
            else:
                post_payload = {
                '_AntiCsrfToken': CSRF_TOKEN,
                'partial': PARTIAL,
                'id': ID
                }
            continue
        except requests.exceptions.HTTPError as err:
            if atc_response.json():
                printToConsole("%s" % str(atc_response.json()["Status"]), id)
                #printToConsole("error")
            if err:
                #print(err)
                #sys.stdout.flush()
                if (len(tokens) > 0):
                    post_payload = {
                        'g-recaptcha-response': tokens.pop(),
                        '_AntiCsrfToken': CSRF_TOKEN,
                        'partial': PARTIAL,
                        'id': ID
                    }
                    label.config(text="captchas: " + str(len(tokens)))
                else:
                    post_payload = {
                        '_AntiCsrfToken': CSRF_TOKEN,
                        'partial': PARTIAL,
                        'id': ID
                    }
            time.sleep(0.25)
            #time.sleep(randint(10,20))
            continue
        else:
            printToConsole("[[SUCCESS]] Added to cart successfully, SIZE:%s attempt #%d" % (size, i), id)
            #printToConsole(c.cookies)
            break
    else:
        printToConsole("[[FAILED]] All attempts failed", id)

    #checkout stuff here
    if (autocheckout):
        # TODO: implement autocheckout
        print("test")
    elif (not autocheckout):
        # open up chrome instance to checkout manually
        printToConsole("Autocheckout Disabled: Opening Cart in Chrome", id)
        chromedriver2 = webdriver.Chrome()
        chromedriver2.get(url)
        time.sleep(0.5)
        chromedriver2.delete_all_cookies()
        for cookie in c.cookies:
            chromedriver2.add_cookie({
            'name': cookie.name,
            'value': cookie.value
            # 'path': '/',
            # 'domain': cookie.domain
            })
        sys.stdout.flush()
        chromedriver2.get("https://www.sneakersnstuff.com/en/cart/view")
        raw_input("Press enter to exit ;)\n")

def startThreads():
    printToConsole("THREADS STARTED")
    sys.stdout.flush()
    for i in range(len(sizes)):
        t = threading.Thread(target=addToCart, args=(i+1, autocheckout, sizes[i]))
        #t.daemon = True
        threads.append(t)
        t.start()

def printToConsole(string, id=-1):
    # TODO: write to log file
    if id > -1:
        sys.stdout.write("[%s](Thread #%d) %s\n" % (time.ctime(), id, string))
    else:
        sys.stdout.write("[%s] %s\n" % (time.ctime(), string))
    sys.stdout.flush()

def harvestCaptcha():
    # TODO: handle captcha errors
    def startThread():
        printToConsole('Requesting a captcha response from 2captcha')
        captcha_id = s.post("http://2captcha.com/in.php?key={}&method=userrecaptcha&googlekey={}&pageurl={}".format(API_KEY, site_key, urlc)).text.split('|')[1]
        # then we parse gresponse from 2captcha response
        recaptcha_answer = s.get("http://2captcha.com/res.php?key={}&action=get&id={}".format(API_KEY, captcha_id)).text
        while 'CAPCHA_NOT_READY' in recaptcha_answer:
            #print("waiting for captcha to be solved")
            sys.stdout.flush()
            time.sleep(3)
            recaptcha_answer = s.get("http://2captcha.com/res.php?key={}&action=get&id={}".format(API_KEY, captcha_id)).text
        recaptcha_answer = recaptcha_answer.split('|')[1]
        tokens.append(recaptcha_answer)
        label.config(text="captchas: " + str(len(tokens)))
        printToConsole("Captcha response recieved from 2captcha")
        #sleep for 2 minutes, delete token
        time.sleep(110)
        for token in tokens:
            if (token == recaptcha_answer):
                tokens.remove(token)
        label.config(text="captchas: " + str(len(tokens)))
    t = threading.Thread(target=startThread)
    threads.append(t)
    t.start()

def harvestCaptcha2():
    # TODO: handle captcha errors
    def startThread():
        printToConsole('Requesting a captcha response from AntiCaptcha')
        headers = {'content-type': 'application/json'}
        request_data = {
			"clientKey":API_KEY_ANTI,
			"task":
				{
					"type":"NoCaptchaTaskProxyless",
					"websiteURL":url,
					"websiteKey":site_key
				},
			"languagePool":"en"
		}
        response = a.post("https://api.anti-captcha.com/createTask", data=json.dumps(request_data), headers=headers)
        json_data = json.loads(response.text)
        taskID = -1
        if (json_data["errorId"] == 0):
            taskID = json_data["taskId"]

        request_data2 = {
		    "clientKey":API_KEY_ANTI,
		    "taskId":taskID
		}
        if (taskID != -1):
            response2 = a.post("https://api.anti-captcha.com/getTaskResult",data=json.dumps(request_data2), headers=headers)
            json_data2 = json.loads(response2.text)
            if json_data2["errorId"] == 0:
                token_waiting = True
                while(token_waiting):
                    if json_data2["status"] == "ready":
                        g_response = json_data2["solution"]["gRecaptchaResponse"]
                        tokens.append(g_response)
                        label.config(text="captchas: " + str(len(tokens)))
                        printToConsole('Captcha response recieved from AntiCaptcha')
                        #sleep for 2 minutes, delete token
                        token_waiting = False
                        time.sleep(110)
                        for token in tokens:
                            if (token == g_response):
                                tokens.remove(token)
                        label.config(text="captchas: " + str(len(tokens)))
                    else:
                        time.sleep(3)
                        response2 = a.post("https://api.anti-captcha.com/getTaskResult",data=json.dumps(request_data2), headers=headers)
                        json_data2 = json.loads(response2.text)
    t = threading.Thread(target=startThread)
    threads.append(t)
    t.start()

def toggleAtcGate():
    global atc_flag
    atc_flag = not atc_flag
    label_atc.config(text="atc flag: " + str(atc_flag))

def toggleBotCheckFlag():
    global botcheck_gate
    botcheck_gate = not botcheck_gate

# UI Elements
root = tk.Tk()
root.title("SNS")
root.geometry("400x500")

label = tk.Label(root, fg="dark green")
label_atc = tk.Label(root, fg="dark green")
label_atc.config(text="atc flag: " + str(atc_flag))
label.config(text="captchas: " + str(len(tokens)))
label.grid(row=0, column=0, padx=(20,0))
label_atc.grid(row=2, column=0, padx=(20,0))

url_entry = tk.Entry(root, width=60)
url_entry.grid(row=5, column=0, columnspan=2, padx=(15,0), pady=(5,0))

captcha2 = tk.Button(root, text='AntiCaptcha', pady=10, width=25, command=harvestCaptcha2)
captcha = tk.Button(root, text='2Captcha', pady=10, width=25, command=harvestCaptcha)
start = tk.Button(root, text='Start Threads / Login', pady=10, width=25, command=startThreads)
botcheck = tk.Button(root, text='Bot Check Passed', pady=10, width=25, command=toggleBotCheckFlag)
atc = tk.Button(root, text='Open ATC Gate', pady=10, width=25, command=toggleAtcGate)
captcha.grid(row=0, column=1, padx=(25,50), pady=(50,10))
captcha2.grid(row=1, column=1, padx=(25,50), pady=(10,10))
start.grid(row=2, column=1, padx=(25,50), pady=20)
botcheck.grid(row=3, column=1, padx=(25,50), pady=20)
atc.grid(row=4, column=1, padx=(25,50), pady=10)
root.mainloop()
