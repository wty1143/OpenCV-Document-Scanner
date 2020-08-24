import cv2
import os
import sys
import scan

from Crypto.Cipher import AES    
from Crypto.Hash import SHA256

from uuid import getnode as get_mac
import argparse
import time
from datetime import datetime

secret = 'pleasegivemoney!'
hash_obj = SHA256.new(secret.encode('utf-8'))  
hkey = hash_obj.digest()
key_name = '.key'

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
    
def integrity_test():
    if not os.path.exists(key_name):
        return False
    mac = get_mac()
    with open(key_name, 'rb') as f:
        plain_text = decrypt(f.read())
    return plain_text == str(mac)
    
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--make_key", action='store_true')
    ap.add_argument("--password", type=str)
    args = ap.parse_args()
    
    if args.make_key and args.password == '55665566':
        mac = get_mac()
        ciphertext = encrypt(str(mac))
        with open(key_name, 'wb') as f:
            f.write(ciphertext)
        sys.exit(0)
    
    if not integrity_test():
        sys.exit(0)
    
    if u'輸入' not in os.listdir():
        os.mkdir(u'輸入')
    
    if u'輸出' not in os.listdir():
        os.mkdir(u'輸出')
    
    # Force disable interactive_mode
    scanner = scan.DocScanner(False)
    
    while True:
        images = os.listdir(u'輸入')
        for image in images:
            print(image)
            im_file_path = os.path.join(u'輸入', image)
            scanner.scan(im_file_path, u'輸出', datetime.now().strftime("%Y%m%d%H%M%S"))
            os.remove(im_file_path)
        time.sleep(5)
