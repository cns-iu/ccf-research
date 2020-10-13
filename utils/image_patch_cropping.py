import json
import csv
from skimage import transform, io
# from collections import OrderedDict
from bokeh.io import show, output_file
from bokeh.plotting import figure
from bokeh.models import HoverTool
from bokeh.palettes import Set2_5
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
from read_roi import read_roi_zip


def make_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


if __name__ == '__main__':
    file_A_path = r'../visualization/annotations/VAN0008-RK-403-100-AF_preIMS_registered_glomerulus_detections.json'
    file_B_path = r'../visualization/student_annotations/VAN0008ML.csv'

    file_A_index = 1
    file_B_index = 1

    edge = 1000
    shift_dict = {
        "VAN0008-RK-403-100-PAS": (1, 0, -4 * 8, 0, 1, - 13 * 8),
        "VAN0009-LK-102-7-PAS": (1, 0, -4 * 8, 0, 1, - 13 * 8),
        "VAN0010-LK-155-40-PAS": (1, 0, -4 * 8, 0, 1, - 13 * 8),
        "VAN0014-LK-203-108-PAS": (1.015, -0.010, 0, 0, 1, -2),
    }

    raw_image_path = r'X:\VAN0008-RK-403-100-PAS_registered.ome.tiff'
    raw_image = io.imread(raw_image_path)
    raw_image = np.transpose(raw_image.reshape(raw_image.shape[2:]), (1, 0, 2))

    file_prefix = raw_image_path.split('\\')[-1].split('_registered')[0]
    output_path = os.path.join(os.path.dirname(raw_image_path), file_prefix)
    make_dir(output_path)

    img_trans = Image.fromarray(raw_image, 'RGB')
    if file_prefix in shift_dict:
        img_trans = img_trans.transform(img_trans.size, Image.AFFINE, shift_dict[file_prefix])
    raw_image = np.array(img_trans)
    # image_with_margin = np.zeros((raw_image.shape[0] + edge, raw_image.shape[1] + edge, raw_image.shape[2]))
    # image_with_margin[edge // 2:edge // 2 + raw_image.shape[0], edge // 2:edge // 2 + raw_image.shape[1]] = raw_image

    # A - VU json
    with open(file_A_path) as data_file:
        data = json.load(data_file)

    coor_list = []

    for item in data:
        coor_list.extend(item["geometry"]["coordinates"])
    A_x_list = [[xy[0] // file_A_index for xy in coor] for coor in coor_list]
    A_y_list = [[xy[1] // file_A_index for xy in coor] for coor in coor_list]

    # B - ML
    B_x_list, B_y_list, widths, heights = [], [], [], []
    tl_xy, br_xy = [], []
    with open(file_B_path, newline='') as inputfile:
        for row in csv.reader(inputfile):
            tlx = int(row[0]) // file_B_index
            tly = int(row[1]) // file_B_index
            brx = int(row[2]) // file_B_index
            bry = int(row[3]) // file_B_index
            widths.append(brx - tlx)
            heights.append(bry - tly)
            B_x_list.append(tlx + widths[-1] // 2)
            B_y_list.append(tly + heights[-1] // 2)
            tl_xy.append((tlx, tly))
            br_xy.append((brx, bry))

    # find difference
    center_list_VU = []
    for i in range(len(A_x_list)):
        mean_x = sum(A_x_list[i]) / len(A_x_list[i])
        mean_y = sum(A_y_list[i]) / len(A_y_list[i])
        center_list_VU.append((mean_x, mean_y))

    center_list_ML = [(B_x_list[i], B_y_list[i]) for i in range(len(B_x_list))]

    VU_false_positive_list = []
    ML_false_positive_list = []

    threshold = 150 // file_A_index
    for x, y in center_list_VU:
        _flag = False
        for _x, _y in center_list_ML:
            if (x - _x) ** 2 + (y - _y) ** 2 <= threshold ** 2:
                _flag = True
                break
        if not _flag:
            VU_false_positive_list.append(center_list_VU.index((x, y)))

    for x, y in center_list_ML:
        _flag = False
        for _x, _y in center_list_VU:
            if (x - _x) ** 2 + (y - _y) ** 2 <= threshold ** 2:
                _flag = True
                break
        if not _flag:
            ML_false_positive_list.append(center_list_ML.index((x, y)))

    type_list = ['VU' for i in range(len(VU_false_positive_list))]
    type_list.extend(['ML' for i in range(len(ML_false_positive_list))])

    # export VU images
    selected_A_x_list = [A_x_list[i] for i in range(len(A_x_list)) if i in VU_false_positive_list]
    selected_A_y_list = [A_y_list[i] for i in range(len(A_y_list)) if i in VU_false_positive_list]

    # export ML images
    tl_xys = [tl_xy[i] for i in range(len(tl_xy)) if i in ML_false_positive_list]
    br_xys = [br_xy[i] for i in range(len(br_xy)) if i in ML_false_positive_list]

    i = 0
    for xs, ys in zip(selected_A_x_list, selected_A_y_list):
        max_x = max(xs)
        min_x = min(xs)
        max_y = max(ys)
        min_y = min(ys)
        mid_x = (max_x + min_x) // 2
        mid_y = (max_y + min_y) // 2

        x_start = mid_x - int(edge // 2)
        x_end = mid_x + int(edge // 2)
        y_start = mid_y - int(edge // 2)
        y_end = mid_y + int(edge // 2)
        if x_start < 0:
            x_end -= x_start
            x_start = 0
        if x_end > raw_image.shape[0]:
            x_start -= (x_end - raw_image.shape[0])
            x_end = raw_image.shape[0]
        if y_start < 0:
            y_end -= y_start
            y_start = 0
        if y_end > raw_image.shape[1]:
            y_start -= (y_end - raw_image.shape[1])
            y_end = raw_image.shape[1]
        mid_x = (x_start + x_end) // 2
        mid_y = (y_start + y_end) // 2
        cropped_patch = raw_image[x_start:x_end, y_start:y_end]
        # cropped_patch = raw_image[mid_x - int(w * 1.5):mid_x + int(w * 1.5),
        #                 mid_y - int(h * 1.5):mid_y + int(h * 1.5)]
        cropped_patch = np.transpose(cropped_patch, (1, 0, 2))

        # left - image processing
        img = Image.fromarray(cropped_patch, 'RGB')
        text = f'{file_prefix}_VU_{VU_false_positive_list[i]}'
        font_path = r"c:\windows\fonts\bahnschrift.ttf"
        font = ImageFont.truetype(font_path, 24)
        ImageDraw.Draw(img).text((20, 20), f'{text}', font=font)
        ImageDraw.Draw(img).text((20, 60), f'Type: Glomerulus', font=font)
        ImageDraw.Draw(img).text((20, 100), f'Anno-', font=font)
        ImageDraw.Draw(img).text((20, 125), f'tation', font=font)
        ImageDraw.Draw(img).text((100, 100), f'Raw', font=font)
        ImageDraw.Draw(img).rectangle(((15, 95), (95, 150)), outline="white", width=2)
        ImageDraw.Draw(img).rectangle(((95, 95), (175, 150)), outline="white", width=2)
        polygon = [(xs[j] - (mid_x - int(edge // 2)), ys[j] - (mid_y - int(edge // 2))) for j in range(len(xs))]
        # polygon.append((xs[0], ys[0]))
        ImageDraw.Draw(img).line(polygon, fill="#4666FF", width=5)
        left = np.array(img)

        margin = np.zeros((cropped_patch.shape[0], 10, 3))
        margin = 255 - margin
        merge = np.concatenate((left, margin, cropped_patch), axis=1)

        io.imsave(os.path.join(output_path, f'{text}.jpg'), merge)
        i += 1

    # export ML images
    tl_xys = [tl_xy[i] for i in range(len(tl_xy)) if i in ML_false_positive_list]
    br_xys = [br_xy[i] for i in range(len(br_xy)) if i in ML_false_positive_list]
    i = 0
    for i in range(len(tl_xys)):
        tl = tl_xys[i]
        br = br_xys[i]
        mid_x = (tl[0] + br[0]) // 2
        mid_y = (tl[1] + br[1]) // 2

        x_start = mid_x - int(edge // 2)
        x_end = mid_x + int(edge // 2)
        y_start = mid_y - int(edge // 2)
        y_end = mid_y + int(edge // 2)
        if x_start < 0:
            x_end -= x_start
            x_start = 0
        if x_end > raw_image.shape[0]:
            x_start -= (x_end - raw_image.shape[0])
            x_end = raw_image.shape[0]
        if y_start < 0:
            y_end -= y_start
            y_start = 0
        if y_end > raw_image.shape[1]:
            y_start -= (y_end - raw_image.shape[1])
            y_end = raw_image.shape[1]
        mid_x = (x_start + x_end) // 2
        mid_y = (y_start + y_end) // 2
        cropped_patch = raw_image[x_start:x_end, y_start:y_end]
        # cropped_patch = raw_image[mid_x - int(w * 1.5):mid_x + int(w * 1.5),
        #                 mid_y - int(h * 1.5):mid_y + int(h * 1.5)]
        cropped_patch = np.transpose(cropped_patch, (1, 0, 2))

        # left - image processing
        img = Image.fromarray(cropped_patch, 'RGB')
        text = f'{file_prefix}_ML_{ML_false_positive_list[i]}'
        font_path = r"c:\windows\fonts\bahnschrift.ttf"
        font = ImageFont.truetype(font_path, 24)
        ImageDraw.Draw(img).text((20, 20), f'{text}', font=font)
        ImageDraw.Draw(img).text((20, 60), f'Type: Glomerulus', font=font)
        ImageDraw.Draw(img).text((20, 100), f'Anno-', font=font)
        ImageDraw.Draw(img).text((20, 125), f'tation', font=font)
        ImageDraw.Draw(img).text((100, 100), f'Raw', font=font)
        ImageDraw.Draw(img).rectangle(((15, 95), (95, 150)), outline="white", width=2)
        ImageDraw.Draw(img).rectangle(((95, 95), (175, 150)), outline="white", width=2)

        ImageDraw.Draw(img).rectangle(
            ((tl[0] - (mid_x - int(edge // 2)), tl[1] - (mid_y - int(edge // 2))),
             (br[0] - (mid_x - int(edge // 2)), br[1] - (mid_y - int(edge // 2)))),
            outline="#4666FF", width=5)
        left = np.array(img)

        margin = np.zeros((cropped_patch.shape[0], 10, 3))
        margin = 255 - margin
        merge = np.concatenate((left, margin, cropped_patch), axis=1)

        io.imsave(os.path.join(output_path, f'{text}.jpg'), merge)
        i += 1