import os
import re


def read_crc_codes(_file):
    codes = []
    with open(_file, "r") as f:
        for line in f:
            line = line.partition("#")[0].strip()
            if line:
                # Smali Format: trailing s to indicate short type
                if line.endswith("s"):
                    line = line[:-1]
                try:
                    codes.append(int(line, 0))
                except ValueError as e:
                    print("File not valid", e)
                    raise e
        return codes


def find_cmd_ids(file_path):
    dic = {}
    match_id_compares = re.compile(r"(\.cmdId == \d*)")
    for file in os.listdir(file_path):
        with open(os.path.join(file_path, file), "r") as f:
            content = f.read()
            for match in re.findall(match_id_compares, content):
                if file not in dic:
                    dic[file] = []
                dic[file].append(int(match[10:]))
    return dic


def write_cmd_ids(jadx_source_path):
    package_path = "sources/com/ryzerobotics/tello/gcs/core/cmd/"
    with open("cmd_ids", "w") as f:
        re_class = re.compile(r"class (.+) extends e {")
        re_source = re.compile(r"/\* compiled from: (.+) \*/")
        for k, v in sorted(list(find_cmd_ids(os.path.join(jadx_source_path, package_path)).items()),
                           key=lambda it: it[0]):
            f.write("\n# ===\n")
            with open(os.path.join(jadx_source_path, package_path, k)) as k_file:
                contents = k_file.read()
                classname = re.search(re_class, contents).group(1)
                source = re.search(re_source, contents).group(1)
                f.write("Class: ")
                f.write(classname)
                f.write("\nSource: ")
                f.write(source)
                f.write("\n")
                f.write("\n".join(v))
                f.write("\n")


jadx_source_path = "/home/jaqxues/CodeProjects/Tello_1.1.1_Sources/"

CODES_CRC8 = read_crc_codes("codes_crc8")
CODES_CRC16 = read_crc_codes("codes_crc16")


# Algorithm found in com.ryzerobotics.tello.gcs.core.a
def calc_crc16(buf, size):
    i = 0
    code = 13970  # public static int a
    while size > 0:
        code = CODES_CRC16[(code ^ buf[i]) & 0xff] ^ (code >> 8)
        i += 1
        size -= 1
    return code


# Algorithm found in com.ryzerobotics.tello.gcs.core.b
def calc_crc8(buf, size):
    i = 0
    code = 119
    while size > 0:
        code = CODES_CRC8[(code ^ buf[i]) & 0xff]
        i += 1
        size -= 1

    return code
