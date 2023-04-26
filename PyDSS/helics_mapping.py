import enum

class PROPERTY(enum.Enum):
    Enabled = {
        "type": "bool",
        "vector": True,
        "prefix": "switch",
        "suffix": "status",
        "unit": "",
        "tags" : [
            "phases",
            "federate"
            ],
    }
    TotalPower =  {
        "type": "complex",
        "vector": False,
        "prefix": "pcc",
        "suffix": "pq",
        "unit": "MVA",
        "tags" : [
            "phases",
            "federate"
            ],
        }
    Voltages = {
        "type": "complex",
        "vector": True,
        "prefix": "ConnectivityNode",
        "suffix": "PNV",
        "unit": "V",
        "tags" : [
            "phases",
            "federate"
            ],
        }
    Currents =  {
        "type": "complex",
        "vector": True,
        "prefix": "ACLineSegment",
        "suffix": "A",
        "unit": "A",
        "tags" : [
            "phases",
            "federate"
            ],
        }
    tap = {
        "type": "double",
        "vector": False,
        "prefix": "RegulatingControl",
        "suffix": "pos",
        "unit": "pu",
        "tags" : [
            "phases",
            "federate"
        ],
    }
    TapNumber = {
        "mapped_object": "Regulator",
        "type": "integer",
        "vector": False,
        "prefix": "RegulatingControl",
        "suffix": "pos",
        "unit": "pu",
        "tags" : [
            "phases",
            "federate"
        ],
    }
    states = {
        "mapped_object": "Capacitor",
        "type": "integer",
        "vector": False,
        "prefix": "ShuntCompensator",
        "suffix": "status",
        "unit": "",
        "tags" : [
            "phases",
            "federate"
        ],   
    }
    Powers = {
        "type": "complex",
        "vector": True,
        "prefix": "EnergyConsumer",
        "suffix": "pq",
        "unit": "VA",
        "tags" : [
            "phases",
            "federate"
        ],
    }

class PUBLICATION_MAP(enum.Enum):
    Circuit = {
        PROPERTY.TotalPower.name : PROPERTY.TotalPower.value
    }
    Bus = {
        PROPERTY.Voltages.name : PROPERTY.Voltages.value
    }
    Line = {
        PROPERTY.Currents.name : PROPERTY.Currents.value,
        PROPERTY.Enabled.name : PROPERTY.Enabled.value,
    }
    Transformer = {
        PROPERTY.tap.name : PROPERTY.tap.value,
    }
    Regulator = {
        PROPERTY.TapNumber.name : PROPERTY.TapNumber.value,
    }
    Capacitor = {
        PROPERTY.states.name : PROPERTY.states.value,
    }
    Load = {
        PROPERTY.Powers.name : PROPERTY.Powers.value,
    }
    Vsource = {
        PROPERTY.Powers.name : PROPERTY.Powers.value,
        PROPERTY.Enabled.name : PROPERTY.Enabled.value,
    }
    

class HELICS_MAPPING:

    def __init__(self, dssObject, ppty, value, federate):
        if "." in dssObject.FullName:
            self.cname, self.ename = dssObject.FullName.split(".")
        else:
            self.cname = "Bus"
            self.ename = dssObject.Name

        self.pub = None
        self.obj = dssObject
        self.ppty = ppty
        self.valuex = value
        self.federate = federate

        found = False
        for PUBLICATION in PUBLICATION_MAP:
            if PUBLICATION.name == self.cname:
                for PPTY in PROPERTY:
                    if PPTY.name == self.ppty:
                        self.ppty_data = PPTY.value
                        found = True
                        break
            if found:
                break
        
        if self.cname == "Vsource":
            self.ppty_data["prefix"] = "pcc"
            self.ppty_data["unit"] = "MVA"

        return
    
    @property
    def dtype(self):
        return self.ppty_data['type']

    @property
    def pubname(self):
        return f"{self.federate}/{self.ppty_data['prefix']}.{self.ename}.{self.ppty_data['suffix']}"

    @property
    def tags(self): 
        tag_dict =  { "federate" : self.federate}
        if self.valuex.units and 'phase' in self.valuex.units[0]:
            phases =  [x['phase'] for x in self.valuex.units if x['phase'] != "N"]    
            phases ="".join(dict.fromkeys(phases))
            tag_dict["phases"] = phases
        return tag_dict
    
    @property
    def units(self):
        return self.ppty_data['unit']

    @property
    def value(self):
        value = self.obj.GetValue(self.ppty, convert=True)
        if self.isVector and not isinstance(value.value, list):
            val = [value.value]
        elif not self.isVector and isinstance(value.value, list):
            val = value.value[0]
        else:
            val = value.value
        return val

    @property
    def isVector(self):
        return self.ppty_data['vector']

    @property
    def publish(self):
        
        return

    def __str__(self):
        return "<Publication tag: {}\n units: {},\n dtype: {},\n isVector: {},\n tags: {}\nat {}>\n".format(
            self.pubname,
            self.units,
            self.dtype,
            self.isVector,
            self.tags,
            hex(id(self))
        )
