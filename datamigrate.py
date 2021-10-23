import os, json

default_linked = {"voice": {},"stage": {},"category": {},"all": {"roles":[], "except":[]},"permanent":{}}

def vamig(filename):
    with open(f'old/data/{filename}', 'r') as f:
        odata = json.load(f)

    data = {}
    data['voice'] = {}
    data['stage'] = {}
    data['category'] = {}
    data['all'] = {}
    data['all']['roles'] = []
    data['all']['except'] = []
    data['permanent'] = {}

    if odata:

        v = {}
        for i in odata:
            if i == 'all':
                data['all']['roles'].append(odata[i])
            else:
                v[i] = []
                v[i].append(odata[i])
                
        data['voice'] = v

    with open(f'Linked/{filename}', 'w') as f:
        json.dump(data, f, indent=4)

def cmig(filename):
    with open(f'old/category/{filename}', 'r') as f:
        odata = json.load(f)
    
    filename = filename[3:]

    try:
        with open(f'Linked/{filename}', 'r') as f:
            data = json.load(f)

        if odata:
            c = {}
            for i in odata:
                c[i] = []
                c[i].append(odata[i])

            data['category'] = c

            with open(f'Linked/{filename}', 'w') as f:
                json.dump(data, f, indent=4)
    except:
        pass

def smig(filename):
    with open(f'old/stage/{filename}', 'r') as f:
        odata = json.load(f)
    
    filename = filename[5:]

    try:
        with open(f'Linked/{filename}', 'r') as f:
            data = json.load(f)

        if odata:
            s = {}
            for i in odata:
                s[i] = []
                s[i].append(odata[i])

            data['stage'] = s

            with open(f'Linked/{filename}', 'w') as f:
                json.dump(data, f, indent=4)
    except:
        pass

def genmig():
    with open(f'old/generator.json', 'r') as f:
        odata = json.load(f)

    data = {}

    for i in odata:
        data[i] = {}
        data[i]['cat'] = str(odata[i]['category'])
        data[i]['gen_id'] = str(odata[i]['lobby_id'])
        data[i]['open'] = []

    with open(f'Data/generator.json', 'w') as f:
        json.dump(data, f, indent=4)

def logttsmig():
    with open(f'old/logging.json', 'r') as f:
        odata = json.load(f)

    with open(f'Data/guild_data.json', 'r') as f:
        data = json.load(f)

    for i in odata:
        data[i] = {}
        data[i]['logging'] = odata[i]
        data[i]['tts'] = {'enabled': False, 'role': None}

    with open(f'old/tts.json', 'r') as f:
        odata = json.load(f)

    for i in odata:
        try:
            data[i]
        except:
            data[i] = {}
        try:
            data[i]['logging']
        except:
            data[i]['logging'] = None

        data[i]['tts'] = {'enabled': True, 'role': odata[i]['role']}

    with open(f'Data/guild_data.json', 'w') as f:
        json.dump(data, f, indent=4)
        

for filename in os.listdir('old/data'):
    vamig(filename)

for filename in os.listdir('old/category'):
    cmig(filename)

for filename in os.listdir('old/stage'):
    smig(filename)

genmig()

logttsmig()