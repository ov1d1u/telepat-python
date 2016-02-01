import uuid
import json
from .models import TelepatContext, TelepatUser, TelepatBaseObject
from telepat import httpmanager
from .response import TelepatResponse
from .transportnotification import *


class TelepatChannel:
    context = None
    user = None
    model_name = ""
    object_type = None
    parent_model_name = ""
    parent_id = ""
    object_id = ""

    on_add_object = None
    on_update_object = None
    on_delete_object = None

    def __init__(self, telepat_instance, model_name, context):
        self.telepat_instance = telepat_instance
        self.model_name = model_name
        self.context = context

    def subscribe(self):
        response = httpmanager.post("/object/subscribe", self.params_for_subscription(), {})
        subscribe_response = TelepatResponse(response)
        if subscribe_response.status == 200 and isinstance(subscribe_response.content, list):
            for obj_dict in subscribe_response.content:
                self.process_notification(
                    TelepatTransportNotification(
                        NOTIFICATION_TYPE_ADDED,
                        "/",
                        obj_dict
                    )
                )
            self.telepat_instance.register_subscription(self)
        return subscribe_response

    def unsubscribe(self):
        response = httpmanager.post("/object/unsubscribe", self.params_for_subscription(), {})
        unsubscribe_response = TelepatResponse(response)
        if unsubscribe_response.status == 200:
            self.telepat_instance.unregister_subscription(self)
        return unsubscribe_response


    def params_for_subscription(self):
        params = {
            "channel": {
                "model": self.model_name
            }
        }
        if self.context:
            params["channel"]["context"] = self.context.id
        if self.user:
            params["channel"]["user"] = self.user.id
        if self.parent_id and self.parent_model_name:
            params["channel"]["parent"] = {
                "id": self.parent_id,
                "model": self.parent_model_name
            }

        return params

    def patch(self, obj):
        old_object = self.object_with_id(obj.id)
        assert old_object
        patches = old_object.patch_against(obj)
        patch = {
            "model": self.model_name,
            "context": self.context.id,
            "id": obj.id,
            "patches": patches
        }
        obj.uuid = str(uuid.uuid4())
        response = httpmanager.post("/object/update", patch, {})
        patch_response = TelepatResponse(response)
        return (obj.uuid, patch_response)

    def object_with_id(self, object_id):
        return self.telepat_instance.db.get_object(object_id, self.subscription_identifier())

    def persist_object(self, obj):
        self.telepat_instance.db.persist_object(obj, self.subscription_identifier())

    def process_notification(self, notification):
        if notification.notification_type == NOTIFICATION_TYPE_ADDED:
            obj = self.object_type(notification.value)
            if self.on_add_object:
                self.on_add_object(obj, notification)

            self.persist_object(obj)

        elif notification.notification_type == NOTIFICATION_TYPE_UPDATED:
            path_components = notification.path.split("/")
            model_name = path_components[0]
            if not model_name == self.model_name: return
            object_id = path_components[1]
            property_name = path_components[2]
            if self.telepat_instance.db.objectExists(object_id, self.subscription_identifier()):
                updated_object = self.telepat_instance.db.get_object(object_id, self.subscription_identifier())
                setattr(updated_object, property_name, notification.value)
                updated_object.channel = self
                if self.on_update_object:
                    self.on_update_object(updated_context, notification)

                self.persist_object(updated_object)

        elif notification.notification_type == NOTIFICATION_TYPE_DELETED:
            pass

    def channel_mask(self):
        mask = 0
        if self.context:
            mask += 1
        if self.user:
            mask += 2
        if self.model_name:
            mask += 4
        if self.parent_id and self.parent_model_name:
            mask += 8
        if self.object_id:
            mask += 16
        return mask

    def subscription_identifier(self):
        subid = "blg"
        channel_mask = self.channel_mask()
        if channel_mask == 4:
            subid = "{0}:{1}:{2}".format(
                subid,
                self.telepat_instance.app_id,
                self.model_name
            )
        elif channel_mask == 5:
            subid = "{0}:{1}:context:{2}:{3}".format(
                subid,
                self.telepat_instance.app_id,
                self.context.id,
                self.model_name
            )
        elif channel_mask == 7:
            subid = "{0}:{1}:context:{2}:users:{3}:{4}".format(
                subid, 
                self.telepat_instance.app_id, 
                self.context.id, 
                self.user.id, 
                self.model_name
            )
        elif channel_mask == 12:
            subid = "{0}:{1}:{2}:{3}:{4}".format(
                subid,
                self.telepat_instance.app_id, 
                self.parent_model_name, 
                self.parent_id, 
                self.model_name
            )
        elif channel_mask == 14:
            subid = "{0}:{1}:users:{2}:{3}:{4}:{5}".format(
                subid, 
                self.telepat_instance.app_id, 
                self.user.id, 
                self.parent_model_name, 
                self.parent_id, 
                self.model_name
            )
        elif channel_mask == 20:
            subid = "{0}:{1}:{2}:{3}".format(
                subid,
                self.telepat_instance.app_id,
                self.model_name,
                self.object_id
            )
        return subid