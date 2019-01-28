
import asyncio
import websockets
import json

def make_prop(k, cb):
    f = '_'+k
    def get(o):
        return getattr(o, f)
    def set(o, v):
        setattr(o, f, v)
        cb(o, k)
    return property(get, set)

def replace_by_prop(o, k, cb):
    setattr(o, '_'+k, getattr(o, k))
    setattr(o, k, make_prop(k, cb))

def model(cls):
    novue = cls._novue if cls._novue else []
    o = cls
    for k in filter(lambda k: k[0] != '_' and k not in novue, dir(o)):
        if not callable(getattr(o, k)):
            replace_by_prop(o, k, _up)
    return cls

def _up(self, k):
    asyncio.ensure_future(broadcast_update(k, getattr(self, k)))


all = []
async def broadcast_update(k, v):
    a = all.copy()
    all[:] = []
    for ws in a:
        try:
            await ws.send("UPDATE "+str(k)+" "+json.dumps(v))
            all.append(ws)
        except:
            pass

def handleClient(o):
    async def handleClient(websocket, path):
        if path == '/init':
            state = {}
            methods = []
            for k in filter(lambda k: k[0] != '_', o.__dir__()):
                if callable(getattr(o, k)):
                    methods.append(k)
                else:
                    state[k] = getattr(o, k)
            to_send = {
                'state': state,
                'methods': methods
            }
            await websocket.send(json.dumps(to_send))
        else:
            all.append(websocket)
            while True:
                comm = await websocket.recv()
                if comm == 'CALL':
                    meth = await websocket.recv()
                    print('METH', meth)
                    data = await websocket.recv()
                    print('DATA', data)
                    res = await getattr(o, meth)(*json.loads(data))
                elif comm == 'UPDATE':
                    k = await websocket.recv()
                    v = await websocket.recv()
                    try:
                        setattr(o, k, json.loads(v))
                    except:
                        print("Not a JSON value for key", k, "->", v)
    return handleClient

def start(o, port=4259, host='localhost'):
    #inreader = asyncio.StreamReader(sys.stdin)
    ws_server = websockets.serve(handleClient(o), host, port)
    asyncio.ensure_future(ws_server)
    asyncio.get_event_loop().run_forever()