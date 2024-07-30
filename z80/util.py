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
    
    registers.condition.S = res & 0x80
    registers.condition.N = 1
    registers.condition.Z = (res == 0)
    registers.condition.F3 = res & 0x08
    registers.condition.F5 = res & 0x20    
    registers.condition.H = (a ^ res ^ b) & 0x10
    if PV:
        registers.condition.PV = (b ^ a) & (a ^ res) & 0x80

    if C:
        registers.condition.C = res & 0x100
    return res &  0xFF
    
def subtract8_check_overflow(a, b, cf, registers):
    return subtract8(a, b, cf, registers, PV=True, C=True)

def add8(a, b, cf, registers, C=True):
    """ add a, b and carry flag,  return result and set flags """
    res = a + b + cf
    registers.condition.S = res & 0x80
    registers.condition.Z = (res & 0xFF) == 0
    registers.condition.H = (a ^ res ^ b) & 0x10
    registers.condition.PV = (a ^ res) & (b ^ res) & 0x80
    registers.condition.N = 0
    if C:
        registers.condition.C = res & 0x100
    registers.condition.F3 = res & 0x08
    registers.condition.F5 = res & 0x20
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
    registers.condition.H = 1
    registers.condition.N = 0
    registers.condition.PV = parity(a)
    registers.condition.C = 0
    registers.condition.Z = (a == 0)
    registers.condition.S = a & 0x80
    set_f5_f3(registers, a)


def a_or_n(registers, n):
    a = registers.A | n
    registers.A = a
    registers.condition.H = 0
    registers.condition.N = 0
    registers.condition.PV = parity(a)
    registers.condition.C = 0
    registers.condition.Z = (a == 0)
    registers.condition.S = a & 0x80
    set_f5_f3(registers, a)
    
def a_xor_n(registers, n):
    a = registers.A ^ n
    registers.A = a
    registers.condition.H = 0
    registers.condition.N = 0
    registers.condition.PV = parity(a)
    registers.condition.C = 0
    registers.condition.Z = (a == 0)
    registers.condition.S = a & 0x80
    set_f5_f3(registers, a)
 
def rotate_left_carry(registers, n):
    c = n >> 7
    v = (n << 1 | c) & 0xFF
    registers.condition.S = v & 0x80
    registers.condition.Z = (v == 0)
    registers.condition.H = 0
    registers.condition.N = 0
    registers.condition.PV = parity(v)
    registers.condition.C = c
    return v


def rotate_left(registers, n):
    c = n >> 7
    v = (n << 1 | registers.condition.C) & 0xFF
    registers.condition.S = v & 0x80
    registers.condition.Z = (v == 0)
    registers.condition.H = 0
    registers.condition.N = 0
    registers.condition.PV = parity(v)
    registers.condition.C = c
    return v


    
 
def rotate_right_carry(registers, n):
    c = n & 0x01
    v = n >> 1 | (c << 7)
    registers.condition.S = v & 0x80
    registers.condition.Z = (v == 0)
    registers.condition.H = 0
    registers.condition.N = 0
    registers.condition.PV = parity(v)
    registers.condition.C = c
    return v


def rotate_right(registers, n):
    c = n & 0x01
    v = n >> 1 | (registers.condition.C << 7)
    registers.condition.S = v & 0x80
    registers.condition.Z = (v == 0)
    registers.condition.H = 0
    registers.condition.N = 0
    registers.condition.PV = parity(v)
    registers.condition.C = c
    return v


def shift_left(registers, n):
    c = n >> 7
    v = (n << 1 ) & 0xFF
    registers.condition.S = v & 0x80
    registers.condition.Z = (v == 0)
    registers.condition.H = 0
    registers.condition.N = 0
    registers.condition.PV = parity(v)
    registers.condition.C = c
    return v


def shift_left_logical(registers, n):
    c = n >> 7
    v = ((n << 1 ) & 0xFF) | 0x01
    registers.condition.S = v & 0x80
    registers.condition.Z = (v == 0)
    registers.condition.H = 0
    registers.condition.N = 0
    registers.condition.PV = parity(v)
    registers.condition.C = c
    return v


def shift_right(registers, n):
    c = n & 0x01
    v = n >> 1 | (n & 0x80)
    registers.condition.S = v & 0x80
    registers.condition.Z = (v == 0)
    registers.condition.H = 0
    registers.condition.N = 0
    registers.condition.PV = parity(v)
    registers.condition.C = c
    return v


def shift_right_logical(registers, n):
    c = n & 0x01
    v = n >> 1
    registers.condition.S = 0
    registers.condition.Z = (v == 0)
    registers.condition.H = 0
    registers.condition.N = 0
    registers.condition.PV = parity(v)
    registers.condition.C = c
    return v


def offset_pc(registers, jump):
    registers.PC = (registers.PC + get_8bit_twos_comp(jump)) & 0xFFFF
        
def set_f5_f3(registers, v):
    registers.condition.F5 = v & 0x20
    registers.condition.F3 = v & 0x08
        
def set_f5_f3_from_a(registers):
    set_f5_f3(registers, registers.A)
    