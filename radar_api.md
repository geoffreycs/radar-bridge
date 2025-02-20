## How to use the RADAR bridge API

### Setup

```bash
pip install -r radar.txt
```

The bridge requires a few external packages.

### Standalone usage

From terminal:
```bash
python radar.py # connects to 127.0.0.1
python radar.py server # connects to "server"
python radar.py 192.168.1.337 # connects to 192.168.1.337
```

### API Calls

```python
# Import library:
import radar

# Start client
radar.connect("server") # specify server address
radar.connect() # defaults to 127.0.0.1

# Check if connection is up
radar.isOpen() # returns true or false

# Find number of tracks
radar.numTracks() 

# Get an array of all tracks
radar.getAll()

# Get a specific track by array index
radar.getByNum(idx)

# Get a specific track by ID string
radar.getById("id")

# Filter tracks by minimum age (msecs), minimum RCS, category list,
# and minimum category certainty (percentage), and also exclude track
# with ID "id"
radar.filterTracks(age = age, rcs = rcs, id = "id", matchCat = ["cat1", "cat2"], minCert = min_certainty)

# Filter by minimum age only
radar.filterTracks(age = age)

# Filter by minimum RCS only
radar.filterTracks(rcs = rcs)

# Exclude specific ID only
radar.filterTracks(id = "id")

# Include only tracks in cat3 with a certainty of at least 50%
radar.filterTracks(matchCat = ["cat3"], minCert = 50.0)

# Include only tracks in cat3, cat5, and cat1
radar.filterTracks(matchCat = ["cat3", "cat5", "cat1"])

# Filter by age and RCS, but without ID exclusion
radar.filterTracks(age = age, rcs = rcs)

# Find a track based on lat-long-alt
radar.getByLLA([lat, long, alt], [tolerance_la, tolerance_lo, tolerance_z])

# Exclude a track by lat-long-alt
radar.excludeByLLA([lat, long, alt], [tolerance_la, tolerance_lo, tolerance_z])

# Disconnect from RADAR server
radar.kill()
```

### Notes

`filterTracks()` takes three arguments, all of which are optional. You can choose to filter by age, RCS, or ID, or any combination of the three. Age and RCS default to zero if left unspecified, meaning they won't filter out any tracks, while ID defaults to "NUL", which never occurs as a track ID.

`getByLLA()` and `excludeByLLA()` take two arguments, both lists in lat-long-alt format (`[lat, long, alt]`). The first is the absolute position you wish to match, and the second is the match tolerance, or how precisely you want to match for each coordinate number. `getByLLA()` will return the first track which fits the match criteria, so tune tolerances carefully.

### Data Format

#### Track Data

Individual RADAR tracks are given as a class:
```python
class Track:
    id = str # always three alphanumeric characters
    rcs = float # decimal out of 1
    start = int # UNIX time in msecs
    lla = [float, float, float] # lat, long, alt
    heading = float # heading in degrees
    isStationary = bool # whether or not object is stationary
    category = str # track category (bird, droneplane, dronerotor, airplane, helicopter, other)
    catProb = { # probability by possible category, given in percentage
        "other": float,
        "bird": float,
        "dronerotor": float,
        "droneplane": float,
        "helicopter": float,
        "airplane": float
    }
    idx = int # index of track in array
    current = bool # whether the track instance is current
    raw = dict # reference to original dictionary (see below)
```

Each `Track()` class object is generated from a dictionary created by parsing the JSON object received over WebSocket. The dictionary is formatted identically to the class:
```python
{
    "id": str, # always three alphanumeric characters
    "rcs": float, # decimal out of 1
    "start": int, # UNIX time in msecs
    "lla": [float, float, float] # lat, long, alt
    "heading": float, # heading in degrees
    "isStationary": bool, # whether or not object is stationary
    "category": str, # track category (bird, droneplane, dronerotor, airplane, helicopter, other)
    "catProb": { # probability by possible category, given in percentage
        "other": float,
        "bird": float,
        "dronerotor": float,
        "droneplane": float,
        "helicopter": float,
        "airplane": float
    }
}
```

Using `Track.raw` gives you access to this dictionary. Since dictionaries are faster than classes, this library uses the dictionary for all filtering operations, but returns the corresponding `Track()` object.

#### Track Methods

Instances of `Track()` also provide two methods, `atLLA()` and `checkFilter()`, which each return True or False depending on if the particular track meets the given criteria:

```python
# get first track object (instance of Track class)
a = radar.getAll()[0]

# check if this particular track is at location (within the given tolerance)
a.atLLA([lat, long, alt], [tolerance_la, tolerance_lo, tolerance_z])

# check if this particular track meets criteria (each parameter is optional)
a.checkFilter(age = age, rcs = rcs, matchCat = ["cat1", "cat2"], minCert = min_certainty)
```

#### Library Methods

Library functions which return multiple tracks (`getAll()`, `filterTracks()`, and `excludeByLLA()`) produce a list where each member is a track, sorted by greatest RCS to smallest.

Calls which return a list of tracks will return an empty list (length of zero) if there are no tracks or if all tracks are filtered by the call:
```python
[]
```

If `getByNum()`, `getById()`, or `getByLLA()` fail to find a match, they return a null `Track` created from the following dictionary:
```python
{"id": "NUL", "rcs": -1.0, "start": -1, "lla": [nan nan nan],
    "heading": nan, "isStationary": True, "category": "other",
    "catProb": {"other": -1.0, "bird": -1.0, "dronerotor": -1.0,
    "droneplane": -1.0, "helicopter": -1.0, "airplane": -1.0}}
```

