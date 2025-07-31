# Usage:
#   import pets
#   pinto = pets.Pet("Pinto", 5, 20, 1, ":pintocool:")
#   pinto.name == "Pinto"
#   >>> True
#   pinto.index == 5
#   >>> True
#   pinto.metadata.emote_name == ":pintocool:"
#   >>> True

class MetaData:
    def __init__(self, emote_id, emote_name):
        self.emote_id = emote_id
        self.emote_name = emote_name

class Pet:
    def __init__(self, name, max_index, index, emote_id, emote_name):
        self.name = name
        self.index = index
        self.max_index = max_index
        self.metadata = MetaData(emote_id, emote_name)
