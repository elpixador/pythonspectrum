import copy
import logging
from . util import *
import sys

class instruction(object):
    def __init__(self, opcode_args, n_operands, string, tstates=1):
        self.string = string
        self.super_op = 0
        #op_args = []
        #for i in opcode_args:
        ##super_op = i[0] >> 8
        ##self.super_op = super_op
        ##op = i[0] & 255
        #op_args.append((op, i[1]))
        #self.opcode_args = op_args
        self.opcode_args = opcode_args

        self.n_operands = n_operands # number bytes to read pos opcodeaa()
        self.tstates = tstates

    def __call__(self, f):
        return Instruction(self, f)


class Instruction(object):
    def __init__(self, ins, executer):
        self.string = ins.string
        self.super_op = ins.super_op
        self.opcode_args = ins.opcode_args
        self.n_operands = ins.n_operands
        self.tstates = ins.tstates
        self.executer = executer

    def get_read_list(self, operands=()):
        return self.executer(*((self, self.registers, True, None) + self.args +
                               tuple([operands[i] for i in self.operands]) ))

    def execute(self, data=None, operands=()):
        return self.executer(*((self, self.registers, False, data) + self.args +
                               tuple([operands[i] for i in self.operands]) ))

    def assembler(self, operands=()):
        return self.string.format(*(self.args + tuple([operands[i] for i in self.operands])))
    
    
    def __str__(self):
        s = "Instruction: " + self.string + "\n"
        s += "args: " + str(self.args) + "\n"
        s += "operand bytes: " + str(self.operands) + "\n"
        return s


class InstructionSet():

    def __init__(self, registers):
        self._registers = registers

        self._instructions = {} #0: [None] * 256} #keys of this are super_ops
        
        self._instructions2 = {}
        # Fill instruction lookup
        for i in dir(self):
            f = getattr(self, i)
            if f.__class__ == Instruction:
                print (i, ":")
                for o in f.opcode_args:
                    print (o)
                    ff = copy.copy(f)
                    ff.registers = self._registers
                    ff.args = o[1]
                    if len(o) == 3:
                        ff.tstates = o[2]
                        #print "Tstates=", ff.tstates
                    else:
                        # print "missing tstates for "
                        # tstates not specified so used instruction group number
                        # so default...
                        pass
                    ff.operands = []
                    d = self._instructions2
                    opargs = o
                    if type(o[0]) == type(0x4):
                        if o[0] > 0xFF:
                            opargs = ((o[0] >> 8, o[0] & 0xFF), o[1])
                        else:
                            opargs = ((o[0], ), o[1])
                    for n, i in enumerate(opargs[0][:-1]):
                        if i in d:
                            d = d[i]
                        elif i == "-":
                            ff.operands.append(n)
                            if len(d.keys()) == 0:
                                d2 = {}
                                for i in range(256):
                                    d[i] = d2
                                d = d2
                            else:
                                d = d[0]
                        else:
                            d[i] = {}
                            d = d[i]
                    if opargs[0][-1] == "-":
                        ff.operands.append(n+1)
                        for i in range(256):
                            d[i] = ff
                    else:
                        d[opargs[0][-1]] = ff
                    
                            

        self._instructions = self._instructions2

        self._instruction_composer = []
        self._composer_instruction = None
        self._composer_len = 1
        
        
    def __getitem__(self, ins):
        if self.is_two_parter(ins):
            return self._instructions[ins]
        else:
            if ins in self._instructions[0]: 
                return self._instructions[0][ins]
            raise AttributeError("Unknown opcode")

    def __lshift__(self, op):
        self._instruction_composer.append(op)
        q = self._instructions
        for i in self._instruction_composer:
            q = q[i]
        if isinstance(q, dict):
            return False, 0
        else:
            ops = tuple(self._instruction_composer)
            self._instruction_composer = []
            self._registers.R = ((self._registers.R + 1) & 0x7F) | (self._registers.R & 0x80)
