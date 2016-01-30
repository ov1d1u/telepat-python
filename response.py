class TelepatResponse:
    def __init__(self, response):
        self.status = response.status_code
        self.json_data = response.json()
        self.content = self.json_data["content"] if "content" in self.json_data else None
        self.message = self.json_data["message"] if "message" in self.json_data else "" 

    def getObjectOfType(self, class_type):
        if type(self.content) == list:
            objects = []
            for json_dict in self.content:
                objects.append(class_type(json_dict))
            return objects
        else:
            return class_type(self.content)