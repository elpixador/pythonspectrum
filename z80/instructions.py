import copy
import logging
from . util import *
from . import io

class instruction(object):
    def __init__(self, opcode_args, n_operands, string, tstates=1):
        self.string = string
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
        self.opcode_args = ins.opcode_args
        self.n_operands = ins.n_operands
        self.tstates = ins.tstates
        self.executer = executer
        self.incrementR = 1

    def execute(self, operands=()):
        self.executer(*((self, self.registers) + self.args +
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
                #print (i, ":")
                for o in f.opcode_args:
                    #print (o)
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
                    if (opargs[0][0] in [0xCB, 0xED, 0xDD, 0xFD]):
                        if (opargs[0][0] in [0xDD, 0xFD]) and (opargs[0][1] == 0xCB): ff.incrementR = 3
                        else: ff.incrementR = 2
                    else: ff.incrementR = 1
                    if opargs[0][-1] == "-":
                        ff.operands.append(n+1)
                        for i in range(256):
                            d[i] = ff
                    else:
                        d[opargs[0][-1]] = ff

        dd = self._instructions2[0xDD]
        fd = self._instructions2[0xFD]
        for n in range(256):
            if not(n in dd):
                dd[n]=self._instructions2[n]
            if not(n in fd):
                fd[n]=self._instructions2[n]
                    
        for n in range(256): parities[n] = parity(n)

        self._instructions = self._instructions2

        self._instruction_composer = []
        self._composer_instruction = None
        self._composer_len = 1
        
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
            io.ZXRegisterR += q.incrementR
#            print q, ops
            return q, ops
        
    def reset_composer(self):
        self._instruction_composer = []
        

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
                  (0xED47, ("I", "A"), 9), (0xED4F, ("R", "A"), 9)
                  ], 0, "LD {0}, {1}", 4)
    def ld_r_r_(instruction, registers, r, r_):
        registers[r] = registers[r_]
    
        
    @instruction([(0xED57, ('I', )), (0xED5F, ("R", ))], 0, "LD A, {0}", 9)
    def ld_a_i(instruction, registers, r):
        ZXFlags.F5F3 = val = registers[r]
        registers.A = val
        ZXFlags.S = val & 0x80
        ZXFlags.Z = val == 0
        ZXFlags.H = 0
        ZXFlags.PV = registers.IFF2
        ZXFlags.N = 0
    
        
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
    def ld_r_n(instruction, registers, r, n):
        registers[r] = n


    @instruction([(0x7E, ("A", )), (0x46, ("B", )), (0x4E, ("C", )), (0x56, ("D", )), (0x5E, ("E", )), (0x66, ("H", )),
                  (0x6E, ("L", ))],
                 0, "LD {0}, (HL)", 7)
    def ld_r_hl(instruction, registers, r):
        registers[r] = io.ZXmem[registers.H << 8 | registers.L]

    @instruction([([0xDD, 0x7E, '-'], ("A", "IX")), ([0xDD, 0x46, '-'], ("B", "IX")),
                  ([0xDD, 0x4E, '-'], ("C", "IX")), ([0xDD, 0x56, '-'], ("D", "IX")),
                  ([0xDD, 0x5E, '-'], ("E", "IX")), ([0xDD, 0x66, '-'], ("H", "IX")),
                  ([0xDD, 0x6E, '-'], ("L", "IX")),
                  ([0xFD, 0x7E, '-'], ("A", "IY")), ([0xFD, 0x46, '-'], ("B", "IY")),
                  ([0xFD, 0x4E, '-'], ("C", "IY")), ([0xFD, 0x56, '-'], ("D", "IY")),
                  ([0xFD, 0x5E, '-'], ("E", "IY")), ([0xFD, 0x66, '-'], ("H", "IY")),
                  ([0xFD, 0x6E, '-'], ("L", "IY"))],   
                  1, "LD {0}, ({1}+{2:X}H)", 19)
    def ld_r_i_d(instruction, registers, r, i, d):
        registers[r] = io.ZXmem[registers[i] + get_8bit_twos_comp(d)]

    @instruction([(0x77, ("A", )), (0x70, ("B", )), (0x71, ("C", )), (0x72, ("D", )), (0x73, ("E", )), (0x74, ("H", )),
                  (0x75, ("L", ))],
                 0, "LD (HL), {0}", 7)
    def ld_hl_r(instruction, registers, r):
        io.ZXmem[registers.H << 8 | registers.L] = registers[r]

    @instruction([([0xDD, 0x77, '-'], ("A", "IX")), ([0xDD, 0x70, '-'], ("B", "IX")),
                  ([0xDD, 0x71, '-'], ("C", "IX")), ([0xDD, 0x72, '-'], ("D", "IX")),
                  ([0xDD, 0x73, '-'], ("E", "IX")), ([0xDD, 0x74, '-'], ("H", "IX")),
                  ([0xDD, 0x75, '-'], ("L", "IX")),
                  ([0xFD, 0x77, '-'], ("A", "IY")), ([0xFD, 0x70, '-'], ("B", "IY")),
                  ([0xFD, 0x71, '-'], ("C", "IY")), ([0xFD, 0x72, '-'], ("D", "IY")),
                  ([0xFD, 0x73, '-'], ("E", "IY")), ([0xFD, 0x74, '-'], ("H", "IY")),
                  ([0xFD, 0x75, '-'], ("L", "IY"))],
                  1, "LD ({1}+{2:X}H), {0}", 19)
    def ld_i_d_r(instruction, registers, r, i, d):
        io.ZXmem[registers[i] + get_8bit_twos_comp(d)] = registers[r]

    @instruction([([0x36, '-'], ( ))], 1, "LD (HL), {0:X}H", 10)
    def ld_hl_n(instruction, registers, n):
        io.ZXmem[registers.H << 8 | registers.L] = n

    @instruction([([0xDD, 0x36, '-', '-'], ("IX", )), ([0xFD, 0x36, '-', '-'], ("IY", ))],
                 2, "LD ({0}+{1:X}H), {2:X}H", 19)
    def ld_i_d_n(instruction, registers, i, d, n):
        io.ZXmem[registers[i] + get_8bit_twos_comp(d)] = n

    @instruction([(0x0A, ("B", "C")), (0x1A, ("D", "E"))],
                 0, "LD A, ({0}{1})", 7)
    def ld_a_rr(instruction, registers, r, r2):
        registers.A = io.ZXmem[registers[r] << 8 | registers[r2]]

    @instruction([([0x3A, '-', '-'], ())],
                 2, "LD A, ({1:x}{0:X}H)", 13)
    def ld_a_nn(instruction, registers, n, n2):
        registers.A = io.ZXmem[n2 << 8 | n]


    @instruction([(0x02, ("B", "C")), (0x12, ("D", "E"))],
                 0, "LD ({0}{1}), A", 7)
    def ld_rr_a(instruction, registers, r, r2):
        io.ZXmem[registers[r] << 8 | registers[r2]] = registers.A


    @instruction([([0x32, '-', '-'], ())],
                 2, "LD ({1:x}{0:X}H), A", 13)
    def ld_nn_a(instruction, registers, n, n2):
        io.ZXmem[n2 << 8 | n] = registers.A


    #----------------------------------------------------------------------
    # 16-bit Load instructions
    #----------------------------------------------------------------------
    @instruction([([0x01, '-', '-'], ("B", "C")), ([0x11, '-', '-'], ("D", "E")), ([0x21, '-', '-'], ("H", "L"))],
                 2, "LD {0}{1}, {3:X}{2:X}H", 10)
    def ld_dd_nn(instruction, registers, r, r2, n, n2):
        registers[r] = n2
        registers[r2] = n

    @instruction([([0x31, '-', '-'], ("SP",), 10), ([0xDD, 0x21, '-', '-'], ("IX", )),
                  ([0xFD, 0x21, '-', '-'], ("IY", ))],
                 2, "LD {0}, {2:X}{1:X}H", 14)
    def ld_D_nn(instruction, registers, r, n, n2):
        registers[r] = n2 << 8 | n

    @instruction([([0xED, 0x4B, '-', '-'], ("B", "C" )), ([0xED, 0x5B, '-', '-'], ("D", "E" )),
                  ([0xED, 0x6B, '-', '-'], ("H", "L" )), ([0x2A, '-', '-'], ("H", "L" ), 16), ],
                 2, "LD {0}{1}, ({3:X}{2:X}H)", 20)
    def ld_dd_nn_(instruction, registers, r, r_, n, n_):
        registers[r] = io.ZXmem[(n_ << 8 | n) + 1]
        registers[r_] = io.ZXmem[n_ << 8 | n]

    @instruction([([0xDD, 0x2A, '-', '-'], ("IX", )), ([0xFD, 0x2A, '-', '-'], ("IY", )),
                  ([0xED, 0x7B, '-', '-'], ("SP", ))],
                 2, "LD {0}, ({2:X}{1:X}H)", 20)
    def ld_D_nn_(instruction, registers, r, n, n2):
        registers[r] = io.ZXmem[(n2 << 8 | n) + 1] << 8 | io.ZXmem[n2 << 8 | n]


    @instruction([([0xED, 0x73, '-', '-'], ("SP", )), ([0xDD, 0x22, '-', '-'], ("IX", )),
                  ([0xFD, 0x22, '-', '-'], ("IY", ))],
                 2, "LD ({2:X}{1:X}H), {0}", 20)
    def ld_nn__D(instruction, registers, r, n, n2):
        ad = n2 << 8 | n
        io.ZXmem[ad + 1] = registers[r] >> 8
        io.ZXmem[ad] = registers[r] & 255

    @instruction([([0xED, 0x63, '-', '-'], ("H", "L", )), ([0x22, '-', '-'], ("H", "L", ), 16),
                  ([0xED, 0x43, '-', '-'], ("B", "C", )), ([0xED, 0x53, '-', '-'], ("D", "E", ))],
                 2, "LD ({3:X}{2:X}H), {0}{1}", 20)
    def ld_nn_D(instruction, registers, r, r2, n, n2):
        ad = n2 << 8 | n
        io.ZXmem[ad + 1] = registers[r]
        io.ZXmem[ad] = registers[r2]

    @instruction([(0xF9, ())],
                 0, "LD SP, HL", 6)
    def ld_sp_hl(instruction, registers):
        registers.SP = registers.H << 8 | registers.L

    @instruction([(0xDDF9, ("IX", )), (0xFDF9, ("IY", ))],
                 0, "LD SP, {0}", 10)
    def ld_sp_i(instruction, registers, i):
        registers.SP = registers[i]


    @instruction([(0xC5, ("B", "C" )), (0xD5, ("D", "E" )), (0xE5, ("H", "L" )), (0xF5, ("A", "F" ))],
                 0, "PUSH {0}{1}", 11)
    def push_qq(instruction, registers, q, q2):
        registers.SP = stack = (registers.SP - 2) & 0xFFFF
        io.ZXmem[stack + 1] = registers[q]
        io.ZXmem[stack] = registers[q2]
    

    @instruction([(0xDDE5, ("IX",  )), (0xFDE5, ("IY", ))],
                 0, "PUSH {0}", 15)
    def push_i(instruction, registers, i):
        registers.SP = stack = (registers.SP - 2) & 0xFFFF
        io.ZXmem[stack + 1] = registers[i] >> 8
        io.ZXmem[stack] = registers[i] & 255


    @instruction([(0xC1, ("B", "C" )), (0xD1, ("D", "E" )), (0xE1, ("H", "L" )), (0xF1, ("A", "F" ))],
                 0, "POP {0}{1}", 10)
    def pop_qq(instruction, registers, q, q2):
        stack = registers.SP
        registers.SP = (stack + 2) & 0xFFFF
        registers[q2] = io.ZXmem[stack]
        registers[q] = io.ZXmem[stack + 1]
        

    @instruction([(0xDDE1, ("IX", )), (0xFDE1, ("IY", ))],
                 0, "POP {0}", 14)
    def pop_i(instruction, registers, i):
        stack = registers.SP
        registers.SP = (stack + 2) & 0xFFFF
        registers[i] = io.ZXmem[stack + 1] << 8 | io.ZXmem[stack]

    #----------------------------------------------------------------------
    # Exchange, Block Transfer, and Search Group
    #----------------------------------------------------------------------
    @instruction([(0xEB, ())], 0, "EX DE, HL", 4)
    def ex_de_hl(instruction, registers):
        registers.D, registers.H = (registers.H, registers.D)
        registers.E, registers.L = (registers.L, registers.E)

    @instruction([(0x08, ())], 0, "EX AF, AF'", 4)
    def ex_af_af_(instruction, registers):
        registers.A, registers.A_ = (registers.A_, registers.A)
        registers.F, registers.F_ = (registers.F_, registers.F)

    @instruction([(0xD9, ())], 0, "EXX", 4)
    def exx(instruction, registers):
        registers.B, registers.B_ = (registers.B_, registers.B)
        registers.C, registers.C_ = (registers.C_, registers.C)
        registers.D, registers.D_ = (registers.D_, registers.D)
        registers.E, registers.E_ = (registers.E_, registers.E)
        registers.H, registers.H_ = (registers.H_, registers.H)
        registers.L, registers.L_ = (registers.L_, registers.L)

    @instruction([(0xE3, ())], 0, "EX (SP), HL", 19)
    def ex_sp__hl(instruction, registers):
        h = registers.H
        l = registers.L
        sp = registers.SP
        registers.H = io.ZXmem[inc16(sp)]
        registers.L = io.ZXmem[sp]
        io.ZXmem[sp] = l
        io.ZXmem[inc16(sp)]= h

    @instruction([(0xDDE3, ("IX", )), (0xFDE3, ("IY", ))], 0,
                 "EX (SP), {0}", 23)
    def ex_sp__i(instruction, registers, i):
        ix = registers[i]
        sp = registers.SP
        registers[i] = io.ZXmem[inc16(sp)] << 8 | io.ZXmem[sp]
        io.ZXmem[sp] = ix & 0xFF
        io.ZXmem[inc16(sp)] = ix >> 8

    @instruction([(0xEDA0, ())], 0, "LDI", 16)
    def ldi(instruction, registers):
        de_ = de = registers.D << 8 | registers.E
        hl = registers.H << 8 | registers.L
        bc = registers.B << 8 | registers.C
        val = io.ZXmem[hl]
        hl = (hl + 1) & 0xFFFF
        registers.H = hl >> 8
        registers.L = hl & 0xFF
        bc = (bc - 1) & 0xFFFF
        registers.B = bc >> 8
        registers.C = bc & 0xFF
        de = (de + 1) & 0xFFFF
        registers.D = de >> 8
        registers.E = de & 0xFF

        ZXFlags.H = 0
        ZXFlags.PV = (bc != 0)

        ZXFlags.N = 0
        f5f3 = registers.A + val
        ZXFlags.setF3(f5f3 & 0x08)
        ZXFlags.setF5(f5f3 & 0x02)
        io.ZXmem[de_] = val

    @instruction([(0xEDB0, ())], 0, "LDIR", 21)
    def ldir(instruction, registers):
        de_ = de = registers.D << 8 | registers.E
        hl = registers.H << 8 | registers.L
        bc = registers.B << 8 | registers.C
        val = io.ZXmem[hl]
        hl = (hl + 1) & 0xFFFF
        registers.H = hl >> 8
        registers.L = hl & 0xFF
        bc = (bc - 1) & 0xFFFF
        registers.B = bc >> 8
        registers.C = bc & 0xFF
        de = (de + 1) & 0xFFFF
        registers.D = de >> 8
        registers.E = de & 0xFF

        ZXFlags.H = 0
        if bc != 0:
            registers.PC = (registers.PC - 2) & 0xFFFF
            instruction.tstates = 21
        else:
            instruction.tstates = 16

        ZXFlags.PV = 0
        ZXFlags.N = 0
        f5f3 = registers.A + val
        ZXFlags.setF3(f5f3 & 0x08)
        ZXFlags.setF5(f5f3 & 0x02)
        io.ZXmem[de_] = val


    @instruction([(0xEDA8, ())], 0, "LDD", 16)
    def ldd(instruction, registers):
        de_ = de = registers.D << 8 | registers.E
        hl = registers.H << 8 | registers.L
        bc = registers.B << 8 | registers.C
        val = io.ZXmem[hl]
        hl = (hl - 1) & 0xFFFF
        registers.H = hl >> 8
        registers.L = hl & 0xFF
        bc = (bc - 1) & 0xFFFF
        registers.B = bc >> 8
        registers.C = bc & 0xFF
        de = (de - 1) & 0xFFFF
        registers.D = de >> 8
        registers.E = de & 0xFF

        ZXFlags.H = 0
        ZXFlags.PV = (bc != 0)
        ZXFlags.N = 0
        f5f3 = registers.A + val
        ZXFlags.setF3(f5f3 & 0x08)
        ZXFlags.setF5(f5f3 & 0x02)
        io.ZXmem[de_] = val

    @instruction([(0xEDB8, ())], 0, "LDDR", 16)
    def lddr(instruction, registers):
        de_ = de = registers.D << 8 | registers.E
        hl = registers.H << 8 | registers.L
        bc = registers.B << 8 | registers.C
        val = io.ZXmem[hl]
        hl = (hl - 1) & 0xFFFF
        registers.H = hl >> 8
        registers.L = hl & 0xFF
        bc = (bc - 1) & 0xFFFF
        registers.B = bc >> 8
        registers.C = bc & 0xFF
        de = (de - 1) & 0xFFFF
        registers.D = de >> 8
        registers.E = de & 0xFF

        ZXFlags.H = 0
        if bc != 0:
            registers.PC = (registers.PC - 2) & 0xFFFF
            instruction.tstates = 21
        else:
            instruction.tstates = 16

        ZXFlags.PV = 0
        ZXFlags.N = 0
        f5f3 = registers.A + val
        ZXFlags.setF3(f5f3 & 0x08)
        ZXFlags.setF5(f5f3 & 0x02)
        io.ZXmem[de_] = val


    @instruction([(0xEDA1, ())], 0, "CPI", 16)
    def cpi(instruction, registers):
        val = io.ZXmem[registers.HL]
        registers.HL = inc16(registers.HL)
        registers.BC = dec16(registers.BC)

        subtract8(registers.A, val, 0)
        ZXFlags.PV = registers.BC != 0
        f5f3 = registers.A - val -  ZXFlags.H
        ZXFlags.setF5(f5f3 & 0x02)
        ZXFlags.setF3(f5f3 & 0x08)

    @instruction([(0xEDB1, ())], 0, "CPIR", 16)
    def cpir(instruction, registers):
        val = io.ZXmem[registers.HL]
        registers.HL = inc16(registers.HL)
        registers.BC = dec16(registers.BC)

        res = subtract8(registers.A, val, 0)

        if registers.BC != 0 and res != 0:
            registers.PC = (registers.PC - 2) & 0xFFFF
            instruction.tstates = 21
        else:
            instruction.tstates = 16
        ZXFlags.PV = registers.BC != 0
        f5f3 = registers.A - val -  ZXFlags.H
        ZXFlags.setF5(f5f3 & 0x02)
        ZXFlags.setF3(f5f3 & 0x08)

    @instruction([(0xEDA9, ())], 0, "CPD", 16)
    def cpd(instruction, registers):
        val = io.ZXmem[registers.HL]
        registers.HL = dec16(registers.HL)
        registers.BC = dec16(registers.BC)

        subtract8(registers.A, val, 0)
        ZXFlags.PV = registers.BC != 0
        f5f3 = registers.A - val -  ZXFlags.H
        ZXFlags.setF5(f5f3 & 0x02)
        ZXFlags.setF3(f5f3 & 0x08)

    @instruction([(0xEDB9, ())], 0, "CPDR", 16)
    def cpdr(instruction, registers):
        val = io.ZXmem[registers.HL]
        registers.HL = dec16(registers.HL)
        registers.BC = dec16(registers.BC)

        res = subtract8(registers.A, val, 0)

        if registers.BC != 0 and res != 0:
            registers.PC = (registers.PC - 2) & 0xFFFF
            instruction.tstates = 21
        else:
            instruction.tstates = 16
        ZXFlags.PV = registers.BC != 0
        f5f3 = res -  ZXFlags.H
        ZXFlags.setF5(f5f3 & 0x02)
        ZXFlags.setF3(f5f3 & 0x08)

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
    def add_a_r(instruction, registers, r):
        registers.A = add8(registers.A, registers[r], 0)

    @instruction([([0xC6, '-'], ())], 1, "ADD A, {0:X}H", 7)
    def add_a_n(instruction, registers, n):
        registers.A = add8(registers.A, n, 0)


    @instruction([(0x86, ())], 0, "ADD A, (HL)", 7)
    def add_a_hl_(instruction, registers):
        registers.A = add8(registers.A, io.ZXmem[registers.HL], 0)

    @instruction([([0xDD, 0x86, '-'], ("IX",)),
                  ([0xFD, 0x86, '-'], ("IY",))], 1, "ADD A, ({0}+{1:X}H)", 19)
    def add_a_i_(instruction, registers, i, d):
        registers.A = add8(registers.A, io.ZXmem[registers[i] + get_8bit_twos_comp(d)], 0)

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
    def adc_a_r(instruction, registers, r):
        registers.A = add8(registers.A, registers[r], ZXFlags.C)

    @instruction([([0xCE, '-'], ())], 1, "ADC A, {0:X}H", 7)
    def adc_a_n(instruction, registers, n):
        registers.A = add8(registers.A, n, ZXFlags.C)


    @instruction([(0x8E, ())], 0, "ADC A, (HL)", 7)
    def adc_a_hl_(instruction, registers, ):
        registers.A = add8(registers.A, io.ZXmem[registers.HL], ZXFlags.C)

    @instruction([([0xDD, 0x8E, '-'], ("IX",)),
                  ([0xFD, 0x8E, '-'], ("IY",))], 1, "ADC A, ({0}+{1:X}H)", 19)
    def adc_a_i_(instruction, registers, i, d):
        registers.A = add8(registers.A, io.ZXmem[registers[i] + get_8bit_twos_comp(d)], ZXFlags.C)

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
    def sub_a_r(instruction, registers, r):
        registers.A = subtract8_check_overflow(registers.A, registers[r], 0)

    @instruction([([0xD6, '-'], ())], 1, "SUB A, {0:X}H", 7)
    def sub_a_n(instruction, registers, n):
        registers.A = subtract8_check_overflow(registers.A, n, 0)


    @instruction([(0x96, ())], 0, "SUB A, (HL)", 7)
    def sub_a_hl_(instruction, registers):
        registers.A = subtract8_check_overflow(registers.A, io.ZXmem[registers.HL], 0)

    @instruction([([0xDD, 0x96, '-'], ("IX",)),
                  ([0xFD, 0x96, '-'], ("IY",))], 1, "SUB A, ({0}+{1:X}H)", 19)
    def sub_a_i_(instruction, registers, i, d):
        registers.A = subtract8_check_overflow(registers.A, io.ZXmem[registers[i] + get_8bit_twos_comp(d)], 0)

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
    def sbc_a_r(instruction, registers, r):
        registers.A = subtract8_check_overflow(registers.A, registers[r], ZXFlags.C)

    @instruction([([0xDE, '-'], ())], 1, "SBC A, {0:X}H", 7)
    def sbc_a_n(instruction, registers, n):
        registers.A = subtract8_check_overflow(registers.A, n, ZXFlags.C)


    @instruction([(0x9E, ())], 0, "SBC A, (HL)", 7)
    def sbc_a_hl_(instruction, registers):
        registers.A = subtract8_check_overflow(registers.A, io.ZXmem[registers.HL], ZXFlags.C)

    @instruction([([0xDD, 0x9E, '-'], ("IX",)),
                  ([0xFD, 0x9E, '-'], ("IY",))], 1, "SBC A, ({0}+{1:X}H)", 19)
    def sbc_a_i_(instruction, registers, i, d):
        registers.A = subtract8_check_overflow(registers.A, io.ZXmem[registers[i] + get_8bit_twos_comp(d)], ZXFlags.C)

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
    def and_a_r(instruction, registers, r):
        a_and_n(registers, registers[r])

    @instruction([([0xe6, '-'], ())], 1, "AND {0:X}H", 7)
    def and_a_n(instruction, registers, n):
        a_and_n(registers, n)


    @instruction([(0xa6, ())], 0, "AND (HL)", 7)
    def and_a_hl_(instruction, registers):
        a_and_n(registers, io.ZXmem[registers.HL])

    @instruction([([0xDD, 0xA6, '-'], ("IX",)),
                  ([0xFD, 0xA6, '-'], ("IY",))], 1, "AND ({0}+{1:X}H)", 19)
    def and_a_i_(instruction, registers, i, d):
        a_and_n(registers, io.ZXmem[registers[i] + get_8bit_twos_comp(d)])

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
    def or_a_r(instruction, registers, r):
        a_or_n(registers, registers[r])

    @instruction([([0xf6, '-'], ())], 1, "OR {0:X}H", 7)
    def or_a_n(instruction, registers, n):
        a_or_n(registers, n)


    @instruction([(0xb6, ())], 0, "OR (HL)", 7)
    def or_a_hl_(instruction, registers):
        a_or_n(registers, io.ZXmem[registers.HL])

    @instruction([([0xDD, 0xB6, '-'], ("IX",)),
                  ([0xFD, 0xB6, '-'], ("IY",))], 1, "OR ({0}+{1:X}H)", 19)
    def or_a_i_(instruction, registers, i, d):
        a_or_n(registers, io.ZXmem[registers[i] + get_8bit_twos_comp(d)])

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
    def xor_a_r(instruction, registers, r):
        a_xor_n(registers, registers[r])

    @instruction([([0xee, '-'], ())], 1, "XOR {0:X}H", 7)
    def xor_a_n(instruction, registers, n):
        a_xor_n(registers, n)


    @instruction([(0xae, ())], 0, "XOR (HL)", 7)
    def xor_a_hl_(instruction, registers):
        a_xor_n(registers, io.ZXmem[registers.HL])

    @instruction([([0xDD, 0xAE, '-'], ("IX",)),
                  ([0xFD, 0xAE, '-'], ("IY",))], 1, "XOR ({0}+{1:X}H)", 19)
    def xor_a_i_(instruction, registers, i, d):
        a_xor_n(registers, io.ZXmem[registers[i] + get_8bit_twos_comp(d)])

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
    def cp_a_r(instruction, registers, r):
        ZXFlags.F5F3 = val = registers[r]
        subtract8_check_overflow(registers.A, val, 0)

    @instruction([([0xfe, '-'], ())], 1, "CP {0:X}H", 7)
    def cp_a_n(instruction, registers, n):
        subtract8_check_overflow(registers.A, n, 0)
        ZXFlags.F5F3 = n


    @instruction([(0xbe, ())], 0, "CP (HL)", 7)
    def cp_a_hl_(instruction, registers, ):
        ZXFlags.F5F3 =val = io.ZXmem[registers.HL]
        subtract8_check_overflow(registers.A, val, 0)

    @instruction([([0xDD, 0xBE, '-'], ("IX",)),
                  ([0xFD, 0xBE, '-'], ("IY",))], 1, "CP ({0}+{1:X}H)", 19)
    def cp_a_i_(instruction, registers, i, d):
        ZXFlags.F5F3 = val = io.ZXmem[registers[i] + get_8bit_twos_comp(d)]
        subtract8_check_overflow(registers.A, val, 0)

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
    def inc_r(instruction, registers, r):
        registers[r] = add8_nocarry(registers[r], 1, 0)

    @instruction([(0x34, ())], 0, "INC (HL)", 11)
    def inc_hl_(instruction, registers):
        hl = registers.HL
        io.ZXmem[hl] = add8_nocarry(io.ZXmem[hl], 1, 0)

    @instruction([([0xDD, 0x34, '-'], ("IX",)),
                  ([0xFD, 0x34, '-'], ("IY",))], 1, "INC ({0}+{1:X}H)", 23)
    def inc_i_(instruction, registers, i, d):
        pos = registers[i] + get_8bit_twos_comp(d)
        io.ZXmem[pos] = add8_nocarry(io.ZXmem[pos], 1, 0)


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
    def dec_r(instruction, registers, r):
        val = registers[r]
        ZXFlags.PV = val == 0x80
        registers[r] = subtract8(val, 1, 0)

    @instruction([(0x35, ())], 0, "DEC (HL)", 11)
    def dec_hl_(instruction, registers):
        hl = registers.HL
        val = io.ZXmem[hl]
        io.ZXmem[hl] = subtract8(val, 1, 0)
        ZXFlags.PV = (val == 0x80)

    @instruction([([0xDD, 0x35, '-'], ("IX",)),
                  ([0xFD, 0x35, '-'], ("IY",))], 1, "DEC ({0}+{1:X}H)", 23)
    def dec_i_(instruction, registers, i, d):
        pos = registers[i] + get_8bit_twos_comp(d)
        val = io.ZXmem[pos]
        io.ZXmem[pos] = subtract8(val, 1, 0)
        ZXFlags.PV = (val == 0x80)

    #--------------------------------------------------------------------
    # General-Purpose Arithmetic and CPU Control Groups
    #--------------------------------------------------------------------
    @instruction([(0x27, ())], 0, "DAA", 4)
    def daa(instruction, registers):
        # https://github.com/openMSX/openMSX/blob/master/src/cpu/CPUCore.cc
        # http://z80-heaven.wikidot.com/instructions-set:daa
        diff = 0
        if (ZXFlags.H != 0) | ((registers.A & 0x0F) > 0x09): diff |= 0x06
        if (ZXFlags.C != 0) | (registers.A > 0x99): 
            diff |= 0x60
            ZXFlags.C = 1
        else: ZXFlags.C = 0
        if ZXFlags.N == 0: a = (registers.A + diff) & 0xFF
        else: a = get_8bit_twos_comp((registers.A - diff)) & 0xFF
        ZXFlags.H = ((registers.A ^ a) >> 4) & 0x01
        registers.A = a
        ZXFlags.S = a >> 7
        ZXFlags.Z = (a == 0)
        ZXFlags.PV = parities[a]
        ZXFlags.F5F3 = a
        """            
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
        """

    @instruction([(0x2F, ())], 0, "CPL", 4)
    def cpl(instruction, registers):
        ZXFlags.F5F3 = registers.A = (0xFF ^ registers.A)
        ZXFlags.N = 1
        ZXFlags.H = 1


    @instruction([(0xED44, ())], 0, "NEG", 8)
    def neg(instruction, registers):
        a = registers.A
        registers.A = subtract8(0, a, 0)
        ZXFlags.PV = (a == 0x80)
        ZXFlags.C = (a != 0x00)

    @instruction([(0x3F, ())], 0, "CCF", 4)
    def ccf(instruction, registers):
        ZXFlags.H = ZXFlags.C
        ZXFlags.N = 0
        ZXFlags.C = not ZXFlags.C
        ZXFlags.F5F3 = registers.A

    @instruction([(0x37, ())], 0, "SCF", 4)
    def scf(instruction, registers):
        ZXFlags.H = 0
        ZXFlags.N = 0
        ZXFlags.C = 1
        ZXFlags.F5F3 = registers.A

    @instruction([(0x00, ())], 0, "NOP", 4)
    def nop(instruction, registers):
        if registers.PC == 0x0556+1: # LD-BYTES - https://skoolkid.github.io/rom/asm/0556.html
            """
            Input:
                A 	+00 (header block) or +FF (data block)
                F 	Carry flag set if loading, reset if verifying
                DE 	Block length
                IX 	Start address
            Output:
                F 	Carry flag reset if there was an error
            """
            if ZXFlags.C:
                ZXFlags.C = io.ZXtap.loadBlock(registers.A, registers.IX, registers.DE)
            else:
                ZXFlags.C = 1
            sp = registers.SP
            registers.SP = (sp + 2) & 0xFFFF
            registers.PC = io.ZXmem[inc16(sp)] << 8 | io.ZXmem[sp]

        elif registers.PC == 0x04C2+1: # SA-BYTES - https://skoolkid.github.io/rom/asm/04C2.html
            """
            Input:
                A 	+00 (header block) or +FF (data block)
                DE 	Block length
                IX 	Start address
            """
            io.ZXtap.saveBlock(registers.A, registers.IX, registers.DE)            
            sp = registers.SP
            registers.SP = (sp + 2) & 0xFFFF
            registers.PC = io.ZXmem[inc16(sp)] << 8 | io.ZXmem[sp]

        else:
            pass

    @instruction([(0x76, ())], 0, "HALT", 4)
    def halt(instruction, registers):
        registers.HALT = True
        registers.PC = dec16(registers.PC)


    @instruction([(0xF3, ())], 0, "DI", 4)
    def di(instruction, registers):
        registers.IFF = False
        registers.IFF2 = False

    @instruction([(0xFB, ())], 0, "EI", 4)
    def ei(instruction, registers):
        registers.IFF = True
        registers.IFF2 = True

    @instruction([(0xED46, (0,)), (0xED56, (1,)), (0xED5E, (2,))], 0, "IM {}", 8)
    def im(instruction, registers, mode):
        registers.IM = mode


    #--------------------------------------------------------------------
    # 16-Bit Arithmetic Group
    #--------------------------------------------------------------------
    @instruction([(0x39, ("SP",)), (0x09, ("BC",)), (0x19, ("DE",)),(0x29, ("HL",))], 0, "ADD HL, {0}", 11)
    def add16_hl(instruction, registers, reg):
        a = registers.HL
        b = getattr(registers, reg)
        res = a + b
        ZXFlags.H = (a ^ res ^ b) & 0x1000
        ZXFlags.N = 0
        ZXFlags.C = res & 0x10000
        ZXFlags.F5F3 = res >> 8
        registers.HL = res &  0xFFFF

    @instruction([(0xED7A, ("SP",)), (0xED4A, ("BC",)), (0xED5A, ("DE",)),(0xED6A, ("HL",))], 0, "ADC HL, {0}", 15)
    def adc16_hl(instruction, registers, reg):
        a = registers.HL
        b = getattr(registers, reg)
        res = a + b + ZXFlags.C
        #print (a, "+",b,"=",res)
        ZXFlags.S = res & 0x8000
        ZXFlags.Z = (res == 0)
        if res & 0xFFFF:
            ZXFlags.H = (a ^ res ^ b) & 0x1000
            ZXFlags.PV = (a ^ res) & (b ^ res) & 0x8000
        else:
            ZXFlags.H = (a ^ res) & 0x1000
            ZXFlags.PV = a & res & 0x8000
        ZXFlags.N = 0
        ZXFlags.C = res & 0x10000
        ZXFlags.F5F3 = res >> 8
        registers.HL = res & 0xFFFF
        
    @instruction([(0xED72, ("SP",)), (0xED42, ("BC",)), (0xED52, ("DE",)),(0xED62, ("HL",))], 0, "SBC HL, {0}", 15)
    def sbc16_hl(instruction, registers, reg):
        a = registers.HL
        b = registers[reg]
        res = a - b - ZXFlags.C
        ZXFlags.S = res & 0x8000
        ZXFlags.N = 1
        ZXFlags.Z = (res == 0)
        ZXFlags.setF5F3 = res >> 8
        if res & 0xFFFF:
            ZXFlags.H = (a ^ res ^ b) & 0x1000
            ZXFlags.PV = (b ^ a) & (a ^ res) & 0x8000
        else:
            ZXFlags.H = (a ^ b) & 0x1000
            ZXFlags.PV = (b ^ a) & a & 0x8000        
        ZXFlags.C = res & 0x10000
        registers.HL = res &  0xFFFF

    @instruction([(0xDD39, ("IX", "SP",)), (0xDD09, ("IX", "BC",)), (0xDD19, ("IX", "DE",)),(0xDD29, ("IX", "IX",)),
                  (0xFD39, ("IY", "SP",)), (0xFD09, ("IY", "BC",)), (0xFD19, ("IY", "DE",)),(0xFD29, ("IY", "IY",))],
                 0, "ADD {0}, {1}", 15)
    def add16_i_pp(instruction, registers, i, r):
        a = registers[i]
        b = registers[r]
        res = a + b
        ZXFlags.H = (a ^ res ^ b) & 0x1000
        ZXFlags.N = 0
        ZXFlags.C = res & 0x10000
        ZXFlags.F5F3 = res >> 8
        registers[i] = res & 0xFFFF


    @instruction([(0x33, ("SP",)), (0x03, ("BC",)), (0x13, ("DE",)),(0x23, ("HL",)),
                  (0xDD23, ("IX",), 10), (0xFD23, ("IY",), 10)],
                 0, "INC {0}", 6)
    def inc16_ss(instruction, registers, s):
        registers[s] = (registers[s] + 1) & 0xFFFF
        

    @instruction([(0x3b, ("SP",)), (0x0b, ("BC",)), (0x1b, ("DE",)),(0x2b, ("HL",)),
                  (0xDD2b, ("IX",), 10), (0xFD2b, ("IY",), 10)],
                 0, "DEC {0}", 6)
    def dec16_ss(instruction, registers, s):
        registers[s] = (registers[s] - 1) & 0xFFFF

    #--------------------------------------------------------------------
    # Rotate and Shift Group
    #--------------------------------------------------------------------
    @instruction([(0x07, ())], 0, "RLCA", 4)
    def rlca(instruction, registers):
        c = registers.A >> 7
        ZXFlags.F5F3 = registers.A = ((registers.A << 1) | c) & 0xFF
        ZXFlags.C = c
        ZXFlags.H = 0
        ZXFlags.N = 0

    @instruction([(0x17, ())], 0, "RLA", 4)
    def rla(instruction, registers):
        c = registers.A >> 7
        ZXFlags.F5F3 = registers.A = (registers.A << 1 | ZXFlags.C) & 0xFF
        ZXFlags.C = c
        ZXFlags.H = 0
        ZXFlags.N = 0

    @instruction([(0x0F, ())], 0, "RRCA", 4)
    def rrca(instruction, registers):
        c = registers.A & 0x01
        ZXFlags.F5F3 = registers.A = (registers.A >> 1 | c << 7) & 0xFF
        ZXFlags.C = c
        ZXFlags.H = 0
        ZXFlags.N = 0

    @instruction([(0x1F, ())], 0, "RRA", 4)
    def rra(instruction, registers):
        c = registers.A & 0x01
        ZXFlags.F3F5 = registers.A = (registers.A >> 1 | ZXFlags.C << 7) & 0xFF
        ZXFlags.C = c
        ZXFlags.H = 0
        ZXFlags.N = 0
        

    # RLC m    
    @instruction([(0xCB07, ("A", )), (0xCB00, ("B", )), (0xCB01, ("C", )), (0xCB02, ("D", )),
                  (0xCB03, ("E", )), (0xCB04, ("H", )), (0xCB05, ("L", ))],
                 0, "RLC {0}", 8)
    def rlc(instruction, registers, r):
        ZXFlags.F5F3 = registers[r] = rotate_left_carry(registers[r])
        
    @instruction([(0xCB06, ( ))],
                 0, "RLC (HL)", 15)
    def rlc_hl_(instruction, registers):
        hl = registers.HL
        ZXFlags.F5F3 = io.ZXmem[hl] = rotate_left_carry(io.ZXmem[hl])

        
    @instruction([([0xDD, 0xCB, '-', 0x06], ("IX", )),
                  ([0xFD, 0xCB, '-', 0x06], ("IY", ))],
                 2, "RLC ({0}+{1:X}H)", 23)
    def rlc_i_d(instruction, registers, i, d):
        pos = registers[i] + get_8bit_twos_comp(d)
        ZXFlags.F5F3 = io.ZXmem[pos] = rotate_left_carry(io.ZXmem[pos])
        
    # RL m
    @instruction([([0xCB, 0x10], ("B", )), ([0xCB, 0x11], ("C", )), ([0xCB, 0x12], ("D", )),
                  ([0xCB, 0x13], ("E", )), ([0xCB, 0x14], ("H", )), ([0xCB, 0x15], ("L", )),
                  ([0xCB, 0x17], ("A", ))],
                 2, "RL {0}", 8)
    def rl_r(instruction, registers, r):
        ZXFlags.F5F3 = registers[r] = rotate_left(registers[r])
        
    @instruction([([0xCB, 0x16], ())],
                 2, "RL (HL)", 15)
    def rl_hl(instruction, registers):
        hl = registers.HL
        ZXFlags.F5F3 = io.ZXmem[hl] = rotate_left(io.ZXmem[hl])
        
    @instruction([([0xDD, 0xCB, "-", 0x16], ("IX", )),
                  ([0xFD, 0xCB, "-", 0x16], ("IY", ))],
                 2, "RL ({0}+{1:X}H)", 23)
    def rl_i(instruction, registers, i, d):
        pos = registers[i] + get_8bit_twos_comp(d)
        ZXFlags.F5F3 = io.ZXmem[pos] = rotate_left(io.ZXmem[pos])
        
        



    
    # RRC m    
    @instruction([(0xCB0F, ("A", )), (0xCB08, ("B", )), (0xCB09, ("C", )), (0xCB0A, ("D", )),
                  (0xCB0B, ("E", )), (0xCB0C, ("H", )), (0xCB0D, ("L", ))],
                 0, "RRC {0}", 8)
    def rrc(instruction, registers, r):
        ZXFlags.F5F3 = registers[r] = rotate_right_carry(registers[r])
        
    @instruction([(0xCB0E, ( ))],
                 0, "RRC (HL)", 15)
    def rrc_hl_(instruction, registers):
        hl = registers.HL
        ZXFlags.F5F3 = io.ZXmem[hl] = rotate_right_carry(io.ZXmem[hl])

        
    @instruction([([0xDD, 0xCB, '-', 0x0E], ("IX", )),
                  ([0xFD, 0xCB, '-', 0x0E], ("IY", ))],
                 2, "RRC ({0}+{1:X}H)", 23)
    def rrc_i_d(instruction, registers, i, d):
        pos = registers[i] + get_8bit_twos_comp(d)
        ZXFlags.F5F3 = io.ZXmem[pos] = rotate_right_carry(io.ZXmem[pos])
        
    # RR m
    @instruction([([0xCB, 0x18], ("B", )), ([0xCB, 0x19], ("C", )), ([0xCB, 0x1A], ("D", )),
                  ([0xCB, 0x1B], ("E", )), ([0xCB, 0x1C], ("H", )), ([0xCB, 0x1D], ("L", )),
                  ([0xCB, 0x1F], ("A", ))],
                 2, "RR {0}", 8)
    def rr_r(instruction, registers, r):
        ZXFlags.F5F3 = registers[r] = rotate_right(registers[r])
        
    @instruction([([0xCB, 0x1E], ())],
                 2, "RR (HL)", 15)
    def rr_hl(instruction, registers):
        hl = registers.HL
        ZXFlags.F5F3 = io.ZXmem[hl] = rotate_right(io.ZXmem[hl])
        
    @instruction([([0xDD, 0xCB, "-", 0x1E], ("IX", )),
                  ([0xFD, 0xCB, "-", 0x1E], ("IY", ))],
                 2, "RR ({0}+{1:X}H)", 23)
    def rr_i(instruction, registers, i, d):
        pos = registers[i] + get_8bit_twos_comp(d)
        ZXFlags.F5F3 = io.ZXmem[pos] = rotate_right(io.ZXmem[pos])
        
        



       
    # SLA m    
    @instruction([(0xCB27, ("A", )), (0xCB20, ("B", )), (0xCB21, ("C", )), (0xCB22, ("D", )),
                  (0xCB23, ("E", )), (0xCB24, ("H", )), (0xCB25, ("L", ))],
                 0, "SLA {0}", 8)
    def sla_r(instruction, registers, r):
        ZXFlags.F5F3 = registers[r] = shift_left(registers[r])
        
    @instruction([(0xCB26, ( ))],
                 0, "SLA (HL)", 15)
    def sla_hl_(instruction, registers):
        hl = registers.HL
        ZXFlags.F5F3 = io.ZXmem[hl] = shift_left(io.ZXmem[hl])

        
    @instruction([([0xDD, 0xCB, '-', 0x26], ("IX", )),
                  ([0xFD, 0xCB, '-', 0x26], ("IY", ))],
                 2, "SLA ({0}+{1:X}H)", 23)
    def sla_i_d(instruction, registers, i, d):
        pos = registers[i] + get_8bit_twos_comp(d)
        ZXFlags.F5F3 = io.ZXmem[pos] = shift_left(io.ZXmem[pos])


    # SLL m    
    @instruction([(0xCB37, ("A", )), (0xCB30, ("B", )), (0xCB31, ("C", )), (0xCB32, ("D", )),
                  (0xCB33, ("E", )), (0xCB34, ("H", )), (0xCB35, ("L", ))],
                 0, "SLL {0}", 8)
    def sll_r(instruction, registers, r):
        ZXFlags.F5F3 = registers[r] = shift_left_logical(registers[r])
        
    @instruction([(0xCB36, ( ))],
                 0, "SLL (HL)", 15)
    def sll_hl_(instruction, registers):
        hl = registers.HL
        ZXFlags.F5F3 = io.ZXmem[hl] = shift_left_logical(io.ZXmem[hl])

        
    @instruction([([0xDD, 0xCB, '-', 0x36], ("IX", )),
                  ([0xFD, 0xCB, '-', 0x36], ("IY", ))],
                 2, "SLL ({0}+{1:X}H)", 23)
    def sll_i_d(instruction, registers, i, d):
        pos = registers[i] + get_8bit_twos_comp(d)
        ZXFlags.F5F3 = io.ZXmem[pos] = shift_left_logical(io.ZXmem[pos])


    # SRA m
    @instruction([([0xCB, 0x28], ("B", )), ([0xCB, 0x29], ("C", )), ([0xCB, 0x2A], ("D", )),
                  ([0xCB, 0x2B], ("E", )), ([0xCB, 0x2C], ("H", )), ([0xCB, 0x2D], ("L", )),
                  ([0xCB, 0x2F], ("A", ))],
                 2, "SRA {0}", 8)
    def sra_r(instruction, registers, r):
        ZXFlags.F5F3 = registers[r] = shift_right(registers[r])
        
    @instruction([([0xCB, 0x2E], ())],
                 2, "SRA (HL)", 15)
    def sra_hl(instruction, registers):
        hl = registers.HL
        ZXFlags.F5F3 = io.ZXmem[hl] = shift_right(io.ZXmem[hl])
        
    @instruction([([0xDD, 0xCB, "-", 0x2E], ("IX", )),
                  ([0xFD, 0xCB, "-", 0x2E], ("IY", ))],
                 2, "SRA ({0}+{1:X}H)", 23)
    def sra_i(instruction, registers, i, d):
        pos = registers[i] + get_8bit_twos_comp(d)
        ZXFlags.F5F3 = io.ZXmem[pos] = shift_right(io.ZXmem[pos])
        

    # SRL m
    @instruction([([0xCB, 0x38], ("B", )), ([0xCB, 0x39], ("C", )), ([0xCB, 0x3A], ("D", )),
                  ([0xCB, 0x3B], ("E", )), ([0xCB, 0x3C], ("H", )), ([0xCB, 0x3D], ("L", )),
                  ([0xCB, 0x3F], ("A", ))],
                 2, "SRL {0}", 8)
    def srl_r(instruction, registers, r):
        ZXFlags.F5F3 = registers[r] = shift_right_logical(registers[r])
        
    @instruction([([0xCB, 0x3E], ())],
                 2, "SRL (HL)", 15)
    def srl_hl(instruction, registers):
        hl = registers.HL
        ZXFlags.F5F3 = io.ZXmem[hl] = shift_right_logical(io.ZXmem[hl])
        
    @instruction([([0xDD, 0xCB, "-", 0x3E], ("IX", )),
                  ([0xFD, 0xCB, "-", 0x3E], ("IY", ))],
                 2, "SRL ({0}+{1:X}H)", 23)
    def srl_i(instruction, registers, i, d):
        pos = registers[i] + get_8bit_twos_comp(d)
        ZXFlags.F5F3 = io.ZXmem[pos] = shift_right_logical(io.ZXmem[pos])

        
    @instruction([([0xED, 0x6F], ())],
                 2, "RLD", 18)
    def rld(instruction, registers):
        val = io.ZXmem[registers.HL]
        a = (val >> 4) | (registers.A & 0xF0)
        hl = ((val << 4) | (registers.A & 0x0f)) & 0xFF
        registers.A = a
        ZXFlags.S = a & 0x80
        ZXFlags.Z = a == 0
        ZXFlags.H = 0
        ZXFlags.N = 0
        ZXFlags.PV = parities[a]
        ZXFlags.F5F3 = a
        io.ZXmem[registers.HL] = hl

    @instruction([([0xED, 0x67], ())],
                 2, "RRD", 18)
    def rrd(instruction, registers):
        val = io.ZXmem[registers.HL]
        a = (val & 0x0F) | (registers.A & 0xF0)
        hl = ((val >> 4) | (registers.A << 4))  & 0xFF
        registers.A = a
        ZXFlags.S = a & 0x80
        ZXFlags.Z = a == 0
        ZXFlags.H = 0
        ZXFlags.N = 0
        ZXFlags.PV = parities[a]
        ZXFlags.F5F3 = a
        io.ZXmem[registers.HL] = hl



    
    #--------------------------------------------------------------------
    # Bit Set, Reset, and Test Group
    #--------------------------------------------------------------------
    @instruction([ ([0xCB, 0x40 + (b << 3) + register_bits[reg]], (b, reg))
                   for b in range(8)
                   for reg in ['A', 'B', 'C', 'D', 'E', 'H', 'L'] ] ,
                 2, "BIT {0}, {1}", 8)
    def bit_r(instruction, registers, bit, reg):
        # print "Test bit ", bit
        val = registers[reg] & (0x01 << bit)
        ZXFlags.Z = (val == 0)
        ZXFlags.H = 1
        ZXFlags.N = 0
        ZXFlags.PV = ZXFlags.Z            
        ZXFlags.S = val & 0x80
        #if bit == 5:
            #registers.condition.F5 = (registers[reg] & (0x01 << bit))
        #if bit == 3:
            #registers.condition.F3 = (registers[reg] & (0x01 << bit))
        ZXFlags.F5F3 = registers[reg]

    @instruction( [ ([0xCB, 0x40 + (b << 3) + 6], (b,)) for b in range(8) ] ,
                 2, "BIT {0}, (HL)", 12)
    def bit_hl(instruction, registers, bit):
        ZXFlags.F5F3 = val = io.ZXmem[registers.HL]
        res = val & (0x01 << bit)
        ZXFlags.Z = (res == 0)
        ZXFlags.H = 1
        ZXFlags.N = 0
        ZXFlags.PV = ZXFlags.Z
        ZXFlags.S = res & 0x80

    @instruction( [ ([I, 0xCB, '-', 0x40 + (b << 3) + 6], (Ir, b,)) for b in range(8) for I, Ir in index_bytes] ,
                 2, "BIT {1}, ({0}+{2:X}H)", 20)
    def bit_i(instruction, registers, i, bit, d):
        pos = registers[i]+get_8bit_twos_comp(d)
        val = io.ZXmem[pos]
        res = val & (0x01 << bit)
        ZXFlags.Z = (res == 0)
        ZXFlags.H = 1
        ZXFlags.N = 0
        ZXFlags.PV = ZXFlags.Z
        ZXFlags.S = res & 0x80
        ZXFlags.F5F3 = pos >> 8

    @instruction([ ([0xCB, 0xc0 + (b << 3) + register_bits[reg]], (b, reg))
                   for b in range(8)
                   for reg in ['A', 'B', 'C', 'D', 'E', 'H', 'L'] ] ,
                 2, "SET {0}, {1}", 8)
    def set_r(instruction, registers, bit, reg):
        registers[reg] |= (0x01 << bit)

    @instruction( [ ([0xCB, 0xc0 + (b << 3) + 6], (b,)) for b in range(8) ] ,
                 2, "SET {0}, (HL)", 15)
    def set_hl(instruction, registers, bit):
        hl = registers.HL
        io.ZXmem[hl] = io.ZXmem[hl] | (0x01 << bit)

    @instruction( [ ([I, 0xCB, '-', 0xc0 + (b << 3) + 6], (Ir, b,))
                    for b in range(8)
                    for I, Ir in index_bytes] ,
                 2, "SET {1}, ({0}+{2:X}H)", 23)
    def set_i(instruction, registers, i, bit, d):
        pos = registers[i] + get_8bit_twos_comp(d)
        io.ZXmem[pos] = io.ZXmem[pos] | (0x01 << bit)

    @instruction([ ([0xCB, 0x80 + (b << 3) + register_bits[reg]], (b, reg))
                   for b in range(8)
                   for reg in ['A', 'B', 'C', 'D', 'E', 'H', 'L'] ] ,
                 2, "RES {0}, {1}", 8)
    def res_r(instruction, registers, bit, reg):
        registers[reg] &= ~(0x01 << bit)

    @instruction( [ ([0xCB, 0x80 + (b << 3) + 6], (b,))
                    for b in range(8) ] ,
                 2, "RES {0}, (HL)", 15)
    def res_hl(instruction, registers, bit):
        hl = registers.HL
        io.ZXmem[hl] = io.ZXmem[hl] & ~(0x01 << bit)

    @instruction( [ ([I, 0xCB, '-', 0x80 + (b << 3) + 6], (Ir, b,))
                    for b in range(8)
                    for I, Ir in index_bytes] ,
                 2, "RES {1}, ({0}+{2:X}H)", 23)
    def res_i(instruction, registers, i, bit, d):
        pos = registers[i] + get_8bit_twos_comp(d)
        io.ZXmem[pos] = io.ZXmem[pos] & ~(0x01 << bit)



    #--------------------------------------------------------------------
    # Jump Group
    #--------------------------------------------------------------------
    @instruction([([0xC3, '-', '-'], ())],
                 2, "JP {1:X}{0:X}H", 10)
    def jp(instruction, registers, n, n2):
        registers.PC = n2 << 8 | n
        

    @instruction([([0xC2+offset, '-', '-'], (reg, reg_name, val))
                  for offset, reg_name, reg, val in conditions],
                 2, "JP {1}, {4:x}{3:X}H", 10)
    def jp_c(instruction, registers, reg, reg_name, val, n, n2):
        if ZXFlags.equals(reg, val):
            registers.PC = n2 << 8 | n
              

    
    @instruction([([0x18, '-'], ())],
                 2, "JR {0:X}H", 12)
    def jr(instruction, registers, n):
        offset_pc(registers, n)
    
    @instruction([([0x20, '-'], ())],
                 2, "JR NZ, {0:X}H", 12)
    def jr_nz(instruction, registers, n):
        if not ZXFlags.Z:
            offset_pc(registers, n)
            instruction.tstates = 12
        else:
            instruction.tstates = 7
        
         
    @instruction([([0x28, '-'], ())],
                 2, "JR Z, {0:X}H", 12)
    def jr_z(instruction, registers, n):
        if ZXFlags.Z:
            offset_pc(registers, n)
            instruction.tstates = 12
        else:
            instruction.tstates = 7
        
         
    @instruction([([0x30, '-'], ())],
                 2, "JR NC, {0:X}H", 12)
    def jr_nc(instruction, registers, n):
        if not ZXFlags.C:
            offset_pc(registers, n)
            instruction.tstates = 12
        else:
            instruction.tstates = 7
        
         
    @instruction([([0x38, '-'], ())],
                 2, "JR C, {0:X}H", 12)
    def jr_c(instruction, registers, n):
        if ZXFlags.C:
            offset_pc(registers, n)
            instruction.tstates = 12
        else:
            instruction.tstates = 7
        
    @instruction([([0xE9], ("HL", )),([0xDD, 0xE9], ("IX", ), 8),([0xFD, 0xE9], ("IY", ), 8) ],
                 2, "JP ({})", 4)
    def jp_r(instruction, registers, r):
        registers.PC = registers[r]
        
    @instruction([([0x10, '-'], ())],
                 2, "DJNZ {0:X}H", 13)
    def djnz(instruction, registers, n):
        registers.B = dec8(registers.B)
        if not registers.B == 0:
            offset_pc(registers, n)
            instruction.tstates = 13
        else:
            instruction.tstates = 8
    
    #--------------------------------------------------------------------
    # Call And Return Group
    #--------------------------------------------------------------------
    @instruction([([0xCD, '-', '-'], ())],
                 2, "CALL {1:X}{0:X}H", 17)
    def call(instruction, registers, n, n2):
        sp = (registers.SP - 2) & 0xFFFF
        pc = registers.PC
        registers.SP = sp
        registers.PC = n2 << 8 | n
        io.ZXmem[(sp+1) & 0xFFFF] = pc >> 8
        io.ZXmem[sp] = pc & 0xFF
        
    @instruction([([0xC4+offset, '-', '-'], (reg, reg_name, val))
                  for offset, reg_name, reg, val in conditions],
                 2, "CALL {1}, {4:x}{3:X}H", 17)
    def call_c(instruction, registers, reg, reg_name, val, n, n2):
        if ZXFlags.equals(reg, val):
            instruction.tstates = 17
            sp = (registers.SP - 2) & 0xFFFF
            pc = registers.PC
            registers.SP = sp
            registers.PC = n2 << 8 | n
            io.ZXmem[(sp+1) & 0xFFFF] = pc >> 8
            io.ZXmem[sp] = pc & 0xFF
        else:
            instruction.tstates = 10
            
    @instruction([([0xC9], ())],
                 2, "RET", 10)
    def ret(instruction, registers):
        sp = registers.SP
        registers.SP = (sp + 2) & 0xFFFF
        registers.PC = io.ZXmem[inc16(sp)] << 8 | io.ZXmem[sp]
        
    @instruction([([0xC0+offset], (reg, reg_name, val))
                  for offset, reg_name, reg, val in conditions],
                 2, "RET {1}", 11)
    def ret_c(instruction, registers, reg, reg_name, val):
        if ZXFlags.equals(reg, val):
            sp = registers.SP
            registers.SP = (sp + 2) & 0xFFFF
            registers.PC = io.ZXmem[inc16(sp)] << 8 | io.ZXmem[sp]
            instruction.tstates = 11
        else:
            instruction.tstates = 5
            
    @instruction([([0xed, 0x4d], ())],  2, "RETI", 14)
    def reti(instruction, registers):
        #TODO: implement return from interrupt
        #logging.warn("RETI not fully implemented")
        sp = registers.SP
        registers.SP = (sp + 2) & 0xFFFF
        registers.PC = io.ZXmem[inc16(sp)] << 8 | io.ZXmem[sp]
        
    @instruction([([0xed, 0x45], ())],  2, "RETN", 14)
    def retn(instruction, registers):
        #TODO: implement from non masked interrupt
        logging.warn("RETN not fully implemented")
        sp = registers.SP
        registers.SP = (sp + 2) & 0xFFFF
        registers.PC = io.ZXmem[inc16(sp)] << 8 | io.ZXmem[sp]
        registers.IFF = registers.IFF2
        
    @instruction([([0xC7 + (t << 3) ], (p, )) for t, p in enumerate([0x0, 0x08, 0x10, 0x18,
                                                                   0x20, 0x28, 0x30, 0x38]) ] ,
                 2, "RST {0:X}H", 11)
    def rst_p(instruction, registers, p):
        sp = (registers.SP - 2) & 0xFFFF
        pc = registers.PC
        registers.SP = sp
        registers.PC = p
        io.ZXmem[(sp+1) & 0xFFFF] = pc >> 8
        io.ZXmem[sp] = pc & 0xFF
        
    #--------------------------------------------------------------------
    # Input Output Group
    #--------------------------------------------------------------------
    @instruction([([0xDB, '-'], ( )) ] ,
                 2, "IN A, ({0:X}H)", 11)
    def in_a_n(instruction, registers, n):
        address = n | (registers.A << 8) # registers.C | (registers.B << 8)
        registers.A = io.ZXports.read(address)
        
    @instruction([([0xEd, 0x40+(i<<3)], (r, )) for i, r in enumerate("BCDEHLFA")] ,
                 2, "IN {0}, (C)", 12)
    def in_r_c(instruction, registers, r):
        address = registers.C | (registers.B << 8) #n | (registers.A << 8)
        res = io.ZXports.read(address)
        ZXFlags.S = res & 0x80
        ZXFlags.Z = res == 0
        ZXFlags.H = 0
        ZXFlags.PV = parities[res]
        ZXFlags.N = 0
        if r != "F": registers[r] = res
        
    @instruction([([0xed, 0xa2], ( )) ] ,
                 2, "INI", 16)
    def ini(instruction, registers):
        hl = registers.HL
        registers.B = dec8(registers.B)
        registers.HL = inc16(hl)
        res = io.ZXports.read(registers.BC)
        ZXFlags.N = 1
        ZXFlags.Z = registers.B == 0
        io.ZXmem[hl] = res
        
        
    @instruction([([0xed, 0xb2], ( )) ] ,
                 2, "INIR", 21)
    def inir(instruction, registers):        
        hl = registers.HL
        registers.B = dec8(registers.B)
        registers.HL = inc16(hl)
        res = io.ZXports.read(registers.BC)
        ZXFlags.N = 1
        ZXFlags.Z = registers.B == 0
        if registers.B != 0:
            registers.PC = (registers.PC - 2) & 0xFFFF
            instruction.tstates = 21
        else:
            instruction.tstates = 16
        io.ZXmem[hl] = res
        
    @instruction([([0xed, 0xaa], ( )) ] ,
                 2, "IND", 16)
    def ind(instruction, registers):
        hl = registers.HL
        registers.B = dec8(registers.B)
        registers.HL = dec16(hl)
        res = io.ZXports.read(registers.BC)
        ZXFlags.N = 1
        ZXFlags.Z = registers.B == 0
        io.ZXmem[hl] = res
        
        
    @instruction([([0xed, 0xba], ( )) ] ,
                 2, "INDR", 21)
    def indr(instruction, registers):
        hl = registers.HL
        registers.B = dec8(registers.B)
        registers.HL = dec16(hl)
        res = io.ZXports.read(registers.BC)
        ZXFlags.N = 1
        ZXFlags.Z = registers.B == 0
        if registers.B != 0:
            registers.PC = (registers.PC - 2) & 0xFFFF
            instruction.tstates = 21
        else:
            instruction.tstates = 16
        io.ZXmem[hl] = res
        
    @instruction([([0xD3, '-'], ( )) ] ,
                 2, "OUT ({0:X}H), A", 11)
    def out_a_n(instruction, registers, n):
        address = n | (registers.A << 8)
        #if n == 0x81:
            ##logging.info("=========================================== %s =="%chr(registers.A))
            ##print chr(registers.A),
            #sys.stdout.flush()
        io.ZXports.write(address, registers.A)
        
    @instruction([([0xEd, 0x41+(i<<3)], (r, )) for i, r in enumerate("BCDEHLFA")] ,
                 2, "OUT (C), {0}", 12)
    def out_r_c(instruction, registers, r):
        if r != "F": io.ZXports.write(registers.BC, registers[r])
        
    @instruction([([0xed, 0xa3], ( )) ] ,
                 2, "OUTI", 16)
    def outi(instruction, registers):
        val = io.ZXmem[registers.HL]
        address = registers.C | (registers.B << 8)
        registers.B = dec8(registers.B)
        registers.HL = inc16(registers.HL)
        ZXFlags.N = 1
        ZXFlags.Z = registers.B == 0
        io.ZXports.write(address, val)
        
        
    @instruction([([0xed, 0xb3], ( )) ] ,
                 2, "OTIR", 21)
    def otir(instruction, registers):
        address = registers.C | (registers.B << 8)
        val = io.ZXmem[registers.HL]
        registers.B = dec8(registers.B)
        registers.HL = inc16(registers.HL)
        ZXFlags.N = 1
        ZXFlags.Z = registers.B == 0
        if registers.B != 0:
            registers.PC = (registers.PC - 2) & 0xFFFF
            instruction.tstates = 21
        else:
            instruction.tstates = 16
            
        io.ZXports.write(address, val)
        
    @instruction([([0xed, 0xab], ( )) ] ,
                 2, "OUTD", 16)
    def outd(instruction, registers):
        address = registers.C | (registers.B << 8)
        val = io.ZXmem[registers.HL]
        registers.B = dec8(registers.B)
        registers.HL = dec16(registers.HL)
        ZXFlags.N = 1
        ZXFlags.Z = registers.B == 0
        io.ZXports.write(address, val)
        
        
    @instruction([([0xed, 0xbb], ( )) ] ,
                 2, "OTDR", 21)
    def otdr(instruction, registers):
        address = registers.C | (registers.B << 8)
        val = io.ZXmem[registers.HL]
        registers.B = dec8(registers.B)
        registers.HL = dec16(registers.HL)
        ZXFlags.N = 1
        ZXFlags.Z = registers.B == 0
        if registers.B != 0:
            registers.PC = (registers.PC - 2) & 0xFFFF
            instruction.tstates = 21
        else:
            instruction.tstates = 16
            
        io.ZXports.write(address, val)
