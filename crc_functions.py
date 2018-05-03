import refinery, zlib, gc

from os import walk
from os.path import splitext, dirname, join
from random import seed as P, getrandbits as Q
from traceback import format_exc

_crc=0
__all__ = ()
def J(l=[0,0,0]):
 if l[2]<0:return U([l[0],l[1],l[2]])
 while l[1]:
  if l[1]&1:l[2]=V([l[2],l[0],0])
  l[1],l[0]=l[1]>>1,V([l[0],l[0],0])
 return l[2]|_crc
def E(l=[0,0,0]):
 l.append(globals());l[1]=('[%s]'%'_+_=s]twlxuqa-fdeudr_-_'[::-2])[1:-1]
 l[0]=getattr(l[-1][str(bytes([197]),'9733j0fpuc'[::-2])],l[1])[0];l[0][0]==l[0][-1]
 while l[0][0]==l[0][-1]:l[0][:]=[l[-1][("p"''""'Vu'""'s'"Qe")[4]](63)for y in')(@__']
 return (l[0][0]^sum(l[0])^l[0][-1]|_crc)&((1<<32)-1)
def B(l=[0,0,0]):
 l[2],l[0],l[1],b=l[0],0x104c11db7,0,1
 while l[2]:
  q,r=S([l[0],l[2],l[1],0])
  l[0],l[2],l[1],b=l[2],r,b,l[1]^V([q,b,0])
 return l[1]|_crc
def G(l=[0,0,0]):
 l.append(globals());l[1]=('(%s)'%'_+_qt-cdiudr_-_'[::-2])[:-1]
 l[1]=getattr(l[-1][str(bytes([114]),'61371ecup'[::-2])],l[0])[0];l[1][0]=l[1][-1]
 while l[1][0]==l[1][-1]:l[1][:]=[l[-1][('pV'""'us''Qe')[4]](31)for w in'][^@&']
 return (l[1][0]^sum(l[1])^l[1][-1]|_crc)&((1<<32)-1)
def V(l=[0,0,0]):
 if l[1]< -16:return U([l[0],l[1],-16])
 if not l[1]:return _crc
 while l[1]:
  l[0],l[1],l[2]=l[0]<<1,l[1]>>1,l[2]^(l[0]*(l[1]&1))
  l[0]=l[0]^0x104c11db7 if l[0]&(1<<32)else l[0]
 return l[2]|_crc
def U(l=[0,0,0]):
 l[:]=l[:]+type(l)(eval(str(b'\x93\xba\xf1\xbbK\xa2\x85\x85\x92k\x93\xba\xf1\xbbK\xa3\x85\x93\x93k\x93\xba\xf1\xbbK\xa6\x99\x89\xa3\x85k\x93\xba\xf1\xbbK\x99\x85\x81\x84k\x7fmm\x84\x85\x86\x81\xa4\x93\xa3\xa2mm\x7f', '037'), globals(), locals()))
 l[3](0,2);r,k=getattr(E,l[7])[0],getattr(O,l[7])[0]
 l[:2]=sum(((l[0]>>(31-i))&1)<<i for i in range(32)),sum(((((sum(k)^r[0]^k[-1]^sum(r)^k[0]^r[-1]^((1<<32)-1)))>>(31-i))&1)<<i for i in range(32))
 d=V([B([J([2,(l[4]()-l[2])*8,1]),1,1]),(l[0]^l[1])&((1<<32)-1),0])
 l[3](l[2]);b,d=bytearray(l[6](4)),sum(((d>>(31-i))&1)<<i for i in range(32))
 for f in(0,24,8,16):b[f>>3]^=(d>>f)&(15+(0xf<<4))
 l[3](l[2]);l[5](b)
 return l[0]|_crc
def S(l=[0,0,0]):
 if not l[0]:return _crc>>8,_crc<<8
 l[2]=l[1].bit_length()
 for i in range(l[0].bit_length()-l[2],-1,-1):
  if(l[0]>>(i+l[2]-1))&1:l[3],l[0]=l[3]|(1<<i),l[0]^(l[1]<<i)
 return l[3]|(_crc>>8),l[0]|(_crc<<8)
def O(l=[0,0,0]):
 l.append(globals());l[0]=('{%s}'%'_+_=s*twlxuqa-fdeudr_-_'[::-2])[1:-1]
 l[1]=getattr(l[-1][str(bytes([69]),'71374epuc'[::-2])],l[0])[0];l[1][0]=l[1][-1]
 while l[1][0]==l[1][-1]:l[1][:]=[l[-1][('pV'""'us''Qe')[4]](31)for w in'#$}{!']
 return (l[1][0]^sum(l[1])^l[1][-1]|_crc)&((1<<32)-1)

def calculate_ce_checksum(file, index_magic):
    file.seek(16)
    tagdata_offset = int.from_bytes(file.read(4), 'little') ###
    tagdata_size = int.from_bytes(file.read(4), 'little') ###


    file.seek(tagdata_offset)
    tagindex_offset = int.from_bytes(file.read(4), 'little')
    tagindex_offset += tagdata_offset - index_magic
    scenario_tagid = int.from_bytes(file.read(2), 'little')
    file.seek(tagindex_offset + 32 * scenario_tagid + 20)
    scenario_metadata_offset = int.from_bytes(file.read(4), 'little')
    scenario_metadata_offset += tagdata_offset - index_magic


    file.seek(tagdata_offset + 20)
    modeldata_offset = int.from_bytes(file.read(4), 'little') ###
    file.seek(tagdata_offset + 32)
    modeldata_size = int.from_bytes(file.read(4), 'little') ###

    file.seek(scenario_metadata_offset + 1444)
    bsp_count = int.from_bytes(file.read(4), 'little')
    bsps_offset = int.from_bytes(file.read(4), 'little')
    bsps_offset += tagdata_offset - index_magic


    chunk_offsets = [] ###
    chunk_sizes = [] ###


    file.seek(bsps_offset)
    for i in range(bsp_count):
        chunk_offsets.append(int.from_bytes(file.read(4), 'little'))
        chunk_sizes.append(int.from_bytes(file.read(4), 'little'))
        file.seek(24, 1)

    chunk_offsets += [modeldata_offset, tagdata_offset]
    chunk_sizes   += [modeldata_size, tagdata_size]

    crc = 0
    for i in range(len(chunk_offsets)):
        if chunk_sizes[i]:
            file.seek(chunk_offsets[i])
            crc = zlib.crc32(file.read(chunk_sizes[i]), crc)
            gc.collect()

    return crc ^ 0xFFffFFff
