import shelve
from os.path import expanduser

home = expanduser("~")


class TelepatDB:
    db_name = "TELEPAT_OPERATIONS"
    db_op_prefix = "TP_OPERATIONS_"
    db_objects_prefix = "TP_OBJECTS_"

    def __init__(self):
        self.db = shelve.open("{0}/{1}".format(home, ".telepat.db"))

    def prefixForChannel(self, channel_id):
        return "{0}{1}".format(self.db_objects_prefix, channel_id)

    def keyForObject(self, object_id, channel_id):
        return "{0}:{1}".format(self.prefixForChannel(channel_id), object_id)

    def objectExists(self, object_id, channel_id):
        return self.keyForObject(object_id, channel_id) in self.db

    def get_object(self, object_id, channel_id):
        object_key = self.keyForObject(object_id, channel_id)
        return self.db[object_key] if object_id in self.db else None

    def objects_in_channel(self, channel_id):
        return self.db[channel_id] if channel_id in self.db else []

    def set_operations_data(self, key, obj):
        self.db["{0}{1}".format(self.db_op_prefix, key)] = obj
        self.db.sync()

    def get_operations_data(self, key):
        op_key = "{0}{1}".format(self.db_op_prefix, key)
        return self.db[op_key] if op_key in self.db else None

    def persist_object(self, obj, channel_id):
        self.db[self.keyForObject(obj.object_id, channel_id)] = obj
        self.db.sync()

    def persist_objects(self, objects, channel_id):
        self.db[channel_id] = objects
        self.db.sync()

    def delete_objects(self, channel_id):
        del self.db[channel_id]

    def empty(self):
        self.db.clear()
        
    def close(self):
        self.db.close()