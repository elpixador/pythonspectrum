from . import util
from . import io

class BitAccesser(object):
    def __init__(self, bit_names, registers, reg):
        object.__setattr__(self, "bitspos",
                           dict(zip(bit_names, range(7, -1, -1))))
        object.__setattr__(self, "bitsval",
                           dict(zip(bit_names, [0x80, 0x40, 0x20, 0x10, 0x8, 0x4, 0x2, 0x1])))
        object.__setattr__(self, "registers", registers) #self.registers = registers # per evitar passar per __setattr__
        object.__setattr__(self, "reg", reg) #self.reg = reg
        
    def __getattr__(self, b):
        return (dict(self.registers)[self.reg] >>  self.bitspos[b]) &  1
    
    def __setattr__(self, b, v):
        if v:
            self.registers[self.reg] = self.registers[self.reg] | self.bitsval[b]
        else:
            self.registers[self.reg] = self.registers[self.reg] & ((self.bitsval[b]) ^  0xFF)
            
class Registers(dict):
    def __init__(self, *arg, **kw):
        super(Registers, self).__init__(*arg, **kw)

        self.reset()
        
    def reset(self):
        self["PC"] = 0 # Program Counter (16bit)
        self["SP"] = 0 # Stack Pointer (16bit)
        self["IX"] = 0 # Index Register X (16bit)
        self["IY"] = 0 # Index Register Y (16bit)
        self["I"] = 0  # Interrupt Page Address (8bit)
        self["RR"] = 0  # Memory Refresh (8bit)

        self["A"] = 0 # Accumulator (8bit)
        #self["F"] = 0 # Flags (8bit)
        self["A_"] = 0 # Alt. Accumulator (8bit)
        self["F_"] = 0 # Alt. Flags (8bit)

        self["B"] = 0 # General (8bit)
        self["C"] = 0 # General (8bit)
        self["B_"] = 0 # General (8bit)
        self["C_"] = 0 # General (8bit)

        self["D"] = 0 # General (8bit)
        self["E"] = 0 # General (8bit)
        self["D_"] = 0 # General (8bit)
        self["E_"] = 0 # General (8bit)

        self["H"] = 0 # General (8bit)
        self["L"] = 0 # General (8bit)
        self["H_"] = 0 # General (8bit)
        self["L_"] = 0 # General (8bit)

        #self["condition"] = BitAccesser(["S", "Z", "F5", "H", "F3", "PV", "N", "C"], self, "F")
        
        self['HALT']=False #
        self['IFF']=False  # Interrupt flip flop
        self['IFF2']=False  # NM Interrupt flip flop
        self['IM']=False   # Iterrupt mode

    def __setattr__(self, attr, val):
        if attr in self:
            super(Registers, self).__setitem__(attr, val)
        elif attr  in ["HL", "BC", "DE"]:
            super(Registers, self).__setitem__(attr[0], val >> 8)
            super(Registers, self).__setitem__(attr[1], val & 0xFF)
        elif attr == "AF":
            super(Registers, self).__setitem__("A", val >> 8)
            util.ZXFlags.setAsF(val & 0xFF)
        elif attr == "F":
            util.ZXFlags.setAsF(val)
        elif attr in ["IXH", "IYH"]:
            i = attr[0:2]
            super(Registers, self).__setitem__(i, (super(Registers, self).__getitem__(i) & 0x00FF) | (val << 8))
        elif attr in ["IXL", "IYL"]:
            i = attr[0:2]
            super(Registers, self).__setitem__(i, (super(Registers, self).__getitem__(i) & 0xFF00) | val)
        elif attr == "R":
            super(Registers, self).__setitem__("RR", val)
            io.ZXRegisterR = val

    def __getattr__(self, reg):
        if reg in self:
            return super(Registers, self).__getitem__(reg)
        elif reg in ["HL", "BC", "DE"]:
            return super(Registers, self).__getitem__(reg[0]) << 8 | super(Registers, self).__getitem__(reg[1])
        elif reg == "AF":
            return super(Registers, self).__getitem__("A") << 8 | util.ZXFlags.getAsF()
        elif reg == "F":
            return util.ZXFlags.getAsF()
        elif reg in ["IXH", "IYH"]:
            return super(Registers, self).__getitem__(reg[0:2]) >> 8
        elif reg in ["IXL", "IYL"]:
            return super(Registers, self).__getitem__(reg[0:2]) & 0xFF
        elif reg == "R":
            return (io.ZXRegisterR & 0x7F) | (super(Registers, self).__getitem__("RR") & 0x80)
        
    def __getitem__(self, reg):
        if reg in self:
            return super(Registers, self).__getitem__(reg)
        elif reg in ["BC", "HL", "DE"]:
            return super(Registers, self).__getitem__(reg[0]) << 8 |  super(Registers, self).__getitem__(reg[1])
        elif reg == "AF":
            return super(Registers, self).__getitem__("A") << 8 | util.ZXFlags.getAsF()
        elif reg == "F":
            return util.ZXFlags.getAsF()
        elif reg in ["IXH", "IXL", "IYH", "IYL"]:
            return getattr(self, reg)
        elif reg == "R":
            return (io.ZXRegisterR & 0x7F) | (super(Registers, self).__getitem__("RR") & 0x80)
        else:
            return super(Registers, self).__getitem__(reg)
        
    def __setitem__(self, reg, val):
        if reg in self:
            return super(Registers, self).__setitem__(reg, val)
        elif reg in ["BC", "HL", "DE"]:
            super(Registers, self).__setitem__(reg[0], val >> 8)
            super(Registers, self).__setitem__(reg[1], val & 0xFF)
        elif reg == "AF":
            super(Registers, self).__setitem__("A", val >> 8)
            util.ZXFlags.setAsF(val & 0xFF)
        elif reg == "F":
            util.ZXFlags.setAsF(val)
        elif reg in ["IXH", "IXL", "IYH", "IYL"]:
            return setattr(self, reg, val)
        elif reg == "R":
            super(Registers, self).__setitem__("RR", val)
            io.ZXRegisterR = val
        else:
            return super(Registers, self).__setitem__(reg, val)
    
    @classmethod
    def create(cls):
        return cls()
        
