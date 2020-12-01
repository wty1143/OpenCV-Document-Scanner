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

from shutil import copyfile, rmtree

import psutil
from urllib.request import urlopen

##################
import tempfile
class SingleInstanceException(BaseException):
    pass


class SingleInstance(object):

    """Class that can be instantiated only once per machine.

    If you want to prevent your script from running in parallel just instantiate SingleInstance() class. If is there another instance already running it will throw a `SingleInstanceException`.

    >>> import tendo
    ... me = SingleInstance()

    This option is very useful if you have scripts executed by crontab at small amounts of time.

    Remember that this works by creating a lock file with a filename based on the full path to the script file.

    Providing a flavor_id will augment the filename with the provided flavor_id, allowing you to create multiple singleton instances from the same file. This is particularly useful if you want specific functions to have their own singleton instances.
    """

    def __init__(self, flavor_id="", lockfile=""):
        self.initialized = False
        if lockfile:
            self.lockfile = lockfile
        else:
            basename = os.path.splitext(os.path.abspath(sys.argv[0]))[0].replace(
                "/", "-").replace(":", "").replace("\\", "-") + '-%s' % flavor_id + '.lock'
            self.lockfile = os.path.normpath(
                tempfile.gettempdir() + '/' + basename)

        if sys.platform == 'win32':
            try:
                # file already exists, we try to remove (in case previous
                # execution was interrupted)
                if os.path.exists(self.lockfile):
                    os.unlink(self.lockfile)
                self.fd = os.open(
                    self.lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            except OSError:
                type, e, tb = sys.exc_info()
                if e.errno == 13:
                    raise SingleInstanceException()
                print(e.errno)
                raise
        else:  # non Windows
            self.fp = open(self.lockfile, 'w')
            self.fp.flush()
            try:
                fcntl.lockf(self.fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                raise SingleInstanceException()
        self.initialized = True

    def __del__(self):
        if not self.initialized:
            return
        try:
            if sys.platform == 'win32':
                if hasattr(self, 'fd'):
                    os.close(self.fd)
                    os.unlink(self.lockfile)
            else:
                fcntl.lockf(self.fp, fcntl.LOCK_UN)
                # os.close(self.fp)
                if os.path.isfile(self.lockfile):
                    os.unlink(self.lockfile)
        except Exception as e:
            pass
            #sys.exit(-1)
##################

DAILY_FILE = 'log.txt'
JSON_FILE = 'record.json'
VERSION = '4.5'

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

def safe_remove(filename):
    safe_remove_count = 1
    while os.path.exists(filename):
        try:
            os.remove(filename)
        except:
            safe_remove_count += 1
            pass
    return safe_remove_count

def STEP_LOG(msg, path):
    log_update_sucess_retry = 0
    now = datetime.datetime.now()
    
    while log_update_sucess_retry < 10:
        try:
            now_str = now.strftime("%Y/%m/%d %H:%M:%S")
            msg = msg.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
            with open(path, "a", encoding="utf-8") as f:
                f.write('[%s] %s\n' % (now_str, msg))
            break
        except:
            log_update_sucess_retry += 1
    
    try:
        if log_update_sucess_retry == 10:
            now_str = now.strftime("%Y/%m/%d %H:%M:%S")
            with open(path, "a") as f:
                f.write('[%s] tried to log 10 times but still fail\n' % (now_str))
    except:
        pass
        
def worker(scanner, window, text):
    
    # Check Dropbox.exe is active
    dropbox_path1 = r'C:\Program Files (x86)\Dropbox\Client\Dropbox.exe'
    dropbox_path2 = r'C:\Program Files\Dropbox\Client\Dropbox.exe'
    find, success = False, False
    for p in psutil.process_iter():
        try:
            name = p.name()
        except:
            name = ''
            continue
        if "Dropbox.exe" == name:
            find = True
            break
            
    if not find:
        try:
            # if not active, try the C:\ version
            if os.path.exists(dropbox_path1):
                subprocess.Popen('"%s"' % dropbox_path1)
                success = True
            # try another
            elif os.path.exists(dropbox_path2):
                subprocess.Popen('"%s"' % dropbox_path2)
                success = True
        except:
            pass
            
        if not success:
            # if none of them works, warning and leave
            from tkinter import messagebox
            messagebox.showerror("錯誤", "請重新啟動Dropbox!!!")
            #sys.exit(0)
        
    if u'輸入' not in os.listdir():
        LOG('創建資料夾:輸入', text)
        os.mkdir(u'輸入')
    
    if u'輸出' not in os.listdir():
        LOG('創建資料夾:輸出', text)
        os.mkdir(u'輸出')
        
    if u'原圖' not in os.listdir():
        LOG('創建資料夾:原圖', text)
        os.mkdir(u'原圖')
        
    if JSON_FILE not in os.listdir():
        d = {}
        json.dump(d, open(JSON_FILE, "w"))
        
    images = os.listdir(u'輸入')
    
    for image in images:
        im_file_path = os.path.join(u'輸入', image)
        
        # record current time
        use_internet_time = True
        try:
            res = urlopen('http://just-the-time.appspot.com/')
            time_str = res.read().strip().decode('utf-8')
            year, month, day = int(time_str[:4]), int(time_str[5:7]), int(time_str[8:10])
            hour, minute, second = int(time_str[11:13]), int(time_str[14:16]), int(time_str[17:19])
            now = (datetime.datetime(year, month, day, hour, minute, second)+datetime.timedelta(hours=8))
        except:
            use_internet_time = False
            now = datetime.datetime.now()
        
        convert_to_image_count = 1
        print_count = 1
        LOG('找到了 %s' % im_file_path, text)
        try:
            # Backup the image first
            backup_folder = os.path.join(u'原圖', now.strftime("%Y%m%d"))
            if not os.path.exists(backup_folder):
                os.mkdir(backup_folder)
            back_path = os.path.join(backup_folder, image)
            
            log_path = os.path.join(backup_folder, DAILY_FILE)
            STEP_LOG('Start to process %s' % im_file_path, log_path)
            if use_internet_time:
                STEP_LOG('Using use_internet_time %s' % now , log_path)
            else:
                STEP_LOG('Using local time %s' % now, log_path)
                
            # Backup to origin
            copyfile(im_file_path, back_path)
            STEP_LOG('Backup to %s done' % back_path, log_path)
        
            im = cv2.imdecode(np.fromfile(im_file_path, dtype=np.uint8),-1)
            (h, w) = im.shape[:2]
            
            STEP_LOG('Get H/W of image done', log_path)
            
            # If image is too small, scale up
            try:
                if h*w <= 500*500:
                    STEP_LOG('Image too small, try to scale up', log_path)
                    output = subprocess.call([SCALE_EXE, im_file_path, '-B', '-O', '-s:200'])
                    STEP_LOG('Image too small, try to scale up done', log_path)
            except:
                pass
                      
            
            # Process the image
            STEP_LOG('Process the image', log_path)
            prefix = now.strftime("%Y%m%d%H%M%S")
            scanner.scan(im_file_path, u'輸出', prefix)
            STEP_LOG('Process the image done', log_path)
            
            new_file_path = os.path.join(u'輸出', '{0}_{1}'.format(prefix, image))
            LOG('輸出至 %s.pdf' % new_file_path, text)
            
            # 王元元_test_20201012235527-382722.jpg
            pattern = '^(.*?)_(.*?)_(..............)-......\.'
            
            date_file_path = os.path.join(u'輸出', 'date_{0}_{1}'.format(prefix, image))
            
            # If image is from server, add timestamps
            m = re.match(pattern, image)
            if m:
                STEP_LOG('Image is from server, add timestamps', log_path)
                from PIL import Image
                from PIL import ImageDraw 
                from PIL import ImageFont 
                
                d = json.load(open(JSON_FILE, "r"))
                date = now.strftime("%Y/%m/%d")
                if date not in d or not isinstance(d[date], dict):
                    d[date] = {}
                    
                from_who = m.group(1)
                to_whom = m.group(2)
                ts = m.group(3)
                
                if from_who not in d[date]:
                    d[date][from_who] = 0
                d[date][from_who] += 1
                
                json_update_sucess = False
                while not json_update_sucess:
                    try:
                        json.dump(d, open(JSON_FILE, "w"))
                        json_update_sucess = True
                    except:
                        pass
                
                year, month, day = ts[:4], ts[4:6], ts[6:8]
                hour, minute, second = ts[8:10], ts[10:12], ts[12:]
                recieve_time = u'接收時間: '
                recieve_time += u'%s/%s/%s %s:%s:%s' % (year, month, day, hour, minute, second)
                
                print_time = u'列印時間: '
                print_time += now.strftime("%Y/%m/%d %H:%M:%S")
                print_time += u' %s 傳給 %s 第 %d 張' % (from_who, to_whom, d[date][from_who])
                
                STEP_LOG(u'add %s 傳給 %s 第 %d 張 to image' % (from_who, to_whom, d[date][from_who]), log_path)
                
                origin_img = Image.open(new_file_path).convert('RGB').rotate(90, expand=True)
                if origin_img.size[0] <= 720:
                    text_width = 20
                    font = ImageFont.truetype(SIMHEI_TTF, 16, encoding="utf-8")
                elif origin_img.size[0] <= 1440:
                    text_width = 30
                    font = ImageFont.truetype(SIMHEI_TTF, 24, encoding="utf-8")
                else:
                    text_width = 40
                    font = ImageFont.truetype(SIMHEI_TTF, 36, encoding="utf-8")
                
                STEP_LOG('Start to extend image', log_path)
                # Extend
                width, height = origin_img.size
                img = Image.new(origin_img.mode, (width, height+48), (255, 255, 255))
                img.paste(origin_img, (0, text_width*2))
                
                STEP_LOG('Start to draw image', log_path)
                draw = ImageDraw.Draw(img)
                draw.text((10, 0), recieve_time, (0, 0, 0), font=font)
                draw.text((10, text_width), print_time, (0, 0, 0), font=font)
                img = img.rotate(-90, expand=True)
                STEP_LOG('Start to save to new path', log_path)
                img.save(date_file_path)
            else:
                STEP_LOG('Not fit format, bypass the add timestamp process', log_path)
                copyfile(new_file_path, date_file_path)
            
            # Convert into pdf
            
            while convert_to_image_count < 4:
                try:
                    STEP_LOG('Convert to image, count %d' % convert_to_image_count, log_path)
                    with open(os.path.abspath("%s.pdf" % date_file_path), 'wb') as f:
                        f.write(img2pdf.convert(os.path.abspath(date_file_path), fit='fill'))
                    STEP_LOG('Convert to image done', log_path)
                    break
                except:
                    convert_to_image_count += 1
            
            
            LOG('刪除 %s' % im_file_path, text)
            STEP_LOG('Try to remove %s' % im_file_path, log_path)
            count = safe_remove(im_file_path)
            STEP_LOG('Try to remove %s done, try %d time' % (im_file_path, count), log_path)
            
            LOG('列印 %s' % im_file_path, text)
            if not args.debug:
                
                while print_count < 4:
                    try:
                        STEP_LOG('Print pdf, count %d' % print_count, log_path)
                        subprocess.call([PDFTOPRINTER_EXE, "%s.pdf" % os.path.abspath(date_file_path)])
                        STEP_LOG('Print pdf, done', log_path)
                        break
                    except:
                        print_count += 1
                
                STEP_LOG('Try to remove %s' % new_file_path, log_path)
                count = safe_remove(new_file_path)
                STEP_LOG('Try to remove %s done, try %d time' % (new_file_path, count), log_path)
                
                STEP_LOG('Try to remove %s' % ("%s.pdf" % os.path.abspath(date_file_path)), log_path)
                count = safe_remove("%s.pdf" % os.path.abspath(date_file_path))
                STEP_LOG('Try to remove %s done, try %d time' % ("%s.pdf" % os.path.abspath(date_file_path), count), log_path)
                
                STEP_LOG('Try to remove %s' % date_file_path, log_path)
                count = safe_remove(date_file_path)
                STEP_LOG('Try to remove %s done, try %d time' % (date_file_path, count), log_path)
            STEP_LOG('SUCCESS', log_path)
            
        except:
            LOG('處理 %s 失敗' % im_file_path, text)
            STEP_LOG('[!!!!Exception!!!!!]', log_path)
            STEP_LOG('convert_to_image_count = %d' % convert_to_image_count, log_path)
            STEP_LOG('print_count = %d' % print_count, log_path)
            
    folders = os.listdir(u'原圖')
    now = datetime.datetime.now()
    # Step 2, delete the folder that is expire
    for folder in folders:
        try:
            date = datetime.datetime.strptime(folder, "%Y%m%d")
            if (now - date).days >= 7:
                rmtree(os.path.join(u'原圖', folder))
                LOG('刪除原圖 %s' % folder, text)
        except:
            traceback.print_exc()
            pass
    
    window.after(1000, worker, scanner, window, text)
    

if __name__ == "__main__":
    try:
        me = SingleInstance()
    except:
        from tkinter import messagebox
        messagebox.showerror("錯誤", "請勿重複開啟銳利化程式!!!")
        sys.exit(0)
    
    #try:
    #    if not internet_checker.check_internet_on():
    #        messagebox.showerror("錯誤", "請先開啟網路!!!")
    #    sys.exit(0)
    #except:
    #    pass
    
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
    
    version_update_sucess = False
    while not version_update_sucess:
        try:
            with open('version.txt', 'w') as f:
                f.write(VERSION)
            version_update_sucess = True
        except:
            pass
    
    window.after(1000, worker, scanner, window, text)
        
    window.mainloop()