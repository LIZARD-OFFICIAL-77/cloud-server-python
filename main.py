# WebSocket

from websockets.asyncio.server import broadcast
from websockets import serve
import asyncio
import signal

# Cloud Variable Server

import pathlib
import json
import time

class Handshake:
    def __init__(self,user,ip,project_id):
        self.result = {
            f"{user}/{ip}/{project_id}":{
                "project_id":project_id,
                "username":user,
                "ip":ip,
            }
        }
        
    def log(self):
        hs = list(self.result.values())[0]
        

class WebSocketRequestsScratch:
    class Request:
        def __init__(
            self,
            
            func,
            name,
        ) -> None:
            self.name = name
            self.func = func
        def __call__(self,*args,**kwargs):
            return self.func(*args,**kwargs)
         
    class Response:
        def __init__(
                self,
                     
                success: bool = True,
                status: int = 1000,
                response: dict = None,
        ):
            self.__dict__.update(success=success,status=status,response=response) 
    
    def __init__(
            self,
            
            server="https://github.com/LIZARD-OFFICIAL-77/cloud-server-python",
            hostname="127.0.0.1",
            namekey="method",
            port=3000,
        ) -> None:
        "Custom websocket class for a scratch cloud server"
        
        self.hostname = hostname
        self.port = port
        self.requests = {}
        self.namekey = namekey
        self.connections = set()
        
    async def run(self):
        loop = asyncio.get_running_loop()
        stop = loop.create_future()
        loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
        
        async with serve(self._handler, self.hostname, self.port):
            await stop
    
    async def _handler(self,websocket):
        self.connections.add(websocket)
        async for data in websocket:
            response = self.handle(json.loads(data),websocket.remote_address[0])
            
            if response:
                if response.success:
                    await websocket.send(json.dumps(response.response))
                else:
                    await websocket.close(response.status)
    
    def request(self,function=None,name=None):
        def inner(function):
            func_name = function.__name__ if name is None else name
            
            self.requests[
                func_name
            ] = self.Request(
                function,
                name
            )
            
        if function is None:
            # => the decorator provides arguments
            return inner
        else:
            # => the decorator doesn't provide arguments
            inner(function)
    
    def handle(self,data: dict,ip=None):
        req = data
        
        req_name = req["method"]
        req.pop("method")
        req["ip"] = ip
        
        self.requests[req_name](**req)
        
    def broadcast(self,message):
        broadcast(self.connections,message)

class JsonDB:
    def __init__(self,filename) -> None:
        self._fn = filename
        self._cpy: dict = {}
        if pathlib.Path(self._fn).is_file():
            self._load()
        else:
            self._dump()
    def _dump(self):
        with open(self._fn,"w") as f:
            json.dump(self._cpy,f,indent=4)
    def _load(self):
        with open(self._fn) as f:
            self._cpy = json.load(f)
    def update(self,change):
        self._cpy.update(change)
        self._dump()
    def __str__(self) -> str:
        return str(self._cpy)
    def __delitem__(self,item):
        del self._cpy[item]
        self._dump()
    def __getitem__(self,item):
        return self._cpy[item]
    def __setitem__(self,item,value):
        self._cpy[item] = value
        self._dump()
    def items(self):
        return self._cpy.items()
    def keys(self):
        return self._cpy.keys()
    def values(self):
        return self._cpy.values()
    def get(self,*args,**kwargs):
        return self._cpy.get(args,kwargs)

