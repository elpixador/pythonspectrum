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
        self.F5 = 0
        self.H = 0
        self.F3 = 0
        self.PV = 0
        self.N = 0
        self.C = 0
    
    def __getattribute__(self, reg):
        if reg in ['S', 'Z', 'F5', 'H', 'F3', 'PV', 'N', 'C']:
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
            (0x20 if super().__getattribute__('F5') else 0) |
            (0x10 if super().__getattribute__('H') else 0) |
            (0x08 if super().__getattribute__('F3') else 0) |
            (0x04 if super().__getattribute__('PV') else 0) |
            (0x02 if super().__getattribute__('N') else 0) |
            (0x01 if super().__getattribute__('C') else 0)
        )
    
    def setAsF(self, f):
        self.S = (f & 0b10000000)
        self.Z = (f & 0b01000000)
        self.F5 = (f & 0b00100000)
        self.H = (f & 0b00010000)
        self.F3 = (f & 0b00001000)
        self.PV = (f & 0b00000100)
        self.N = (f & 0b00000010)
        self.C = (f & 0b00000001)

ZXFlags = ZXFlagsClass()

def get_16bit_twos_comp(val):
    """ Return the value of an 8bit 2s comp number"""
    if (val & 0x8000) == 0:
        return val
    else:
        return - ((val ^  0xFFFF) +  1)

def get_8bit_twos_comp(val):
    """ Return the value of an 8bit 2s comp number"""
    if (val & 0x80) == 0:
        return val
    else:
        return - ((val ^  0xFF) +  1) 
        
def make_8bit_twos_comp(val):
    if val > -1:
        return val
    val = (0 - val) ^  0xFF
    val += 1
    return val

def subtract8(a, b, cf, registers, PV=False, C=False):
    """ subtract b, a and carry,  return result and set flags """
    res = a - b - cf
    
    ZXFlags.S = res & 0x80
    ZXFlags.N = 1
    ZXFlags.Z = (res == 0)
    ZXFlags.F3 = res & 0x08
    ZXFlags.F5 = res & 0x20    
    ZXFlags.H = (a ^ res ^ b) & 0x10
    if PV:
        ZXFlags.PV = (b ^ a) & (a ^ res) & 0x80

    if C:
        ZXFlags.C = res & 0x100
    return res &  0xFF
    
def subtract8_check_overflow(a, b, cf, registers):
    return subtract8(a, b, cf, registers, PV=True, C=True)

def add8(a, b, cf, registers, C=True):
    """ add a, b and carry flag,  return result and set flags """
    res = a + b + cf
    ZXFlags.S = res & 0x80
    ZXFlags.Z = (res & 0xFF) == 0
    ZXFlags.H = (a ^ res ^ b) & 0x10
    ZXFlags.PV = (a ^ res) & (b ^ res) & 0x80
    ZXFlags.N = 0
    if C:
        ZXFlags.C = res & 0x100
    ZXFlags.F3 = res & 0x08
    ZXFlags.F5 = res & 0x20
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
    a = registers.A & n
    registers.A = a
    ZXFlags.H = 1
    ZXFlags.N = 0
    ZXFlags.PV = parities[a]
    ZXFlags.C = 0
    ZXFlags.Z = (a == 0)
    ZXFlags.S = a & 0x80
    set_f5_f3(registers, a)


def a_or_n(registers, n):
    a = registers.A | n
    registers.A = a
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[a]
    ZXFlags.C = 0
    ZXFlags.Z = (a == 0)
    ZXFlags.S = a & 0x80
    set_f5_f3(registers, a)
    
def a_xor_n(registers, n):
    a = registers.A ^ n
    registers.A = a
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[a]
    ZXFlags.C = 0
    ZXFlags.Z = (a == 0)
    ZXFlags.S = a & 0x80
    set_f5_f3(registers, a)
 
def rotate_left_carry(registers, n):
    c = n >> 7
    v = (n << 1 | c) & 0xFF
    ZXFlags.S = v & 0x80
    ZXFlags.Z = (v == 0)
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[v]
    ZXFlags.C = c
    return v


def rotate_left(registers, n):
    c = n >> 7
    v = (n << 1 | ZXFlags.C) & 0xFF
    ZXFlags.S = v & 0x80
    ZXFlags.Z = (v == 0)
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[v]
    ZXFlags.C = c
    return v


    
 
def rotate_right_carry(registers, n):
    c = n & 0x01
    v = n >> 1 | (c << 7)
    ZXFlags.S = v & 0x80
    ZXFlags.Z = (v == 0)
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[v]
    ZXFlags.C = c
    return v


def rotate_right(registers, n):
    c = n & 0x01
    v = n >> 1 | (ZXFlags.C << 7)
    ZXFlags.S = v & 0x80
    ZXFlags.Z = (v == 0)
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[v]
    ZXFlags.C = c
    return v


def shift_left(registers, n):
    c = n >> 7
    v = (n << 1 ) & 0xFF
    ZXFlags.S = v & 0x80
    ZXFlags.Z = (v == 0)
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[v]
    ZXFlags.C = c
    return v


def shift_left_logical(registers, n):
    c = n >> 7
    v = ((n << 1 ) & 0xFF) | 0x01
    ZXFlags.S = v & 0x80
    ZXFlags.Z = (v == 0)
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[v]
    ZXFlags.C = c
    return v


def shift_right(registers, n):
    c = n & 0x01
    v = n >> 1 | (n & 0x80)
    ZXFlags.S = v & 0x80
    ZXFlags.Z = (v == 0)
    ZXFlags.H = 0
    ZXFlags.N = 0
    ZXFlags.PV = parities[v]
    ZXFlags.C = c
    return v


def shift_right_logical(registers, n):
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
        
def set_f5_f3(registers, v):
    ZXFlags.F5 = v & 0x20
    ZXFlags.F3 = v & 0x08
        
def set_f5_f3_from_a(registers):
    set_f5_f3(registers, registers.A)
    