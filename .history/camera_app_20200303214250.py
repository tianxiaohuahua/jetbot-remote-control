from tornado import httpclient
import tornado.ioloop
import tornado.web
import cv2
import logging
from tornado.escape import json_encode

logger = logging.getLogger(__name__)
handler1 = logging.StreamHandler()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
handler1.setFormatter(formatter)

def gstreamer_pipeline(
    capture_width=640,
    capture_height=480,
    display_width=640,
    display_height=480,
    framerate=60,
    flip_method=2,
):
    return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), "
        "width=(int)%d, height=(int)%d, "
        "format=(string)NV12, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
        % (
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
    )

def open_onboard_camera():
    pl = gstreamer_pipeline()
    print(pl)
    return cv2.VideoCapture(pl,  cv2.CAP_GSTREAMER)


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('templates/index.html')


class VideoHandler(tornado.web.RequestHandler):
    async def get(self):
        
        self.set_header( 'Content-Type', 'multipart/x-mixed-replace;boundary=frame')
        camera = open_onboard_camera()
        if camera.isOpened():
            while True:
                _, img = camera.read()
                img_bytes =  cv2.imencode('.jpg', img)[1].tobytes()

                self.write('--frame\r\n')
                self.write("Content-type: image/jpeg\r\n")
                self.write("Content-length: %s\r\n\r\n" % len(img_bytes))
                self.write(img_bytes)
                self.flush()
        

class MotionHandler(tornado.web.RequestHandler):
    async def get(self):
        logger.debug('[Motion Handler] GOT IT!!!!!')
        self.finish('ok!')

class SnapShotHandler(tornado.web.RequestHandler):

    def get(self):

        self.render('templates/index.html')
        
        self.set_header('Cache-Control',
        'no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0')
        self.set_header('Connection', 'close')
        self.set_header('Content-Type', 'multipart/x-mixed-replace;boundary=-boundarydonotcross')

        camera = open_onboard_camera()
        if camera.isOpened():
            img = camera.grab()
            img_bytes =  cv2.imencode('.jpg', img)[1].tobytes()
            self.write("--boundarydonotcross\n")
            self.write("Content-type: image/jpeg\r\n")
            self.write("Content-length: %s\r\n\r\n" % len(img_bytes))
            self.write(json_encode(str(img_bytes)))
            # self.flush()
        # self.finish()

def make_app():
    return tornado.web.Application([
        (r'/',  IndexHandler),
        (r"/video_feed", VideoHandler),
        (r'/motion', MotionHandler),
        # (r'/shot', SnapShotHandler),
        (r'/(?:image)/(.*)', tornado.web.StaticFileHandler, {'path': './image'}),
        (r'/(?:css)/(.*)', tornado.web.StaticFileHandler, {'path': './css'}),
        (r'/(?:js)/(.*)', tornado.web.StaticFileHandler, {'path': './js'})
    ], debug=True)

if __name__ == "__main__":
    app = make_app()
    app.listen(4488)
    tornado.ioloop.IOLoop.current().start()