#            print q, ops
            return q, ops
        
    def reset_composer(self):
        self._instruction_composer = []
        
    def is_two_parter(self, ins):
        return ins in self._instructions

    #----------------------------------------------------------------------

    #----------------------------------------------------------------------    
    # 8-bit Load Instructions
    #----------------------------------------------------------------------
    @instruction([(0x7F, ("A", "A")), (0x78, ("A", "B")), (0x79, ("A", "C")), (0x7A, ("A", "D")), (0x7B, ("A", "E")),
                  (0x7C, ("A", "H")), (0x7D, ("A", "L")),
                  (0x47, ("B", "A")), (0x40, ("B", "B")), (0x41, ("B", "C")), (0x42, ("B", "D")), (0x43, ("B", "E")),
                  (0x44, ("B", "H")), (0x45, ("B", "L")),
                  (0x4F, ("C", "A")), (0x48, ("C", "B")), (0x49, ("C", "C")), (0x4A, ("C", "D")), (0x4B, ("C", "E")),
                  (0x4C, ("C", "H")), (0x4D, ("C", "L")),
                  (0x57, ("D", "A")), (0x50, ("D", "B")), (0x51, ("D", "C")), (0x52, ("D", "D")), (0x53, ("D", "E")),
                  (0x54, ("D", "H")), (0x55, ("D", "L")),
                  (0x5F, ("E", "A")), (0x58, ("E", "B")), (0x59, ("E", "C")), (0x5A, ("E", "D")), (0x5B, ("E", "E")),
                  (0x5C, ("E", "H")), (0x5D, ("E", "L")),
                  (0x67, ("H", "A")), (0x60, ("H", "B")), (0x61, ("H", "C")), (0x62, ("H", "D")), (0x63, ("H", "E")),
                  (0x64, ("H", "H")), (0x65, ("H", "L")),
                  (0x6F, ("L", "A")), (0x68, ("L", "B")), (0x69, ("L", "C")), (0x6A, ("L", "D")), (0x6B, ("L", "E")),
                  (0x6C, ("L", "H")), (0x6D, ("L", "L")),
                  (0xDD7F, ("A", "A"), 8), (0xDD78, ("A", "B"), 8), (0xDD79, ("A", "C"), 8), (0xDD7A, ("A", "D"), 8), (0xDD7B, ("A", "E"), 8),
                  (0xDD7C, ("A", "IXH"), 8), (0xDD7D, ("A", "IXL"), 8),
                  (0xDD47, ("B", "A"), 8), (0xDD40, ("B", "B"), 8), (0xDD41, ("B", "C"), 8), (0xDD42, ("B", "D"), 8), (0xDD43, ("B", "E"), 8),
                  (0xDD44, ("B", "IXH"), 8), (0xDD45, ("B", "IXL"), 8),
                  (0xDD4F, ("C", "A"), 8), (0xDD48, ("C", "B"), 8), (0xDD49, ("C", "C"), 8), (0xDD4A, ("C", "D"), 8), (0xDD4B, ("C", "E"), 8),
                  (0xDD4C, ("C", "IXH"), 8), (0xDD4D, ("C", "IXL"), 8),
                  (0xDD57, ("D", "A"), 8), (0xDD50, ("D", "B"), 8), (0xDD51, ("D", "C"), 8), (0xDD52, ("D", "D"), 8), (0xDD53, ("D", "E"), 8),
                  (0xDD54, ("D", "IXH"), 8), (0xDD55, ("D", "IXL"), 8),
                  (0xDD5F, ("E", "A"), 8), (0xDD58, ("E", "B"), 8), (0xDD59, ("E", "C"), 8), (0xDD5A, ("E", "D"), 8), (0xDD5B, ("E", "E"), 8),
                  (0xDD5C, ("E", "IXH"), 8), (0xDD5D, ("E", "IXL"), 8),
                  (0xDD67, ("IXH", "A"), 8), (0xDD60, ("IXH", "B"), 8), (0xDD61, ("IXH", "C"), 8), (0xDD62, ("IXH", "D"), 8), (0xDD63, ("IXH", "E"), 8),
                  (0xDD64, ("IXH", "IXH"), 8), (0xDD65, ("IXH", "IXL"), 8),
                  (0xDD6F, ("IXL", "A"), 8), (0xDD68, ("IXL", "B"), 8), (0xDD69, ("IXL", "C"), 8), (0xDD6A, ("IXL", "D"), 8), (0xDD6B, ("IXL", "E"), 8),
                  (0xDD6C, ("IXL", "IXH"), 8), (0xDD6D, ("IXL", "IXL"), 8),
                  (0xFD7F, ("A", "A"), 8), (0xFD78, ("A", "B"), 8), (0xFD79, ("A", "C"), 8), (0xFD7A, ("A", "D"), 8), (0xFD7B, ("A", "E"), 8),
                  (0xFD7C, ("A", "IYH"), 8), (0xFD7D, ("A", "IYL"), 8),
                  (0xFD47, ("B", "A"), 8), (0xFD40, ("B", "B"), 8), (0xFD41, ("B", "C"), 8), (0xFD42, ("B", "D"), 8), (0xFD43, ("B", "E"), 8),
                  (0xFD44, ("B", "IYH"), 8), (0xFD45, ("B", "IYL"), 8),
                  (0xFD4F, ("C", "A"), 8), (0xFD48, ("C", "B"), 8), (0xFD49, ("C", "C"), 8), (0xFD4A, ("C", "D"), 8), (0xFD4B, ("C", "E"), 8),
                  (0xFD4C, ("C", "IYH"), 8), (0xFD4D, ("C", "IYL"), 8),
                  (0xFD57, ("D", "A"), 8), (0xFD50, ("D", "B"), 8), (0xFD51, ("D", "C"), 8), (0xFD52, ("D", "D"), 8), (0xFD53, ("D", "E"), 8),
                  (0xFD54, ("D", "IYH"), 8), (0xFD55, ("D", "IYL"), 8),
                  (0xFD5F, ("E", "A"), 8), (0xFD58, ("E", "B"), 8), (0xFD59, ("E", "C"), 8), (0xFD5A, ("E", "D"), 8), (0xFD5B, ("E", "E"), 8),
                  (0xFD5C, ("E", "IYH"), 8), (0xFD5D, ("E", "IYL"), 8),
                  (0xFD67, ("IYH", "A"), 8), (0xFD60, ("IYH", "B"), 8), (0xFD61, ("IYH", "C"), 8), (0xFD62, ("IYH", "D"), 8), (0xFD63, ("IYH", "E"), 8),
                  (0xFD64, ("IYH", "IYH"), 8), (0xFD65, ("IYH", "IYL"), 8),
                  (0xFD6F, ("IYL", "A"), 8), (0xFD68, ("IYL", "B"), 8), (0xFD69, ("IYL", "C"), 8), (0xFD6A, ("IYL", "D"), 8), (0xFD6B, ("IYL", "E"), 8),
                  (0xFD6C, ("IYL", "IYH"), 8), (0xFD6D, ("IYL", "IYL"), 8),
                  (0xED47, ("I", "A"), 9), (0xED4F, ("R", "A"), 9),
                  ], 0, "LD {0}, {1}", 4)
    def ld_r_r_(instruction, registers, get_reads, data, r, r_):
        if get_reads:
            return []
        else:
            registers[r] = registers[r_]
            return []
        
    @instruction([(0xED57, ('I', )), (0xED5F, ("R", ))], 0, "LD A, {0}", 9)
    def ld_a_ir(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            if r == "R":
                # Add 2 to refresh. TODO: fix
                registers[r] += 2
            registers.A = registers[r]
            registers.condition.S = registers[r] >> 7
            registers.condition.Z = registers[r] == 0
            registers.condition.H = 0
            registers.condition.PV = registers.IFF2
            registers.condition.N = 0
            set_f5_f3_from_a(registers)
            return []
        
    #@instruction([(0xED47, ("I", )), (0xED5F, ("R", )), (0x00, (), 30) ],
                  #1, "LD {0}, {1}", 9)
    #def ld_a_ir(instruction, registers, get_reads, data, r):
        #if get_reads:
            #return []
        #else:
            ##registers.A = registers[r]
            ##registers.condition.S = registers[r] >> 7
            ##registers.condition.Z = registers[r] == 0
            ##registers.condition.H = 0
            ##registers.condition.PV = registers.IFF2
            ##registers.condition.N = 0
            ##set_f5_f3_from_a(registers)
            #return []
        
     

    @instruction([([0x3E, '-'], ("A", )), ([0x06, '-'], ("B", )), ([0x0E, '-'], ("C", )),
                  ([0x16, '-'], ("D", )), ([0x1E, '-'], ("E", )), ([0x26, '-'], ("H", )),
                  ([0x2E, '-'], ("L", )),
                  ([0xDD, 0x3E, '-'], ("A", ), 11), ([0xDD, 0x06, '-'], ("B", ), 11), ([0xDD, 0x0E, '-'], ("C", ), 11),
                  ([0xDD, 0x16, '-'], ("D", ), 11), ([0xDD, 0x1E, '-'], ("E", ), 11), ([0xDD, 0x26, '-'], ("IXH", ), 11),
                  ([0xDD, 0x2E, '-'], ("IXL", ), 11),
                  ([0xFD, 0x3E, '-'], ("A", ), 11), ([0xFD, 0x06, '-'], ("B", ), 11), ([0xFD, 0x0E, '-'], ("C", ), 11),
                  ([0xFD, 0x16, '-'], ("D", ), 11), ([0xFD, 0x1E, '-'], ("E", ), 11), ([0xFD, 0x26, '-'], ("IYH", ), 11),
                  ([0xFD, 0x2E, '-'], ("IYL", ), 11)],
                 1, "LD {0}, {1:X}H", 7)
    def ld_r_n(instruction, registers, get_reads, data, r, n):
        if get_reads:
            return []
        else:
            registers[r] = n
            return []


    @instruction([(0x7E, ("A", )), (0x46, ("B", )), (0x4E, ("C", )), (0x56, ("D", )), (0x5E, ("E", )), (0x66, ("H", )),
                  (0x6E, ("L", ))],
                 0, "LD {0}, (HL)", 7)
    def ld_r_hl(instruction, registers, get_reads, data, r):
        if get_reads:
            return [registers.H << 8 | registers.L]
        else:
            registers[r] = data[0]
            return []

    @instruction([([0xDD, 0x7E, '-'], ("A", "IX")), ([0xDD, 0x46, '-'], ("B", "IX")),
                  ([0xDD, 0x4E, '-'], ("C", "IX")), ([0xDD, 0x56, '-'], ("D", "IX")),
                  ([0xDD, 0x5E, '-'], ("E", "IX")), ([0xDD, 0x66, '-'], ("H", "IX")),
                  ([0xDD, 0x6E, '-'], ("L", "IX")),
                  ([0xFD, 0x7E, '-'], ("A", "IY")), ([0xFD, 0x46, '-'], ("B", "IY")),
                  ([0xFD, 0x4E, '-'], ("C", "IY")), ([0xFD, 0x56, '-'], ("D", "IY")),
                  ([0xFD, 0x5E, '-'], ("E", "IY")), ([0xFD, 0x66, '-'], ("H", "IY")),
                  ([0xFD, 0x6E, '-'], ("L", "IY"))],   
                  1, "LD {0}, ({1}+{2:X}H)", 19)
    def ld_r_i_d(instruction, registers, get_reads, data, r, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            registers[r] = data[0]
            return []

    @instruction([(0x77, ("A", )), (0x70, ("B", )), (0x71, ("C", )), (0x72, ("D", )), (0x73, ("E", )), (0x74, ("H", )),
                  (0x75, ("L", ))],
                 0, "LD (HL), {0}", 7)
    def ld_hl_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            return [(registers.H << 8 | registers.L, registers[r])]

    @instruction([([0xDD, 0x77, '-'], ("A", "IX")), ([0xDD, 0x70, '-'], ("B", "IX")),
                  ([0xDD, 0x71, '-'], ("C", "IX")), ([0xDD, 0x72, '-'], ("D", "IX")),
                  ([0xDD, 0x73, '-'], ("E", "IX")), ([0xDD, 0x74, '-'], ("H", "IX")),
                  ([0xDD, 0x75, '-'], ("L", "IX")),
                  ([0xFD, 0x77, '-'], ("A", "IY")), ([0xFD, 0x70, '-'], ("B", "IY")),
                  ([0xFD, 0x71, '-'], ("C", "IY")), ([0xFD, 0x72, '-'], ("D", "IY")),
                  ([0xFD, 0x73, '-'], ("E", "IY")), ([0xFD, 0x74, '-'], ("H", "IY")),
                  ([0xFD, 0x75, '-'], ("L", "IY"))],
                  1, "LD ({1}+{2:X}H), {0}", 19)
    def ld_i_d_r(instruction, registers, get_reads, data, r, i, d):
        if get_reads:
            return []
        else:
            return [( registers[i] + get_8bit_twos_comp(d), registers[r])]

    @instruction([([0x36, '-'], ( ))], 1, "LD (HL), {0:X}H", 10)
    def ld_hl_n(instruction, registers, get_reads, data, n):
        if get_reads:
            return []
        else:
            return [(registers.H << 8 | registers.L, n)]

    @instruction([([0xDD, 0x36, '-', '-'], ("IX", )), ([0xFD, 0x36, '-', '-'], ("IY", ))],
                 2, "LD ({0}+{1:X}H), {2:X}H", 19)
    def ld_i_d_n(instruction, registers, get_reads, data, i, d, n):
        if get_reads:
            return []
        else:
            return [( registers[i] + get_8bit_twos_comp(d), n)]

    @instruction([(0x0A, ("B", "C")), (0x1A, ("D", "E"))],
                 0, "LD A, ({0}{1})", 7)
    def ld_a_rr(instruction, registers, get_reads, data, r, r2):
        if get_reads:
            return [registers[r] << 8 | registers[r2]]
        else:
            registers.A = data[0]
            return []

    @instruction([([0x3A, '-', '-'], ())],
                 2, "LD A, ({1:x}{0:X}H)", 13)
    def ld_a_nn(instruction, registers, get_reads, data, n, n2):
        if get_reads:
            return [n2 << 8 | n]
        else:
            registers.A = data[0]
            return []


    @instruction([(0x02, ("B", "C")), (0x12, ("D", "E"))],
                 0, "LD ({0}{1}), A", 7)
    def ld_rr_a(instruction, registers, get_reads, data, r, r2):
        if get_reads:
            return []
        else:
            return [(registers[r] << 8 | registers[r2], registers.A)]


    @instruction([([0x32, '-', '-'], ())],
                 2, "LD ({1:x}{0:X}H), A", 13)
    def ld_nn_a(instruction, registers, get_reads, data, n, n2):
        if get_reads:
            return []
        else:
            return [(n2 << 8 | n, registers.A)]


    #----------------------------------------------------------------------
    # 16-bit Load instructions
    #----------------------------------------------------------------------
    @instruction([([0x01, '-', '-'], ("B", "C")), ([0x11, '-', '-'], ("D", "E")), ([0x21, '-', '-'], ("H", "L"))],
                 2, "LD {0}{1}, {3:X}{2:X}H", 10)
    def ld_dd_nn(instruction, registers, get_reads, data, r, r2, n, n2):
        if get_reads:
            return []
        else:
            registers[r] = n2
            registers[r2] = n
            return []

    @instruction([([0x31, '-', '-'], ("SP",), 10), ([0xDD, 0x21, '-', '-'], ("IX", )),
                  ([0xFD, 0x21, '-', '-'], ("IY", ))],
                 2, "LD {0}, {2:X}{1:X}H", 14)
    def ld_D_nn(instruction, registers, get_reads, data, r, n, n2):
        if get_reads:
            return []
        else:
            registers[r] = n2 << 8 | n
            return []

    @instruction([([0xED, 0x4B, '-', '-'], ("B", "C" )), ([0xED, 0x5B, '-', '-'], ("D", "E" )),
                  ([0xED, 0x6B, '-', '-'], ("H", "L" )), ([0x2A, '-', '-'], ("H", "L" ), 16), ],
                 2, "LD {0}{1}, ({3:X}{2:X}H)", 20)
    def ld_dd_nn_(instruction, registers, get_reads, data, r, r_, n, n_):
        if get_reads:
            return [n_ << 8 | n, (n_ << 8 | n) + 1]
        else:
            registers[r] = data[1]
            registers[r_] = data[0]
            return []

    @instruction([([0xDD, 0x2A, '-', '-'], ("IX", )), ([0xFD, 0x2A, '-', '-'], ("IY", )),
                  ([0xED, 0x7B, '-', '-'], ("SP", ))],
                 2, "LD {0}, ({2:X}{1:X}H)", 20)
    def ld_D_nn_(instruction, registers, get_reads, data, r, n, n2):
        if get_reads:
            return [n2 << 8 | n, (n2 << 8 | n) + 1]
        else:
            registers[r] = data[1] << 8 | data[0]
            return []


    @instruction([([0xED, 0x73, '-', '-'], ("SP", )), ([0xDD, 0x22, '-', '-'], ("IX", )),
                  ([0xFD, 0x22, '-', '-'], ("IY", ))],
                 2, "LD ({2:X}{1:X}H), {0}", 20)
    def ld_nn__D(instruction, registers, get_reads, data, r, n, n2):
        if get_reads:
            return []
        else:
            ad = n2 << 8 | n
            return [(ad + 1, registers[r] >> 8),
                    (ad, registers[r] & 255)]

    @instruction([([0xED, 0x63, '-', '-'], ("H", "L", )), ([0x22, '-', '-'], ("H", "L", ), 16),
                  ([0xED, 0x43, '-', '-'], ("B", "C", )), ([0xED, 0x53, '-', '-'], ("D", "E", ))],
                 2, "LD ({3:X}{2:X}H), {0}{1}", 20)
    def ld_nn_D(instruction, registers, get_reads, data, r, r2, n, n2):
        if get_reads:
            return []
        else:
            ad = n2 << 8 | n
            return [(ad + 1, registers[r]),
                    (ad, registers[r2])]

    @instruction([(0xF9, ())],
                 0, "LD SP, HL", 6)
    def ld_sp_hl(instruction, registers, get_reads, data):
        if get_reads:
            return []
        else:
            registers.SP = registers.H << 8 | registers.L
            return []

    @instruction([(0xDDF9, ("IX", )), (0xFDF9, ("IY", ))],
                 0, "LD SP, {0}", 10)
    def ld_sp_i(instruction, registers, get_reads, data, i):
        if get_reads:
            return []
        else:
            registers.SP = registers[i]
            return []


    @instruction([(0xC5, ("B", "C" )), (0xD5, ("D", "E" )), (0xE5, ("H", "L" )), (0xF5, ("A", "F" ))],
                 0, "PUSH {0}{1}", 11)
    def push_qq(instruction, registers, get_reads, data, q, q2):
        if get_reads:
            return []
        else:
            stack = registers.SP
            registers.SP -= 2
            return [(stack - 1, registers[q]), (stack - 2, registers[q2])]


    @instruction([(0xDDE5, ("IX",  )), (0xFDE5, ("IY", ))],
                 0, "PUSH {0}", 15)
    def push_i(instruction, registers, get_reads, data, i):
        if get_reads:
            return []
        else:
            stack = registers.SP
            registers.SP -= 2
            return [(stack - 1, registers[i] >> 8), (stack - 2, registers[i] & 255)]


    @instruction([(0xC1, ("B", "C" )), (0xD1, ("D", "E" )), (0xE1, ("H", "L" )), (0xF1, ("A", "F" ))],
                 0, "POP {0}{1}", 10)
    def pop_qq(instruction, registers, get_reads, data, q, q2):
        if get_reads:
            stack = registers.SP
            return [stack, stack + 1]
        else:
            registers.SP += 2
            registers[q2] = data[0]
            registers[q] = data[1]
            return []


    @instruction([(0xDDE1, ("IX", )), (0xFDE1, ("IY", ))],
                 0, "POP {0}", 14)
    def pop_i(instruction, registers, get_reads, data, i):
        if get_reads:
            stack = registers.SP
            return [stack, stack + 1]
        else:
            registers.SP += 2
            registers[i] = data[1] << 8 | data[0]
            return []

    #----------------------------------------------------------------------
    # Exchange, Block Transfer, and Search Group
    #----------------------------------------------------------------------
    @instruction([(0xEB, ())], 0, "EX DE, HL", 4)
    def ex_de_hl(instruction, registers, get_reads, data):
        if get_reads:
            return []
        else:
            registers.D, registers.H = (registers.H, registers.D)
            registers.E, registers.L = (registers.L, registers.E)
            return []

    @instruction([(0x08, ())], 0, "EX AF, AF'", 4)
    def ex_af_af_(instruction, registers, get_reads, data):
        if get_reads:
            return []
        else:
            registers.A, registers.A_ = (registers.A_, registers.A)
            registers.F, registers.F_ = (registers.F_, registers.F)
            return []

    @instruction([(0xD9, ())], 0, "EXX", 4)
    def exx(instruction, registers, get_reads, data):
        if get_reads:
            return []
        else:
            registers.B, registers.B_ = (registers.B_, registers.B)
            registers.C, registers.C_ = (registers.C_, registers.C)
            registers.D, registers.D_ = (registers.D_, registers.D)
            registers.E, registers.E_ = (registers.E_, registers.E)
            registers.H, registers.H_ = (registers.H_, registers.H)
            registers.L, registers.L_ = (registers.L_, registers.L)
            return []

    @instruction([(0xE3, ())], 0, "EX (SP), HL", 19)
    def ex_sp__hl(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.SP, registers.SP + 1]
        else:
            h = registers.H
            l = registers.L
            registers.H = data[1]
            registers.L = data[0]
            return [(registers.SP, l), (registers.SP + 1, h)]

    @instruction([(0xDDE3, ("IX", )), (0xFDE3, ("IY", ))], 0,
                 "EX (SP), {0}", 23)
    def ex_sp__i(instruction, registers, get_reads, data, i):
        if get_reads:
            return [registers.SP, registers.SP + 1]
        else:
            ix = registers[i]
            registers[i] = data[1] << 8 | data[0]

            return [(registers.SP, registers[i] & 255),
                    (registers.SP + 1, registers[i] >> 8)]

    @instruction([(0xEDA0, ())], 0, "LDI", 16)
    def ldi(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.H << 8 | registers.L]
        
        else:
            de_ = de = registers.D << 8 | registers.E
            hl = registers.H << 8 | registers.L
            bc = registers.B << 8 | registers.C
            hl += 1
            if hl > 0xFFFF: hl = 0
            registers.H = hl >> 8
            registers.L = hl & 0xFF
            bc -= 1
            if bc < 0: bc = 0xFFFF
            registers.B = bc >> 8
            registers.C = bc & 0xFF
            de += 1
            if de > 0xFFFF: de = 0
            registers.D = de >> 8
            registers.E = de & 0xFF

            registers.condition.H = 0
            if bc != 0:
                registers.condition.PV = 1
            else:
                registers.condition.PV = 0
            registers.condition.N = 0
            registers.condition.F3 = (registers.A + data[0]) & 0x08
            registers.condition.F5 = (registers.A + data[0]) & 0x02
            return [(de_, data[0])]

    @instruction([(0xEDB0, ())], 0, "LDIR", 21)
    def ldir(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.H << 8 | registers.L]
        else:
            de_ = de = registers.D << 8 | registers.E
            hl = registers.H << 8 | registers.L
            bc = registers.B << 8 | registers.C
            hl += 1
            if hl > 0xFFFF: hl = 0
            registers.H = hl >> 8
            registers.L = hl & 0xFF
            bc -= 1
            if bc < 0: bc = 0xFFFF
            registers.B = bc >> 8
            registers.C = bc & 0xFF
            de += 1
            if de > 0xFFFF: de = 0
            registers.D = de >> 8
            registers.E = de & 0xFF

            registers.condition.H = 0
            if bc != 0:
                registers.PC -= 2
                instruction.tstates = 21
            else:
                instruction.tstates = 16

            registers.condition.PV = 0
            registers.condition.N = 0
            registers.condition.F3 = (registers.A + data[0]) & 0x08
            registers.condition.F5 = (registers.A + data[0]) & 0x02
            return [(de_, data[0])]


    @instruction([(0xEDA8, ())], 0, "LDD", 16)
    def ldd(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.H << 8 | registers.L]
        else:
            de_ = de = registers.D << 8 | registers.E
            hl = registers.H << 8 | registers.L
            bc = registers.B << 8 | registers.C
            hl -= 1
            if hl < 0: hl = 0xFFFF
            registers.H = hl >> 8
            registers.L = hl & 0xFF
            bc -= 1
            if bc < 0: bc = 0xFFFF
            registers.B = bc >> 8
            registers.C = bc & 0xFF
            de -= 1
            if de < 0: de = 0xFFFF
            registers.D = de >> 8
            registers.E = de & 0xFF

            registers.condition.H = 0
            if bc != 0:
                registers.condition.PV = 1
            else:
                registers.condition.PV = 0
            registers.condition.N = 0
            registers.condition.F3 = (registers.A + data[0]) & 0x08
            registers.condition.F5 = (registers.A + data[0]) & 0x02
            return [(de_, data[0])]

    @instruction([(0xEDB8, ())], 0, "LDDR", 16)
    def lddr(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.H << 8 | registers.L]
        else:
            de_ = de = registers.D << 8 | registers.E
            hl = registers.H << 8 | registers.L
            bc = registers.B << 8 | registers.C
            hl -= 1
            if hl < 0: hl = 0xFFFF
            registers.H = hl >> 8
            registers.L = hl & 0xFF
            bc -= 1
            if bc < 0: bc = 0xFFFF
            registers.B = bc >> 8
            registers.C = bc & 0xFF
            de -= 1
            if de < 0: de = 0xFFFF
            registers.D = de >> 8
            registers.E = de & 0xFF

            registers.condition.H = 0
            if bc != 0:
                registers.PC -= 2
                instruction.tstates = 21
            else:
                instruction.tstates = 16

            registers.condition.PV = 0
            registers.condition.N = 0
            registers.condition.F3 = (registers.A + data[0]) & 0x08
            registers.condition.F5 = (registers.A + data[0]) & 0x02
            return [(de_, data[0])]


    @instruction([(0xEDA1, ())], 0, "CPI", 16)
    def cpi(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            registers.HL = inc16(registers.HL)
            registers.BC = dec16(registers.BC)

            subtract8(registers.A, data[0], registers)
            registers.condition.PV = registers.BC != 0
            # F3 is bit 3 of (A - (HL) - H), H 
            # F5 is bit 1 of (A - (HL) - H), H a
            f5f3 = registers.A - data[0] -  registers.H
            registers.condition.F5 = f5f3 & 0x01
            registers.condition.F3 = f5f3 & 0x04
            return []

    @instruction([(0xEDB1, ())], 0, "CPIR", 16)
    def cpir(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            registers.HL = inc16(registers.HL)
            registers.BC = dec16(registers.BC)

            res = subtract8(registers.A, data[0], registers)

            if registers.BC != 0 and res != 0:
                registers.PC -= 2
                instruction.tstates = 21
            else:
                instruction.tstates = 16
            registers.condition.PV = registers.BC != 0
            return []

    @instruction([(0xEDA9, ())], 0, "CPD", 16)
    def cpd(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            registers.HL = dec16(registers.HL)
            registers.BC = dec16(registers.BC)

            subtract8(registers.A, data[0], registers)
            registers.condition.PV = registers.BC != 0
            return []

    @instruction([(0xEDB9, ())], 0, "CPDR", 16)
    def cpdr(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            registers.HL = dec16(registers.HL)
            registers.BC = dec16(registers.BC)

            res = subtract8(registers.A, data[0], registers)

            if registers.BC != 0 and res != 0:
                registers.PC -= 2
                instruction.tstates = 21
            else:
                instruction.tstates = 16
            registers.condition.PV = registers.BC != 0
            return []

    #----------------------------------------------------------------------
    # 8-Bit Arithmetic Group
    #----------------------------------------------------------------------
    #---- ADD ----
    @instruction([(0x87, ("A",)), (0x80, ("B",)), (0x81, ("C",)),
                  (0x82, ("D",)), (0x83, ("E",)), (0x84, ("H",)),
                  (0x85, ("L",)),
                  (0xDD87, ("A",), 8), (0xDD80, ("B",), 8), (0xDD81, ("C",), 8),
                  (0xDD82, ("D",), 8), (0xDD83, ("E",), 8), (0xDD84, ("IXH",), 8),
                  (0xDD85, ("IXL",), 8),
                  (0xFD87, ("A",), 8), (0xFD80, ("B",), 8), (0xFD81, ("C",), 8),
                  (0xFD82, ("D",), 8), (0xFD83, ("E",), 8), (0xFD84, ("IYH",), 8),
                  (0xFD85, ("IYL",), 8)], 0, "ADD A, {0}", 4)
    def add_a_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            registers.A = add8(registers.A, registers[r], registers)
            return []

    @instruction([([0xC6, '-'], ())], 1, "ADD A, {0:X}H", 7)
    def add_a_n(instruction, registers, get_reads, data, n):
        if get_reads:
            return []
        else:
            registers.A = add8(registers.A, n, registers)
            return []


    @instruction([(0x86, ())], 0, "ADD A, (HL)", 7)
    def add_a_hl_(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            registers.A = add8(registers.A, data[0], registers)
            return []

    @instruction([([0xDD, 0x86, '-'], ("IX",)),
                  ([0xFD, 0x86, '-'], ("IY",))], 1, "ADD A, ({0}+{1:X}H)", 19)
    def add_a_i_(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            registers.A = add8(registers.A, data[0], registers)
            return []

    #---- ADC ----
    @instruction([(0x8f, ("A",)), (0x88, ("B",)), (0x89, ("C",)),
                  (0x8A, ("D",)), (0x8B, ("E",)), (0x8C, ("H",)),
                  (0x8D, ("L",)),
                  (0xDD8f, ("A",), 8), (0xDD88, ("B",), 8), (0xDD89, ("C",), 8),
                  (0xDD8A, ("D",), 8), (0xDD8B, ("E",), 8), (0xDD8C, ("IXH",), 8),
                  (0xDD8D, ("IXL",), 8),
                  (0xFD8f, ("A",), 8), (0xFD88, ("B",), 8), (0xFD89, ("C",), 8),
                  (0xFD8A, ("D",), 8), (0xFD8B, ("E",), 8), (0xFD8C, ("IYH",), 8),
                  (0xFD8D, ("IYL",), 8)], 0, "ADC A, {0}", 4)
    def adc_a_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            registers.A = add8(registers.A + registers.condition.C, registers[r], registers)
            return []

    @instruction([([0xCE, '-'], ())], 1, "ADC A, {0:X}H", 7)
    def adc_a_n(instruction, registers, get_reads, data, n):
        if get_reads:
            return []
        else:
            registers.A = add8(registers.A + registers.condition.C, n, registers)
            return []


    @instruction([(0x8E, ())], 0, "ADC A, (HL)", 7)
    def adc_a_hl_(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            registers.A = add8(registers.A + registers.condition.C, data[0], registers)
            return []

    @instruction([([0xDD, 0x8E, '-'], ("IX",)),
                  ([0xFD, 0x8E, '-'], ("IY",))], 1, "ADC A, ({0}+{1:X}H)", 19)
    def adc_a_i_(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            registers.A = add8(registers.A + registers.condition.C, data[0], registers)
            return []

    #---- SUB ----
    @instruction([(0x97, ("A",)), (0x90, ("B",)), (0x91, ("C",)),
                  (0x92, ("D",)), (0x93, ("E",)), (0x94, ("H",)),
                  (0x95, ("L",)),
                  (0xDD97, ("A",), 8), (0xDD90, ("B",), 8), (0xDD91, ("C",), 8),
                  (0xDD92, ("D",), 8), (0xDD93, ("E",), 8), (0xDD94, ("IXH",), 8),
                  (0xDD95, ("IXL",), 8),
                  (0xFD97, ("A",), 8), (0xFD90, ("B",), 8), (0xFD91, ("C",), 8),
                  (0xFD92, ("D",), 8), (0xFD93, ("E",), 8), (0xFD94, ("IYH",), 8),
                  (0xFD95, ("IYL",), 8)], 0, "SUB A, {0}", 4)
    def sub_a_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            registers.A = subtract8_check_overflow(registers.A, registers[r], registers)
            return []

    @instruction([([0xD6, '-'], ())], 1, "SUB A, {0:X}H", 7)
    def sub_a_n(instruction, registers, get_reads, data, n):
        if get_reads:
            return []
        else:
            registers.A = subtract8_check_overflow(registers.A, n, registers)
            return []


    @instruction([(0x96, ())], 0, "SUB A, (HL)", 7)
    def sub_a_hl_(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            registers.A = subtract8_check_overflow(registers.A, data[0], registers)
            return []

    @instruction([([0xDD, 0x96, '-'], ("IX",)),
                  ([0xFD, 0x96, '-'], ("IY",))], 1, "SUB A, ({0}+{1:X}H)", 19)
    def sub_a_i_(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            registers.A = subtract8_check_overflow(registers.A, data[0], registers)
            return []

    #---- SBC ----
    @instruction([(0x9f, ("A",)), (0x98, ("B",)), (0x99, ("C",)),
                  (0x9A, ("D",)), (0x9B, ("E",)), (0x9C, ("H",)),
                  (0x9D, ("L",)),
                  (0xDD9f, ("A",), 8), (0xDD98, ("B",), 8), (0xDD99, ("C",), 8),
                  (0xDD9A, ("D",), 8), (0xDD9B, ("E",), 8), (0xDD9C, ("IXH",), 8),
                  (0xDD9D, ("IXL",), 8),
                  (0xFD9f, ("A",), 8), (0xFD98, ("B",), 8), (0xFD99, ("C",), 8),
                  (0xFD9A, ("D",), 8), (0xFD9B, ("E",), 8), (0xFD9C, ("IYH",), 8),
                  (0xFD9D, ("IYL",), 8)], 0, "SBC A, {0}", 4)
    def sbc_a_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            registers.A = subtract8_check_overflow(registers.A - registers.condition.C, registers[r], registers)
            return []

    @instruction([([0xDE, '-'], ())], 1, "SBC A, {0:X}H", 7)
    def sbc_a_n(instruction, registers, get_reads, data, n):
        if get_reads:
            return []
        else:
            registers.A = subtract8_check_overflow(registers.A - registers.condition.C, n, registers)
            return []


    @instruction([(0x9E, ())], 0, "SBC A, (HL)", 7)
    def sbc_a_hl_(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            registers.A = subtract8_check_overflow(registers.A - registers.condition.C, data[0], registers)
            return []

    @instruction([([0xDD, 0x9E, '-'], ("IX",)),
                  ([0xFD, 0x9E, '-'], ("IY",))], 1, "SBC A, ({0}+{1:X}H)", 19)
    def sbc_a_i_(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            registers.A = subtract8_check_overflow(registers.A - registers.condition.C, data[0], registers)
            return []

    #---- AND ----
    @instruction([(0xa7, ("A",)), (0xa0, ("B",)), (0xa1, ("C",)),
                  (0xa2, ("D",)), (0xa3, ("E",)), (0xa4, ("H",)),
                  (0xa5, ("L",)),
                  (0xDDa7, ("A",), 8), (0xDDa0, ("B",), 8), (0xDDa1, ("C",), 8),
                  (0xDDa2, ("D",), 8), (0xDDa3, ("E",), 8), (0xDDa4, ("IXH",), 8),
                  (0xDDa5, ("IXL",), 8),
                  (0xFDa7, ("A",), 8), (0xFDa0, ("B",), 8), (0xFDa1, ("C",), 8),
                  (0xFDa2, ("D",), 8), (0xFDa3, ("E",), 8), (0xFDa4, ("IYH",), 8),
                  (0xFDa5, ("IYL",), 8)], 0, "AND {0}", 4)
    def and_a_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            a_and_n(registers, registers[r])
            registers.condition.S = (registers.A >> 7)
            return []

    @instruction([([0xe6, '-'], ())], 1, "AND {0:X}H", 7)
    def and_a_n(instruction, registers, get_reads, data, n):
        if get_reads:
            return []
        else:
            a_and_n(registers, n)
            return []


    @instruction([(0xa6, ())], 0, "AND (HL)", 7)
    def and_a_hl_(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            a_and_n(registers, data[0])
            return []

    @instruction([([0xDD, 0xA6, '-'], ("IX",)),
                  ([0xFD, 0xA6, '-'], ("IY",))], 1, "AND ({0}+{1:X}H)", 19)
    def and_a_i_(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            a_and_n(registers, data[0])
            return []

    #---- OR ----
    @instruction([(0xb7, ("A",)), (0xb0, ("B",)), (0xb1, ("C",)),
                  (0xb2, ("D",)), (0xb3, ("E",)), (0xb4, ("H",)),
                  (0xb5, ("L",)),
                  (0xDDb7, ("A",), 8), (0xDDb0, ("B",), 8), (0xDDb1, ("C",), 8),
                  (0xDDb2, ("D",), 8), (0xDDb3, ("E",), 8), (0xDDb4, ("IXH",), 8),
                  (0xDDb5, ("IXL",), 8),
                  (0xFDb7, ("A",), 8), (0xFDb0, ("B",), 8), (0xFDb1, ("C",), 8),
                  (0xFDb2, ("D",), 8), (0xFDb3, ("E",), 8), (0xFDb4, ("IYH",), 8),
                  (0xFDb5, ("IYL",), 8)], 0, "OR {0}", 4)
    def or_a_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            a_or_n(registers, registers[r])
            registers.condition.S = (registers.A >> 7)
            return []

    @instruction([([0xf6, '-'], ())], 1, "OR {0:X}H", 7)
    def or_a_n(instruction, registers, get_reads, data, n):
        if get_reads:
            return []
        else:
            a_or_n(registers, n)
            return []


    @instruction([(0xb6, ())], 0, "OR (HL)", 7)
    def or_a_hl_(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            a_or_n(registers, data[0])
            return []

    @instruction([([0xDD, 0xB6, '-'], ("IX",)),
                  ([0xFD, 0xB6, '-'], ("IY",))], 1, "OR ({0}+{1:X}H)", 19)
    def or_a_i_(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            a_or_n(registers, data[0])
            return []

    #---- XOR ----
    @instruction([(0xaf, ("A",)), (0xa8, ("B",)), (0xa9, ("C",)),
                  (0xaa, ("D",)), (0xab, ("E",)), (0xac, ("H",)),
                  (0xad, ("L",)),
                  (0xDDaf, ("A",), 8), (0xDDa8, ("B",), 8), (0xDDa9, ("C",), 8),
                  (0xDDaa, ("D",), 8), (0xDDab, ("E",), 8), (0xDDac, ("IXH",), 8),
                  (0xDDad, ("IXL",), 8),
                  (0xFDaf, ("A",), 8), (0xFDa8, ("B",), 8), (0xFDa9, ("C",), 8),
                  (0xFDaa, ("D",), 8), (0xFDab, ("E",), 8), (0xFDac, ("IYH",), 8),
                  (0xFDad, ("IYL",), 8)], 0, "XOR {0}", 4)
    def xor_a_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            a_xor_n(registers, registers[r])
            registers.condition.S = (registers.A >> 7)
            return []

    @instruction([([0xee, '-'], ())], 1, "XOR {0:X}H", 7)
    def xor_a_n(instruction, registers, get_reads, data, n):
        if get_reads:
            return []
        else:
            a_xor_n(registers, n)
            return []


    @instruction([(0xae, ())], 0, "XOR (HL)", 7)
    def xor_a_hl_(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            a_xor_n(registers, data[0])
            return []

    @instruction([([0xDD, 0xAE, '-'], ("IX",)),
                  ([0xFD, 0xAE, '-'], ("IY",))], 1, "XOR ({0}+{1:X}H)", 19)
    def xor_a_i_(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            a_xor_n(registers, data[0])
            return []

    #---- CP ----
    @instruction([(0xbf, ("A",)), (0xb8, ("B",)), (0xb9, ("C",)),
                  (0xba, ("D",)), (0xbb, ("E",)), (0xbc, ("H",)),
                  (0xbd, ("L",)),
                  (0xDDbf, ("A",), 8), (0xDDb8, ("B",), 8), (0xDDb9, ("C",), 8),
                  (0xDDba, ("D",), 8), (0xDDbb, ("E",), 8), (0xDDbc, ("IXH",), 8),
                  (0xDDbd, ("IXL",), 8),
                  (0xFDbf, ("A",), 8), (0xFDb8, ("B",), 8), (0xFDb9, ("C",), 8),
                  (0xFDba, ("D",), 8), (0xFDbb, ("E",), 8), (0xFDbc, ("IYH",), 8),
                  (0xFDbd, ("IYL",), 8)], 0, "CP {0}", 4)
    def cp_a_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            subtract8_check_overflow(registers.A, registers[r], registers)
            set_f5_f3(registers, registers[r])
            return []

    @instruction([([0xfe, '-'], ())], 1, "CP {0:X}H", 7)
    def cp_a_n(instruction, registers, get_reads, data, n):
        if get_reads:
            return []
        else:
            subtract8_check_overflow(registers.A, n, registers)
            set_f5_f3(registers, n)
            return []


    @instruction([(0xbe, ())], 0, "CP (HL)", 7)
    def cp_a_hl_(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            subtract8_check_overflow(registers.A, data[0], registers)
            set_f5_f3(registers, data[0])
            return []

    @instruction([([0xDD, 0xBE, '-'], ("IX",)),
                  ([0xFD, 0xBE, '-'], ("IY",))], 1, "CP ({0}+{1:X}H)", 19)
    def cp_a_i_(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            subtract8_check_overflow(registers.A, data[0], registers)
            set_f5_f3(registers, data[0])
            return []

    #---- INC s ----    
    @instruction([(0x3c, ("A",)), (0x04, ("B",)), (0x0c, ("C",)),
                  (0x14, ("D",)), (0x1c, ("E",)), (0x24, ("H",)),
                  (0x2c, ("L",)),
                  (0xDD3c, ("A",), 8), (0xDD04, ("B",), 8), (0xDD0c, ("C",), 8),
                  (0xDD14, ("D",), 8), (0xDD1c, ("E",), 8), (0xDD24, ("IXH",), 8),
                  (0xDD2c, ("IXL",), 8),
                  (0xFD3c, ("A",), 8), (0xFD04, ("B",), 8), (0xFD0c, ("C",), 8),
                  (0xFD14, ("D",), 8), (0xFD1c, ("E",), 8), (0xFD24, ("IYH",), 8),
                  (0xFD2c, ("IYL",), 8)], 0, "INC {0}", 4)
    def inc_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            registers[r] = add8(registers[r], 1, registers, C=False )
            return []

    @instruction([(0x34, ())], 0, "INC (HL)", 11)
    def inc_hl_(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            new = add8(data[0], 1, registers, C=False )
            return [(registers.HL, new)]

    @instruction([([0xDD, 0x34, '-'], ("IX",)),
                  ([0xFD, 0x34, '-'], ("IY",))], 1, "INC ({0}+{1:X}H)", 23)
    def inc_i_(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            new = add8(data[0], 1, registers, C=False )
            return [(registers.HL, new)]


    #---- DEC s ----
    @instruction([(0x3d, ("A",)), (0x05, ("B",)), (0x0d, ("C",)),
                  (0x15, ("D",)), (0x1d, ("E",)), (0x25, ("H",)),
                  (0x2d, ("L",)),
                  (0xDD3d, ("A",), 8), (0xDD05, ("B",), 8), (0xDD0d, ("C",), 8),
                  (0xDD15, ("D",), 8), (0xDD1d, ("E",), 8), (0xDD25, ("IXH",), 8),
                  (0xDD2d, ("IXL",), 8),
                  (0xFD3d, ("A",), 8), (0xFD05, ("B",), 8), (0xFD0d, ("C",), 8),
                  (0xFD15, ("D",), 8), (0xFD1d, ("E",), 8), (0xFD25, ("IYH",), 8),
                  (0xFD2d, ("IYL",), 8)], 0, "DEC {0}", 4)
    def dec_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            registers.condition.PV = registers[r] == 0x80
            registers[r] = subtract8(registers[r], 1, registers,
                                     PV=False)
            
            return []

    @instruction([(0x35, ())], 0, "DEC (HL)", 11)
    def dec_hl_(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            new = subtract8(data[0], 1, registers,
                                     PV=False)
            if data[0] == 0x80:
                registers.condition.PV = 1
            else:
                registers.condition.PV = 0
                
            return [(registers.HL, new)]

    @instruction([([0xDD, 0x35, '-'], ("IX",)),
                  ([0xFD, 0x35, '-'], ("IY",))], 1, "DEC ({0}+{1:X}H)", 23)
    def dec_i_(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            new = subtract8(data[0], 1, registers,
                                     PV=False)
            if data[0] == 0x80:
                registers.condition.PV = 1
            else:
                registers.condition.PV = 0
            return [(registers[i] + get_8bit_twos_comp(d), new)]

    #--------------------------------------------------------------------
    # General-Purpose Arithmetic and CPU Control Groups
    #--------------------------------------------------------------------
    @instruction([(0x27, ())], 0, "DAA", 4)
    def daa(instruction, registers, get_reads, data):
        if get_reads:
            return []
        else:
            # https://raine.1emulation.com/archive/dev/z80-documented.pdf
            # (The Undocumented Z80 Documented)
            hn = (registers.A & 0xF0) >> 4 # high nibble
            ln = registers.A & 0x0F # low nibble

           # Flag C
            if (registers.condition.C == 0):
                if (
                    ((hn >= 0x09) & (ln >= 0x0A)) |
                    ((hn >= 0x0A) & (ln <= 0x09))
                ): c_ = 1
                else: c_ = 0
            else: c_ = 1
            
            # Flag H
            if (registers.condition.N == 0):
                if (ln < 0x0A): h_ = 0
                else: h_ = 1
            else:
                if (registers.condition.H == 0): h_ = 0
                else:
                    if (ln < 0x06): h_ = 1
                    else: h_ = 0
            
            # Calculate diff
            diff = 0
            if (registers.condition.C == 0):
                if ((hn <= 0x09) & (ln <= 0x09) & (registers.condition.H == 0)): diff = 0x00
                elif ((hn <= 0x09) & (ln <= 0x09) & (registers.condition.H == 1)): diff = 0x06
                elif ((hn <= 0x08) & (ln >= 0x0A)): diff = 0x06
                elif ((hn >= 0x0A) & (ln <= 0x09) & (registers.condition.H == 0)): diff = 0x60
                elif ((hn >= 0x09) & (ln >= 0x0A)): diff = 0x66
                elif ((hn >= 0x0A) & (ln <= 0x09) & (registers.condition.H == 1)): diff = 0x66
            else:
                if ((ln <= 0x09) & (registers.condition.H == 0)): diff = 0x60
                elif ((ln <= 0x09) & (registers.condition.H == 1)): diff = 0x66
                elif (ln >= 0x0A): diff = 0x66

            if registers.condition.N == 1:
                registers.A = get_8bit_twos_comp((registers.A - diff)) & 0xFF
            else:
                registers.A = (registers.A + diff) & 0xFF

            registers.condition.C = c_
            registers.condition.H = h_
            registers.condition.S = registers.A >> 7
            registers.condition.Z = (registers.A == 0)
            registers.condition.PV = parity(registers.A)
            set_f5_f3_from_a(registers)
            return []

    @instruction([(0x2F, ())], 0, "CPL", 4)
    def cpl(instruction, registers, get_reads, data):
        if get_reads:
            return []
        else:
            registers.A = 0xFF ^ registers.A
            registers.condition.N = 1
            registers.condition.H = 1
            set_f5_f3_from_a(registers)
            return []


    @instruction([(0xED44, ())], 0, "NEG", 8)
    def neg(instruction, registers, get_reads, data):
        if get_reads:
            return []
        else:
            registers.A = subtract8_check_overflow(0, registers.A, registers)
            return []

    @instruction([(0x3F, ())], 0, "CCF", 4)
    def ccf(instruction, registers, get_reads, data):
        if get_reads:
            return []
        else:
            registers.condition.H = registers.condition.C
            registers.condition.N = 0
            registers.condition.C = not registers.condition.C
            set_f5_f3_from_a(registers)
            return []

    @instruction([(0x37, ())], 0, "SCF", 4)
    def scf(instruction, registers, get_reads, data):
        if get_reads:
            return []
        else:
            registers.condition.H = 0
            registers.condition.N = 0
            registers.condition.C = 1
            set_f5_f3_from_a(registers)
            return []

    @instruction([(0x00, ())], 0, "NOP", 4)
    def nop(instruction, registers, get_reads, data):
        if get_reads:
            return []
        else:
            return []

    @instruction([(0x76, ())], 0, "HALT", 4)
    def halt(instruction, registers, get_reads, data):
        if get_reads:
            return []
        else:
            registers.HALT = True
            registers.PC -= 1
            return []


    @instruction([(0xF3, ())], 0, "DI", 4)
    def di(instruction, registers, get_reads, data):
        if get_reads:
            return []
        else:
            registers.IFF = False
            registers.IFF2 = False
            return []

    @instruction([(0xFB, ())], 0, "EI", 4)
    def ei(instruction, registers, get_reads, data):
        if get_reads:
            return []
        else:
            registers.IFF = True
            registers.IFF2 = True
            return []

    @instruction([(0xED46, (0,)), (0xED56, (1,)), (0xED5E, (2,))], 0, "IM {}", 8)
    def im(instruction, registers, get_reads, data, mode):
        if get_reads:
            return []
        else:
            registers.IM = mode
            return []        


    #--------------------------------------------------------------------
    # 16-Bit Arithmetic Group
    #--------------------------------------------------------------------
    @instruction([(0x39, ("SP",)), (0x09, ("BC",)), (0x19, ("DE",)),(0x29, ("HL",))], 0, "ADD HL, {0}", 11)
    def add16_hl(instruction, registers, get_reads, data, reg):
        if get_reads:
            return []
        else:
            val = registers.HL + getattr(registers, reg)
            dummy_reg = registers.create()
            add8(registers.HL & 0xFF, getattr(registers, reg) & 0xFF, dummy_reg, PV=True)
            registers.condition.H = dummy_reg.condition.C
            add8(registers.HL >> 8, getattr(registers, reg) >> 8, dummy_reg, PV=True)
            registers.condition.F3 = dummy_reg.condition.F3
            registers.condition.F5 = dummy_reg.condition.F5
            registers.condition.N = 0
            registers.condition.C = val > 0xFFFF
            registers.HL = val & 0xFFFF
            return []

    @instruction([(0xED7A, ("SP",)), (0xED4A, ("BC",)), (0xED5A, ("DE",)),(0xED6A, ("HL",))], 0, "ADC HL, {0}", 15)
    def adc16_hl(instruction, registers, get_reads, data, reg):
        if get_reads:
            return []
        else:
            registers.HL = add16(registers.HL + registers.condition.C, getattr(registers, reg), registers)

            return []
        
    @instruction([(0xED72, ("SP",)), (0xED42, ("BC",)), (0xED52, ("DE",)),(0xED62, ("HL",))], 0, "SBC HL, {0}", 15)
    def sbc16_hl(instruction, registers, get_reads, data, reg):
        if get_reads:
            return []
        else:
            a = registers.HL
            b = registers[reg]
            res = a - b
            if registers.condition.C:
                res -= 1
            registers.condition.S = (res >> 15) &  0x01
            registers.condition.N = 1
            registers.condition.Z = (res == 0)
            registers.condition.F3 = res & 0x0800
            registers.condition.F5 = res & 0x2000
            if (b & 0xFFF) > (a & 0xFFF) - registers.condition.C :
                registers.condition.H = 1
            else:
                registers.condition.H = 0
            
            pvtest = get_16bit_twos_comp(a) -  get_16bit_twos_comp(b) -  registers.condition.C
            if pvtest < -32768 or pvtest > 32767:
                registers.condition.PV = 1 # overflow
            else:
                registers.condition.PV = 0
        
            registers.condition.C = res > 0xFFFF or res < 0
            registers.HL = res &  0xFFFF

            return []

    @instruction([(0xDD39, ("IX", "SP",)), (0xDD09, ("IX", "BC",)), (0xDD19, ("IX", "DE",)),(0xDD29, ("IX", "IX",)),
                  (0xFD39, ("IY", "SP",)), (0xFD09, ("IY", "BC",)), (0xFD19, ("IY", "DE",)),(0xFD29, ("IY", "IY",))],
                 0, "ADD {0}, {1}", 15)
    def add16_i_pp(instruction, registers, get_reads, data, i, r):
        if get_reads:
            return []
        else:
            val = registers[i] + registers[r]
            if ((registers[i] & 0xFFF) + (registers[r] & 0xFFF)) > 0xFFF :
                registers.condition.H = 1
            else:
                registers.condition.H = 0
            registers.condition.N = 0
            registers.condition.C = val > 0xFFFF
            set_f5_f3(registers, (registers[i] >>8)+(registers[r]>>8))
            registers[i] = val & 0xFFFF
            return []


    @instruction([(0x33, ("SP",)), (0x03, ("BC",)), (0x13, ("DE",)),(0x23, ("HL",)),
                  (0xDD23, ("IX",), 10), (0xFD23, ("IY",), 10)],
                 0, "INC {0}", 6)
    def inc16_ss(instruction, registers, get_reads, data, s):
        if get_reads:
            return []
        else:
            registers[s] = inc16(registers[s])
            return []
        

    @instruction([(0x3b, ("SP",)), (0x0b, ("BC",)), (0x1b, ("DE",)),(0x2b, ("HL",)),
                  (0xDD2b, ("IX",), 10), (0xFD2b, ("IY",), 10)],
                 0, "DEC {0}", 6)
    def dec16_ss(instruction, registers, get_reads, data, s):
        if get_reads:
            return []
        else:
            registers[s] = dec16(registers[s])
            return []

    #--------------------------------------------------------------------
    # Rotate and Shift Group
    #--------------------------------------------------------------------
    @instruction([(0x07, ())], 0, "RLCA", 4)
    def rlca(instruction, registers, get_reads, data):
        if get_reads:
            return []
        else:
            c = registers.A >> 7
            registers.A = ((registers.A << 1) | c) & 0xFF
            registers.condition.C = c
            registers.condition.H = 0
            registers.condition.N = 0
            set_f5_f3_from_a(registers)
            return []

    @instruction([(0x17, ())], 0, "RLA", 4)
    def rla(instruction, registers, get_reads, data):
        if get_reads:
            return []
        else:
            c = registers.A >> 7
            pc = registers.condition.C
            registers.A = (registers.A << 1 | pc) & 0xFF
            registers.condition.C = c
            registers.condition.H = 0
            registers.condition.N = 0
            set_f5_f3_from_a(registers)
            return []

    @instruction([(0x0F, ())], 0, "RRCA", 4)
    def rrca(instruction, registers, get_reads, data):
        if get_reads:
            return []
        else:
            c = registers.A & 0x01
            registers.A = (registers.A >> 1 | c << 7) & 0xFF
            registers.condition.C = c
            registers.condition.H = 0
            registers.condition.N = 0
            set_f5_f3_from_a(registers)
            return []

    @instruction([(0x1F, ())], 0, "RRA", 4)
    def rra(instruction, registers, get_reads, data):
        if get_reads:
            return []
        else:
            c = registers.A & 0x01
            pc = registers.condition.C
            registers.A = (registers.A >> 1 | pc << 7) & 0xFF
            registers.condition.C = c
            registers.condition.H = 0
            registers.condition.N = 0
            set_f5_f3_from_a(registers)
            return []
        

    # RLC m    
    @instruction([(0xCB07, ("A", )), (0xCB00, ("B", )), (0xCB01, ("C", )), (0xCB02, ("D", )),
                  (0xCB03, ("E", )), (0xCB04, ("H", )), (0xCB05, ("L", ))],
                 0, "RLC {0}", 8)
    def rlc(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            registers[r] = rotate_left_carry(registers, registers[r])
            set_f5_f3(registers, registers[r])
            return []
        
    @instruction([(0xCB06, ( ))],
                 0, "RLC (HL)", 15)
    def rlc_hl_(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            val = rotate_left_carry(registers, data[0])
            set_f5_f3(registers, val)
            return [(registers.HL, val)]

        
    @instruction([([0xDD, 0xCB, '-', 0x06], ("IX", )),
                  ([0xFD, 0xCB, '-', 0x06], ("IY", ))],
                 2, "RLC ({0}+{1:X}H)", 23)
    def rlc_i_d(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            new = rotate_left_carry(registers, data[0])
            set_f5_f3(registers, new)
            return [(registers[i] + get_8bit_twos_comp(d), new)]
        
    # RL m
    @instruction([([0xCB, 0x10], ("B", )), ([0xCB, 0x11], ("C", )), ([0xCB, 0x12], ("D", )),
                  ([0xCB, 0x13], ("E", )), ([0xCB, 0x14], ("H", )), ([0xCB, 0x15], ("L", )),
                  ([0xCB, 0x17], ("A", ))],
                 2, "RL {0}", 8)
    def rl_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            registers[r] = rotate_left(registers, registers[r])
            set_f5_f3(registers, registers[r])
            return []
        
    @instruction([([0xCB, 0x16], ())],
                 2, "RL (HL)", 15)
    def rl_hl(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            val = rotate_left(registers, data[0])
            set_f5_f3(registers, val)
            return [(registers.HL, val)]
        
    @instruction([([0xDD, 0xCB, "-", 0x16], ("IX", )),
                  ([0xFD, 0xCB, "-", 0x16], ("IY", ))],
                 2, "RL ({0}+{1:X}H)", 23)
    def rl_i(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            val = rotate_left(registers, data[0])
            set_f5_f3(registers, val)
            return [(registers[i] + get_8bit_twos_comp(d), val)]
        
        



    
    # RRC m    
    @instruction([(0xCB0F, ("A", )), (0xCB08, ("B", )), (0xCB09, ("C", )), (0xCB0A, ("D", )),
                  (0xCB0B, ("E", )), (0xCB0C, ("H", )), (0xCB0D, ("L", ))],
                 0, "RRC {0}", 8)
    def rrc(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            registers[r] = rotate_right_carry(registers, registers[r])
            set_f5_f3(registers, registers[r])
            return []
        
    @instruction([(0xCB0E, ( ))],
                 0, "RRC (HL)", 15)
    def rrc_hl_(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            val = rotate_right_carry(registers, data[0])
            set_f5_f3(registers, val)
            return [(registers.HL, val)]

        
    @instruction([([0xDD, 0xCB, '-', 0x0E], ("IX", )),
                  ([0xFD, 0xCB, '-', 0x0E], ("IY", ))],
                 2, "RRC ({0}+{1:X}H)", 23)
    def rrc_i_d(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            new = rotate_right_carry(registers, data[0])
            set_f5_f3(registers, new)
            return [(registers[i] + get_8bit_twos_comp(d), new)]
        
    # RR m
    @instruction([([0xCB, 0x18], ("B", )), ([0xCB, 0x19], ("C", )), ([0xCB, 0x1A], ("D", )),
                  ([0xCB, 0x1B], ("E", )), ([0xCB, 0x1C], ("H", )), ([0xCB, 0x1D], ("L", )),
                  ([0xCB, 0x1F], ("A", ))],
                 2, "RR {0}", 8)
    def rr_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            registers[r] = rotate_right(registers, registers[r])
            set_f5_f3(registers, registers[r])
            return []
        
    @instruction([([0xCB, 0x1E], ())],
                 2, "RR (HL)", 15)
    def rr_hl(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            val = rotate_right(registers, data[0])
            set_f5_f3(registers, val)
            return [(registers.HL, val)]
        
    @instruction([([0xDD, 0xCB, "-", 0x1E], ("IX", )),
                  ([0xFD, 0xCB, "-", 0x1E], ("IY", ))],
                 2, "RR ({0}+{1:X}H)", 23)
    def rr_i(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            val = rotate_right(registers, data[0])
            set_f5_f3(registers, val)
            return [(registers[i] + get_8bit_twos_comp(d), val)]
        
        



       
    # SLA m    
    @instruction([(0xCB27, ("A", )), (0xCB20, ("B", )), (0xCB21, ("C", )), (0xCB22, ("D", )),
                  (0xCB23, ("E", )), (0xCB24, ("H", )), (0xCB25, ("L", ))],
                 0, "SLA {0}", 8)
    def sla_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            registers[r] = shift_left(registers, registers[r])
            set_f5_f3(registers, registers[r])
            return []
        
    @instruction([(0xCB26, ( ))],
                 0, "SLA (HL)", 15)
    def sla_hl_(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            val = shift_left(registers, data[0])
            set_f5_f3(registers, val)
            return [(registers.HL, val)]

        
    @instruction([([0xDD, 0xCB, '-', 0x26], ("IX", )),
                  ([0xFD, 0xCB, '-', 0x26], ("IY", ))],
                 2, "SLA ({0}+{1:X}H)", 23)
    def sla_i_d(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            new = shift_left(registers, data[0])
            set_f5_f3(registers, new)
            return [(registers[i] + get_8bit_twos_comp(d), new)]


    # SLL m    
    @instruction([(0xCB37, ("A", )), (0xCB30, ("B", )), (0xCB31, ("C", )), (0xCB32, ("D", )),
                  (0xCB33, ("E", )), (0xCB34, ("H", )), (0xCB35, ("L", ))],
                 0, "SLL {0}", 8)
    def sll_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            registers[r] = shift_left_logical(registers, registers[r])
            set_f5_f3(registers, registers[r])
            return []
        
    @instruction([(0xCB36, ( ))],
                 0, "SLL (HL)", 15)
    def sll_hl_(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            val = shift_left_logical(registers, data[0])
            set_f5_f3(registers, val)
            return [(registers.HL, val)]

        
    @instruction([([0xDD, 0xCB, '-', 0x36], ("IX", )),
                  ([0xFD, 0xCB, '-', 0x36], ("IY", ))],
                 2, "SLL ({0}+{1:X}H)", 23)
    def sll_i_d(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            new = shift_left_logical(registers, data[0])
            set_f5_f3(registers, new)
            return [(registers[i] + get_8bit_twos_comp(d), new)]


    # SRA m
    @instruction([([0xCB, 0x28], ("B", )), ([0xCB, 0x29], ("C", )), ([0xCB, 0x2A], ("D", )),
                  ([0xCB, 0x2B], ("E", )), ([0xCB, 0x2C], ("H", )), ([0xCB, 0x2D], ("L", )),
                  ([0xCB, 0x2F], ("A", ))],
                 2, "SRA {0}", 8)
    def sra_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            registers[r] = shift_right(registers, registers[r])
            set_f5_f3(registers, registers[r])
            return []
        
    @instruction([([0xCB, 0x2E], ())],
                 2, "SRA (HL)", 15)
    def sra_hl(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            val = shift_right(registers, data[0])
            set_f5_f3(registers, val)
            return [(registers.HL, val)]
        
    @instruction([([0xDD, 0xCB, "-", 0x2E], ("IX", )),
                  ([0xFD, 0xCB, "-", 0x2E], ("IY", ))],
                 2, "SRA ({0}+{1:X}H)", 23)
    def sra_i(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            val = shift_right(registers, data[0])
            set_f5_f3(registers, val)
            return [(registers[i] + get_8bit_twos_comp(d), val)]
        

    # SRL m
    @instruction([([0xCB, 0x38], ("B", )), ([0xCB, 0x39], ("C", )), ([0xCB, 0x3A], ("D", )),
                  ([0xCB, 0x3B], ("E", )), ([0xCB, 0x3C], ("H", )), ([0xCB, 0x3D], ("L", )),
                  ([0xCB, 0x3F], ("A", ))],
                 2, "SRL {0}", 8)
    def srl_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            registers[r] = shift_right_logical(registers, registers[r])
            set_f5_f3(registers, registers[r])
            return []
        
    @instruction([([0xCB, 0x3E], ())],
                 2, "SRL (HL)", 15)
    def srl_hl(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            val = shift_right_logical(registers, data[0])
            set_f5_f3(registers, val)
            return [(registers.HL, val)]
        
    @instruction([([0xDD, 0xCB, "-", 0x3E], ("IX", )),
                  ([0xFD, 0xCB, "-", 0x3E], ("IY", ))],
                 2, "SRL ({0}+{1:X}H)", 23)
    def srl_i(instruction, registers, get_reads, data, i, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            val = shift_right_logical(registers, data[0])
            set_f5_f3(registers, val)
            return [(registers[i] + get_8bit_twos_comp(d), val)]

        
    @instruction([([0xED, 0x6F], ())],
                 2, "RLD", 18)
    def rld(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            a = (data[0] >> 4) | (registers.A & 0xF0)
            hl = ((registers.HL << 4) | (registers.A & 0x0f)) & 0xFF
            registers.A = a
            registers.condition.S = a >> 7
            registers.condition.Z = a == 0
            registers.condition.H = 0
            registers.condition.N = 0
            registers.condition.PV = parity(a)
            set_f5_f3(registers, registers.A)
            return [(registers.HL, hl)]
        
    @instruction([([0xED, 0x67], ())],
                 2, "RRD", 18)
    def rrd(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            a = (data[0] & 0x0F) | (registers.A & 0xF0)
            hl = ((registers.HL >> 4) | (registers.A << 4))  & 0xFF
            registers.A = a
            registers.condition.S = a >> 7
            registers.condition.Z = a == 0
            registers.condition.H = 0
            registers.condition.N = 0
            registers.condition.PV = parity(a)
            set_f5_f3(registers, registers.A)
            return [(registers.HL, hl)]



    
    #--------------------------------------------------------------------
    # Bit Set, Reset, and Test Group
    #--------------------------------------------------------------------
    @instruction([ ([0xCB, 0x40 + (b << 3) + register_bits[reg]], (b, reg))
                   for b in range(8)
                   for reg in ['A', 'B', 'C', 'D', 'E', 'H', 'L'] ] ,
                 2, "BIT {0}, {1}", 8)
    def bit_r(instruction, registers, get_reads, data, bit, reg):
        if get_reads:
            return []
        else:
            # print "Test bit ", bit
            registers.condition.Z = (registers[reg] & (0x01 << bit)) == 0
            registers.condition.H = 1
            registers.condition.N = 0
            registers.condition.PV = registers.condition.Z
            if bit == 7:
                registers.condition.S = (registers[reg] & (0x01 << bit))
            #if bit == 5:
                #registers.condition.F5 = (registers[reg] & (0x01 << bit))
            #if bit == 3:
                #registers.condition.F3 = (registers[reg] & (0x01 << bit))
            set_f5_f3(registers, registers[reg])
            return []

    @instruction( [ ([0xCB, 0x40 + (b << 3) + 6], (b,)) for b in range(8) ] ,
                 2, "BIT {0}, (HL)", 12)
    def bit_hl(instruction, registers, get_reads, data, bit):
        if get_reads:
            return [registers.HL]
        else:
            registers.condition.Z = (data[0] & (0x01 << bit)) == 0
            registers.condition.H = 1
            registers.condition.N = 0
            registers.condition.PV = registers.condition.Z
            if bit == 7:
                registers.condition.S = (data[0] & (0x01 << bit))
            set_f5_f3(registers, data[0])
            return []

    @instruction( [ ([I, 0xCB, '-', 0x40 + (b << 3) + 6], (Ir, b,)) for b in range(8) for I, Ir in index_bytes] ,
                 2, "BIT {1}, ({0}+{2:X}H)", 20)
    def bit_i(instruction, registers, get_reads, data, i, bit, d):
        if get_reads:
            return [registers[i]+get_8bit_twos_comp(d)]
        else:
            registers.condition.Z = (data[0] & (0x01 << bit)) == 0
            registers.condition.H = 1
            registers.condition.N = 0
            registers.condition.PV = registers.condition.Z
            if bit == 7:
                registers.condition.S = (data[0] & (0x01 << bit))
            else:
                registers.condition.S = 0
            set_f5_f3(registers, (registers[i]+get_8bit_twos_comp(d)) >> 8)
            return []

    @instruction([ ([0xCB, 0xc0 + (b << 3) + register_bits[reg]], (b, reg))
                   for b in range(8)
                   for reg in ['A', 'B', 'C', 'D', 'E', 'H', 'L'] ] ,
                 2, "SET {0}, {1}", 8)
    def set_r(instruction, registers, get_reads, data, bit, reg):
        if get_reads:
            return []
        else:
            registers[reg] |= (0x01 << bit)
            return []

    @instruction( [ ([0xCB, 0xc0 + (b << 3) + 6], (b,)) for b in range(8) ] ,
                 2, "SET {0}, (HL)", 15)
    def set_hl(instruction, registers, get_reads, data, bit):
        if get_reads:
            return [registers.HL]
        else:
            val = data[0] | (0x01 << bit)
            return [(registers.HL, val)]

    @instruction( [ ([I, 0xCB, '-', 0xc0 + (b << 3) + 6], (Ir, b,))
                    for b in range(8)
                    for I, Ir in index_bytes] ,
                 2, "SET {1}, ({0}+{2:X}H)", 23)
    def set_i(instruction, registers, get_reads, data, i, bit, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            val = data[0] | (0x01 << bit)
            return [(registers[i] + get_8bit_twos_comp(d), val)]

    @instruction([ ([0xCB, 0x80 + (b << 3) + register_bits[reg]], (b, reg))
                   for b in range(8)
                   for reg in ['A', 'B', 'C', 'D', 'E', 'H', 'L'] ] ,
                 2, "RES {0}, {1}", 8)
    def res_r(instruction, registers, get_reads, data, bit, reg):
        if get_reads:
            return []
        else:
            registers[reg] &= ~(0x01 << bit)
            return []

    @instruction( [ ([0xCB, 0x80 + (b << 3) + 6], (b,))
                    for b in range(8) ] ,
                 2, "RES {0}, (HL)", 15)
    def res_hl(instruction, registers, get_reads, data, bit):
        if get_reads:
            return [registers.HL]
        else:
            val = data[0] & ~(0x01 << bit)
            return [(registers.HL, val)]

    @instruction( [ ([I, 0xCB, '-', 0x80 + (b << 3) + 6], (Ir, b,))
                    for b in range(8)
                    for I, Ir in index_bytes] ,
                 2, "RES {1}, ({0}+{2:X}H)", 23)
    def res_i(instruction, registers, get_reads, data, i, bit, d):
        if get_reads:
            return [registers[i] + get_8bit_twos_comp(d)]
        else:
            val = data[0] & ~(0x01 << bit)
            return [(registers[i] + get_8bit_twos_comp(d), val)]



    #--------------------------------------------------------------------
    # Jump Group
    #--------------------------------------------------------------------
    @instruction([([0xC3, '-', '-'], ())],
                 2, "JP {1:X}{0:X}H", 10)
    def jp(instruction, registers, get_reads, data, n, n2):
        if get_reads:
            return []
        else:
            registers.PC = n2 << 8 | n
            return []
        

    @instruction([([0xC2+offset, '-', '-'], (reg, reg_name, val))
                  for offset, reg_name, reg, val in conditions],
                 2, "JP {1}, {4:x}{3:X}H", 10)
    def jp_c(instruction, registers, get_reads, data, reg, reg_name, val, n, n2):
        if get_reads:
            return []
        else:
            if getattr(registers.condition, reg) == val:
                registers.PC = n2 << 8 | n
            return []
              

    
    @instruction([([0x18, '-'], ())],
                 2, "JR {0:X}H", 12)
    def jr(instruction, registers, get_reads, data, n):
        if get_reads:
            return []
        else:
            offset_pc(registers, n)
            return []
    
    @instruction([([0x20, '-'], ())],
                 2, "JR NZ, {0:X}H", 12)
    def jr_nz(instruction, registers, get_reads, data, n):
        if get_reads:
            return []
        else:
            if not registers.condition.Z:
                offset_pc(registers, n)
                instruction.tstates = 12
            else:
                instruction.tstates = 7
            return []
        
         
    @instruction([([0x28, '-'], ())],
                 2, "JR Z, {0:X}H", 12)
    def jr_z(instruction, registers, get_reads, data, n):
        if get_reads:
            return []
        else:
            if registers.condition.Z:
                offset_pc(registers, n)
                instruction.tstates = 12
            else:
                instruction.tstates = 7
            return []
        
         
    @instruction([([0x30, '-'], ())],
                 2, "JR NC, {0:X}H", 12)
    def jr_nc(instruction, registers, get_reads, data, n):
        if get_reads:
            return []
        else:
            if not registers.condition.C:
                offset_pc(registers, n)
                instruction.tstates = 12
            else:
                instruction.tstates = 7
            return []
        
         
    @instruction([([0x38, '-'], ())],
                 2, "JR C, {0:X}H", 12)
    def jr_c(instruction, registers, get_reads, data, n):
        if get_reads:
            return []
        else:
            if registers.condition.C:
                offset_pc(registers, n)
                instruction.tstates = 12
            else:
                instruction.tstates = 7
            return []
        
    @instruction([([0xE9], ("HL", )),([0xDD, 0xE9], ("IX", ), 8),([0xFD, 0xE9], ("IY", ), 8) ],
                 2, "JP ({})", 4)
    def jp_r(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            registers.PC = registers[r]
            return []
        
    @instruction([([0x10, '-'], ())],
                 2, "DJNZ {0:X}H", 13)
    def djnz(instruction, registers, get_reads, data, n):
        if get_reads:
            return []
        else:
            registers.B = dec8(registers.B)
            if not registers.B == 0:
                offset_pc(registers, n)
                instruction.tstates = 13
            else:
                instruction.tstates = 8
            return []
    
    #--------------------------------------------------------------------
    # Call And Return Group
    #--------------------------------------------------------------------
    @instruction([([0xCD, '-', '-'], ())],
                 2, "CALL {1:X}{0:X}H", 17)
    def call(instruction, registers, get_reads, data, n, n2):
        if get_reads:
            return []
        else:
            sp = registers.SP
            pc = registers.PC
            registers.SP = dec16(registers.SP)
            registers.SP = dec16(registers.SP)
            registers.PC = n2 << 8 | n
            return [(sp - 1, pc >> 8),
                    (sp - 2, pc & 0xFF)]
        
    @instruction([([0xC4+offset, '-', '-'], (reg, reg_name, val))
                  for offset, reg_name, reg, val in conditions],
                 2, "CALL {1}, {4:x}{3:X}H", 17)
    def call_c(instruction, registers, get_reads, data, reg, reg_name, val, n, n2):
        if get_reads:
            return []
        else:
            if getattr(registers.condition, reg) == val:
                instruction.tstates = 17
                sp = registers.SP
                pc = registers.PC
                registers.SP = dec16(registers.SP)
                registers.SP = dec16(registers.SP)
                registers.PC = n2 << 8 | n
                return [(sp - 1, pc >> 8),
                        (sp - 2, pc & 0xFF)]
            else:
                instruction.tstates = 10
                return []
            
    @instruction([([0xC9], ())],
                 2, "RET", 10)
    def ret(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.SP, inc16(registers.SP)]
        else:
            registers.SP = inc16(registers.SP)
            registers.SP = inc16(registers.SP)
            registers.PC = data[1] << 8 | data[0]
            return []
        
    @instruction([([0xC0+offset], (reg, reg_name, val))
                  for offset, reg_name, reg, val in conditions],
                 2, "RET {1}", 11)
    def ret_c(instruction, registers, get_reads, data, reg, reg_name, val):
        if get_reads:
            return [registers.SP, inc16(registers.SP)]
        else:
            if getattr(registers.condition, reg) == val:
                registers.SP = inc16(registers.SP)
                registers.SP = inc16(registers.SP)
                registers.PC = data[1] << 8 | data[0]
                instruction.tstates = 11
            else:
                instruction.tstates = 5
            return []
            
    @instruction([([0xed, 0x4d], ())],  2, "RETI", 14)
    def reti(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.SP, inc16(registers.SP)]
        else:
            #TODO: implement return from interrupt
            logging.warn("RETI not fully implemented")
            registers.SP = inc16(registers.SP)
            registers.SP = inc16(registers.SP)
            registers.PC = data[1] << 8 | data[0]
            return []
        
    @instruction([([0xed, 0x45], ())],  2, "RETN", 14)
    def retn(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.SP, inc16(registers.SP)]
        else:
            #TODO: implement from non masked interrupt
            logging.warn("RETN not fully implemented")
            registers.SP = inc16(registers.SP)
            registers.SP = inc16(registers.SP)
            registers.PC = data[1] << 8 | data[0]
            registers.IFF = registers.IFF2
            return []
        
    @instruction([([0xC7 + (t << 3) ], (p, )) for t, p in enumerate([0x0, 0x08, 0x10, 0x18,
                                                                   0x20, 0x28, 0x30, 0x38]) ] ,
                 2, "RST {0:X}H", 11)
    def rst_p(instruction, registers, get_reads, data, p):
        if get_reads:
            return []
        else:
            sp = registers.SP
            pc = registers.PC
            registers.SP = dec16(registers.SP)
            registers.SP = dec16(registers.SP)
            registers.PC = p
            return [(sp - 1, pc >> 8),
                    (sp - 2, pc & 0xFF)]
        
    #--------------------------------------------------------------------
    # Input Output Group
    #--------------------------------------------------------------------
    @instruction([([0xDB, '-'], ( )) ] ,
                 2, "IN A, ({0:X}H)", 11)
    def in_a_n(instruction, registers, get_reads, data, n):
        if get_reads:
            address = n | (registers.A << 8) # registers.C | (registers.B << 8)
            return [address+0x10000]
        else:
            registers.A = data[0]
            return []
        
    @instruction([([0xEd, 0x40+(i<<3)], (r, )) for i, r in enumerate("BCDEHLFA")] ,
                 2, "IN {0}, (C)", 12)
    def in_r_c(instruction, registers, get_reads, data, r):
        if get_reads:
            address = registers.C | (registers.B << 8) #n | (registers.A << 8)
            return [address+0x10000]
        else:
            registers.condition.S = data[0] & 0x80
            registers.condition.Z = data[0] == 0
            registers.condition.H = 0
            registers.condition.PV = parity(data[0])
            registers.condition.N = 0
            if r == "F":
                return []
            registers[r] = data[0]
            return []
        
    @instruction([([0xed, 0xa2], ( )) ] ,
                 2, "INI", 16)
    def ini(instruction, registers, get_reads, data):
        if get_reads:
            address = registers.C | (registers.B << 8)
            return [address+0x10000]
        else:
            registers.B = dec8(registers.B)
            registers.HL = inc16(registers.HL)
            registers.condition.N = 1
            registers.condition.Z = registers.B == 0
            return [(dec16(registers.HL), data[0])]
        
        
    @instruction([([0xed, 0xb2], ( )) ] ,
                 2, "INIR", 21)
    def inir(instruction, registers, get_reads, data):
        if get_reads:
            address = registers.C | (registers.B << 8)
            return [address+0x10000]
        else:
            registers.B = dec8(registers.B)
            registers.HL = inc16(registers.HL)
            registers.condition.N = 1
            registers.condition.Z = registers.B == 0
            if registers.B == 0:
                dec16(registers.PC)
                dec16(registers.PC)
                instruction.tstates = 16
            else:
                instruction.tstates = 21
            return [(dec16(registers.HL), data[0])]
        
    @instruction([([0xed, 0xaa], ( )) ] ,
                 2, "IND", 16)
    def ind(instruction, registers, get_reads, data):
        if get_reads:
            address = registers.C | (registers.B << 8)
            return [address+0x10000]
        else:
            registers.B = dec8(registers.B)
            registers.HL = dec16(registers.HL)
            registers.condition.N = 1
            registers.condition.Z = registers.B == 0
            return [(dec16(registers.HL), data[0])]
        
        
    @instruction([([0xed, 0xba], ( )) ] ,
                 2, "INDR", 21)
    def indr(instruction, registers, get_reads, data):
        if get_reads:
            address = registers.C | (registers.B << 8)
            return [address+0x10000]
        else:
            registers.B = dec8(registers.B)
            registers.HL = dec16(registers.HL)
            registers.condition.N = 1
            registers.condition.Z = registers.B == 0
            if not registers.B == 0:
                dec16(registers.PC)
                dec16(registers.PC)
                instruction.tstates = 21
            else:
                instruction.tstates = 16
            return [(dec16(registers.HL), data[0])]
        
    @instruction([([0xD3, '-'], ( )) ] ,
                 2, "OUT ({0:X}H), A", 11)
    def out_a_n(instruction, registers, get_reads, data, n):
        if get_reads:
            return []
        else:
            address = n | (registers.A << 8)
            #if n == 0x81:
                ##logging.info("=========================================== %s =="%chr(registers.A))
                ##print chr(registers.A),
                #sys.stdout.flush()
            return [(address+0x10000, registers.A)]
        
    @instruction([([0xEd, 0x41+(i<<3)], (r, )) for i, r in enumerate("BCDEHLFA")] ,
                 2, "OUT (C), {0}", 12)
    def out_r_c(instruction, registers, get_reads, data, r):
        if get_reads:
            return []
        else:
            if r == "F":
                return []
            return [(registers.BC+0x10000, registers[r])]
        
    @instruction([([0xed, 0xa3], ( )) ] ,
                 2, "OUTI", 16)
    def outi(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            address = registers.C | (registers.B << 8)
            registers.B = dec8(registers.B)
            registers.HL = inc16(registers.HL)
            registers.condition.N = 1
            registers.condition.Z = registers.B == 0
            return [(address+0x10000, data[0])]
        
        
    @instruction([([0xed, 0xb3], ( )) ] ,
                 2, "OTIR", 21)
    def otir(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            address = registers.C | (registers.B << 8)
            registers.B = dec8(registers.B)
            registers.HL = inc16(registers.HL)
            registers.condition.N = 1
            registers.condition.Z = registers.B == 0
            if not registers.B == 0:
                dec16(registers.PC)
                dec16(registers.PC)
                instruction.tstates = 21
            else:
                instruction.tstates = 16
                
            return [(registers.BC+0x10000, data[0])]
        
    @instruction([([0xed, 0xab], ( )) ] ,
                 2, "OUTD", 16)
    def outd(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            address = registers.C | (registers.B << 8)
            registers.B = dec8(registers.B)
            registers.HL = dec16(registers.HL)
            registers.condition.N = 1
            registers.condition.Z = registers.B == 0
            return [(registers.BC+0x10000, data[0])]
        
        
    @instruction([([0xed, 0xbb], ( )) ] ,
                 2, "OTDR", 21)
    def otdr(instruction, registers, get_reads, data):
        if get_reads:
            return [registers.HL]
        else:
            address = registers.C | (registers.B << 8)
            registers.B = dec8(registers.B)
            registers.HL = dec16(registers.HL)
            registers.condition.N = 1
            registers.condition.Z = registers.B == 0
            if not registers.B == 0:
                dec16(registers.PC)
                dec16(registers.PC)
                instruction.tstates = 21
            else:
                instruction.tstates = 16
                
            return [(registers.BC+0x10000, data[0])]
