import threading
import uuid
import platform
import hashlib
from socketIO_client import SocketIO
from .models import *
from .channel import *
from .response import TelepatResponse
from .db import TelepatDB
from .transportnotification import *
from telepat import httpmanager


class TelepatError(Exception):
    pass


class Telepat(object):
    def __init__(self, remote_url, sockets_url):
        self.token = ""
        self._mServerContexts = {}
        self._subscriptions = {}
        self.socketIO = None

        self.remote_url = remote_url
        self.sockets_url = sockets_url

        # Callbacks
        self.on_add_context = None
        self.on_update_context = None

        self.db = TelepatDB()

    def _start_ws(self):
        def on_socket_welcome(*args):
            response_data = args[0]
            self.token = response_data['sessionId']
            print("Received sessionId: {0}".format(self.token))
            self.token_event.set()

        def on_socket_message(*args):
            patch_data = args[0]
            if isinstance(patch_data, bytes):
                return
            if not "data" in patch_data:
                return

            patches = patch_data["data"]

            for ndict in patches["new"]:
                notification = TelepatTransportNotification()
                notification.notification_type = NOTIFICATION_TYPE_ADDED
                notification.value = ndict["value"]
                notification.subscription = ndict["subscription"]
                notification.guid = ndict["guid"]

                context = self.context_with_identifier(ndict["subscription"])
                if context:
                    self.process_notification(notification)
                    continue

                channel = self.channel_with_subscription(ndict["subscription"])
                channel.process_notification(notification)


            for ndict in patches["updated"]:
                notification = TelepatTransportNotification()
                notification.notification_type = NOTIFICATION_TYPE_UPDATED
                notification.path = ndict["path"]
                notification.value = ndict["value"]

                context = self.context_with_identifier(ndict["subscription"])
                if context:
                    self.process_notification(notification)
                    continue
                
                channel = self.channel_with_subscription(ndict["subscription"])
                channel.process_notification(notification)

            for ndict in patches["deleted"]:
                notification = TelepatTransportNotification()
                notification.notification_type = NOTIFICATION_TYPE_DELETED
                notification.path = ndict["path"]
                notification.value = None

                context = self.context_with_identifier(ndict["subscription"])
                if context:
                    self.process_notification(notification)
                    continue
                
                channel = self.channel_with_subscription(ndict["subscription"])
                channel.process_notification(notification)

            print("Received ws message: {0}".format(args[0]))

        self.socketIO = SocketIO(self.sockets_url, 80)
        self.socketIO.on('message', on_socket_message)
        self.socketIO.on('welcome', on_socket_welcome)
        self.socketIO.wait()

    def process_notification(self, notification):
        if notification.notification_type == NOTIFICATION_TYPE_ADDED:
            context = TelepatContext(notification.value)
            self._mServerContexts[context.id] = context
            if self.on_add_context:
                self.on_add_context(context, notification)

        elif notification.notification_type == NOTIFICATION_TYPE_UPDATED:
            path_components = notification.path.split("/")
            object_id = path_components[1]
            property_name = path_components[2]
            updated_context = self._mServerContexts[object_id]
            setattr(updated_context, property_name, notification.value)
            print("Calling on_update_context: {0}".format(self.on_update_context))
            if self.on_update_context:
                self.on_update_context(updated_context, notification)

        elif notification.notification_type == NOTIFICATION_TYPE_DELETED:
            pass

    @property
    def api_key(self):
        return httpmanager.api_key

    @api_key.setter
    def api_key(self, value):
        httpmanager.api_key = hashlib.sha256(value.encode()).hexdigest()
        
    @property
    def app_id(self):
        return httpmanager.app_id
        
    @app_id.setter
    def app_id(self, value):
        httpmanager.app_id = value
        device_id_key = "device_id_{0}".format(self.app_id)
        if self.db.get_operations_data(device_id_key):
            self.device_id = self.db.get_operations_data(device_id_key)
        else:
            self.device_id = ""

    @property
    def remote_url(self):
        return httpmanager.remote_url

    @remote_url.setter
    def remote_url(self, value):
        httpmanager.remote_url = value[:-1] if value.endswith("/") else value

    @property
    def device_id(self):
        return httpmanager.device_id

    @device_id.setter
    def device_id(self, value):
        httpmanager.device_id = value

    def context_map(self):
        return self._mServerContexts

    def context_with_identifier(self, identifier):
        for ctx_id in self._mServerContexts:
            if self._mServerContexts[ctx_id].context_identifier() == identifier:
                return self._mServerContexts[ctx_id]
        return None

    def register_subscription(self, channel):
        self._subscriptions[channel.subscription_identifier()] = channel

    def unregister_subscription(self, channel):
        del self._subscriptions[channel.subscription_identifier()]

    def channel_with_subscription(self, subscription_id):
        return self._subscriptions[subscription_id]

    def subscribe(self, context, model_name, object_type):
        channel = TelepatChannel(self, model_name, context)
        channel.object_type = object_type
        subscribe_response = channel.subscribe()
        return (channel, subscribe_response)

    def remove_subscription(self, channel):
        response = channel.unsubscribe()
        return TelepatResponse(response)

    def register_device(self, update=False):
        if self.socketIO:
            self.socketIO.disconnect()
            self.socketIO = None
        self.token_event = threading.Event()
        self.ws_thread = threading.Thread(target=self._start_ws)
        self.ws_thread.start()
        self.token_event.wait(15)
        if not self.token:
            if hasattr(self, "socketIO"):
                self.socketIO.disconnect()
            raise TelepatError('Websocket connection failed')
        params = {}
        info = {"os": platform.system(),
                "version": platform.release()
        }
        if not update: info["udid"] = str(uuid.uuid4())
        params["info"] = info
        params["volatile"] = {
            "type": "sockets",
            "token": self.token,
            "active": 1
        }
        response = httpmanager.post("/device/register", params, {})
        if response.status_code == 200:
            response_json = response.json()
            if "identifier" in response_json["content"]:
                device_id = response_json["content"]["identifier"]
                self.device_id = device_id
                self.db.set_operations_data("device_id_{0}".format(self.app_id), device_id)
        return response

    def login_admin(self, username, password):
        params = {
            "email": username,
            "password": password
        }
        response = httpmanager.post("/admin/login", params, {})
        if response.status_code == 200:
            httpmanager.bearer = response.json()["content"]["token"]
        return response

    def get_apps(self):
        response = httpmanager.get("/admin/apps", {}, {})
        return TelepatResponse(response)

    def get_schema(self):
        response = httpmanager.get("/admin/schema/all", {}, {})
        return TelepatResponse(response)

    def get_all(self):
        response = httpmanager.get("/admin/contexts", {}, {})
        contexts_response = TelepatResponse(response)
        for context in contexts_response.getObjectOfType(TelepatContext):
            self._mServerContexts[context.id] = context
        return contexts_response

    def update_context(self, updated_context):
        context = self.context_map()[updated_context.id]
        return TelepatResponse(httpmanager.post("/admin/context/update", context.patch_against(updated_context), {}))
        
    def disconnect(self):
        if self.socketIO:
            self.socketIO.disconnect()
        self.db.close()
 
