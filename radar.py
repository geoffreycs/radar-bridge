import websocket
import json
from typing import List, Dict, TypedDict
import time
import numpy as np
import threading
import math

Probs = TypedDict('Probs', {
    "other": float,
    "bird": float,
    "dronerotor": float,
    "droneplane": float,
    "helicopter": float,
    "airplane": float
})

Detection = TypedDict('Track', {
    "id": str,
    "rcs": float,
    "start": int,
    "heading": float,
    "isStationary": bool,
    "lla": List[float],
    "category": str,
    "catProb": Probs
})

class Track:
    def __init__(self, detect: Detection):
        self.id = detect["id"]
        self.rcs = detect["rcs"]
        self.start = detect["start"]
        self.lla = detect["lla"]
        self.heading = detect["heading"]
        self.isStationary = detect["isStationary"]
        self.category = detect["category"]
        self.catProb = detect["catProb"]
        self.raw = detect
        self.idx = catalog[detect["id"]]
        self.current = True

    def atLLA(self, lla: List[float], tol: List[float]):
        for idx, val in enumerate(self.lla):
            if abs(lla[idx] - val) > tol[idx]:
                return False
        return True
    
    def checkFilter(self, age: int = 0, rcs: float = 0.0, matchCat: List[str] = ["other", "bird", "dronerotor", "droneplane", "helicopter", "airplane"], minCert: float = 0.0):
        d = self.raw
        return False if ((master_time - d["start"]) < age or d["rcs"] < rcs or not (d["category"] in matchCat) or d["catProb"][d["category"]] < minCert) else True

standalone : bool = False
server_time: int = 0
master_time: int = 0
detections : List[Detection] = list()
tracks : List[Track] = list()
catalog : Dict[str, int] = dict()
error_last : bool = False
is_open : bool = False
NUL = Track({"id": "NUL", "rcs": -1.0, "start": -1, "lla": [np.nan, np.nan, np.nan],
             "heading": math.nan, "isStationary": True, "category": "other",
             "catProb": {"other": -1.0, "bird": -1.0, "dronerotor": -1.0,
                            "droneplane": -1.0, "helicopter": -1.0, "airplane": -1.0}})

def handler(ws: websocket.WebSocketApp, message: str):
    global server_time, detections, error_last, master_time, catalog, tracks
    parsed: List[float|List[dict]|str|int|Dict[str, int]] = json.loads(message)
    server_time = parsed[2]
    if server_time > master_time:
        master_time = server_time
    if parsed[1] == 0:
        error_last = False
        detections = parsed[0]
        catalog = parsed[3]
        for inst in tracks:
            inst.current = False
        tracks.clear()
        for detection in detections:
            tracks.append(Track(detection))
    else:
        error_last = True
        print("Error: " + str(parsed[0]))

def interactive(ws: websocket.WebSocketApp, message: str):
    global server_time
    parsed: List[float|List[dict]|str|int] = json.loads(message)
    server_time = parsed[2]
    print(parsed[0])
    print(parsed[3])
    print("Time diff: " + str(int(time.time() * 1000) - server_time) + "\n")

def numTracks():
    global detections
    return len(detections)

def getAll():
    # global detections
    # return detections
    global tracks
    return tracks

def getByNum(idx: int):
    global detections, tracks
    if (idx + 1) > len(detections):
        return tracks[idx]
    return NUL

def getById(id: str):
    global tracks, catalog
    if id in catalog:
        return tracks[int(catalog[id])]
    # if len(detections) > 0:
    #     for det in detections:
    #         if det["id"] == id:
    #             return det
    return NUL

def filterTracks(age: int = 0, rcs: float = 0.0, id: str = "NUL", matchCat: List[str] = ["other", "bird", "dronerotor", "droneplane", "helicopter", "airplane"], minCert: float = 0.0):
    global detections, tracks
    filtered: List[Track] = []
    if len(detections) > 0:
        for idx, det in enumerate(detections):
            if (master_time - det["start"]) >= age and det["rcs"] >= rcs and det["id"] != id and det["category"] in matchCat and det["catProb"][det["category"]] >= minCert:
                filtered.append(tracks[idx])
    return filtered

def getByLLA(lla: List[float], tol: List[float]):
    global detections, tracks
    if len(detections) > 0:
        for idx, det in enumerate(detections):
            coords = np.array(det["lla"])
            target = np.array(lla)
            diff = np.abs(coords - target)
            if (diff <= np.array(tol)).all():
                return tracks[idx]
    return NUL

def excludeByLLA(lla: List[float], tol: List[float]):
    global detections, tracks
    filtered: List[Track] = []
    if len(detections) > 0:
        for idx, det in enumerate(detections):
            coords = np.array(det["lla"])
            target = np.array(lla)
            diff = np.abs(coords - target)
            if (diff > np.array(tol)).all():
                filtered.append(tracks[idx])
    return filtered

def isOpen():
    return is_open

def on_error(ws: websocket.WebSocketApp, error):
    print(error)
    ws.close()

def on_close(ws: websocket.WebSocketApp, close_status_code: int, close_msg: str):
    global is_open
    is_open = False
    print("WebSocket connection closed: " + str(close_status_code) + " " + str(close_msg))

def on_open(ws: websocket.WebSocketApp):
    global is_open
    is_open = True
    print("WebSocket connection opened")

def connect(server: str = "127.0.0.1"):
    global standalone, is_open, ws, runner
    if is_open:
        print("Aborting connect() because socket is already open")
        return
    addr = "ws://" + server + ":8080"
    websocket.enableTrace(False)
    if standalone:
        msg_cb: function = interactive
    else:
        msg_cb: function = handler
    ws = websocket.WebSocketApp(addr,
                              on_open=on_open,
                              on_message=msg_cb,
                              on_error=on_error,
                              on_close=on_close)

    def proxy():
        ws.run_forever(reconnect=1)

    runner = threading.Thread(target=proxy)
    runner.start()
    
def kill():
    global is_open
    is_open = False
    ws.close()
    if runner.is_alive():
        runner.join()

if __name__ == "__main__":
    import sys
    standalone = True
    if len(sys.argv) > 1:
        connect(str(sys.argv[1])) 
    else:
        connect()