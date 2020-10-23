import cv2
import numpy as np
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

import re
import json

JSON_FILE = 'record.json'
VERSION = '3.0'

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
SIMHEI_TTF = os.path.join(base_path, 'bin', 'simhei.ttf')
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
    
def integrity_test(window, text):
    if not os.path.exists(key_path):
        return False
    
    with open(key_path, 'rb') as f:
        plain_text = decrypt(f.read())
    
    uuid = subprocess.Popen(['wmic', 'csproduct','get' ,'UUID'],shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE).stdout.read().decode('ascii')
    return str(plain_text[8:]) == uuid 
    
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
    
    if JSON_FILE not in os.listdir():
        d = {}
        json.dump(d, open(JSON_FILE, "w"))
        
    images = os.listdir(u'輸入')
    
    for image in images:
        im_file_path = os.path.join(u'輸入', image)
        LOG('找到了 %s' % im_file_path, text)
        try:
            im = cv2.imdecode(np.fromfile(im_file_path, dtype=np.uint8),-1)
            (h, w) = im.shape[:2]
            
            # If image is too small, scale up
            if h*w <= 500*500:
                output = subprocess.Popen([SCALE_EXE, im_file_path, '-B', '-O', '-s:200'],
                                shell=True, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                stdin=subprocess.PIPE).stdout.read().decode('ascii')
                LOG(output, text)       
            
            # Process the image
            prefix = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            scanner.scan(im_file_path, u'輸出', prefix)
            
            new_file_path = os.path.join(u'輸出', '{0}_{1}'.format(prefix, image))
            LOG('輸出至 %s.pdf' % new_file_path, text)
            
            # 王元元_test_20201012235527-382722.jpg
            pattern = '^(.*?)_(.*?)_(..............)-......\.'
            
            # If image is from server, add timestamps
            m = re.match(pattern, image)
            if m:
                from PIL import Image
                from PIL import ImageDraw 
                from PIL import ImageFont 
                
                d = json.load(open(JSON_FILE, "r"))
                date = datetime.datetime.now().strftime("%Y/%m/%d")
                if date not in d or not isinstance(d[date], dict):
                    d[date] = {}
                    
                from_who = m.group(1)
                to_whom = m.group(2)
                ts = m.group(3)
                
                if from_who not in d[date]:
                    d[date][from_who] = 0
                d[date][from_who] += 1
                
                json.dump(d, open(JSON_FILE, "w"))
                
                year, month, day = ts[:4], ts[4:6], ts[6:8]
                hour, minute, second = ts[8:10], ts[10:12], ts[12:]
                recieve_time = u'接收時間: '
                recieve_time += u'%s/%s/%s %s:%s:%s' % (year, month, day, hour, minute, second)
                
                print_time = u'列印時間: '
                print_time += datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                print_time += u' %s 傳給 %s 第 %d 張' % (from_who, to_whom, d[date][from_who])
                
                origin_img = Image.open(new_file_path).convert('RGB').rotate(90, expand=True)
                if origin_img.size[0] < 720:
                    font = ImageFont.truetype(SIMHEI_TTF, 16, encoding="utf-8")
                else:
                    font = ImageFont.truetype(SIMHEI_TTF, 24, encoding="utf-8")
                
                # Extend
                width, height = origin_img.size
                img = Image.new(origin_img.mode, (width, height+48), (255, 255, 255))
                img.paste(origin_img, (0, 60))
                
                draw = ImageDraw.Draw(img)
                draw.text((10, 0), recieve_time, (0, 0, 0), font=font)
                draw.text((10, 30), print_time, (0, 0, 0), font=font)
                img = img.rotate(-90, expand=True)
                img.save(new_file_path)
                
            # Convert into pdf
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
    
    window.after(2000, worker, scanner, window, text)
    

if __name__ == "__main__":
    global args
    ap = argparse.ArgumentParser()
    ap.add_argument("--make_key", action='store_true')
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
       
        d = datetime.timedelta(days = 80*365)
        expire = datetime.datetime.now()

        
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
    LOG("銳利化程式執行中 版本 %s" % VERSION, text)

    window.after(1000, worker, scanner, window, text)
        
    window.mainloop()