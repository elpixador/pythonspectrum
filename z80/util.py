register_bits = {'A': 7, 'B': 0, 'C': 1, 'D': 2, 'E': 3, 'H': 4, 'L': 5}
index_bytes = [(0xDD, 'IX'), (0xfd, 'IY')]
#              i, name, bit, val
conditions = [(0 << 3, 'NZ', 'Z', 0),
              (1 << 3, 'Z', 'Z', 1),
              (2 << 3, 'NC', 'C', 0),
              (3 << 3, 'C', 'C', 1),
              (4 << 3, 'PO', 'PV', 0),
              (5 << 3, 'PE', 'PV', 1),
              (6 << 3, 'P', 'S', 0),
              (7 << 3, 'M', 'S', 1),]
parities = [False]*256

class ZXFlagsClass(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.S = 0
        self.Z = 0
        #self.F5 = 0
        self.H = 0
        #self.F3 = 0
        self.PV = 0
        self.N = 0
        self.C = 0
        self.F5F3 = 0
    
    def __getattribute__(self, reg):
        if reg in ['S', 'Z', 'H', 'PV', 'N', 'C']:
            if super().__getattribute__(reg): return 1
            else: return 0
        else:
            return super().__getattribute__(reg)

    def equals(self, reg, val):
        if super().__getattribute__(reg): return (val == 1)
        else: return (val == 0)

    def getAsF(self):
        #return (self.S << 7) | (self.Z << 6) | (self.F5 << 5) | (self.H << 4) | (self.F3 << 3) | (self.PV << 2) | (self.N << 1) | (self.C)
        return (
            (0x80 if super().__getattribute__('S') else 0) |
            (0x40 if super().__getattribute__('Z') else 0) |
            #(0x20 if super().__getattribute__('F5') else 0) |
            (0x10 if super().__getattribute__('H') else 0) |
            #(0x08 if super().__getattribute__('F3') else 0) |
            (0x04 if super().__getattribute__('PV') else 0) |
            (0x02 if super().__getattribute__('N') else 0) |
            (0x01 if super().__getattribute__('C') else 0) |
            (super().__getattribute__('F5F3') & 0x28)
        )
    
    def setAsF(self, f):
        self.S = (f & 0b10000000)
        self.Z = (f & 0b01000000)
        #self.F5 = (f & 0b00100000)
        self.H = (f & 0b00010000)
        #self.F3 = (f & 0b00001000)
        self.PV = (f & 0b00000100)
        self.N = (f & 0b00000010)
        self.C = (f & 0b00000001)
        self.F5F3 = (f & 0b00101000)
    
    def setF3(self, f):
        if f:
            self.F5F3 = self.F5F3 | 0b00001000
        else:
            self.F5F3 = self.F5F3 & 0b11110111

    def setF5(self, f):
        if f:
            self.F5F3 = self.F5F3 | 0b00100000
        else:
            self.F5F3 = self.F5F3 & 0b11011111


ZXFlags = ZXFlagsClass()

def get_16bit_twos_comp(val):
    """ Return the value of an 8bit 2s comp number"""
    if (val & 0x8000):
        return - ((val ^  0xFFFF) +  1)
    else:
        return val

def get_8bit_twos_comp(val):
    """ Return the value of an 8bit 2s comp number"""
    if (val & 0x80):
        return - ((val ^  0xFF) +  1)
    else:
        return val
        
def make_8bit_twos_comp(val):
    if val > -1:
        return val
    return ((0 - val) ^ 0xFF) + 1

def subtract8(a, b, cf):
    """ subtract b, a and carry,  return result and set flags """
    ZXFlags.F5F3 = res = a - b - cf
    
    ZXFlags.S = res & 0x80
    ZXFlags.N = 1
    ZXFlags.Z = (res == 0)
    ZXFlags.H = (a ^ res ^ b) & 0x10
    return res &  0xFF
    
def subtract8_check_overflow(a, b, cf):
    ZXFlags.F5F3 = res = a - b - cf
    
    ZXFlags.S = res & 0x80
    ZXFlags.N = 1
    ZXFlags.Z = (res == 0)
    ZXFlags.H = (a ^ res ^ b) & 0x10
    ZXFlags.PV = (b ^ a) & (a ^ res) & 0x80
    ZXFlags.C = res & 0x100
    return res &  0xFF

def add8(a, b, cf):
    """ add a, b and carry flag,  return result and set flags """
    ZXFlags.F5F3 = res = a + b + cf
    ZXFlags.S = res & 0x80
    ZXFlags.Z = (res & 0xFF) == 0
    ZXFlags.H = (a ^ res ^ b) & 0x10
    ZXFlags.PV = (a ^ res) & (b ^ res) & 0x80
    ZXFlags.N = 0
    ZXFlags.C = res & 0x100
    return res &  0xFF

def add8_nocarry(a, b, cf):
    """ add a, b and carry flag,  return result and set flags """
    ZXFlags.F5F3 = res = a + b + cf
    ZXFlags.S = res & 0x80
    ZXFlags.Z = (res & 0xFF) == 0
    ZXFlags.H = (a ^ res ^ b) & 0x10
    ZXFlags.PV = (a ^ res) & (b ^ res) & 0x80
    ZXFlags.N = 0
    return res &  0xFF

def inc16(val):
    return (val + 1) & 0xFFFF

def dec16(val):
    return (val - 1) & 0xFFFF

def inc8(val):
    return (val + 1) & 0xFF

def dec8(val):
    return (val - 1) & 0xFF

def parity(n):
    p=0
    for i in range(0,8):
        p+=(n >> i) & 0x01
    return not (p % 2) 

def a_and_n(registers, n):
    ZXFlags.F5F3 = a = (registers.A & n)
    registers.A = a
    ZXFlags.H = 1
    ZXFlags.N = 0
    ZXFlags.PV = parities[a]
    ZXFlags.C = 0
    ZXFlags.Z = (a == 0)
    ZXFlags.S = a & 0x80


def a_or_n(registers, n):
    ZXFlags.F5F3 = a = registers.A | n
    registers.A = a
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[a]
    ZXFlags.C = 0
    ZXFlags.Z = (a == 0)
    ZXFlags.S = a & 0x80
    
def a_xor_n(registers, n):
    ZXFlags.F5F3 = a = registers.A ^ n
    registers.A = a
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[a]
    ZXFlags.C = 0
    ZXFlags.Z = (a == 0)
    ZXFlags.S = a & 0x80
 
def rotate_left_carry(n):
    c = n >> 7
    v = (n << 1 | c) & 0xFF
    ZXFlags.S = v & 0x80
    ZXFlags.Z = (v == 0)
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[v]
    ZXFlags.C = c
    return v


def rotate_left(n):
    c = n >> 7
    v = (n << 1 | ZXFlags.C) & 0xFF
    ZXFlags.S = v & 0x80
    ZXFlags.Z = (v == 0)
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[v]
    ZXFlags.C = c
    return v


    
 
def rotate_right_carry(n):
    c = n & 0x01
    v = n >> 1 | (c << 7)
    ZXFlags.S = v & 0x80
    ZXFlags.Z = (v == 0)
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[v]
    ZXFlags.C = c
    return v


def rotate_right(n):
    c = n & 0x01
    v = n >> 1 | (ZXFlags.C << 7)
    ZXFlags.S = v & 0x80
    ZXFlags.Z = (v == 0)
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[v]
    ZXFlags.C = c
    return v


def shift_left(n):
    c = n >> 7
    v = (n << 1 ) & 0xFF
    ZXFlags.S = v & 0x80
    ZXFlags.Z = (v == 0)
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[v]
    ZXFlags.C = c
    return v


def shift_left_logical(n):
    c = n >> 7
    v = ((n << 1 ) & 0xFF) | 0x01
    ZXFlags.S = v & 0x80
    ZXFlags.Z = (v == 0)
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[v]
    ZXFlags.C = c
    return v


def shift_right(n):
    c = n & 0x01
    v = n >> 1 | (n & 0x80)
    ZXFlags.S = v & 0x80
    ZXFlags.Z = (v == 0)
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[v]
    ZXFlags.C = c
    return v


def shift_right_logical(n):
    c = n & 0x01
    v = n >> 1
    ZXFlags.S = 0
    ZXFlags.Z = (v == 0)
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[v]
    ZXFlags.C = c
    return v


def offset_pc(registers, jump):
    registers.PC = (registers.PC + get_8bit_twos_comp(jump)) & 0xFFFF
