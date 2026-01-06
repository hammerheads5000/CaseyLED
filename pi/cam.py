import cv2

cam = None
def init():
    global cam
    cam = cv2.VideoCapture(-1, cv2.CAP_V4L2)
    cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('M', 'J', 'P', 'G'))
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cam.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    cam.set(cv2.CAP_PROP_FOCUS, 20)
    cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
    cam.set(cv2.CAP_PROP_EXPOSURE, 10)

positions = [
    (1220, 600), (1120, 320),
    (1108, 596), (1010, 280),
    (955,  555), (885,  250),
    (750,  530), (740,  200),
    (525,  520), (550,  140)
]
positions.reverse()

def read_battery_vals():
    if cam is None:
        init()
    ret, frame = cam.read()
    out = []
    for x,y in positions:
        pix = frame[y,x]
        b = pix[0]
        g = pix[1]
        r = pix[2]
        if g > 245 and b > 200:
            out.append('g')
        elif r > 200:
            out.append('r')
        else:
            out.append('x')
        cv2.circle(frame, center=(x,y), radius=5, color=(255,0,0) if out[-1]=='r' else (0,255,0))
    cv2.imshow('Camera', frame)
    cv2.waitKey(1)
    return out

def close():
    cam.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    try:
        init()
        #while True:
        _, frame = cam.read()
        cv2.imshow('Cam', frame)
        cv2.waitKey(0)
    finally:
        close()