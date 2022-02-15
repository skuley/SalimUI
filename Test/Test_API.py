from flask import Flask, request, jsonify
import json
import os
from datetime import datetime


config = {
    "DEBUG": True,
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    'JSON_AS_ASCII': False
}

app = Flask('Salim OCR Result')
app.config.from_mapping(config)

result = {}

@app.route('/ocr', methods=['POST'])
def get_ocr_result():
    global result
    if request.method == 'POST':
        data = request.data
        datas = json.loads(data)
        data_key_length = [len(data.keys()) for data in datas]
        selected_idx = 0
        if len(data_key_length) > 1:
            selected_idx = data_key_length.index(max(data_key_length))
        print(datas[selected_idx])
        barcode_dir = datas[selected_idx].get("barcode", 'unrecognized')
        result_file = f'../Image/ocr/{barcode_dir}/result.json'
        now = datetime.now()
        result = {'date_time': now.strftime("%m/%d/%Y, %H:%M:%S"),
                  'barcode': barcode_dir,
                  'label_id': datas[selected_idx]['label_id'],
                  'product_name': datas[selected_idx]['barcode_result'].get('subject', 'unrecognized'),
                  'weight': datas[selected_idx]['barcode_result']['weight'],
                  'cert_mark': datas[selected_idx]['detected_mark'],
                  'cert_result': datas[selected_idx]["producer_result"],
                  'rot_angle': datas[selected_idx]['rot_angle']}
        if os.path.isfile(result_file):
            ocr_result_lst = []
            with open(result_file, 'r', encoding='utf-8') as file:
                ocr_result_lst = json.load(file)
                new_ocr_result = result

            if result['label_id'] > ocr_result_lst[-1]['label_id']:
                ocr_result_lst.append(new_ocr_result)
                with open(result_file, 'w+', encoding='utf-8') as file:
                    ocr_result = json.dumps(ocr_result_lst)
                    # print(ocr_result)
                    file.write(ocr_result)

        else:
            with open(result_file, 'w', encoding='utf-8') as file:
                lst = []
                lst.append(result)
                ocr_result = json.dumps(lst)
                # print(ocr_result)
                file.write(ocr_result)

    return jsonify({"message":"successfully received ocr_result"})


@app.route('/print_ocr', methods=['GET'])
def print_ocr_result():
    global result
    return jsonify(result)


if __name__ == '__main__':
    app.run(host='0.0.0.0')