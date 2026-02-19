import struct
import sys
import os

def merge_vec_files(vec_files, output_file):
    if not vec_files:
        print("Nu e vec")
        return

    # Header structure in OpenCV .vec files:
    # 4 bytes: count (int)
    # 4 bytes: vecSize (int)
    # 2 bytes: min (short)
    # 2 bytes: max (short)

    total_count = 0
    data_list = []
    header_info = None

    print(f"Unim fisierele: {vec_files}...")

    for fname in vec_files:
        with open(fname, 'rb') as f:
            count = struct.unpack('i', f.read(4))[0]
            vec_size = struct.unpack('i', f.read(4))[0]
            min_val = struct.unpack('h', f.read(2))[0]
            max_val = struct.unpack('h', f.read(2))[0]
            
            if header_info is None:
                header_info = (vec_size, min_val, max_val)
            elif header_info != (vec_size, min_val, max_val):
                print(f"EROARE: Fisierul {fname} are dimensiuni diferite (w/h)!")
                return

            total_count += count
            data_list.append(f.read())

    print(f"Scriem {output_file} cu un total de {total_count} mostre:")
    with open(output_file, 'wb') as f:
        f.write(struct.pack('i', total_count)) 
        f.write(struct.pack('i', header_info[0]))
        f.write(struct.pack('h', header_info[1]))
        f.write(struct.pack('h', header_info[2]))
        
        for data in data_list:
            f.write(data)
    
    print("gata!")

files_to_merge = ["pos1.vec", "pos2.vec", "pos3.vec"]
merge_vec_files(files_to_merge, "final_positives.vec")
