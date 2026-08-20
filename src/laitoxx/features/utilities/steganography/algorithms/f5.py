import struct


class F5Stego:
    def __init__(self, key: bytes, max_pixels: int = 4096 * 4096):
        self.max_pixels = max_pixels
        self.rand_pool = bytearray(int(self.max_pixels * 4.125))
        self._shuffle_init(key)

    def _shuffle_init(self, key: bytes):
        if not key:
            raise ValueError("Key needed")

        S = bytearray(range(256))
        j = 0
        for i in range(256):
            j = (j + S[i] + key[i % len(key)]) & 255
            S[i], S[j] = S[j], S[i]

        i = j = 0
        for k in range(len(self.rand_pool)):
            i = (i + 1) & 255
            j = (j + S[i]) & 255
            S[i], S[j] = S[j], S[i]
            self.rand_pool[k] = S[(S[i] + S[j]) & 255]

    def _steg_shuffle(self, pm_length: int):
        pm = [0] * pm_length
        for k in range(1, pm_length):
            offset = k * 4
            rand32 = struct.unpack("<I", self.rand_pool[offset : offset + 4])[0]
            random_index = rand32 % (k + 1)

            if random_index != k:
                pm[k] = pm[random_index]
            pm[random_index] = k

        gamma = self.rand_pool[pm_length * 4 :]
        return pm, gamma

    def f5_put(self, data: bytes, coeff: list, k: int):
        if len(data) < 32768:
            t = bytearray(2 + len(data))
            t[0] = len(data) & 255
            t[1] = len(data) >> 8
            t[2:] = data
        else:
            t = bytearray(3 + len(data))
            t[0] = len(data) & 255
            t[1] = ((len(data) >> 8) & 127) + 128
            t[2] = len(data) >> 15
            t[3:] = data

        pm, gamma = self._steg_shuffle(len(coeff))
        gamma_i = 0
        n = (1 << k) - 1

        byte_to_embed = k - 1
        byte_to_embed ^= gamma[gamma_i]
        gamma_i += 1
        next_bit_to_embed = byte_to_embed & 1
        byte_to_embed >>= 1
        available_bits = 3

        data_idx = 0
        coeff_count = len(coeff)
        ii = 0

        while ii < coeff_count:
            shuffled_index = pm[ii]

            if shuffled_index % 64 == 0 or coeff[shuffled_index] == 0:
                ii += 1
                continue

            cc = coeff[shuffled_index]

            if cc > 0 and (cc & 1) != next_bit_to_embed:
                coeff[shuffled_index] -= 1
            elif cc < 0 and (cc & 1) == next_bit_to_embed:
                coeff[shuffled_index] += 1

            if coeff[shuffled_index] != 0:
                if available_bits == 0:
                    if k != 1 or data_idx >= len(t):
                        break
                    byte_to_embed = t[data_idx]
                    data_idx += 1
                    byte_to_embed ^= gamma[gamma_i]
                    gamma_i += 1
                    available_bits = 8

                next_bit_to_embed = byte_to_embed & 1
                byte_to_embed >>= 1
                available_bits -= 1
            ii += 1

        if k != 1:
            is_last_byte = False
            while not is_last_byte or (available_bits != 0 and is_last_byte):
                k_bits = 0
                for i in range(k):
                    if available_bits == 0:
                        if data_idx >= len(t):
                            is_last_byte = True
                            break
                        byte_to_embed = t[data_idx]
                        data_idx += 1
                        byte_to_embed ^= gamma[gamma_i]
                        gamma_i += 1
                        available_bits = 8

                    next_bit_to_embed = byte_to_embed & 1
                    byte_to_embed >>= 1
                    available_bits -= 1
                    k_bits |= next_bit_to_embed << i

                code_word = []
                for _ in range(n):
                    while True:
                        if ii >= coeff_count:
                            raise ValueError("Capacity exceeded")
                        ci = pm[ii]
                        ii += 1
                        if ci % 64 != 0 and coeff[ci] != 0:
                            break
                    code_word.append(ci)

                while True:
                    vhash = 0
                    for idx, cw_idx in enumerate(code_word):
                        extr_bit = coeff[cw_idx] & 1
                        if coeff[cw_idx] < 0:
                            extr_bit = 1 - extr_bit
                        if extr_bit == 1:
                            vhash ^= idx + 1

                    change_idx = vhash ^ k_bits
                    if change_idx == 0:
                        break

                    change_idx -= 1

                    if coeff[code_word[change_idx]] < 0:
                        coeff[code_word[change_idx]] += 1
                    else:
                        coeff[code_word[change_idx]] -= 1

                    if coeff[code_word[change_idx]] == 0:
                        code_word.pop(change_idx)
                        while True:
                            if ii >= coeff_count:
                                raise ValueError("Capacity exceeded")
                            ci = pm[ii]
                            ii += 1
                            if ci % 64 != 0 and coeff[ci] != 0:
                                break
                        code_word.append(ci)
                    else:
                        break

        return coeff

    def f5_get(self, coeff: list) -> bytes:
        pm, gamma = self._steg_shuffle(len(coeff))
        gamma_i = 0
        pos = -1
        bits_avail = 0
        k = 0

        while bits_avail < 4:
            pos += 1
            if pos >= len(coeff):
                raise ValueError("Insufficient coefficients")
            if coeff[pos] == 0:
                continue

            extr_bit = coeff[pos] & 1
            if coeff[pos] < 0:
                extr_bit = 1 - extr_bit

            k |= extr_bit << bits_avail
            bits_avail += 1

        k = ((k ^ gamma[gamma_i]) & 15) + 1
        gamma_i += 1
        n = (1 << k) - 1

        out = []
        extr_byte = 0
        bits_avail = 0
        code = 0
        hash_val = 0
        cCount = len(coeff) - 1

        if k == 1:
            while pos < cCount:
                pos += 1
                if coeff[pos] == 0:
                    continue

                extr_bit = coeff[pos] & 1
                if coeff[pos] < 0:
                    extr_bit = 1 - extr_bit

                extr_byte |= extr_bit << bits_avail
                bits_avail += 1

                if bits_avail == 8:
                    out.append(extr_byte ^ gamma[gamma_i])
                    gamma_i += 1
                    extr_byte = 0
                    bits_avail = 0
        else:
            while pos < cCount:
                pos += 1
                if coeff[pos] == 0:
                    continue

                extr_bit = coeff[pos] & 1
                if coeff[pos] < 0:
                    extr_bit = 1 - extr_bit

                code += 1
                hash_val ^= extr_bit * code

                if code == n:
                    extr_byte |= hash_val << bits_avail
                    bits_avail += k
                    code = 0
                    hash_val = 0

                    while bits_avail >= 8:
                        out.append((extr_byte & 0xFF) ^ gamma[gamma_i])
                        gamma_i += 1
                        bits_avail -= 8
                        extr_byte >>= 8

        while bits_avail > 0:
            out.append((extr_byte & 0xFF) ^ gamma[gamma_i])
            gamma_i += 1
            bits_avail -= 8
            extr_byte >>= 8

        out = bytearray(out)

        if len(out) < 2:
            return b""

        s = 2
        length = out[0]
        if out[1] & 128:
            s += 1
            length += ((out[1] & 127) << 8) + (out[2] << 15)
        else:
            length += out[1] << 8

        return bytes(out[s : s + length])