class CloudServer:
    class Variable:
        def __init__(self,name,value):
            self.name = self.varname(name)
            self.value = str(value)
        def set(self,value):
            self.value = str(value)
        def rename(self,name):
            self.name = self.varname(name)
        @staticmethod
        def varname(name):
            return f"☁ {name}"
    def __init__(
        self,
        banned_usernames: list = None,
        project_id_whitelist: list = None,
        project_id_blacklist: list = None,
        banned_ip_list: list = None,
        size_limit_int: int = 256,
        db: JsonDB = None,
    ):
        """Turbowarp's cloud server implemented in python.

        Args:
            banned_usernames (list, optional): Banned usernames. Defaults to None.
            project_id_whitelist (list, optional): List of whitelisted project ids. Defaults to None.
            project_id_blacklist (list, optional): List of blacklisted project ids. Defaults to None.
            banned_ip_list (list, optional): List of banned IP addresses. Defaults to None.
            size_limit_int (int, optional): Variable length limit. Defaults to 256.
            db (JsonDB, optional): A dict-like class that functions like a database. Defaults to None.

        Raises:
            RuntimeError: If both whitelist and blacklist are specified
        """
        self.handshakes = []
        self.size_limit = size_limit_int
        self.banned_usernames=banned_usernames or ["*"]
        self.banned_ip_list=banned_ip_list or ["*"]
        self.db = False if not db else db
        
        self.variables: dict[str,Variable] = {}
        
        if not any([project_id_blacklist,project_id_whitelist]):
            self.project_id_allow = "*"
        elif (project_id_blacklist and project_id_whitelist):
            raise RuntimeError("Cannot use whitelist and black list.")
        elif project_id_blacklist:
            self.project_id_allow = "blacklist"
            self.project_id_blacklist = project_id_blacklist
        elif project_id_whitelist:
            self.project_id_allow = "whitelist"
            self.project_id_whitelist = project_id_whitelist
        
        self.websocket = WebSocketRequestsScratch()

        @self.websocket.request
        def handshake(project_id,user,ip):
            
            # Ruleset for a handshake
            if all([
                not ip in self.banned_ip_list,
                not user in self.banned_usernames,
                (
                    (self.project_id_allow == "*") or 
                    
                    (self.project_id_allow == "blacklist" and 
                        (project_id not in self.project_id_blacklist)
                    ) or 
                    
                    (self.project_id_allow == "whitelist" and 
                        (project_id in self.project_id_whitelist)
                    )
                )
            ]):
                HANDSHAKE = Handshake(project_id=project_id,user=user,ip=ip)
                if self.db:
                    self.db["handshakes"] = self.db["handshakes"] + HANDSHAKE
                self.handshakes.append(HANDSHAKE)
                return self.websocket.Response()
            else:
                return self.websocket.Response(False,4003)
        
        @self.websocket.request
        def create(project_id,user,name,value,ip):
            if not Handshake(project_id=project_id,user=user,ip=ip) in self.handshakes:return
            name = name.replace("☁ ","")
            self.variables[self.Variable.varname(name)] = self.Variable(name,value)
        
        @self.websocket.request
        def delete(project_id,user,name,ip):
            if not Handshake(project_id=project_id,user=user,ip=ip) in self.handshakes:return            
            name = name.replace("☁ ","")
            if not self.Variable.varname(name) in self.variables.keys():
                return self.websocket.Response(False,4003)
            self.variables.pop(name)
        
        @self.websocket.request
        def rename(project_id,user,name,new_name,ip):
            if not Handshake(project_id=project_id,user=user,ip=ip) in self.handshakes:return
            name = name.replace("☁ ","")
            self.variables[name].rename(new_name)
            
        @self.websocket.request
        def set(project_id,user,name,value,ip,server=None):
            if server:
                return
            if not Handshake(project_id=project_id,user=user,ip=ip) in self.handshakes:return
            name = name.replace("☁ ","")
            if self.Variable.varname(name) in self.variables:  
                self.variables[self.Variable.varname(name)].set(value)
            else:
                self.variables[self.Variable.varname(name)] = self.Variable(name,value)
                
            self.websocket.broadcast(json.dumps({
                "method":"set",
                "name": self.variables[self.Variable.varname(name)].name,
                "value": self.variables[self.Variable.varname(name)].value
            }))
            
server = CloudServer()
asyncio.run(server.websocket.run())