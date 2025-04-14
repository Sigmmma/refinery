'''
This module adds an new format to arbytmap, which allows it
to read new formats. Specifically it adds A16R16G16B16_F 
and R9G9B9E5, which is are floating-point formats
'''

import arbytmap
import array
import types

FORMAT_R9G9B9E5_SHAREDEXP = "R9G9B9E5_SHAREDEXP"
FORMAT_A16R16G16B16F      = "A16R16G16B16F"

MAX_R9G9B9E5_UNPACK_VALUE = 64
AVG_R9G9B9E5_UNPACK_SCALE = 10


def _apply_exponent_scales_to_pixels(pixels, scales):
    # scale the pixels to floats
    float_pixels = map(int(511).__rtruediv__, pixels)

    # multiply the float pixels by their scales and return them
    return list(map(float.__mul__, float_pixels, scales))


def unpack_r9g9b9e5(arby, bitmap_index, width, height, depth=1):
    # unpack the pixels so we can easily manipulate them
    unpacked_pixels = arby._unpack_raw_4_channel(
        arby.texture_block[bitmap_index],
        _R9G9B9E5_OFFSETS, _R9G9B9E5_MASKS,
        [_UPSCALE_5BIT, _UPSCALE_9BIT, _UPSCALE_9BIT, _UPSCALE_9BIT]
        )

    # slice the eponents out, and apply map operations to get an exponent
    # scale for each exponent using the following algorithm:  v = 2^(e-15)
    exps = map(int(15).__rsub__, unpacked_pixels[0::4])
    exp_scales = list(map(int(2).__pow__, exps))

    # apply the exponent to each channel
    channel_values = [(0,)]
    for i in (1, 2, 3):
        channel_values.append(_apply_exponent_scales_to_pixels(
            unpacked_pixels[i::4], exp_scales, 
            ))

    # NOTE: this part is a hack. we're scaling the color range values
    #       to take up as much of the [0, 65536] value range as possible
    average_vals = list(sum(vals)/len(vals) for vals in channel_values)
    max_val = min(
        MAX_R9G9B9E5_UNPACK_VALUE,
        AVG_R9G9B9E5_UNPACK_SCALE * max(average_vals)
        )
    max_clamp = types.MethodType(min, max_val)
    for i in (1, 2, 3):
        # clamp the values that are just too bright to the max
        channel_values[i] = map(max_clamp, channel_values[i])
        # scale the values to the range we defined
        channel_values[i] = map(float(0xFFff/max_val).__mul__, channel_values[i])

    # create a new array to hold the exponent applied pixels
    exp_applied_pixels = array.array(
        unpacked_pixels.typecode, b'\xFF' * (len(unpacked_pixels) * unpacked_pixels.itemsize)
        )
    for i in (1, 2, 3):
        # convert the floats to ints and slice them into
        # the new array(leaving the alpha white)
        exp_applied_pixels[i::4] = array.array("H", map(int, channel_values[i]))

    return exp_applied_pixels


def unpack_a16r16g16b16_f(arby, bitmap_index, width, height, depth=1):
    offsets   = arby.channel_offsets
    masks     = arby.channel_masks
    upscalers = arby.channel_upscalers
    chan_ct = len(offsets)

    blank_channels = []
    for i in range(chan_ct):
        if len(set(upscalers[i])) == 1:
            blank_channels.append(i)
            upscalers[i] = _UPSCALE_16BIT_ERASE

    # convert the pixel channels to uint16's so we can easily manipulate them
    packed_channels = arby._unpack_raw_4_channel(
        arby.texture_block[bitmap_index], offsets, masks, upscalers,
        )

    channel_values = array.array("I", b'\x00' * (4 * len(packed_channels)))
    # pad the half-floats to regular floats
    for i, half_float in enumerate(packed_channels):
        # sign, exponent, and mantissa
        s = half_float >> 15
        e = (half_float >> 10) & 0x1F
        m = half_float & 0x3FF

        if e == 0x1F:
            e = 0xFF
        elif e:
            e += 0x70
        elif m:
            e = 0x71
            while not m & 0x400:
                m <<= 1
                e -= 1
            m &= ~0x400

        channel_values[i] = (s << 31) | (e << 23) | (m << 13)

    channel_values = array.array("f", bytearray(channel_values))

    # clamp the values to the [0.0, 1.0] bounds
    channel_values = map(types.MethodType(max, 0.0), channel_values)
    channel_values = map(types.MethodType(min, 1.0), channel_values)
    # scale the values to the range we defined
    channel_values = map(float(0x7FFF).__mul__, channel_values)

    # convert the floats to ints and slice them into
    # the new array(leaving the alpha white)
    unpacked_pixels = array.array("H", map(int, channel_values))

    # replace any empty channels with their 
    for chan in blank_channels:
        if chan == 0:
            unpacked_pixels[::chan_ct] = array.array(
                "H", b'\xFF\xFF' * (len(unpacked_pixels) // chan_ct)
                )

    return unpacked_pixels


def pack_r9g9b9e5(arby, unpacked, width, height, depth=1):
    raise NotImplementedError("Not Implemented")


def pack_a16r16g16b16_f(arby, unpacked, width, height, depth=1):
    raise NotImplementedError("Not Implemented")


arbytmap.format_defs.register_format(
    FORMAT_R9G9B9E5_SHAREDEXP, 1,
    depths=(9,9,9,5), offsets=(18,9,0,27),
    unpacker=unpack_r9g9b9e5, packer=pack_r9g9b9e5
    )

arbytmap.format_defs.register_format(
    FORMAT_A16R16G16B16F, 1,
    depths=(16,16,16,16), offsets=(16,32,48,0),
    unpacker=unpack_a16r16g16b16_f, packer=pack_a16r16g16b16_f
    )

_R9G9B9E5_OFFSETS = array.array(
    "B", arbytmap.format_defs.CHANNEL_OFFSETS[FORMAT_R9G9B9E5_SHAREDEXP]
    )
_R9G9B9E5_MASKS = array.array(
    "H", arbytmap.format_defs.CHANNEL_MASKS[FORMAT_R9G9B9E5_SHAREDEXP]
    )
_UPSCALE_9BIT = array.array("H", list(range(2**9)))
_UPSCALE_5BIT = array.array("H", list(range(2**5)))
_UPSCALE_16BIT_ERASE = array.array("H", b'\x00\x00' * (2**16))
