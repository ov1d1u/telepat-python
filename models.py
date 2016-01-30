from jsonobject import *


class TelepatBaseObject(JsonObject):
    object_id = StringProperty()
    context = None
    model = ""

    def patch_against(self, updated_obj):
        if not isinstance(updated_obj, TelepatBaseObject):
            raise TelepatError("The received object is not the same as the current one")
        patch = {
            "model": self.model,
            "id": self.object_id,
            "context": self.context.id
        }
        patches = []
        # Deleted keys
        deletions = list(set(self.keys()) - set(updated_obj.keys()))
        for del_prop in deletions:
            del_patch = {
                "op": "delete",
                "path": "{0}/{1}/{2}".format(self.model, self.object_id, del_prop)
            }
            patches.append(deletions)

        for key in list(updated_obj.keys()):
            if not updated_obj[key] == self[key]:
                replace_patch = {
                    "op": "replace",
                    "path": "{0}/{1}/{2}".format(self.model, self.object_id, key),
                    "value": updated_obj[key]
                }
                patches.append(replace_patch)

        patch["patches"] = patches
        return patch


class TelepatAppSchema(TelepatBaseObject):
    pass


class TelepatContext(TelepatBaseObject):
    name = StringProperty()
    id = StringProperty()
    application_id = StringProperty()
    state = IntegerProperty()
    meta = DictProperty()

    def patch_against(self, updated_obj):
        if not isinstance(updated_obj, TelepatContext):
            raise TelepatError("The received object is not the same as the current one")
        patch = {
            "id": self.id
        }
        patches = []
        # Deleted keys
        deletions = list(set(self.keys()) - set(updated_obj.keys()))
        for del_prop in deletions:
            del_patch = {
                "op": "delete",
                "path": "context/{0}/{1}".format(self.id, del_prop)
            }
            patches.append(deletions)

        for key in list(updated_obj.keys()):
            if not updated_obj[key] == self[key]:
                replace_patch = {
                    "op": "replace",
                    "path": "context/{0}/{1}".format(self.id, key),
                    "value": updated_obj[key]
                }
                patches.append(replace_patch)

        patch["patches"] = patches
        return patch

    @property
    def object_id(self):
        return self.id

    @object_id.setter
    def object_id(self, value):
        self.id = value

    def context_identifier(self):
        return "blg:{0}:context".format(self.application_id)