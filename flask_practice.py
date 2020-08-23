from flask import Flask, render_template, request
import time
import threading
import random
import webbrowser
import io
import scan

app = Flask(__name__)

class worker(threading.Thread):
    def __init__(self):
        self.progress = 0
        super(worker, self).__init__()
        self.daemon = True
        
    def run(self):
        # Your exporting stuff goes here ...
        for _ in range(100):
            time.sleep(0.1)
            self.progress += 1
            print(self.progress)
            
threads = [worker()]
lock = threading.Lock()

@app.route('/')
def index():
    return render_template('count_down.html')

@app.route('/transform', methods=['POST'])
def transform():
    for key, f in request.files.items():
        print (key, f)
        scan.worker(f.read())
        break
    # Do something in the local, but want to use progress to track
    #thread_id = random.randint(0, 10)
    #while True:
    #    if thread_id not in threads:
    #        break
    #    thread_id = random.randint(0, 10)
    #    
    #print('thread_id: %d' % thread_id)
    #lock.acquire()
    #if not threads or not threads[0].is_alive():
    #    print('[Start worker]')
    #    threads[0] = worker()
    #    threads[0].start()
    #lock.release()
    return {}

@app.route('/progress')
def progress(thread_id):
    #return Response("data:" + str(threads[7].progress) + "\n\n", mimetype= 'text/event-stream')
    return {"data": threads[0].progress}

def open_browser():
    url = 'http://127.0.0.1:5000/'
    webbrowser.open_new(url)

if __name__ == '__main__':
    threading.Timer(2, open_browser).start();
    #app.run(debug=False, threaded=False)
    app.run(debug=True)
    