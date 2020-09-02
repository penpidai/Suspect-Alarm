# -*- coding: utf-8 -*-

import requests
import cv2
import time
import datetime
import pytz
import os
import numpy as np
from queue import Queue
import _thread

BKT = pytz.timezone('Asia/Bangkok')
Year = Month = Day = Hr = Min = Sec = Mcs = DirY = DirM = DirD = Fna = ''


def get_datetime():
    global Year, Month, Day, Hr, Min, Sec, Mcs, DirY, DirM, DirD, Fna
    x = datetime.datetime.now(datetime.timezone.utc)
    x = x.astimezone(BKT)  # datetime.datetime(2007, 12, 6, 5, 9, 3, 79060, tzinfo=datetime.timezone.utc)
    Year = x.strftime("%Y")
    Month = x.strftime("%m")
    Day = x.strftime("%d")
    Hr = x.strftime("%H")
    Min = x.strftime("%M")
    Sec = x.strftime("%S")
    Mcs = x.strftime("%f")
    DirY = os.getcwd() + '\\' + Year
    DirM = DirY + '\\' + Month
    DirD = DirM + '\\' + Day
    Fna = Year + Month + Day + Hr + Min + Sec


def create_dir(path, name):
    if os.path.exists(path):
        if not os.path.isdir(path):
            os.system("attrib -r -h -s " + name)
            os.remove(path)
            os.mkdir(path)
    else:
        os.mkdir(path)


def chk_dir():
    create_dir(DirY, Year)
    create_dir(DirM, Month)
    create_dir(DirD, Day)


def line_notify(message):
    payload = {'message': message}
    return _line_notify(payload)


def notify_file(filename):
    file = {'imageFile': open(filename, 'rb')}
    payload = {'message': 'Suspected Person.'}
    return _line_notify(payload, file)


def notify_picture(url):
    payload = {'message': " ", 'imageThumbnail': url, 'imageFullsize': url}
    return _line_notify(payload)


def notify_sticker(sticker_id, sticker_package_id):
    payload = {'message': " ", 'stickerPackageId': sticker_package_id, 'stickerId': sticker_id}
    return _line_notify(payload)


def _line_notify(payload, file=None):
    url = 'https://notify-api.line.me/api/notify'
    token = 'iUTVLqS6GhjYcfU6jlSdceJL1VjVkoq7RmtqQD9aTJs'
    headers = {'Authorization': 'Bearer ' + token}
    return requests.post(url, headers=headers, data=payload, files=file)


class YOLOv3:
    def __init__(self, classesFile, modelConfiguration, modelWeights):
        # Initialize the parameters
        self.confThreshold = 0.4  #Confidence threshold
        self.nmsThreshold = 0.34   #Non-maximum suppression threshold
        self.inpWidth = 416       #Width of network's input image
        self.inpHeight = 416      #Height of network's input image
        self.inputQueue = Queue(maxsize=1)
        self.outputQueue = Queue(maxsize=1)
        self.outs = None

        # Load names of classes
        self.classes = None
        with open(classesFile, 'rt') as f:
            self.classes = f.read().rstrip('\n').split('\n')

        self.net = cv2.dnn.readNetFromDarknet(modelConfiguration, modelWeights)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        _thread.start_new_thread(self.process_frame, ())

    # Get the names of the output layers
    def getOutputsNames(self):
        # Get the names of all the layers in the network
        layersNames = self.net.getLayerNames()
        # Get the names of the output layers, i.e. the layers with unconnected outputs
        return [layersNames[i[0] - 1] for i in self.net.getUnconnectedOutLayers()]

    # Remove the bounding boxes with low confidence using non-maxima suppression
    def detect(self, frame, draw=True):
        detected = []
        if self.inputQueue.empty():
            self.inputQueue.put(frame)

        outs = self.outs
        if not self.outputQueue.empty():
            outs = self.outputQueue.get()
            self.outs = outs
        if outs is None:
            outs = self.outs
        if outs is None:
            return detected

        frameHeight = frame.shape[0]
        frameWidth = frame.shape[1]

        classIds = []
        confidences = []
        boxes = []
        # Scan through all the bounding boxes output from the network and keep only the
        # ones with high confidence scores. Assign the box's class label as the class with the highest score.
        classIds = []
        confidences = []
        boxes = []
        for out in outs:
            for detection in out:
                scores = detection[5:]
                classId = np.argmax(scores)
                confidence = scores[classId]
                if confidence > self.confThreshold:
                    center_x = int(detection[0] * frameWidth)
                    center_y = int(detection[1] * frameHeight)
                    width = int(detection[2] * frameWidth)
                    height = int(detection[3] * frameHeight)
                    left = int(center_x - width / 2)
                    top = int(center_y - height / 2)
                    classIds.append(classId)
                    confidences.append(float(confidence))
                    boxes.append([left, top, width, height])

        # Perform non maximum suppression to eliminate redundant overlapping boxes with
        # lower confidences.
        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.confThreshold, self.nmsThreshold)

        for i in indices:
            i = i[0]
            box = boxes[i]
            left = box[0]
            top = box[1]
            width = box[2]
            height = box[3]

            label = '%.2f' % confidences[i]
            percent = confidences[i]
            if self.classes:
                assert (classIds[i] < len(self.classes))
                label = '%s:%s' % (self.classes[classIds[i]], int(confidences[i] * 100))
            if draw:
                self.draw_label(frame, label, left, top, width, height, percent)
            detected.append((label, left, top, width, height))
        return detected


    def draw_label(self, frame, label, left, top, width, height, percent):
        labelSize, baseLine = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 1)
        top = max(top, labelSize[1])
        cv2.putText(frame, label + '%', (left + int(width/7), top - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 1)
        cv2.rectangle(frame, (left, top), (left + width, top + height), (0, 0, 255), 1)
        if percent >= 0.90:
            get_datetime()
            chk_dir()
            cv2.imwrite(DirD + '\\' + Fna + '.jpg', frame)
            notify_file(DirD + '\\' + Fna + '.jpg')

    def process_frame(self):
        while True:
            if not self.inputQueue.empty():
                frame = self.inputQueue.get()
                blob = cv2.dnn.blobFromImage(frame, 1 / 255, (self.inpWidth, self.inpHeight), [0, 0, 0], 1, crop=False)
                self.net.setInput(blob)
                detections = self.net.forward(self.getOutputsNames())
                self.outputQueue.put(detections)


# cap = cv2.VideoCapture('tong1.mp4')
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
yolo = YOLOv3('obj.names', 'yolov3-obj.cfg', 'yolov3-obj_2400.weights')
while True:
    _, frame = cap.read()
    yolo.detect(frame)
    cv2.imshow('frame', frame)
    # Stop if escape key is pressed
    k = cv2.waitKey(30) & 0xff
    if k == 27:  # wait for ESC key to exit
        break

# Release the VideoCapture object
cap.release()
cv2.destroyAllWindows()


