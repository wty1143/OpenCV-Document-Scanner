import cv2
import os
import sys
import scan
import traceback

from Crypto.Cipher import AES    
from Crypto.Hash import SHA256

import argparse
import time
import datetime
import requests

from tkinter import *

import img2pdf

import internet_checker
import subprocess
secret = 'pleasegivemoney!'
hash_obj = SHA256.new(secret.encode('utf-8'))  
hkey = hash_obj.digest()
key_name = '.key'

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    key_path = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), key_name)
else:
    base_path = ""
    key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), key_name)
        
SCALE_EXE = os.path.join(base_path, 'bin', 'scale.exe')
#IMG2PDF_EXE = os.path.join(base_path, 'bin', 'img2pdf.exe')
PDFTOPRINTER_EXE = os.path.join(base_path, 'bin', 'PDFtoPrinter.exe')
TRAIL_USE_DAY = 14

def encrypt(info):
    msg = info
    BLOCK_SIZE = 16
    PAD = "{"
    padding = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PAD
    cipher = AES.new(hkey, AES.MODE_ECB)
    result = cipher.encrypt(padding(msg).encode('utf-8'))
    return result 

def decrypt(info):
    msg = info
    PAD = "{"
    decipher = AES.new(hkey, AES.MODE_ECB)
    pt = decipher.decrypt(msg).decode('utf-8')
    pad_index = pt.find(PAD)
    result = pt[: pad_index]
    return result    

def get_today():    
    try:
        res = requests.get('http://just-the-time.appspot.com/')
        time_str = res.content.strip().decode('utf-8')
        year, month, day = int(time_str[:4]), int(time_str[5:7]), int(time_str[8:10])
        today = datetime.date(year, month, day)
        return today
    except Exception as ex:
        print(ex)
        sys.exit(0)
    
def integrity_test(window, text):
    if not os.path.exists(key_path):
        return False
    
    with open(key_path, 'rb') as f:
        plain_text = decrypt(f.read())
    
    time_str = plain_text[:8]
    year, month, day = int(time_str[:4]), int(time_str[4:6]), int(time_str[6:8])
    expire = datetime.date(year, month, day)
    
    remain_day = (expire - get_today()).days

    if remain_day <= 7:
        LOG("%d 天後到期" % remain_day, text)
    
    if remain_day <= TRAIL_USE_DAY:
        window.title('自動黑白銳利化(測試版) %d 天後到期' % remain_day)
    
    uuid = subprocess.Popen(['wmic', 'csproduct','get' ,'UUID'],shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE).stdout.read().decode('ascii')
    return str(plain_text[8:]) == uuid and remain_day > 0
    
def LOG(info, text):
    text.insert("insert", str(info)+'\n')
    
def DEBUG(info, text):
    if args.debug:
        LOG(info, text)
    
def worker(scanner, window, text):
    
    if u'輸入' not in os.listdir():
        LOG('創建資料夾:輸入', text)
        os.mkdir(u'輸入')
    
    if u'輸出' not in os.listdir():
        LOG('創建資料夾:輸出', text)
        os.mkdir(u'輸出')
    
    if not internet_checker.check_internet_on():
        LOG('請開啟網路')
        return
    
    if not integrity_test(window, text):
        return
    
    today = get_today()
    
    images = os.listdir(u'輸入')
    
    for image in images:
        im_file_path = os.path.join(u'輸入', image)
        LOG('找到了 %s' % im_file_path, text)
        try:
            output = subprocess.Popen([SCALE_EXE, im_file_path, '-B', '-O', '-s:250'],
                            shell=True, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE, 
                            stdin=subprocess.PIPE).stdout.read().decode('ascii')
            #LOG(os.path.exists(SCALE_EXE), text)
            #LOG(SCALE_EXE, text)
            #LOG(str([SCALE_EXE, im_file_path, '-B', '-O', '-s:250']), text)
            LOG(output, text)            
            prefix = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            scanner.scan(im_file_path, u'輸出', prefix)
            new_file_path = os.path.join(u'輸出', '{0}_{1}'.format(prefix, image))
            LOG('輸出至 %s.pdf' % new_file_path, text)
            
            with open(os.path.abspath("%s.pdf" % new_file_path), 'wb') as f:
                f.write(img2pdf.convert(os.path.abspath(new_file_path), fit='fill'))
            
            LOG('刪除 %s' % im_file_path, text)
            os.remove(im_file_path)
            
            LOG('列印 %s' % im_file_path, text)
            if not args.debug:
                output = subprocess.Popen([PDFTOPRINTER_EXE, "%s.pdf" % os.path.abspath(new_file_path)],
                                shell=True, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                stdin=subprocess.PIPE).stdout.read().decode('ascii')
                            
                os.remove(new_file_path)
                os.remove("%s.pdf" % os.path.abspath(new_file_path))
            
        except:
            LOG('處理 %s 失敗' % im_file_path, text)
            traceback.print_exc()
    
    window.after(5000, worker, scanner, window, text)
    

if __name__ == "__main__":
    global args
    ap = argparse.ArgumentParser()
    ap.add_argument("--make_key", action='store_true')
    ap.add_argument("--active", action='store_true')
    ap.add_argument("--debug", action='store_true')
    
    args = ap.parse_args()
    
    def register(info, expire):
        if info != '55665566':
            print('密碼錯誤')
            sys.exit(0)
            
        uuid = subprocess.Popen(['wmic', 'csproduct','get' ,'UUID'], 
                                shell=True, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                stdin=subprocess.PIPE).stdout.read().decode('ascii')
                                
        ciphertext = encrypt(expire.strftime("%Y%m%d")+uuid)
        
        with open(key_path, 'wb') as f:
            f.write(ciphertext)
        sys.exit(0)

    if args.make_key:
        print('註冊中')
        
        if args.active:
            d = datetime.timedelta(days = 80*365)
            expire = get_today() + d
        else:
            d = datetime.timedelta(days = TRAIL_USE_DAY)
            expire = get_today() + d
            print("14天後到期")
        
        parent = Tk()
        widget = Entry(parent, textvariable='註冊碼', bd=5, show="*", width=30)
        widget.pack()
        parent.bind('<Return>', lambda v: register(widget.get(), expire))
        parent.mainloop()
        
        
    window = Tk()
    window.title('自動黑白銳利化')
    window.geometry('400x300')
    window.configure(background='white')

    text = Text(window, width=360, height=280)
    text.pack()
    
    if not integrity_test(window, text):
        sys.exit(0)
        
    # Force disable interactive_mode
    scanner = scan.DocScanner(False)
    LOG("銳利化程式執行中", text)

    window.after(1000, worker, scanner, window, text)
        
    window.mainloop()