import ctypes, platform

print (platform.system())

match platform.system(): 
    case "Windows":
        _sum = ctypes.CDLL("c_stuff/libsum.dll")
    case "Darwin":
        _sum = ctypes.CDLL("c_stuff/libsum_mac.so")
    case _:
        _sum = ctypes.CDLL("c_stuff/libsum.so")

_sum.our_function.argtypes = (ctypes.c_int, ctypes.POINTER(ctypes.c_int))

def our_function(numbers):
    global _sum
    num_numbers = len(numbers)
    array_type = ctypes.c_int * num_numbers
    result = _sum.our_function(ctypes.c_int(num_numbers), array_type(*numbers))
    return int(result)
