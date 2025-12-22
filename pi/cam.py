import cv2

cam = cv2.VideoCapture(-1, cv2.CAP_V4L)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)

positions = [
    (1218, 545), (1076, 226),
    (1064, 572), (948,  205),
    (872,  588), (747,  183),
    (622,  620), (524,  126),
    (270,  646), (298,  108)
]

while True:
    ret, frame = cam.read()
    cv2.imshow('Camera', frame)
    out = ''
    for x,y in positions:
        pix = frame[y,x]
        b = pix[0]
        g = pix[1]
        r = pix[2]
        if g > 245:
            out += 'g'
        elif r > 200:
            out += 'r'
        else:
            out += 'x'
        out += '\t'
    print(out)
    if cv2.waitKey(1) == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()