#### Important (Read Entirely)

Each `Track()` object, such as those in the `list` returned by `getAll()`, is an *instance* of the `Track()` class. More specifically, it represents the RADAR track as received *in one given moment*. When the plugin receives new data over the network stream, it does *not* update each previous instance outside of marking them as no longer current (`Track.current` becomes `False`). That is done purely to allow you, the programmer, to have a means of checking if a `Track()` instance is obsolete.

For example, let's say on one loop iteration, a track with ID `91F` is extracted from the array returned by `radar.getAll()` and assigned to the global variable `a`. On the next loop iteration, unless `a` is explicitly overwritten with a new `Track()` object, `a` would still point to the track data *as it was* when first extracted in the previous loop iteration. In other words, even if RADAR track `91F` is updated in the new data burst, the instance stored in `a` would contain an old copy of `91F`.

This is because each time new data is received, the `list` containing `Track()` objects is cleared and then repopulated from empty with new instances of the `Track()` class. In Python, instance object variables are really references, or pointers, to what is essentially a `struct`. The track `list` is thus an array of pointers, so clearing that array means deleting *references* to `Track()` instance objects, not the objects themselves. The Python interpretor's garbage collector automatically frees objects which no longer have any references pointing to them (i.e. there is no variable which can be used to access them), but so long as `a` points to that old instance, it will continue to exist and *will not* be updated to match new instances of `91F` tracks.

Consider this code:

```python
i = 0

# function that gets called periodically
def myLoop():
    global a, i
    if i == 0:
        a = radar.getAll()[0] # assign track instance to global variable
    print(i, a.current, a.id, a.lla[2]) # Print values from "a"
    print(radar.getAll()[0].id, radar.getAll()[0].lla[2]) # Print values from current
    i = i + 1

runFunctionEvery500msec(myLoop)
```

The first loop iteration would print:
```
0 True 91F 2189.97412
91F 2189.97412
```

The second loop iteration would then print:
```
1 False 91F 2189.97412
91F 2192.32619
```

Notice that the values stored in `a` remain the same while values extracted directly from the data are updated.

### Example outputs

```python
# isOpen()
True

# numTracks()
2

# getById("88K").raw
{'id': '88K', 'rcs': 0.0026665297291702467, 'start': 1738949529000, 'lla': [39.01759340000001, -104.891701, 2189.97412]}

# getByNum(0).raw
{'id': '10H', 'rcs': 0.0010763157612444301, 'start': 1738949528000, 'lla': [39.01892090000001, -104.893204, 2179.44507]}

# getById("test").raw
{"id": "NUL", "rcs": -1.0, "start": -1, "lla": [nan, nan, nan],
    "heading": nan, "isStationary": True, "category": "other",
    "catProb": {"other": -1.0, "bird": -1.0, "dronerotor": -1.0,
    "droneplane": -1.0, "helicopter": -1.0, "airplane": -1.0}}

# filterTracks(str = "10H")
[{'id': '88K', 'rcs': 0.0026665297291702467, 'start': 1738949529000, 'lla': [39.01759340000001, -104.891701, 2189.97412]}]

# filterTracks(rcs = 0.002)
[{'id': '88K', 'rcs': 0.0026665297291702467, 'start': 1738949529000, 'lla': [39.01759340000001, -104.891701, 2189.97412]}]
```

### Logging, replay, and emulation

During normal operation, the server logs all RADAR poll results to a file called the replay log. The replay log can then be loaded by a different server script which uses the replay log to mimic the RADAR server later on. Timestamps are stored in the replay log as relative to server startup time, and upon replay, the emulator script adjusts all timestamps to appear as if they are occuring in realtime. In other words, from the perspective of the client, realtime RADAR data and replayed data should be indistinguishable.

### Internal Details

The server is a Node.JS script which provides a WebSocket service. Upon the client connecting, the server begins polling the SkyDome system. Using data returned by the RADAR, the server then sends a JSON string containing the message type (data or error), the array of tracks (or in the case of an error, the error string), the server's Unix time, and, when not in an error state, an object mapping each track ID to its corresponding index in the track array. The WebSocket is fixed over port 8080. No HTTP handshake occurs between the plugin and server, and after the initial WebSocket connection is started, data is automatically pushed to the plugin periodically by the server.

Both the server and client are, in theory, resilient to network drops, and in the case of a disconnect, the client automatically reconnects. The server pauses SkyDome polling when no client is connected, and only streams data to one client at a time, as there should never be more than one in use anyway. If multiple connections do get opened (due to network errors), data is only streamed over the most recent connection.

### Danger Zone

The following are internal variables and private calls used by the plugin and should never be modified unless you are me (although you may generally read them if you wish):
```python
# True if invoked as script, false if as module
radar.standalone

# Holds last server UNIX timestamp
radar.server_time

# Time used for age checks, defaults to local UNIX time but uses server_time if server is ahead
radar.master_time 

# Holds detections (dictionaries) array
radar.detections

# Holds tracks (class instance objects) array
radar.tracks

# Holds mapping of IDs to array indices
radar.catalog

# True if last data packet indicated a server error
radar.error_last

# True if connection is alive
radar.is_open

# Constant containing the null track
radar.NUL

# Runs on connection or server error
radar.on_error(ws, error)

# Runs on connection close
radar.on_close(ws, status_code, msg)

# Runs on connection open
radar.on_open(ws)

# Primary handler for packets in module mode
radar.handler(ws, msg)

# Handler for interactive mode
radar.interactive(ws, message)
```