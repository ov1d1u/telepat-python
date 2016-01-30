NOTIFICATION_TYPE_ADDED = 1 
NOTIFICATION_TYPE_UPDATED = 2
NOTIFICATION_TYPE_DELETED = 3

class TelepatTransportNotification:
	notification_type = 0
	value = ""
	path = ""
	subscription = ""
	guid = ""

	def __init__(self, notification_type=None, path=None, value=None, subscription=None, guid=None):
		self.notification_type = notification_type
		self.value = value
		self.path = path