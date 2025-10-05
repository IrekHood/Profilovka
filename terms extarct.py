import json

info = json.load(open("maps/World_h.json"))

keys = [item for item in info.keys()]
names = [{item: list(info[item].keys())} for item in [key for key in keys]]
print(names)
json.dump(names, open("maps/terms.json", "w"))
